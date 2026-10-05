"""Resume official WEMI batches only after their Retry-After gate expires."""
import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

from eu_acquire import HERE

STATE = HERE / "manifests" / "wemi_supervisor_state.json"
LOG = HERE / "manifests" / "wemi_supervisor.log"
PY = sys.executable


def stamp():
    return datetime.now(timezone.utc).isoformat()


def save(**fields):
    STATE.write_text(json.dumps({**fields, "updated_at_utc": stamp()}, indent=2) + "\n")


def first_pending(start, end):
    months = sorted(p.stem for p in (HERE / "manifests" / "months").glob("*.json")
                    if start <= p.stem <= end)
    for month in months:
        path = HERE / "manifests" / "wemi" / f"{month}.json"
        if not path.exists() or json.loads(path.read_text()).get("status") != "complete":
            return month
    return ""


def failed_checkpoint(month):
    pages = sorted((HERE / "raw" / "wemi_pages" / month[:4]).glob(f"{month}_batch_*.request.json"))
    for path in reversed(pages):
        meta = json.loads(path.read_text())
        if meta.get("status") != "downloaded":
            return path, meta
    return None, {}


def run(start, end, delay):
    command = [PY, str(HERE / "eu_wemi.py"), "--start", start, "--end", end,
               "--delay", str(delay)]
    with LOG.open("a", encoding="utf-8") as log:
        log.write(f"\n[{stamp()}] START {' '.join(command)}\n")
        log.flush()
        process = subprocess.Popen(command, cwd=HERE.parents[2], stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, bufsize=1)
        assert process.stdout is not None
        for line in process.stdout:
            log.write(line)
            log.flush()
        code = process.wait()
        log.write(f"[{stamp()}] END code={code}\n")
        log.flush()
    return code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2007-04")
    parser.add_argument("--end", default="2026-09")
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--max-retries", type=int, default=20)
    args = parser.parse_args()
    lock_path = HERE / "manifests" / "wemi_supervisor.lock"
    with lock_path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        retries = 0
        transient_retries = 0
        while True:
            month = first_pending(args.start, args.end)
            if not month:
                save(status="all_wemi_months_complete", start=args.start, end=args.end)
                return
            if shutil.disk_usage(HERE).free < 15_000_000_000:
                save(status="blocked_storage_floor", month=month,
                     free_bytes=shutil.disk_usage(HERE).free)
                return
            checkpoint, meta = failed_checkpoint(month)
            if meta:
                until_text = meta.get("retry_not_before_utc", "")
                status = meta.get("http_status")
                if status == 502 or (status == 0 and meta.get("error", "").startswith("ReadTimeout:")):
                    transient_retries += 1
                    if transient_retries > 3:
                        save(status="blocked_transient_after_retries", month=month,
                             retries=transient_retries-1, http_status=status,
                             error=meta.get("error", ""), evidence_path=str(checkpoint.relative_to(HERE)))
                        return
                    delay_seconds = (60 if status == 502 else 120) * 2**(transient_retries-1)
                    until = datetime.fromisoformat(meta["retrieved_at_utc"]) + timedelta(seconds=delay_seconds)
                    until_text = until.isoformat()
                    wait_status = "waiting_transient_retry"
                elif status in (429, 503) and until_text:
                    until = datetime.fromisoformat(until_text)
                    wait_status = "waiting_retry_after"
                else:
                    save(status="blocked_access_or_transport", month=month,
                         evidence_path=str(checkpoint.relative_to(HERE)),
                         http_status=status, error=meta.get("error", ""))
                    return
                remaining = (until - datetime.now(timezone.utc)).total_seconds()
                if remaining > 0:
                    save(status=wait_status, month=month,
                         retry_not_before_utc=until_text,
                         evidence_path=str(checkpoint.relative_to(HERE)))
                    while remaining > 0:
                        time.sleep(min(30, remaining))
                        remaining = (until - datetime.now(timezone.utc)).total_seconds()
                if status in (429, 503):
                    retries += 1
                    if retries > args.max_retries:
                        save(status="retry_limit_reached", month=month, retries=retries)
                        return
            else:
                retries = 0
                transient_retries = 0
            save(status="running", month=month, retries=retries)
            code = run(month, args.end, args.delay)
            if code:
                save(status="error", month=month, exit_code=code)
                return
            after = first_pending(args.start, args.end)
            if after == month:
                _, new_meta = failed_checkpoint(month)
                if not new_meta or new_meta.get("retrieved_at_utc") == meta.get("retrieved_at_utc"):
                    save(status="no_progress", month=month)
                    return
            if after != month:
                retries = 0
                transient_retries = 0


if __name__ == "__main__":
    main()
