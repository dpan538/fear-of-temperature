"""Resume the fixed US queue only after an evidenced HTTP 429 cooldown.

The ordinary supervisor remains the single DuckDB writer and still stops on
access, transport and storage limits. This wrapper stops on any outcome other
than a recent 429 and caps retries of the same raw-text object.
"""
import argparse
import fcntl
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from acquire import HERE

STATE = HERE / "checkpoints" / "supervisor_state.json"
LOCK = HERE / "checkpoints" / "us_polite_resume.lock"
RAW = HERE / "raw" / "us_fr"


def parsed(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def recent_429(state):
    stopped_at = parsed(state["updated_at_utc"])
    matches = []
    for path in RAW.glob("*/*.txt.request.json"):
        meta = json.loads(path.read_text())
        if meta.get("status") != "failed" or meta.get("http_status") != 429:
            continue
        when = parsed(meta["retrieved_at_utc"])
        if timedelta(0) <= stopped_at - when <= timedelta(minutes=30):
            matches.append((when, path, meta))
    if not matches:
        return None
    when, path, meta = max(matches)
    attempts = path.with_name(path.name.replace(".request.json", ".attempts.jsonl"))
    prior = [json.loads(line) for line in attempts.read_text().splitlines()] if attempts.exists() else []
    same_429 = 1 + sum(row.get("http_status") == 429 for row in prior)
    return when, path, meta, same_429


def retry_eligible_at(when, meta, cooldown_seconds):
    eligible = when + timedelta(seconds=cooldown_seconds)
    retry_after = meta.get("response_headers", {}).get("Retry-After", "")
    if retry_after:
        try:
            if retry_after.isdigit():
                server_date = meta.get("response_headers", {}).get("Date", "")
                base = parsedate_to_datetime(server_date) if server_date else when
                mandated = base + timedelta(seconds=int(retry_after))
            else:
                mandated = parsedate_to_datetime(retry_after)
            eligible = max(eligible, mandated.astimezone(timezone.utc))
        except (TypeError, ValueError):
            raise RuntimeError(f"unparseable Retry-After on {meta['request_url']}: {retry_after!r}")
    return eligible


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cooldown-seconds", type=int, default=3600)
    parser.add_argument("--max-same-object-429", type=int, default=3)
    parser.add_argument("--max-restarts", type=int, default=100)
    parser.add_argument("--batch", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    with LOCK.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        restarts = 0
        while True:
            state = json.loads(STATE.read_text())
            status = state.get("status")
            if status != "blocked_access_or_no_progress":
                print(json.dumps({"action": "stop", "supervisor_status": status}), flush=True)
                return
            failure = recent_429(state)
            if not failure:
                print(json.dumps({"action": "stop", "reason": "no_recent_429", "supervisor_status": status}), flush=True)
                return
            when, path, meta, same_429 = failure
            if same_429 >= args.max_same_object_429 or restarts >= args.max_restarts:
                print(json.dumps({"action": "stop", "reason": "bounded_retry_limit",
                                  "same_object_429": same_429, "restarts": restarts,
                                  "request_url": meta["request_url"]}), flush=True)
                return
            eligible = retry_eligible_at(when, meta, args.cooldown_seconds)
            print(json.dumps({"action": "wait_then_resume", "request_url": meta["request_url"],
                              "same_object_429": same_429, "eligible_at_utc": eligible.isoformat(),
                              "restarts": restarts}), flush=True)
            if args.dry_run:
                return
            while True:
                remaining = (eligible - datetime.now(timezone.utc)).total_seconds()
                if remaining <= 0:
                    break
                time.sleep(min(60, remaining))
            # Recheck before launch in case an operator resumed the queue.
            current = json.loads(STATE.read_text())
            if current.get("status") != status or current.get("updated_at_utc") != state["updated_at_utc"]:
                print(json.dumps({"action": "stop", "reason": "supervisor_state_changed"}), flush=True)
                return
            command = [sys.executable, str(HERE / "run_us_remaining.py"), "--batch", str(args.batch)]
            print(json.dumps({"action": "resume", "command": command}), flush=True)
            code = subprocess.call(command, cwd=HERE.parents[2])
            restarts += 1
            if code:
                print(json.dumps({"action": "stop", "reason": "supervisor_nonzero", "exit_code": code}), flush=True)
                return


if __name__ == "__main__":
    main()
