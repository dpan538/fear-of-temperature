"""Bounded EU Item continuation after checkpointed transport failures only.

May monitor an already-running Item supervisor. Never restarts on a source HTTP
response, storage stop, stage error, or an unclassified failure.
"""
import argparse
import fcntl
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

from eu_acquire import HERE
from eu_item_supervisor import MIN_FREE_BYTES, STATE, storage_free
from eu_items import path_for, selected

LOCK = HERE / "manifests" / "transport_resume.lock"
LOG = HERE / "manifests" / "transport_resume.jsonl"
ITEM_LOCK = HERE / "manifests" / "item_supervisor.lock"
TRANSPORT_ERRORS = ("ProxyError:", "ReadTimeout:", "ConnectTimeout:",
                    "ConnectionError:", "SSLError:")


def stamp():
    return datetime.now(timezone.utc).isoformat()


def event(action, **fields):
    row = {"at_utc": stamp(), "action": action, **fields}
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(row, ensure_ascii=False), flush=True)


def state():
    try:
        return json.loads(STATE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def latest_failed_selected(month):
    failures = []
    for choice in selected(month):
        if not choice["item_uri"]:
            continue
        path = path_for(choice["item_uri"])
        checkpoint = path.with_suffix(".request.json")
        if not checkpoint.exists():
            continue
        try:
            meta = json.loads(checkpoint.read_text())
        except json.JSONDecodeError:
            continue
        if meta.get("status") == "failed":
            failures.append((meta.get("retrieved_at_utc", ""), path, meta))
    return max(failures, default=None)


def same_object_transport_failures(path, meta):
    history = path.with_suffix(".attempts.jsonl")
    prior = [json.loads(line) for line in history.read_text().splitlines()] if history.exists() else []
    return sum(row.get("http_status") == 0 and
               str(row.get("error", "")).startswith(TRANSPORT_ERRORS)
               for row in [*prior, meta])


def item_lock_free():
    with ITEM_LOCK.open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(handle, fcntl.LOCK_UN)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--end", default="2026-09")
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--incomplete-retries", type=int, default=2)
    parser.add_argument("--cooldown-seconds", type=int, default=600)
    parser.add_argument("--poll-seconds", type=int, default=20)
    parser.add_argument("--max-restarts", type=int, default=5)
    parser.add_argument("--max-same-object-failures", type=int, default=3)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    with LOCK.open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        restarts = 0
        while True:
            current = state()
            status = current.get("status")
            if status in {"running", "retrying_incomplete", "month_complete"}:
                if args.dry_run:
                    event("monitor_existing", supervisor_status=status,
                          month=current.get("month"))
                    return
                time.sleep(args.poll_seconds)
                continue
            if status != "blocked_access_or_incomplete":
                event("stop", supervisor_status=status or "unreadable_state")
                return
            if current.get("fetch_exit_code") != 0 or current.get("source_stop") is not True:
                event("stop", reason="not_a_checkpointed_source_stop", month=current.get("month"))
                return
            month = current["month"]
            failure = latest_failed_selected(month)
            if not failure:
                event("stop", reason="no_failed_selected_item", month=month)
                return
            when, path, meta = failure
            if meta.get("http_status") != 0 or not str(meta.get("error", "")).startswith(TRANSPORT_ERRORS):
                event("stop", reason="source_response_or_unclassified_failure", month=month,
                      http_status=meta.get("http_status"), error=meta.get("error"))
                return
            same = same_object_transport_failures(path, meta)
            if same >= args.max_same_object_failures or restarts >= args.max_restarts:
                event("stop", reason="bounded_retry_limit", month=month,
                      same_object_failures=same, restarts=restarts)
                return
            if storage_free() < MIN_FREE_BYTES:
                event("stop", reason="storage_floor", month=month, free_bytes=storage_free())
                return
            eligible = datetime.fromisoformat(when) + timedelta(seconds=args.cooldown_seconds)
            event("wait_then_resume", month=month, item_uri=meta.get("item_uri"),
                  same_object_failures=same, eligible_at_utc=eligible.isoformat(),
                  restarts=restarts)
            if args.dry_run:
                return
            while datetime.now(timezone.utc) < eligible:
                time.sleep(min(args.poll_seconds,
                               max(0.1, (eligible - datetime.now(timezone.utc)).total_seconds())))
            if state().get("updated_at_utc") != current.get("updated_at_utc"):
                event("stop", reason="supervisor_state_changed")
                return
            while not item_lock_free():
                time.sleep(args.poll_seconds)
                if state().get("updated_at_utc") != current.get("updated_at_utc"):
                    event("stop", reason="supervisor_state_changed_while_waiting_for_lock")
                    return
            command = [sys.executable, str(HERE / "eu_item_supervisor.py"),
                       "--start", month, "--end", args.end, "--delay", str(args.delay),
                       "--incomplete-retries", str(args.incomplete_retries)]
            event("resume", month=month, restarts=restarts, command=command)
            code = subprocess.call(command, cwd=HERE.parents[2])
            restarts += 1
            if code:
                event("stop", reason="supervisor_nonzero", exit_code=code, restarts=restarts)
                return


if __name__ == "__main__":
    main()
