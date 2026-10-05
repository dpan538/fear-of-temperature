"""Resume EU Item acquisition month by month, staging only verified bytes.

The WEMI harvester may run independently. This process alone owns the Item
download and EU stage writer lock; it never opens the US/AU database.
"""
import argparse
import fcntl
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

from eu_acquire import HERE
from eu_items import MIN_FREE_BYTES, path_for, selected

PY = sys.executable
STATE = HERE / "manifests" / "item_supervisor_state.json"
LOG = HERE / "manifests" / "item_supervisor.log"


def stamp():
    return datetime.now(timezone.utc).isoformat()


def save(**fields):
    STATE.write_text(json.dumps({**fields, "updated_at_utc": stamp()}, indent=2) + "\n")


def run(script, month, extra):
    command = [PY, str(HERE / script), "--start", month, "--end", month, *extra]
    stopped = False
    with LOG.open("a", encoding="utf-8") as log:
        log.write(f"\n[{stamp()}] START {' '.join(command)}\n")
        log.flush()
        process = subprocess.Popen(command, cwd=HERE.parents[2], stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, bufsize=1)
        assert process.stdout is not None
        for line in process.stdout:
            log.write(line)
            log.flush()
            if "STOP: official Item access limit or transport failure" in line:
                stopped = True
        code = process.wait()
        log.write(f"[{stamp()}] END code={code}; source_stop={stopped}\n")
        log.flush()
    return code, stopped


def counts(month):
    choices = [r for r in selected(month) if r["item_uri"]]
    downloaded = 0
    for row in choices:
        path = path_for(row["item_uri"])
        meta_path = path.with_suffix(".request.json")
        if path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text())
            if meta.get("status") == "downloaded" and path.stat().st_size == meta.get("byte_count"):
                downloaded += 1
    return len(choices), downloaded


def storage_free():
    external = HERE / "raw" / "items_external"
    volumes = [shutil.disk_usage(HERE).free]
    if external.is_symlink():
        try:
            volumes.append(shutil.disk_usage(external).free)
        except FileNotFoundError:
            return 0
    return min(volumes)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="1989-01")
    parser.add_argument("--end", default="2026-09")
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--incomplete-retries", type=int, default=2)
    args = parser.parse_args()
    lock_path = HERE / "manifests" / "item_supervisor.lock"
    with lock_path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        months = sorted(p.stem for p in (HERE / "manifests" / "months").glob("*.json")
                        if args.start <= p.stem <= args.end)
        for month in months:
            wemi = HERE / "manifests" / "wemi" / f"{month}.json"
            if not wemi.exists() or json.loads(wemi.read_text()).get("status") != "complete":
                save(status="waiting_for_wemi", next_month=month)
                return
            if storage_free() < MIN_FREE_BYTES:
                save(status="blocked_storage_floor", next_month=month,
                     free_bytes=storage_free())
                return
            for attempt in range(args.incomplete_retries + 1):
                target, before = counts(month)
                save(status="running", month=month, target=target, downloaded=before,
                     incomplete_attempt=attempt)
                if before < target:
                    code, stopped = run("eu_items.py", month, ["--limit", str(target), "--delay", str(args.delay)])
                else:
                    code, stopped = 0, False
                stage_code, _ = run("eu_stage.py", month, [])
                target, after = counts(month)
                if stage_code:
                    save(status="stage_error", month=month, target=target, downloaded=after,
                         error=f"eu_stage.py returned {stage_code}")
                    return
                if not code and not stopped and after == target:
                    break
                if (code or stopped or attempt >= args.incomplete_retries
                        or storage_free() < MIN_FREE_BYTES):
                    status = "blocked_storage_floor" if storage_free() < MIN_FREE_BYTES else "blocked_access_or_incomplete"
                    save(status=status, month=month, target=target, downloaded=after,
                         fetch_exit_code=code, source_stop=stopped,
                         free_bytes=storage_free())
                    return
                save(status="retrying_incomplete", month=month, target=target,
                     downloaded=after, next_attempt=attempt + 1)
                time.sleep(30 * (attempt + 1))
            save(status="month_complete", month=month, target=target, downloaded=after)
        save(status="available_wemi_months_complete", last_month=months[-1] if months else "")


if __name__ == "__main__":
    main()
