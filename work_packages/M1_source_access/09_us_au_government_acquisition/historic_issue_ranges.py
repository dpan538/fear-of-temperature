"""Resume a large official GovInfo issue PDF using checked HTTP byte ranges."""
import argparse
import hashlib
import json
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from historic_index import RAW

CHUNK = 1_048_576
HEADERS = {"User-Agent": "FearTemperatureResearch/1.0 (public historical issue range acquisition)"}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def save(path, state):
    path.write_text(json.dumps({**state, "updated_at_utc": stamp()}, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--output-dir", type=Path, default=RAW / "issues")
    parser.add_argument("--chunk-mib", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.chunk_mib <= 16:
        raise ValueError("chunk-mib must be 1..16")
    request_chunk = args.chunk_mib * CHUNK
    url = f"https://www.govinfo.gov/content/pkg/FR-{args.date}/pdf/FR-{args.date}.pdf"
    path = args.output_dir.expanduser().resolve() / f"FR-{args.date}.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".ranges.part")
    ranges_path = path.with_suffix(".ranges.json")
    meta_path = path.with_suffix(".request.json")
    if path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        if meta.get("status") == "downloaded" and sha_file(path) == meta.get("sha256"):
            print(json.dumps({"date": args.date, "status": "verified_existing", "bytes": path.stat().st_size}), flush=True)
            return
    state = json.loads(ranges_path.read_text()) if ranges_path.exists() else {"request_url": url, "total_bytes": 0, "chunks": []}
    if state["request_url"] != url:
        raise RuntimeError("range checkpoint URL mismatch")
    offset = 0
    if part.exists():
        with part.open("rb") as handle:
            for chunk in state["chunks"]:
                if chunk["start"] != offset:
                    raise RuntimeError("noncontiguous range checkpoint")
                body = handle.read(chunk["end"] - chunk["start"] + 1)
                if len(body) != chunk["end"] - chunk["start"] + 1 or digest(body) != chunk["sha256"]:
                    raise RuntimeError("saved range hash mismatch")
                offset = chunk["end"] + 1
        if part.stat().st_size != offset:
            raise RuntimeError("partial file/checkpoint length mismatch")
    elif state["chunks"]:
        raise RuntimeError("range checkpoint exists without partial file")
    session = requests.Session()
    while not state["total_bytes"] or offset < state["total_bytes"]:
        if shutil.disk_usage(path.parent).free < 5_000_000_000:
            state["stop_reason"] = "less_than_5GB_free"
            save(ranges_path, state)
            break
        end = offset + request_chunk - 1
        if state["total_bytes"]:
            end = min(end, state["total_bytes"] - 1)
        try:
            response = session.get(url, headers={**HEADERS, "Range": f"bytes={offset}-{end}"}, timeout=(10, 45))
            with response:
                match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                if response.status_code != 206 or not match:
                    state["stop_reason"] = f"unexpected_http_{response.status_code}"
                    state["last_response_headers"] = {k: response.headers.get(k, "") for k in ("Date", "Retry-After", "Content-Range")}
                    save(ranges_path, state)
                    break
                actual_start, actual_end, total = map(int, match.groups())
                if actual_start != offset or actual_end != min(end, total - 1) or (state["total_bytes"] and total != state["total_bytes"]):
                    raise RuntimeError("unexpected Content-Range or changing source length")
                body = response.content
                if len(body) != actual_end - actual_start + 1:
                    raise RuntimeError("incomplete range body")
                if offset == 0 and not body.startswith(b"%PDF-"):
                    raise RuntimeError("range response lacks PDF signature")
                if not state["total_bytes"]:
                    state["total_bytes"] = total
                    state["first_response_headers"] = {k: response.headers.get(k, "") for k in ("Date", "ETag", "Last-Modified", "Content-Type", "Accept-Ranges")}
                with part.open("ab") as handle:
                    handle.write(body)
                    handle.flush()
                    os.fsync(handle.fileno())
                state["chunks"].append({"start": actual_start, "end": actual_end, "sha256": digest(body)})
                offset = actual_end + 1
                state.pop("stop_reason", None)
                save(ranges_path, state)
                print(json.dumps({"date": args.date, "bytes": offset, "total": total, "chunks": len(state["chunks"])}), flush=True)
        except requests.RequestException as exc:
            state["stop_reason"] = f"{type(exc).__name__}: {str(exc)[-400:]}"
            save(ranges_path, state)
            break
        time.sleep(args.delay)
    if not state["total_bytes"] or offset != state["total_bytes"]:
        print(json.dumps({"date": args.date, "status": "partial", "bytes": offset,
                          "total": state["total_bytes"], "stop_reason": state.get("stop_reason", "")}), flush=True)
        return
    if part.stat().st_size != state["total_bytes"]:
        raise RuntimeError("completed PDF size mismatch")
    file_sha = sha_file(part)
    part.replace(path)
    previous = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta = {"request_url": url, "http_status": 206, "retrieved_at_utc": stamp(),
            "mime_type": "application/pdf", "byte_count": state["total_bytes"],
            "sha256": file_sha, "raw_path": str(path.relative_to(RAW.parent)) if path.is_relative_to(RAW.parent) else str(path),
            "status": "downloaded", "acquisition_method": "verified_contiguous_http_byte_ranges",
            "range_checkpoint": str(ranges_path.relative_to(RAW.parent)) if ranges_path.is_relative_to(RAW.parent) else str(ranges_path),
            "prior_whole_stream_failure": previous.get("error", ""),
            "response_headers": state.get("first_response_headers", {})}
    save(meta_path, meta)
    print(json.dumps({"date": args.date, "status": "downloaded", "bytes": state["total_bytes"],
                      "sha256": file_sha}), flush=True)


if __name__ == "__main__":
    main()
