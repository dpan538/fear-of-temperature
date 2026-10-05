"""One-time documentation correction for the already applied cleaning rule."""
import json
from datetime import datetime, timezone

import duckdb

from acquire import CLEAN_VERSION, DB, HERE, clean_rule_json, sha


def main():
    old = json.dumps({"source": "US Federal Register raw text", "remove": "FR boilerplate/page markers",
                      "join": "line wraps and hyphenated word continuations", "min_chars": 12, "version": CLEAN_VERSION}, sort_keys=True)
    new = clean_rule_json()
    c = duckdb.connect(str(DB))
    row = c.execute("SELECT rule_sha256, rules_json FROM normalisation_rules WHERE rule_version=?", [CLEAN_VERSION]).fetchone()
    if not row or row[0] not in {sha(old.encode()), sha(new.encode())}:
        raise RuntimeError("Unexpected cleaning-rule state; no change made")
    before = c.execute("SELECT count(*) FROM text_segments WHERE representation_kind='cleaned' AND extraction_run_id IN (SELECT extraction_run_id FROM extraction_runs WHERE batch_id IN ('us_fr_epa_doe_rules_1994_v1','au_dcceew_2026_snapshot_v1'))").fetchone()[0]
    if row[0] == sha(old.encode()):
        c.execute("UPDATE normalisation_rules SET rule_sha256=?, rules_json=? WHERE rule_version=?", [sha(new.encode()), new, CLEAN_VERSION])
    after = c.execute("SELECT count(*) FROM text_segments WHERE representation_kind='cleaned' AND extraction_run_id IN (SELECT extraction_run_id FROM extraction_runs WHERE batch_id IN ('us_fr_epa_doe_rules_1994_v1','au_dcceew_2026_snapshot_v1'))").fetchone()[0]
    evidence = {"corrected_at_utc": datetime.now(timezone.utc).isoformat(), "rule_version": CLEAN_VERSION,
                "old_rule_sha256": row[0], "new_rule_sha256": sha(new.encode()),
                "before_cleaned_segment_count": before, "after_cleaned_segment_count": after,
                "change": "metadata description only; no body, content version or segment edit"}
    (HERE / "reports" / "rule_metadata_correction.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))
    c.close()


if __name__ == "__main__": main()
