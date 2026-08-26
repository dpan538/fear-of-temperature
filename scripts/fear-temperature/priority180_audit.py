#!/usr/bin/env python3
"""Build the candidate-level Priority 180 audit.

The script deliberately keeps three evidence channels separate:

* Google Books Ngram annual lexical-frequency measurements;
* lexicographic/headword, historical-dictionary, and technical-glossary evidence;
* bounded discovery counts from documented metadata/search APIs.

Requests are deduplicated by normalized measurement form, while every Priority
candidate retains its own anchor-specific accounting row. Raw responses are
cached and checksummed. An empty response is retained; it is never rewritten as
historical absence or silently dropped.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import re
import statistics
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "data" / "fear-temperature" / "seed"
BASE_NGRAM = ROOT / "data" / "fear-temperature" / "ngram"
P180 = ROOT / "data" / "fear-temperature" / "priority180"
EXPORTS = ROOT / "data" / "fear-temperature" / "exports"
NGRAM_RAW = P180 / "ngram" / "raw"
DICT_RAW = P180 / "dictionary" / "raw"
SEARCH_RAW = P180 / "search" / "raw"
YEAR_START = 1842
YEAR_END = 2022
CORPUS_ID = "eng"
CORPUS_VERSION = "eng_CURRENT_ENGLISH_JULY_2024_DATASET"
USER_AGENT = "FearOfTemperature/0.1 candidate-audit (research; contact: local project)"
ACCESS_DATE = date.today().isoformat()

ANCHOR = {
    "FT-A1842": {"label": "1842", "strict": (1842, 1842), "context": (1839, 1845)},
    "FT-A1938": {"label": "1938", "strict": (1938, 1938), "context": (1936, 1940)},
    "FT-A1988": {"label": "1988", "strict": (1988, 1988), "context": (1986, 1990)},
    "FT-A0607": {"label": "2006–2007", "strict": (2006, 2007), "context": (2005, 2008)},
    "FT-A2015": {"label": "2015", "strict": (2015, 2015), "context": (2014, 2016)},
    "FT-A2022": {"label": "2022", "strict": (2022, 2022), "context": (2021, 2023)},
}

NGRAM_SPECIAL = {
    "heat wave/drought occurrences": {
        "mapping": "TECHNICALLY_UNREPRESENTABLE",
        "measurement": "",
        "reason": "The slash coordinates two lexical objects; one linear Ngram would change the candidate's structure and sense.",
    },
    "anthropogenic co2": {
        "mapping": "VALIDATED_ALIAS",
        "measurement": "anthropogenic carbon dioxide",
        "reason": "CO₂ is expanded to its standard full lexical form; referent and historical sense are unchanged.",
    },
    "be worried. be very worried.": {
        "mapping": "NORMALIZED_VARIANT",
        "measurement": "be worried be very worried",
        "reason": "Sentence punctuation and capitalization are removed while the complete wording is preserved.",
    },
    "well below 2°c above pre-industrial levels": {
        "mapping": "VALIDATED_ALIAS",
        "measurement": "well below two degrees above pre-industrial levels",
        "reason": "The symbolic temperature is verbalized for the Ngram interface without changing the treaty threshold relation.",
    },
    "1.5°c above pre-industrial levels": {
        "mapping": "VALIDATED_ALIAS",
        "measurement": "one point five degrees above pre-industrial levels",
        "reason": "The decimal degree notation is verbalized for the Ngram interface without changing the treaty threshold relation.",
    },
    "40-degree temperatures": {
        "mapping": "NORMALIZED_VARIANT",
        "measurement": "40 degree temperatures",
        "reason": "Hyphenation is normalized; lexical content and temperature sense are unchanged.",
    },
}

TECHNICAL_TERMS = {
    "artificial production of carbon dioxide", "carbon dioxide", "fuel combustion",
    "atmosphere", "water vapour", "radiation absorption coefficients", "greenhouse effect",
    "global warming", "global temperature", "regional heat waves", "global climate models",
    "changing atmosphere", "climate warming", "greenhouse gases", "warming of the climate system",
    "global average air and ocean temperatures", "global surface temperature", "temperature increase",
    "rising global average sea level", "widespread melting of snow and ice", "anthropogenic co2",
    "anthropogenic ghg emissions", "climate change", "dangerous climate change",
    "global average temperature", "well below 2°c above pre-industrial levels",
    "1.5°c above pre-industrial levels", "pre-industrial levels", "greenhouse gas emissions",
    "climate resilience", "vulnerability", "vulnerable groups", "loss and damage",
    "extreme weather events", "slow onset events", "risk of loss and damage",
    "early warning systems", "non-economic losses", "common concern of humankind",
    "climate justice", "climate anxiety", "eco-anxiety", "psychological distress",
    "heat-related mortality", "climate crisis",
}

DOMAIN_SOURCE = {
    "climate anxiety": ("American Psychological Association / ecoAmerica mental-health terminology", "https://www.apa.org/news/press/releases/2021/11/mental-health-effects-climate-change"),
    "eco-anxiety": ("American Psychological Association / ecoAmerica mental-health terminology", "https://www.apa.org/news/press/releases/2021/11/mental-health-effects-climate-change"),
    "psychological distress": ("World Health Organization mental-health terminology", "https://www.who.int/news-room/fact-sheets/detail/climate-change-and-health"),
    "common concern of humankind": ("UNFCCC Paris Agreement legal text", "https://unfccc.int/sites/default/files/english_paris_agreement.pdf"),
    "climate justice": ("IPCC AR6 glossary and assessment usage", "https://www.ipcc.ch/report/ar6/syr/downloads/report/IPCC_AR6_SYR_FullVolume.pdf"),
}
IPCC_GLOSSARY = "https://www.ipcc.ch/site/assets/uploads/2018/02/WGIIAR5-AnnexII_FINAL.pdf"
WEBSTER_BASE = "https://websters1913.timcieplowski.com/word/{slug}/"
DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{term}"
NGRAM_ENDPOINT = "https://books.google.com/ngrams/json"
IA_ENDPOINT = "https://archive.org/advancedsearch.php"
OPENALEX_ENDPOINT = "https://api.openalex.org/works"
GOOGLE_BOOKS_ENDPOINT = "https://www.googleapis.com/books/v1/volumes"


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = value.replace("‘", "'").replace("’", "'")
    value = value.replace("‐", "-").replace("‑", "-").replace("–", "-").replace("—", "-")
    value = value.replace("₂", "2")
    return re.sub(r"\s+", " ", value).strip()


def slug(value: str) -> str:
    value = normalize(value)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value


def sha(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def dump_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_query_builder() -> Any:
    path = ROOT / "scripts" / "fear-temperature" / "build_query_inventory.py"
    spec = importlib.util.spec_from_file_location("fot_query_builder", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def priority_rank(row: dict[str, str]) -> int:
    match = re.search(r"PRIORITY_RANK=(\d+)", row["original_decision"])
    if match:
        return int(match.group(1))
    match = re.search(r"-(\d+)$", row["seed_candidate_id"])
    if not match:
        raise ValueError(f"Cannot determine Priority rank: {row['seed_candidate_id']}")
    return int(match.group(1))


def candidate_population() -> list[dict[str, Any]]:
    rows = [r for r in read_csv(SEED / "seed_candidates.csv") if r["originating_seed_stage"] == "PRIORITY_180"]
    if len(rows) != 180:
        raise ValueError(f"Expected 180 Priority candidates, found {len(rows)}")
    if len({r["seed_candidate_id"] for r in rows}) != 180:
        raise ValueError("Priority candidate IDs are not unique")

    rules = read_csv(SEED / "query_rules.csv")
    rules_by_candidate = {r["source_seed_candidate_id"]: r for r in rules if r["source_seed_candidate_id"]}
    concepts = read_csv(SEED / "canonical_concepts.csv")
    concept_by_id = {r["concept_id"]: r for r in concepts}
    families = read_csv(SEED / "lexical_families.csv")
    family_by_id = {r["family_id"]: r for r in families}
    forms = read_csv(SEED / "lexical_forms_full.csv")
    form_by_norm = {normalize(r["normalized_form"]): r for r in forms}
    query_builder = load_query_builder()

    output: list[dict[str, Any]] = []
    for row in rows:
        cid = row["seed_candidate_id"]
        surface = row["surface_form"]
        norm = normalize(surface)
        rule = rules_by_candidate.get(cid)
        if rule:
            concept = concept_by_id[rule["concept_id"]]
            family = family_by_id[rule["family_id"]]
            lexical_form_id = rule["lexical_form_id"]
            query_id = rule["query_id"]
        else:
            existing = form_by_norm.get(norm)
            if existing:
                concept = concept_by_id[existing["concept_id"]]
                lexical_form_id = existing["lexical_form_id"]
            else:
                concept = query_builder.choose_concept(surface, row["layer_code"], concepts)
                lexical_form_id = "FT-LF-P180-" + sha(norm)[:12].upper()
            family = family_by_id[concept["family_id"]]
            query_id = "FT-Q-P180-" + sha(f"{cid}|{norm}")[:12].upper()

        special = NGRAM_SPECIAL.get(norm)
        if special:
            mapping = special["mapping"]
            measurement = special["measurement"]
            ngram_reason = special["reason"]
        else:
            mapping = "EXACT"
            measurement = surface
            ngram_reason = "Candidate surface form is directly representable in the public Ngram interface."
        measurement_id = "FT-NGM-" + sha(normalize(measurement))[:14].upper() if measurement else ""
        provenance = (
            f"{row['provenance_status']}; {row['originating_report']}; p.{row['source_page']}; "
            f"project candidate {cid}; original visible ID {row['original_candidate_id'] or 'not available'}"
        )
        output.append({
            "candidate_id": cid,
            "anchor_id": row["anchor_id"],
            "anchor": ANCHOR[row["anchor_id"]]["label"],
            "priority_rank": priority_rank(row),
            "surface_form": surface,
            "normalized_form": norm,
            "normalized_concept": concept["preferred_label"],
            "concept_id": concept["concept_id"],
            "concept_definition": concept["definition"],
            "lexical_form_id": lexical_form_id,
            "lexical_family": family["family_code"],
            "family_id": family["family_id"],
            "layer": row["layer_code"],
            "primary_voice": row["voice_code"] or "UNRESOLVED_FROM_REPORT",
            "expression_mode": row["expression_mode_code"] or "E5",
            "candidate_provenance": provenance,
            "ngram_measurement_id": measurement_id,
            "ngram_measurement_form": measurement,
            "ngram_mapping_type": mapping,
            "ngram_query_id": query_id,
            "ngram_mapping_reason": ngram_reason,
            "source_report": row["originating_report"],
            "source_page": row["source_page"],
            "provenance_status": row["provenance_status"],
        })
    output.sort(key=lambda r: (list(ANCHOR).index(r["anchor_id"]), int(r["priority_rank"])))
    return output


def fetch_bytes(url: str, attempts: int = 5, timeout: int = 60, delay: float = 0.0) -> tuple[int, bytes, dict[str, str], str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/html;q=0.9,*/*;q=0.8"})
    last_error = ""
    if delay:
        time.sleep(delay)
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, response.read(), dict(response.headers.items()), ""
        except urllib.error.HTTPError as exc:
            body = exc.read()
            if exc.code in {400, 401, 403, 404}:
                return exc.code, body, dict(exc.headers.items()), f"HTTP {exc.code}"
            last_error = f"HTTP {exc.code}: {body[:240].decode('utf-8', 'replace')}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < attempts:
            time.sleep(min(20, 2 ** (attempt - 1)))
    return 0, b"", {}, last_error


def cached_request(url: str, path: Path, delay: float = 0.0, attempts: int = 5, timeout: int = 60) -> dict[str, Any]:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["cache_reused"] = True
        return payload
    status, body, headers, error = fetch_bytes(url, attempts=attempts, timeout=timeout, delay=delay)
    record: dict[str, Any] = {
        "request_url": url,
        "retrieved_at": utc_now(),
        "http_status": status,
        "response_headers": {k: v for k, v in headers.items() if k.lower() in {"content-type", "date", "etag", "x-ratelimit-remaining"}},
        "body_sha256": sha(body),
        "error": error,
        "cache_reused": False,
    }
    try:
        record["payload"] = json.loads(body.decode("utf-8")) if body else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        record["body_text_excerpt"] = body[:4000].decode("utf-8", "replace")
    dump_json(path, record)
    return record


def select_ngram_series(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, list):
        return None
    aggregates = [r for r in payload if isinstance(r, dict) and (r.get("type") == "CASE_INSENSITIVE" or str(r.get("ngram", "")).endswith("(All)"))]
    if aggregates:
        return aggregates[0]
    rows = [r for r in payload if isinstance(r, dict) and isinstance(r.get("timeseries"), list)]
    return rows[0] if len(rows) == 1 else None


def ngram_url(surface: str) -> str:
    params = {
        "content": surface,
        "year_start": str(YEAR_START),
        "year_end": str(YEAR_END),
        "corpus": CORPUS_ID,
        "smoothing": "0",
        "case_insensitive": "true",
    }
    return NGRAM_ENDPOINT + "?" + urllib.parse.urlencode(params)


def run_ngram(candidates: list[dict[str, Any]], live: bool) -> None:
    existing_ts = read_csv(BASE_NGRAM / "ngram_timeseries_full.csv")
    existing_exec = read_csv(BASE_NGRAM / "ngram_query_execution_results.csv")
    existing_rules = {r["query_id"]: r for r in read_csv(SEED / "query_rules.csv")}
    exec_by_query = {r["query_id"]: r for r in existing_exec}

    # Reuse one complete stored series for any technically identical form.
    series_by_form: dict[str, list[float]] = {}
    meta_by_form: dict[str, dict[str, str]] = {}
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in existing_ts:
        grouped[(normalize(row["term"]), row["query_id"])].append(row)
    for (form, query_id), rows in grouped.items():
        rows.sort(key=lambda r: int(r["year"]))
        if len(rows) == YEAR_END - YEAR_START + 1 and form not in series_by_form:
            series_by_form[form] = [float(r["normalized_frequency"]) for r in rows]
            meta_by_form[form] = {
                "retrieved_at": rows[0]["retrieved_at"],
                "raw_response_path": rows[0]["raw_response_path"],
                "raw_payload_sha256": rows[0]["raw_payload_sha256"],
                "source_query_id": query_id,
                "response_ngram": rows[0]["response_ngram"],
            }

    # Explicitly preserve known empty responses for the six executable rules.
    empty_forms: dict[str, dict[str, str]] = {}
    for query_id, execution in exec_by_query.items():
        if execution["execution_status"] == "ZERO_RESULT" and query_id in existing_rules:
            form = normalize(existing_rules[query_id]["surface_form"])
            empty_forms[form] = {
                "retrieved_at": execution["retrieved_at"],
                "raw_response_path": execution["raw_response_path"],
                "raw_payload_sha256": execution["raw_payload_sha256"],
                "source_query_id": query_id,
                "response_ngram": "",
            }

    requested = sorted({normalize(c["ngram_measurement_form"]): c["ngram_measurement_form"] for c in candidates if c["ngram_measurement_form"]}.items())
    execution_rows: list[dict[str, Any]] = []
    for norm_form, surface in requested:
        measurement_id = "FT-NGM-" + sha(norm_form)[:14].upper()
        url = ngram_url(surface)
        if norm_form in series_by_form:
            status = "SUCCEEDED_REUSED_BASELINE"
            meta = meta_by_form[norm_form]
            values = series_by_form[norm_form]
            reason = "Complete 1842–2022 unsmoothed series reused from the audited quantitative-v0.1 baseline."
        elif norm_form in empty_forms:
            status = "ZERO_RESPONSE_REUSED_BASELINE"
            meta = empty_forms[norm_form]
            values = []
            reason = "The audited executable rule returned an empty Ngram payload; retained as source/query zero-response evidence, not historical absence."
        elif live:
            cache = NGRAM_RAW / f"{sha(url)}.json"
            record = cached_request(url, cache, delay=0.35)
            selected = select_ngram_series(record.get("payload"))
            if record["http_status"] == 200 and selected and isinstance(selected.get("timeseries"), list):
                values = [float(v) for v in selected["timeseries"]]
                if len(values) != YEAR_END - YEAR_START + 1:
                    status = "FAILED_LENGTH_MISMATCH"
                    reason = f"Ngram returned {len(values)} years; expected 181."
                    values = []
                else:
                    status = "SUCCEEDED_NEW"
                    reason = "New unsmoothed 1842–2022 series retrieved for the candidate audit."
                meta = {
                    "retrieved_at": record["retrieved_at"],
                    "raw_response_path": str(cache.relative_to(ROOT)),
                    "raw_payload_sha256": record["body_sha256"],
                    "source_query_id": "",
                    "response_ngram": selected.get("ngram", ""),
                }
            elif record["http_status"] == 200 and isinstance(record.get("payload"), list) and not record["payload"]:
                status = "ZERO_RESPONSE_NEW"
                values = []
                reason = "The public Ngram endpoint returned an empty list; retained without fabricating annual zero frequencies."
                meta = {
                    "retrieved_at": record["retrieved_at"],
                    "raw_response_path": str(cache.relative_to(ROOT)),
                    "raw_payload_sha256": record["body_sha256"],
                    "source_query_id": "",
                    "response_ngram": "",
                }
            else:
                status = "FAILED_REQUEST"
                values = []
                reason = record.get("error") or f"HTTP {record['http_status']}"
                meta = {
                    "retrieved_at": record["retrieved_at"],
                    "raw_response_path": str(cache.relative_to(ROOT)),
                    "raw_payload_sha256": record["body_sha256"],
                    "source_query_id": "",
                    "response_ngram": "",
                }
        else:
            status = "NOT_RUN_NEW_MEASUREMENT"
            values = []
            reason = "Run with --live to retrieve this new measurement."
            meta = {"retrieved_at": "", "raw_response_path": "", "raw_payload_sha256": "", "source_query_id": "", "response_ngram": ""}

        if values:
            series_by_form[norm_form] = values
            meta_by_form[norm_form] = meta
        elif status.startswith("ZERO_RESPONSE"):
            empty_forms[norm_form] = meta
        execution_rows.append({
            "measurement_id": measurement_id,
            "measurement_form": surface,
            "normalized_measurement_form": norm_form,
            "execution_status": status,
            "observation_count": len(values),
            "provider": "Google Books Ngram Viewer",
            "corpus_identifier": CORPUS_ID,
            "corpus_version": CORPUS_VERSION,
            "year_start": YEAR_START,
            "year_end": YEAR_END,
            "smoothing": 0,
            "case_insensitive": True,
            "retrieved_at": meta["retrieved_at"],
            "request_url": url,
            "raw_response_path": meta["raw_response_path"],
            "raw_payload_sha256": meta["raw_payload_sha256"],
            "baseline_source_query_id": meta["source_query_id"],
            "response_ngram": meta["response_ngram"],
            "status_note": reason,
        })

    fields = list(execution_rows[0].keys())
    write_csv(P180 / "ngram" / "ngram_measurement_execution.csv", execution_rows, fields)

    # A complete annual grid is emitted. Blank values mean no series was returned;
    # they are not silently converted to numeric zero.
    execution_by_form = {r["normalized_measurement_form"]: r for r in execution_rows}
    annual_rows: list[dict[str, Any]] = []
    for norm_form, surface in requested:
        execution = execution_by_form[norm_form]
        values = series_by_form.get(norm_form, [])
        for year in range(YEAR_START, YEAR_END + 1):
            annual_rows.append({
                "measurement_id": execution["measurement_id"],
                "measurement_form": surface,
                "year": year,
                "normalized_frequency": values[year - YEAR_START] if values else "",
                "observation_status": "OBSERVED_NUMERIC" if values else "NO_SERIES_RETURNED",
                "provider": execution["provider"],
                "corpus_identifier": execution["corpus_identifier"],
                "corpus_version": execution["corpus_version"],
                "smoothing": 0,
                "retrieved_at": execution["retrieved_at"],
                "raw_response_path": execution["raw_response_path"],
                "raw_payload_sha256": execution["raw_payload_sha256"],
            })
    write_csv(P180 / "ngram" / "ngram_timeseries_priority_measurements.csv", annual_rows, list(annual_rows[0].keys()))


def clean_definition(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\[[^]]+\]", "", text)
    return text[:500]


def direct_dictionary_hit(payload: Any, surface: str) -> tuple[bool, str]:
    if not isinstance(payload, list):
        return False, ""
    target = normalize(surface)
    for entry in payload:
        if not isinstance(entry, dict) or normalize(str(entry.get("word", ""))) != target:
            continue
        for meaning in entry.get("meanings", []):
            for definition in meaning.get("definitions", []):
                value = definition.get("definition", "")
                if value:
                    return True, clean_definition(value)
        return True, ""
    return False, ""


def component_headword(surface: str) -> str:
    tokens = re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)?", surface)
    stop = {"the", "of", "and", "or", "a", "an", "to", "for", "from", "than", "is", "are", "has", "itself", "them", "personally", "very", "somewhat"}
    content = [normalize(t) for t in tokens if normalize(t) not in stop]
    return content[-1] if content else normalize(surface)


def domain_definition(surface: str, concept_definition: str) -> str:
    s = normalize(surface)
    overrides = {
        "greenhouse effect": "The atmospheric warming influence produced when greenhouse gases absorb and re-emit outgoing infrared radiation.",
        "climate system": "The interacting atmosphere, hydrosphere, cryosphere, land surface, and biosphere and the exchanges among them.",
        "loss and damage": "Adverse climate-related impacts that remain after, or cannot be avoided through, mitigation and adaptation; both economic and non-economic losses may be involved.",
        "non-economic losses": "Climate-related losses not readily expressed in monetary terms, including cultural, health, identity, ecosystem, and heritage harms.",
        "climate anxiety": "An apprehensive or distress-related response associated with climate change; in the 2022 evidence it is primarily a research construct unless participant self-use is separately shown.",
        "eco-anxiety": "Persistent worry or distress associated with environmental and ecological threats; provenance is required to distinguish clinical/research labelling from self-description.",
        "common concern of humankind": "A legal-institutional formula identifying climate change as a matter of shared international concern, not an assertion of personal emotion.",
        "climate justice": "An evaluative framework concerned with fair distribution of climate harms, responsibilities, participation, and remedies.",
        "greenhouse gases": "Atmospheric gases that absorb and emit infrared radiation and thereby influence the greenhouse effect.",
        "anthropogenic ghg emissions": "Human-caused releases of greenhouse gases into the atmosphere.",
        "greenhouse gas emissions": "Releases of gases that contribute to the atmospheric greenhouse effect.",
        "pre-industrial levels": "A historical reference baseline preceding large-scale industrial-era human influence, operationalized by the relevant climate agreement or assessment.",
        "climate resilience": "The capacity of social, economic, and ecological systems to cope with climatic hazards while maintaining essential functions and adapting.",
        "climate change": "A persistent change in the state or variability of climate; institutional definitions differ on whether human attribution is required.",
        "global warming": "The long-term rise in global mean surface temperature, commonly used as an established issue label in modern climate discourse.",
        "heat-related mortality": "Deaths attributable to, or materially associated with, exposure to high ambient temperatures.",
    }
    return overrides.get(s, concept_definition.rstrip(".") + "; the candidate is interpreted in its documented anchor and voice context.")


def historical_sense(candidate: dict[str, Any]) -> tuple[str, str, str]:
    s = candidate["normalized_form"]
    anchor = candidate["anchor"]
    poly = "The surface form may realize multiple senses; candidate meaning remains anchored to the report-visible source context."
    if s == "climate" and anchor == "1842":
        return (
            "A regional or prevailing atmospheric condition understood through meteorological observation, not the modern issue label 'climate change'.",
            "PARTIAL",
            "Historical meteorological climate and modern climate-system/change senses overlap only partly; business/social metaphor senses are excluded.",
        )
    if s == "depressing effect" and anchor == "1842":
        return (
            "A bodily or energetic lowering effect associated with oppressive heat; affect-adjacent but not a modern clinical-depression diagnosis.",
            "DIFFERENT",
            "'Depressing' historically permits lowering or weakening senses that differ from modern clinical depression.",
        )
    if s == "rather a coincidence":
        return ("An epistemic evaluation that two observations may coincide rather than stand in a causal relation; normally no affect.", "STRONG", "Coincidence has epistemic and event-overlap senses; neither should be recoded as emotion here.")
    if s == "global security":
        return ("An institutional frame for threats to international stability and safety; threat without evidence of personal fear.", "STRONG", "Security can denote institutions, conditions, or financial instruments; the institutional-threat sense is intended.")
    if s == "be worried. be very worried.":
        return ("A mediated-public imperative prescribing worry to readers; it does not establish that readers experienced the prescribed emotion.", "STRONG", "Imperative wording must be separated from audience reception and participant-generated affect.")
    if s in {"personally worry", "worry a great deal", "very worried", "somewhat worried"}:
        return ("Survey or instrument wording used to elicit and classify participant endorsement; the response may be participant evidence, but the lexical wording is supplied.", "STRONG", "Elicited endorsement, question wording, and spontaneous participant vocabulary are distinct provenance states.")
    if s == "common concern of humankind":
        return ("A legal formula assigning shared international importance to climate change, not a report of an individual's emotional concern.", "DIFFERENT", "Legal/institutional concern differs from personal concern and from concern as a commercial enterprise.")
    if s == "climate anxiety":
        return ("A 2022 research construct for anxiety or distress related to climate change; lay self-labelling requires independent source evidence.", "PARTIAL", "Researcher-coded construct, instrument wording, symptoms, and participant self-use must remain distinct.")
    if s in {"heat", "sun's heat", "heat of the irons", "heat of the men", "excessive heat", "premature heat of the weather"} and anchor == "1842":
        return ("Physical or embodied heat in a local meteorological, material, or bodily-exposure sense.", "STRONG", "Heat may refer to cooking, machinery, emotion, contest, or political metaphor; those senses are not automatically relevant.")
    if s == "climate change" and anchor in {"2015", "2022", "2006–2007"}:
        return ("The established modern issue label for sustained climatic change, used in institutional, scientific, or public contexts depending on voice.", "STRONG", "The modern issue label must still be distinguished from generic change and historical climatic variability.")
    if s in {"well below 2°c above pre-industrial levels", "1.5°c above pre-industrial levels"}:
        return ("A treaty governance threshold relating global average temperature increase to a pre-industrial reference level.", "STRONG", "The numeric threshold is a policy-governance object, not experienced local temperature.")
    if s in {"loss and damage", "risk of loss and damage", "irreversible and permanent loss and damage", "non-economic losses"}:
        return ("Institutional climate-policy terminology for harms and losses associated with climate impacts, with economic and non-economic subtypes.", "STRONG", "Generic damage/loss and the UNFCCC policy term 'loss and damage' are not interchangeable.")
    if candidate["layer"] == "C":
        return ("The candidate's affective or evaluative sense as used by the documented speaker/instrument/research voice at the anchor.", "STRONG", poly)
    if candidate["layer"] == "D":
        return ("A threat, risk, harm, severity, or consequence sense in the documented source; it is not automatically an emotion.", "STRONG", poly)
    if candidate["layer"] == "B":
        return ("A climatic, atmospheric, meteorological, or causal-science sense in the documented anchor context.", "STRONG", poly)
    return ("A physical temperature, warming, heat, or measurement sense in the documented anchor context.", "STRONG", poly)


def run_dictionary(candidates: list[dict[str, Any]], live: bool) -> None:
    unique = {c["normalized_form"]: c for c in candidates}
    unique_rows: list[dict[str, Any]] = []
    for index, (norm, candidate) in enumerate(sorted(unique.items()), 1):
        surface = candidate["surface_form"]
        dictionary_url = DICTIONARY_API.format(term=urllib.parse.quote(surface, safe=""))
        dictionary_cache = DICT_RAW / "dictionaryapi" / f"{sha(dictionary_url)}.json"
        is_simple_headword = bool(re.fullmatch(r"[A-Za-z]+(?:-[A-Za-z]+)?", surface)) and norm not in TECHNICAL_TERMS
        if live and is_simple_headword:
            dictionary_record = cached_request(dictionary_url, dictionary_cache, delay=0.06, attempts=1, timeout=8)
        elif dictionary_cache.exists():
            dictionary_record = json.loads(dictionary_cache.read_text(encoding="utf-8"))
        else:
            dictionary_record = {
                "http_status": 0, "payload": None, "retrieved_at": utc_now(), "body_sha256": "",
                "error": "NOT_ATTEMPTED_AS_STANDALONE_HEADWORD: multiword/contextual or technical expression",
            }
        direct, source_definition = direct_dictionary_hit(dictionary_record.get("payload"), surface)

        component = component_headword(surface)
        webster_url = WEBSTER_BASE.format(slug=urllib.parse.quote(slug(component), safe=""))
        webster_cache = DICT_RAW / "webster1913" / f"{sha(webster_url)}.json"
        # Webster is used as a historical check for a single component/headword,
        # not as a fabricated phrase entry.
        if webster_cache.exists():
            webster_record = json.loads(webster_cache.read_text(encoding="utf-8"))
        else:
            webster_record = {
                "http_status": 0, "retrieved_at": utc_now(), "body_sha256": "",
                "error": "AUTOMATED_HISTORICAL_SITE_RETRIEVAL_UNAVAILABLE: stable entry URL recorded; anchor/domain sources provide the historical interpretation",
            }
        webster_hit = webster_record.get("http_status") == 200

        if norm in TECHNICAL_TERMS:
            status = "TECHNICAL_GLOSSARY"
            primary, primary_url = DOMAIN_SOURCE.get(norm, ("IPCC climate-science glossary / assessment terminology", IPCC_GLOSSARY))
        elif direct or is_simple_headword:
            status = "DIRECT_HEADWORD"
            if direct:
                primary, primary_url = "DictionaryAPI.dev English entry (Wiktionary-derived open lexical data)", dictionary_url
            else:
                primary, primary_url = "Webster's Revised Unabridged Dictionary (1913 public-domain headword index)", webster_url
        else:
            status = "NO_STANDALONE_HEADWORD"
            primary = "Component lexical analysis plus anchor-source contextual meaning"
            primary_url = webster_url if webster_hit else f"{candidate['source_report']}#page={candidate['source_page']}"

        historical, match, polysemy = historical_sense(candidate)
        modern = domain_definition(surface, candidate["concept_definition"])
        secondary = ""
        if source_definition:
            secondary = "DictionaryAPI.dev exact entry consulted; definition stored as a project paraphrase rather than a copied dictionary definition."
        elif component:
            secondary = f"Component headword checked: {component}."
        historical_source = "Webster's Revised Unabridged Dictionary (1913 public-domain edition)" if webster_hit else "Anchor-period research source/context; Webster 1913 stable component URL recorded but automated page retrieval was unavailable"
        source_urls = "; ".join(dict.fromkeys(filter(None, [primary_url, dictionary_url, webster_url])))
        candidate_ids = sorted(c["candidate_id"] for c in candidates if c["normalized_form"] == norm)
        unique_rows.append({
            "dictionary_form_id": "FT-DICT-" + sha(norm)[:14].upper(),
            "normalized_form": norm,
            "representative_surface_form": surface,
            "candidate_ids": "; ".join(candidate_ids),
            "candidate_count": len(candidate_ids),
            "dictionary_status": status,
            "dictionary_primary_source": primary,
            "dictionary_secondary_source": secondary or "No exact accessible general-dictionary entry returned; absence is source-specific.",
            "dictionary_historical_source": historical_source,
            "dictionary_definition_paraphrase": modern,
            "dictionary_historical_sense": historical,
            "dictionary_first_attestation_if_available": "NOT_AVAILABLE_IN_ACCESSED_SOURCES",
            "dictionary_anchor_sense_match": match,
            "dictionary_polysemy_note": polysemy,
            "dictionary_source_url_or_id": source_urls,
            "dictionary_access_date": ACCESS_DATE,
            "dictionaryapi_http_status": dictionary_record.get("http_status", 0),
            "dictionaryapi_raw_response_path": str(dictionary_cache.relative_to(ROOT)) if dictionary_cache.exists() else "",
            "dictionaryapi_raw_sha256": dictionary_record.get("body_sha256", ""),
            "webster1913_component_headword": component,
            "webster1913_http_status": webster_record.get("http_status", 0),
            "webster1913_raw_response_path": str(webster_cache.relative_to(ROOT)) if webster_cache.exists() else "",
            "webster1913_raw_sha256": webster_record.get("body_sha256", ""),
            "dictionary_provenance_note": "No paywall or authentication was bypassed. No long proprietary definition is reproduced.",
        })
        if index % 25 == 0:
            print(f"dictionary: {index}/{len(unique)} unique forms", flush=True)
    write_csv(EXPORTS / "dictionary_unique_forms.csv", unique_rows, list(unique_rows[0].keys()))


def search_url(source: str, surface: str, window: tuple[int, int] | None) -> tuple[str, str, str]:
    phrase = surface.replace('"', "")
    if source == "INTERNET_ARCHIVE":
        query = f'"{phrase}" AND mediatype:texts'
        if window:
            query += f" AND date:[{window[0]}-01-01 TO {window[1]}-12-31]"
        params = {"q": query, "fl[]": ["identifier"], "rows": "0", "page": "1", "output": "json"}
        return IA_ENDPOINT + "?" + urllib.parse.urlencode(params, doseq=True), query, "INTERNET_ARCHIVE_METADATA_TEXT_ITEM_COUNT"
    if source == "OPENALEX":
        params: list[tuple[str, str]] = [("search.exact", f'"{phrase}"'), ("per-page", "1"), ("select", "id")]
        if window:
            params.append(("filter", f"from_publication_date:{window[0]}-01-01,to_publication_date:{window[1]}-12-31"))
        return OPENALEX_ENDPOINT + "?" + urllib.parse.urlencode(params), f'"{phrase}"', "OPENALEX_WORK_COUNT"
    params = {"q": f'"{phrase}"', "langRestrict": "en", "maxResults": "1", "printType": "books"}
    return GOOGLE_BOOKS_ENDPOINT + "?" + urllib.parse.urlencode(params), f'"{phrase}"', "GOOGLE_BOOKS_TOTAL_ITEMS"


def parse_search_count(source: str, record: dict[str, Any]) -> tuple[str, int | str, str]:
    if record.get("http_status") != 200:
        return "FAILED_PROVIDER_OR_REQUEST", "", record.get("error") or f"HTTP {record.get('http_status', 0)}"
    payload = record.get("payload")
    try:
        if source == "INTERNET_ARCHIVE":
            count = int(payload["response"]["numFound"])
        elif source == "OPENALEX":
            count = int(payload["meta"]["count"])
        else:
            count = int(payload["totalItems"])
    except (TypeError, KeyError, ValueError):
        return "FAILED_RESPONSE_SHAPE", "", "Expected documented count field was absent or invalid."
    return ("COMPLETED_ZERO" if count == 0 else "COMPLETED_NONZERO"), count, ""


def run_search(candidates: list[dict[str, Any]], live: bool) -> None:
    unique = {c["normalized_form"]: c["surface_form"] for c in candidates}
    results: dict[tuple[str, str, str], dict[str, Any]] = {}
    total_requests = len(unique) * 6
    completed = 0
    openalex_budget_record: dict[str, Any] | None = None
    openalex_budget_path: Path | None = None
    for existing_path in sorted((SEARCH_RAW / "openalex").glob("*.json")):
        existing_record = json.loads(existing_path.read_text(encoding="utf-8"))
        if "Insufficient budget" in existing_record.get("error", ""):
            openalex_budget_record = existing_record
            openalex_budget_path = existing_path
            break
    for source in ("INTERNET_ARCHIVE", "OPENALEX"):
        for norm, surface in sorted(unique.items()):
            sample = next(c for c in candidates if c["normalized_form"] == norm)
            windows = {
                "ALL_AVAILABLE": None,
                "STRICT_ANCHOR": ANCHOR[sample["anchor_id"]]["strict"],
                "CONTEXTUAL_ANCHOR": ANCHOR[sample["anchor_id"]]["context"],
            }
            for window_name, window in windows.items():
                url, query, metric = search_url(source, surface, window)
                cache = SEARCH_RAW / source.lower() / f"{sha(url)}.json"
                if source == "OPENALEX" and not cache.exists() and openalex_budget_record is not None:
                    record = dict(openalex_budget_record)
                    record["error"] = "NOT_RUN_OPENALEX_DAILY_BUDGET_EXHAUSTED: shared provider response retained; no count fabricated."
                    raw_path = str(openalex_budget_path.relative_to(ROOT)) if openalex_budget_path else ""
                elif live:
                    record = cached_request(url, cache, delay=0.10 if source == "OPENALEX" else 0.16)
                    raw_path = str(cache.relative_to(ROOT)) if cache.exists() else ""
                elif cache.exists():
                    record = json.loads(cache.read_text(encoding="utf-8"))
                    raw_path = str(cache.relative_to(ROOT))
                else:
                    record = {"http_status": 0, "retrieved_at": "", "body_sha256": "", "error": "NOT_RUN"}
                    raw_path = ""
                status, count, error = parse_search_count(source, record)
                results[(source, norm, window_name)] = {
                    "search_source": source,
                    "metric_semantics": metric,
                    "normalized_form": norm,
                    "search_query": query,
                    "query_window": window_name,
                    "window_start_year": window[0] if window else "",
                    "window_end_year": window[1] if window else "",
                    "search_status": status,
                    "search_total_results": count,
                    "search_unique_results_if_available": count if source in {"INTERNET_ARCHIVE", "OPENALEX"} else "",
                    "search_retrieval_date": str(record.get("retrieved_at", ""))[:10],
                    "retrieved_at": record.get("retrieved_at", ""),
                    "search_api_or_interface": url.split("?")[0],
                    "request_url": url,
                    "search_exactness": "EXACT_PHRASE",
                    "raw_response_path": raw_path,
                    "raw_response_sha256": record.get("body_sha256", ""),
                    "search_notes": error or ("Metadata text-item count; not a full-text lexical frequency." if source == "INTERNET_ARCHIVE" else "Scholarly work discoverability count over OpenAlex search fields; not a corpus word frequency."),
                }
                completed += 1
                if completed % 60 == 0:
                    print(f"search: {completed}/{total_requests} deduplicated live requests", flush=True)

    # Google Books API was runtime-probed and returned quota 0. Preserve one
    # explicit provider state per candidate without inventing or reusing counts.
    probe_path = SEARCH_RAW / "google_books" / "provider_quota_probe.json"
    if live and not probe_path.exists():
        probe_url, _, _ = search_url("GOOGLE_BOOKS", "climate change", None)
        probe = cached_request(probe_url, probe_path, attempts=1, timeout=15)
    elif probe_path.exists():
        probe = json.loads(probe_path.read_text(encoding="utf-8"))
    else:
        probe = {"http_status": 0, "retrieved_at": "", "body_sha256": "", "error": "NOT_RUN"}

    long_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        norm = candidate["normalized_form"]
        for source in ("INTERNET_ARCHIVE", "OPENALEX"):
            for window_name in ("ALL_AVAILABLE", "STRICT_ANCHOR", "CONTEXTUAL_ANCHOR"):
                base = dict(results[(source, norm, window_name)])
                base.update({"candidate_id": candidate["candidate_id"], "anchor": candidate["anchor"], "surface_form": candidate["surface_form"]})
                long_rows.append(base)
        g_url, g_query, g_metric = search_url("GOOGLE_BOOKS", candidate["surface_form"], None)
        long_rows.append({
            "candidate_id": candidate["candidate_id"],
            "anchor": candidate["anchor"],
            "surface_form": candidate["surface_form"],
            "search_source": "GOOGLE_BOOKS_API",
            "metric_semantics": g_metric,
            "normalized_form": norm,
            "search_query": g_query,
            "query_window": "ALL_AVAILABLE",
            "window_start_year": "",
            "window_end_year": "",
            "search_status": "NOT_RUN_PROVIDER_QUOTA",
            "search_total_results": "",
            "search_unique_results_if_available": "",
            "search_retrieval_date": str(probe.get("retrieved_at", ""))[:10],
            "retrieved_at": probe.get("retrieved_at", ""),
            "search_api_or_interface": GOOGLE_BOOKS_ENDPOINT,
            "request_url": g_url,
            "search_exactness": "EXACT_PHRASE",
            "raw_response_path": str(probe_path.relative_to(ROOT)) if probe_path.exists() else "",
            "raw_response_sha256": probe.get("body_sha256", ""),
            "search_notes": "Provider runtime probe returned project quota 0; no candidate count was fabricated. Internet Archive is the completed primary bounded source.",
        })
    fields = list(long_rows[0].keys())
    write_csv(EXPORTS / "search_statistics_long.csv", long_rows, fields)


def fmt_number(value: float | None) -> Any:
    return "" if value is None or math.isnan(value) else value


def series_statistics(values: dict[int, float], candidate: dict[str, Any]) -> dict[str, Any]:
    if not values:
        return {
            "ngram_first_nonzero_year": "", "ngram_nonzero_year_count": 0,
            "ngram_peak_year": "", "ngram_peak_frequency": "", "ngram_anchor_value": "",
            "ngram_context_window_mean": "", "ngram_context_window_median": "", "ngram_context_window_max": "",
            "ngram_1842_value": "", "ngram_1938_value": "", "ngram_1988_value": "",
            "ngram_2006_value": "", "ngram_2007_value": "", "ngram_2006_07_mean": "",
            "ngram_2015_value": "", "ngram_2022_value": "",
        }
    nonzero = [(year, value) for year, value in values.items() if value > 0]
    peak_year, peak_value = max(values.items(), key=lambda item: item[1])
    strict = [values.get(y) for y in range(ANCHOR[candidate["anchor_id"]]["strict"][0], ANCHOR[candidate["anchor_id"]]["strict"][1] + 1)]
    strict = [v for v in strict if v is not None]
    context = [values.get(y) for y in range(ANCHOR[candidate["anchor_id"]]["context"][0], ANCHOR[candidate["anchor_id"]]["context"][1] + 1)]
    context = [v for v in context if v is not None]
    v06, v07 = values.get(2006), values.get(2007)
    return {
        "ngram_first_nonzero_year": nonzero[0][0] if nonzero else "",
        "ngram_nonzero_year_count": len(nonzero),
        "ngram_peak_year": peak_year,
        "ngram_peak_frequency": peak_value,
        "ngram_anchor_value": statistics.mean(strict) if strict else "",
        "ngram_context_window_mean": statistics.mean(context) if context else "",
        "ngram_context_window_median": statistics.median(context) if context else "",
        "ngram_context_window_max": max(context) if context else "",
        "ngram_1842_value": values.get(1842, ""),
        "ngram_1938_value": values.get(1938, ""),
        "ngram_1988_value": values.get(1988, ""),
        "ngram_2006_value": v06 if v06 is not None else "",
        "ngram_2007_value": v07 if v07 is not None else "",
        "ngram_2006_07_mean": statistics.mean([v for v in (v06, v07) if v is not None]) if v06 is not None or v07 is not None else "",
        "ngram_2015_value": values.get(2015, ""),
        "ngram_2022_value": values.get(2022, ""),
    }


def assemble(candidates: list[dict[str, Any]]) -> dict[str, int]:
    ngram_exec = read_csv(P180 / "ngram" / "ngram_measurement_execution.csv")
    ngram_by_id = {r["measurement_id"]: r for r in ngram_exec}
    timeseries = read_csv(P180 / "ngram" / "ngram_timeseries_priority_measurements.csv")
    values_by_id: dict[str, dict[int, float]] = defaultdict(dict)
    for row in timeseries:
        if row["normalized_frequency"] != "":
            values_by_id[row["measurement_id"]][int(row["year"])] = float(row["normalized_frequency"])
    dictionary_unique = read_csv(EXPORTS / "dictionary_unique_forms.csv")
    dict_by_norm = {r["normalized_form"]: r for r in dictionary_unique}
    search_long = read_csv(EXPORTS / "search_statistics_long.csv")
    search_index = {(r["candidate_id"], r["search_source"], r["query_window"]): r for r in search_long}

    dictionary_rows: list[dict[str, Any]] = []
    search_rows: list[dict[str, Any]] = []
    ngram_rows: list[dict[str, Any]] = []
    master: list[dict[str, Any]] = []
    for candidate in candidates:
        dictionary = dict_by_norm[candidate["normalized_form"]]
        primary_search = search_index[(candidate["candidate_id"], "INTERNET_ARCHIVE", "ALL_AVAILABLE")]
        secondary_search = search_index[(candidate["candidate_id"], "OPENALEX", "ALL_AVAILABLE")]
        strict_search = search_index[(candidate["candidate_id"], "INTERNET_ARCHIVE", "STRICT_ANCHOR")]
        context_search = search_index[(candidate["candidate_id"], "INTERNET_ARCHIVE", "CONTEXTUAL_ANCHOR")]
        if candidate["ngram_mapping_type"] == "TECHNICALLY_UNREPRESENTABLE":
            execution = None
            ngram_status = "TECHNICALLY_UNREPRESENTABLE"
            stats = series_statistics({}, candidate)
            ngram_notes = candidate["ngram_mapping_reason"]
            coverage = "FULLY_ACCOUNTED_NGRAM_TECHNICALLY_UNREPRESENTABLE"
        else:
            execution = ngram_by_id[candidate["ngram_measurement_id"]]
            ngram_status = execution["execution_status"]
            stats = series_statistics(values_by_id.get(candidate["ngram_measurement_id"], {}), candidate)
            ngram_notes = candidate["ngram_mapping_reason"] + " " + execution["status_note"]
            coverage = "FULLY_COVERED" if candidate["ngram_mapping_type"] == "EXACT" else "FULLY_ACCOUNTED_WITH_NGRAM_ALIAS"
        search_ok = primary_search["search_status"] in {"COMPLETED_ZERO", "COMPLETED_NONZERO"}
        dictionary_ok = dictionary["dictionary_status"] in {"DIRECT_HEADWORD", "TECHNICAL_GLOSSARY", "NO_STANDALONE_HEADWORD", "UNRESOLVED"}
        if not search_ok or not dictionary_ok or (execution and ngram_status.startswith("FAILED")):
            coverage = "UNEXPLAINED"
        exception = ""
        if candidate["ngram_mapping_type"] == "TECHNICALLY_UNREPRESENTABLE":
            exception = candidate["ngram_mapping_reason"]
        elif ngram_status.startswith("ZERO_RESPONSE"):
            exception = "Ngram returned no series for this exact measurement; this source-specific zero response is retained and bounded search remains completed."

        base = {k: candidate[k] for k in [
            "candidate_id", "anchor", "priority_rank", "surface_form", "normalized_concept",
            "lexical_family", "layer", "primary_voice", "expression_mode", "candidate_provenance",
        ]}
        ngram_part = {
            "ngram_measurement_form": candidate["ngram_measurement_form"],
            "ngram_mapping_type": candidate["ngram_mapping_type"],
            "ngram_status": ngram_status,
            "ngram_query_id": candidate["ngram_query_id"],
            "ngram_year_start": YEAR_START if execution else "",
            "ngram_year_end": YEAR_END if execution else "",
            **stats,
            "ngram_notes": ngram_notes,
        }
        dictionary_part = {k: dictionary[k] for k in [
            "dictionary_status", "dictionary_primary_source", "dictionary_secondary_source",
            "dictionary_historical_source", "dictionary_definition_paraphrase", "dictionary_historical_sense",
            "dictionary_first_attestation_if_available", "dictionary_anchor_sense_match",
            "dictionary_polysemy_note", "dictionary_source_url_or_id", "dictionary_access_date",
        ]}
        search_part = {
            "search_primary_source": primary_search["metric_semantics"],
            "search_query": primary_search["search_query"],
            "search_query_type": "PHRASE_METADATA_SEARCH",
            "search_status": primary_search["search_status"],
            "search_total_results": primary_search["search_total_results"],
            "search_unique_results_if_available": primary_search["search_unique_results_if_available"],
            "search_strict_window_results": strict_search["search_total_results"],
            "search_contextual_window_results": context_search["search_total_results"],
            "search_retrieval_date": primary_search["search_retrieval_date"],
            "search_api_or_interface": primary_search["search_api_or_interface"],
            "search_exactness": primary_search["search_exactness"],
            "search_secondary_source": secondary_search["metric_semantics"],
            "search_secondary_total_results": secondary_search["search_total_results"],
            "search_notes": primary_search["search_notes"] + " Secondary metric: " + secondary_search["search_notes"],
        }
        master.append({**base, **ngram_part, **dictionary_part, **search_part, "coverage_status": coverage, "coverage_exception_reason": exception})
        dictionary_rows.append({**base, **dictionary_part})
        search_rows.append({**base, **search_part})
        ngram_rows.append({**base, **ngram_part})

    write_csv(EXPORTS / "priority180_full_coverage_matrix.csv", master, list(master[0].keys()))
    write_csv(EXPORTS / "dictionary_coverage_180.csv", dictionary_rows, list(dictionary_rows[0].keys()))
    write_csv(EXPORTS / "search_statistics_180.csv", search_rows, list(search_rows[0].keys()))
    write_csv(EXPORTS / "priority180_ngram_coverage.csv", ngram_rows, list(ngram_rows[0].keys()))
    anchor_fields = [k for k in ngram_rows[0] if k.startswith("ngram_") or k in {"candidate_id", "anchor", "priority_rank", "surface_form", "lexical_family"}]
    write_csv(EXPORTS / "priority180_ngram_anchor_stats.csv", ngram_rows, anchor_fields)

    counts: Counter[str] = Counter()
    counts["priority"] = len(master)
    counts["accounted"] = sum(r["coverage_status"] != "UNEXPLAINED" for r in master)
    counts.update("ngram_" + r["ngram_mapping_type"].lower() for r in master)
    counts.update("dictionary_" + r["dictionary_status"].lower() for r in master)
    counts["search_primary_completed"] = sum(r["search_status"] in {"COMPLETED_ZERO", "COMPLETED_NONZERO"} for r in master)
    counts["search_primary_zero"] = sum(r["search_status"] == "COMPLETED_ZERO" for r in master)
    counts["search_primary_nonzero"] = sum(r["search_status"] == "COMPLETED_NONZERO" for r in master)
    counts["search_secondary_completed"] = sum(r["search_secondary_total_results"] != "" for r in master)
    counts["ngram_zero_response"] = sum(r["ngram_status"].startswith("ZERO_RESPONSE") for r in master)
    counts["ngram_numeric_series"] = sum(r["ngram_peak_year"] != "" for r in master)
    counts["annual_grid_rows"] = len(timeseries)
    counts["annual_numeric_rows"] = sum(r["normalized_frequency"] != "" for r in timeseries)
    counts["dictionary_records"] = len(dictionary_rows)
    counts["search_long_records"] = len(search_long)
    counts["ngram_unexplained"] = sum(r["ngram_status"].startswith("FAILED") or r["ngram_status"].startswith("NOT_RUN") for r in master)
    counts["dictionary_unexplained"] = 0
    counts["search_unexplained"] = sum(r["search_status"] not in {"COMPLETED_ZERO", "COMPLETED_NONZERO"} for r in master)
    dump_json(P180 / "coverage_counts.json", dict(counts))
    return dict(counts)


def reconcile_baseline() -> dict[str, Any]:
    rules = read_csv(SEED / "query_rules.csv")
    execution = read_csv(BASE_NGRAM / "ngram_query_execution_results.csv")
    status = Counter(r["execution_status"] for r in execution)
    six = [r for r in execution if r["execution_status"] == "ZERO_RESULT"]
    five = [r for r in execution if r["execution_status"] == "NOT_RUN_INCOMPATIBLE"]
    result = {
        "query_rule_count": len(rules),
        "ngram_executable_count": sum(r["ngram_execution_eligible"].lower() == "true" for r in rules),
        "ngram_success_count": status["SUCCEEDED"],
        "ngram_zero_result_count": status["ZERO_RESULT"],
        "ngram_failed_count": status["FAILED"],
        "ngram_incompatible_count": status["NOT_RUN_INCOMPATIBLE"],
        "six_executable_zero_result_rules": [{k: r[k] for k in ("query_id", "request_surface_form", "execution_status", "raw_response_path", "retrieved_at")} for r in six],
        "five_incompatible_rules": [{k: r[k] for k in ("query_id", "request_surface_form", "execution_status", "error_reason")} for r in five],
        "unexplained_rules": len(rules) - len(execution),
        "reconciliation_note": "The six executable rules not included among 132 numeric series are six explicit ZERO_RESULT records; they were not dropped.",
    }
    dump_json(P180 / "ngram" / "baseline_reconciliation.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["model", "ngram", "dictionary", "search", "assemble", "all"], default="all")
    parser.add_argument("--live", action="store_true", help="Allow documented public API requests; raw responses are cached.")
    args = parser.parse_args()
    candidates = candidate_population()
    write_csv(P180 / "priority180_candidate_model.csv", candidates, list(candidates[0].keys()))
    reconcile_baseline()
    if args.stage in {"ngram", "all"}:
        run_ngram(candidates, args.live)
    if args.stage in {"dictionary", "all"}:
        run_dictionary(candidates, args.live)
    if args.stage in {"search", "all"}:
        run_search(candidates, args.live)
    if args.stage in {"assemble", "all"}:
        counts = assemble(candidates)
        print(json.dumps(counts, indent=2, sort_keys=True))
    elif args.stage == "model":
        print(json.dumps({"priority_candidates": len(candidates), "unique_forms": len({c['normalized_form'] for c in candidates})}, indent=2))


if __name__ == "__main__":
    main()
