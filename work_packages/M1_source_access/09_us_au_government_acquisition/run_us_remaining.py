"""Single-writer, bounded-block supervisor for the fixed US series.

It runs ordinary public requests at one-second spacing, stops on access/transport
limits or no progress, and checkpoints after each committed ingestion block.
"""
import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from acquire import DB, HERE, US_SOURCE, us_fallback_path, us_path, us_rows


PY = sys.executable
LOG = HERE / "checkpoints" / "supervisor.log"
STATE = HERE / "checkpoints" / "supervisor_state.json"
BATCHES = HERE / "checkpoints" / "batch_progress.jsonl"
MIN_FREE_BYTES = 15_000_000_000  # Keep room for the next raw block and DuckDB transaction.


def stamp():
    return datetime.now(timezone.utc).isoformat()


def save(state):
    STATE.write_text(json.dumps({**state, "updated_at_utc": stamp()}, indent=2) + "\n")


def run(command, label):
    stopped = False
    with LOG.open("a", encoding="utf-8") as log:
        log.write(f"\n[{stamp()}] START {label}: {' '.join(command)}\n")
        log.flush()
        env = {**os.environ, "MPLBACKEND": "Agg", "MPLCONFIGDIR": "/private/tmp/ft_mpl_cache"}
        process = subprocess.Popen(command, cwd=HERE.parents[2], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, bufsize=1)
        assert process.stdout is not None
        for line in process.stdout:
            log.write(line)
            log.flush()
            if "STOP: access/transport limit" in line:
                stopped = True
        code = process.wait()
        log.write(f"[{stamp()}] END {label}: code={code}; external_stop={stopped}\n")
        log.flush()
    if code:
        raise RuntimeError(f"{label} returned {code}; see {LOG}")
    return stopped


def counts(group):
    targets = [r for r in us_rows() if group[0] <= int(r["publication_date"][:4]) <= group[1]]
    # Fetch writes the digest only after checking the saved bytes. The final
    # audit rehashes every object; avoid rehashing the entire queue each block.
    downloaded = 0
    for row in targets:
        for path in (us_path(row), us_fallback_path(row)):
            checkpoint = path.with_suffix(path.suffix + ".request.json")
            if not (path.exists() and checkpoint.exists()):
                continue
            meta = json.loads(checkpoint.read_text())
            if meta.get("status") == "downloaded" and path.stat().st_size == meta.get("byte_count"):
                downloaded += 1
                break
    c = duckdb.connect(str(DB), read_only=True)
    ingested = c.execute("""SELECT count(DISTINCT d.document_id) FROM documents d
        JOIN document_content_objects x USING(document_id)
        JOIN content_versions v USING(content_object_id)
        WHERE d.source_id=? AND year(d.publication_date) BETWEEN ? AND ?""", [US_SOURCE, *group]).fetchone()[0]
    c.close()
    return len(targets), downloaded, ingested


def terminal_raw_text_failures(group):
    """Count parents whose ordinary raw-text endpoint is recorded as 404/410."""
    failures = 0
    for row in us_rows():
        if not (group[0] <= int(row["publication_date"][:4]) <= group[1]):
            continue
        path = us_path(row)
        checkpoint = path.with_suffix(path.suffix + ".request.json")
        if path.exists() or us_fallback_path(row).exists() or not checkpoint.exists():
            continue
        meta = json.loads(checkpoint.read_text())
        if meta.get("status") == "failed" and meta.get("http_status") in (404, 410):
            failures += 1
    return failures


def checkpoint_batch(group, target, before, after, before_db, after_db, stopped):
    if after < before or after_db < before_db or after_db > after or after > target:
        raise RuntimeError("batch counts violate target/download/version ordering")
    row = {"at_utc": stamp(), "year_scope": list(group), "target": target,
           "downloaded_before": before, "downloaded_after": after,
           "ingested_before": before_db, "ingested_after": after_db,
           "new_downloads": after - before, "new_ingested_parents": after_db - before_db,
           "free_bytes": shutil.disk_usage(HERE).free, "source_stop": stopped}
    with BATCHES.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def consolidate():
    for script, label in [("report.py", "final_report_data"),
                          ("audit.py", "final_integrity_audit"),
                          ("figure5.py", "final_figure5"),
                          ("build_report.py", "final_coverage_data_quality_report")]:
        run([PY, str(HERE / script)], label)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max-cycles", type=int, default=100)
    p.add_argument("--batch", type=int, default=500)
    a = p.parse_args()
    lock_path = HERE / "checkpoints" / "supervisor.lock"
    with lock_path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = {"status": "running", "started_at_utc": stamp(), "cycles": 0,
                 "series": US_SOURCE, "group_raw_text_exceptions": {}}
        save(state)
        try:
            for group in [(1994, 2002), (2003, 2026)]:
                while state["cycles"] < a.max_cycles:
                    free_bytes = shutil.disk_usage(HERE).free
                    if free_bytes < MIN_FREE_BYTES:
                        state.update({"status": "blocked_storage_floor", "free_bytes": free_bytes})
                        save(state)
                        return
                    target, before, before_db = counts(group)
                    state.update({"year_scope": list(group), "target": target, "downloaded": before, "ingested": before_db})
                    save(state)
                    if before == target and before_db == target:
                        break
                    terminal = terminal_raw_text_failures(group)
                    if before_db == before and before + terminal == target:
                        state["group_raw_text_exceptions"][f"{group[0]}-{group[1]}"] = terminal
                        save(state)
                        break
                    stopped = run([PY, str(HERE / "acquire.py"), "fetch-us", "--limit", str(a.batch),
                                   "--start-year", str(group[0]), "--end-year", str(group[1]), "--delay", "1.0"], "fetch_us") if before < target else False
                    run([PY, str(HERE / "acquire.py"), "ingest-us", "--limit", str(a.batch * 2)], "ingest_us")
                    target, after, after_db = counts(group)
                    checkpoint_batch(group, target, before, after, before_db, after_db, stopped)
                    state.update({"cycles": state["cycles"] + 1, "downloaded": after, "ingested": after_db})
                    save(state)
                    if stopped or (after <= before and after_db <= before_db):
                        terminal = terminal_raw_text_failures(group)
                        if not stopped and after_db == after and after + terminal == target:
                            state["group_raw_text_exceptions"][f"{group[0]}-{group[1]}"] = terminal
                            save(state)
                            break
                        state["status"] = "blocked_access_or_no_progress"
                        save(state)
                        if not stopped:
                            consolidate()
                        return
                if state["cycles"] >= a.max_cycles:
                    state["status"] = "cycle_limit_reached"
                    save(state)
                    return
            state["status"] = ("us_selected_series_processed_with_raw_text_exceptions"
                               if any(state["group_raw_text_exceptions"].values())
                               else "us_selected_series_complete")
            save(state)
            consolidate()
        except Exception as exc:
            state.update({"status": "error", "error": repr(exc)})
            save(state)
            raise


if __name__ == "__main__": main()
