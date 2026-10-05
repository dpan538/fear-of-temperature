"""Sequential, resumable official issue scan queue for pre-1994 rule review."""
import argparse
import csv
import fcntl
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from historic_index import RAW

HERE = Path(__file__).resolve().parent
STATE = HERE / "checkpoints" / "historic_issue_queue_state.json"
LOG = HERE / "checkpoints" / "historic_issue_queue.log"


def stamp():
    return datetime.now(timezone.utc).isoformat()


def save(**data):
    STATE.write_text(json.dumps({**data, "updated_at_utc": stamp()}, indent=2) + "\n")


def sha_file(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def verified(path):
    meta_path = path.with_suffix(".request.json")
    if not path.exists() or not meta_path.exists():
        return False
    meta = json.loads(meta_path.read_text())
    return (meta.get("status") == "downloaded" and path.stat().st_size == meta.get("byte_count")
            and sha_file(path) == meta.get("sha256"))


def dates():
    days = set()
    for year in range(1988, 1994):
        with (RAW / f"{year}_parent_agency_resolved_locators.csv").open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row["link_state"] == "resolved_to_issue_page":
                    days.add(row["issue_date_from_official_link"])
    return sorted(days)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-issues", type=int, default=0)
    parser.add_argument("--chunk-mib", type=int, default=1)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--free-floor-gb", type=float, default=10.0)
    args = parser.parse_args()
    output = args.output_dir.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    queue = dates()
    lock_path = HERE / "checkpoints" / "historic_issue_queue.lock"
    with lock_path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        complete = 0
        skipped_local = 0
        failed = 0
        consecutive_failures = 0
        attempted = 0
        for day in queue:
            if verified(RAW / "issues" / f"FR-{day}.pdf"):
                skipped_local += 1
                continue
            target = output / f"FR-{day}.pdf"
            if verified(target):
                complete += 1
                continue
            if args.max_issues and attempted >= args.max_issues:
                save(status="bounded_limit_reached", target=len(queue), completed_external=complete,
                     verified_local=skipped_local, attempted_this_run=attempted, failed_this_run=failed,
                     output_dir=str(output))
                return
            free = shutil.disk_usage(output).free
            if free < args.free_floor_gb * 1_000_000_000:
                save(status="blocked_storage_floor", next_issue=day, target=len(queue),
                     completed_external=complete, verified_local=skipped_local,
                     attempted_this_run=attempted, failed_this_run=failed,
                     free_bytes=free, output_dir=str(output))
                return
            save(status="running", current_issue=day, target=len(queue),
                 completed_external=complete, verified_local=skipped_local,
                 attempted_this_run=attempted, failed_this_run=failed,
                 free_bytes=free, output_dir=str(output))
            command = [sys.executable, str(HERE / "historic_issue_ranges.py"), "--date", day,
                       "--output-dir", str(output), "--chunk-mib", str(args.chunk_mib)]
            with LOG.open("a", encoding="utf-8") as log:
                log.write(f"\n[{stamp()}] START {day}\n")
                log.flush()
                code = subprocess.run(command, cwd=HERE.parents[2], stdout=log,
                                      stderr=subprocess.STDOUT, check=False).returncode
                log.write(f"[{stamp()}] END {day} code={code}\n")
                log.flush()
            attempted += 1
            if code == 0 and verified(target):
                complete += 1
                consecutive_failures = 0
                print(json.dumps({"date": day, "status": "verified", "bytes": target.stat().st_size}), flush=True)
            else:
                failed += 1
                consecutive_failures += 1
                range_path = target.with_suffix(".ranges.json")
                detail = json.loads(range_path.read_text()) if range_path.exists() else {}
                reason = detail.get("stop_reason", f"subprocess_exit_{code}")
                print(json.dumps({"date": day, "status": "partial_or_failed", "reason": reason}), flush=True)
                if ("unexpected_http_403" in reason or "unexpected_http_429" in reason
                        or "unexpected_http_503" in reason or consecutive_failures >= 3):
                    save(status="blocked_source_or_repeated_failure", current_issue=day,
                         reason=reason, target=len(queue), completed_external=complete,
                         verified_local=skipped_local, attempted_this_run=attempted,
                         failed_this_run=failed, output_dir=str(output))
                    return
            time.sleep(args.delay)
        save(status="candidate_issue_dates_processed", target=len(queue), completed_external=complete,
             verified_local=skipped_local, attempted_this_run=attempted,
             failed_this_run=failed, output_dir=str(output))


if __name__ == "__main__":
    main()
