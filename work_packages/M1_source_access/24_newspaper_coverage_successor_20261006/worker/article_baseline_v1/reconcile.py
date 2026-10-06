"""Local selected-evidence reconciliation. No transport or database operations."""
import collections
import csv
import datetime as dt
import fcntl
import hashlib
import io
import json
import pathlib
import re
import shutil
import sys
from urllib.parse import urlsplit, urlunsplit

from bs4 import BeautifulSoup

OUT = pathlib.Path(__file__).resolve().parent
WORKER = OUT.parent
REPO = WORKER.parents[3]
BASE = REPO / 'work_packages/M1_source_access/23_newspaper_acquisition_and_transition_20261005/transition_research/acquisition_followthrough_20261005'
SCOPE_PATH = WORKER.parent / 'control/ARTICLE_BASELINE_SCOPE_v2.json'
SCOPE = json.loads(SCOPE_PATH.read_text())
RESOURCE = json.loads((WORKER.parent / 'control/EXECUTION_SCOPE.json').read_text())
LOCK = REPO / 'work_packages/M1_source_access/14_structural_validation_20261004/control/heavy_io.lock'
GEOS = ['EU/Europe excluding UK', 'UK', 'AU', 'US', 'NZ']

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def digest(data):
    return hashlib.sha256(data).hexdigest()

def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]

def resolve_path(value, origin):
    if not value:
        return None
    p = pathlib.Path(value)
    if p.is_absolute():
        return p
    if (REPO / p).exists():
        return REPO / p
    return origin / p

def rel(path):
    return str(path.relative_to(REPO)) if path else None

def budget(pending=0):
    used = RESOURCE['prior_media_bytes'] + sum(p.stat().st_size for root in RESOURCE['media_lifetime_accounting_roots'] for p in (REPO / root).rglob('*') if p.is_file())
    free = shutil.disk_usage(OUT).free
    coordination = json.loads((WORKER.parent / 'control/COORDINATION.json').read_text())
    lease = sum(x['reserved_bytes'] for x in coordination.get('active_leases', []) if x.get('active', True))
    receipt = 65536
    return {'at_utc': now(), 'cumulative_accounting_bytes': used, 'lifetime_cap_bytes': RESOURCE['media_lifetime_cap_bytes'], 'free_bytes': free, 'physical_floor_bytes': RESOURCE['physical_floor_bytes'], 'recovery_allowance_bytes': RESOURCE['recovery_allowance_bytes'], 'active_lease_bytes': lease, 'pending_derived_bytes': pending, 'pending_receipt_allowance_bytes': receipt, 'allocation_headroom_after_pending_bytes': RESOURCE['media_lifetime_cap_bytes'] - used - pending - receipt, 'physical_headroom_after_pending_bytes': free - RESOURCE['physical_floor_bytes'] - RESOURCE['recovery_allowance_bytes'] - lease - pending - receipt, 'original_combined_reserve_bytes': 0}

# These decisions describe inspected source structures, not keyword/length gates.
PRIOR_DECISIONS = {
    0: ('pending', 'Original article spans pages 1 and 27 in accepted mapping; severe OCR corruption at column joins and an unverified continuation transcription remain. The accepted visible-span claim is preserved, not silently upgraded to a complete restored body.'),
    1: ('non_article', 'Applicants table with attribution; no independent full article body.'),
    2: ('pending', 'Publisher explicitly labels an excerpt and retains ellipses from the letter. Full original-letter/article boundaries are not established by this selected page.'),
    3: ('non_article', 'Several unrelated campus notices plus publisher tips footer; not one independent article.'),
    8: ('non_article', 'Competition-results list of names; no accompanying independent article body on the selected page.'),
    10: ('pending', 'Finite publisher-compiled incident log with introduction and compiler credit. Its article-versus-record-list unit requires adjudication; incidents are not split into counted articles.'),
    11: ('non_article', 'Election-result table with explanatory sentence; component evidence rather than a complete independent article.'),
    13: ('non_article', 'Labelled biographical/contact facts only; profile sidebar/directory component, not the complete accompanying feature.'),
    16: ('pending', 'Complete narrative is visible, but header/URL assign 2007-10-06 while body explicitly states original publication April 20, 2007 at 5:10 p.m.; cross-month publication/version mapping unresolved.'),
    18: ('pending', 'Reproduced legal memorandum argument and conclusion. Whether this is the full original document or an excerpt/component is unresolved; newspaper carriage alone does not establish an independent complete newspaper article.'),
    20: ('non_article', 'Field, hometown, experience and email facts only; biographical sidebar/directory component.'),
    34: ('non_article', 'Fraternity event timetable; no independent article body.'),
    40: ('non_article', 'Rush event timetable with extraction-style markers; no independent article body.'),
    43: ('non_article', 'Unrelated event and deadline notices plus publisher tips footer.'),
    46: ('pending', 'Introductory component directs readers to a multi-page rush schedule/map. Independence as a complete article rather than supplement preface is unresolved.'),
    52: ('non_article', 'Unrelated campus notices plus publisher tips footer.'),
    53: ('non_article', 'Orientation event timetable; no independent article body.'),
    57: ('non_article', 'Fraternity rush event timetable; no independent article body.'),
    59: ('non_article', 'Independent-living-group rush event timetable; no independent article body.'),
    76: ('non_article', 'Unrelated closure, relocation, shuttle and deadline notices.'),
    79: ('non_article', 'Unrelated registration and degree-application deadline notices.'),
    86: ('non_article', 'Unrelated career fair, committee and UROP notices plus publisher footer.'),
    90: ('non_article', 'Unrelated registration, blood drive and PE notices plus publisher footer.'),
    92: ('non_article', 'Unrelated sports, deadline and blood drive notices plus publisher footer.'),
    95: ('non_article', 'Unrelated registration, PE and meal-plan notices plus publisher footer.'),
    102: ('non_article', 'Unrelated quarantine-week, PE and UROP/deadline notices.'),
    112: ('non_article', 'Saved body is empty and page is an activities component; complete article text is unavailable.'),
    115: ('non_article', 'Registration and xFair notices plus publisher footer.'),
    122: ('pending', 'One page contains separate section-editor letters with independent signatures. Original item mapping remains unresolved; the collection is not counted as one article or split to supply another.'),
    124: ('pending', 'One page contains separately signed editor/section reflections. Original item mapping remains unresolved; the collection is not counted as one article or split to supply another.'),
    127: ('non_article', 'Unrelated orientation, registration and holiday notices plus publisher footer.'),
    130: ('non_article', 'Unrelated registration and PE/deadline notices plus publisher footer.'),
}
NEW_DECISIONS = {
    2: ('pending', 'Saved publisher timestamp is 2026-09-28, outside the fixed 2026-09-21 cutoff. Retained as historical out-of-interval evidence, not assessed as an eligible article candidate.'),
    10: ('pending', 'Only a live-blog introductory lead survives locally; live updates/components are absent. Complete body not established.'),
    11: ('pending', 'Legacy content is repeated literal text placeholders with external image references; complete original body unavailable locally.'),
    12: ('pending', 'Placeholder headline and missing native body; original article identity/content unresolved.'),
    14: ('pending', 'Publisher-compiled incident log is locally complete as a log; article-versus-record-list status remains unresolved. No incident splitting.'),
    23: ('non_article', 'The complete saved text advertises a discounted student-entry offer and free cocktails, ending in a call to attend; promotional offer component, not a complete independent article.'),
    26: ('pending', 'News Briefs contains two unrelated native subheadlines with separate signatures (DAPER summer fees; asbestos in Stata). The container cannot count as one article. No new article is created by splitting this page in this bounded correction.'),
    34: ('non_article', 'Publisher title Table; one candidates table, 292 characters in frozen body. The table is retained as a non-article component, not rejected for its length or topic.'),
    49: ('pending', 'The original titled article and page-1/page-14 continuation span are established. Native OCR contains broken text at joins; marker removal is a derivative correction, not verification of a complete accurate restored transcription.'),
    50: ('pending', 'The original two-column front-page article boundary is established, excluding policy box and adjacent items. Final quotation is corrupted in native OCR; complete restored transcription remains unresolved.'),
    51: ('pending', 'Original page-1/page-2 article/continuation established. Vision OCR merges neighbouring columns and corrupts first-page lines. A demonstrated missing department line is corrected from the retained scan, but full transcription fidelity remains unresolved.'),
}

def canon(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, p.query, ''))

def source_id(r):
    return r.get('source_id') or {'The Tech': 'mit_tech', 'InDaily': 'indaily'}[r['source']]

def main():
    assert OUT == REPO / SCOPE['worker_write_root']
    assert SCOPE['monthly_minimum_distinct_complete_articles'] == 2
    assert SCOPE['network_operations_allowed'] == 0
    assert dt.datetime.now(dt.timezone.utc) < dt.datetime.fromisoformat(SCOPE['hard_deadline_at_utc'])
    selected = json.loads((OUT / 'SELECTION_v1.json').read_text())
    assert len(selected['prior_candidates']) == 133
    month_selections = collections.Counter(r['publication_date'][:7] for r in selected['prior_candidates'])
    assert max(month_selections.values()) <= 3
    input_checks = []
    for receipt in SCOPE['input_receipts']:
        p = REPO / receipt['path']
        data = p.read_bytes()
        input_checks.append({'path': receipt['path'], 'expected_sha256': receipt['sha256'], 'observed_sha256': digest(data), 'expected_bytes': receipt['bytes'], 'observed_bytes': len(data), 'unchanged': digest(data) == receipt['sha256'] and len(data) == receipt['bytes']})
    assert all(r['unchanged'] for r in input_checks)
    issues = {r['publication_date']: r for r in json.loads((BASE / 'ISSUE_CONTAINER_MANIFEST.json').read_text())}
    early = json.loads((BASE / 'EARLY_ARTICLE_RECORD.json').read_text())
    persisted_path = OUT / 'IDENTITY_MAP.json'
    identities = json.loads(persisted_path.read_text())['identity_key_to_article_id'] if persisted_path.exists() else {}
    files = {}
    corrections = []
    records = []
    inspected = []
    body_boundary_qa = []
    for tranche, candidates, origin, decisions in [('prior', selected['prior_candidates'], BASE, PRIOR_DECISIONS), ('successor', selected['new_candidates'], WORKER, NEW_DECISIONS)]:
        for i, r in enumerate(candidates):
            body_path = resolve_path(r.get('body_path'), origin)
            body_data = body_path.read_bytes() if body_path and body_path.exists() else b''
            body = body_data.decode('utf-8')
            original_body_hash = digest(body_data) if body_data else None
            if body_data:
                assert original_body_hash == r.get('body_sha256'), (tranche, i, 'body receipt differs')
            raw_path = resolve_path(r.get('raw_path'), origin)
            sid = source_id(r)
            is_scan = (tranche == 'prior' and i == 0) or r.get('unit_kind') == 'mapped_article'
            dom = None
            selector_matches = None
            headings = []
            observed_canonical = None
            if raw_path and raw_path.exists() and not is_scan:
                dom = BeautifulSoup(raw_path.read_bytes(), 'html.parser')
                links = dom.select('link[rel=canonical]')
                observed_canonical = links[0].get('href') if links else None
                selector = r.get('body_boundary')
                # Older body-boundary prose is not a CSS selector.
                if selector:
                    if sid == 'indaily':
                        selector = 'div.relative.w-full.overflow-hidden'
                    selector = selector.split(', retained native content children')[0]
                    try:
                        nodes = dom.select(selector)
                    except Exception:
                        nodes = []
                    selector_matches = len(nodes)
                    if nodes:
                        headings = [{'tag': n.name, 'text': n.get_text(' ', strip=True)} for n in nodes[0].select('h1,h2,h3,h4')]
            status, reason = decisions.get(i, ('confirmed_complete', 'Selected saved publisher page contains one complete independent titled narrative/review/editorial/brief; source-native body boundary, opening and closing inspected. No length, byline, topic or affect gate.'))
            native_item_note = None
            if tranche == 'prior' and i == 7:
                native_item_note = 'Despite container title News Briefs, only one independently titled and signed report appears in this saved body (email/Athena outages); no unrelated second item.'
            if tranche == 'prior' and i == 14:
                native_item_note = 'One coherent road-repaving news brief with complete notice details; the generic In Short heading is not itself an exclusion rule. Publisher tips footer is ancillary.'
            if tranche == 'successor' and i == 40:
                native_item_note = 'Multiple native subsection headings develop one latke/hamantaschen debate report; headings are not automatically independent articles.'
            if tranche == 'successor' and i in [6,8,33]:
                native_item_note = 'Complete publisher editorial/welcome or satirical column. Promotional mention or absence of byline alone does not turn a complete article into an advertisement.'
            if is_scan:
                issue = issues[r['publication_date']]
                actual_link = issue['source_url']
                canonical = issue['index_url']
                locator = early['native_derived_id'] if tranche == 'prior' else r['unit_id'].split('#', 1)[1]
                identity_key = sid + '|print|' + canonical + '|' + locator
                aid = early['native_derived_id'] if tranche == 'prior' else sid + ':print:' + canonical.rstrip('/').split('/issues/')[1].replace('/', ':') + ':' + locator
                geometry = early['segments'] if tranche == 'prior' else r['segments']
            else:
                actual_link = observed_canonical or r.get('source_url') or r['url']
                canonical = canon(actual_link)
                identity_key = sid + '|publisher-item|' + canonical
                aid = sid + ':article:' + digest(identity_key.encode())[:24]
                geometry = None
            aid = identities.setdefault(identity_key, aid)
            aliases = sorted({v for v in [r.get('url'), r.get('source_url'), observed_canonical, r.get('issue_parent_reference')] if v})
            body_reference = rel(body_path)
            version_hash = original_body_hash
            correction = None
            if tranche == 'successor' and i in [49,50,51]:
                marker = '\n\n[CONTIGUOUS ARTICLE SEGMENT]\n\n'
                parts = body.split(marker)
                assert len(parts) == len(r['segments'])
                clean_parts = []
                offsets = []
                offset = 0
                for part, segment in zip(parts, r['segments']):
                    # Printed continuation cues belong with source geometry, not body prose.
                    cleaned = re.sub(r'\(?Please[- ]turn to (?:page|puge)\s*\d+\)?', '', part, flags=re.I)
                    cleaned = re.sub(r'\(Continued from page\s*1[J\)]', '', cleaned, flags=re.I)
                    if i == 51 and len(clean_parts) == 0:
                        old = 'Moses, who headed the De-\ning and Computer Science from'
                        new = 'Moses, who headed the De-\npartment of Electrical Engineer-\ning and Computer Science from'
                        assert old in cleaned
                        cleaned = cleaned.replace(old, new)
                    cleaned = cleaned.strip()
                    offsets.append(dict(segment, character_start=offset, character_end=offset + len(cleaned), original_segment_text_sha256=segment['text_sha256']))
                    offset += len(cleaned) + 1
                    clean_parts.append(cleaned)
                restored = '\n'.join(clean_parts) + '\n'
                assert '[CONTIGUOUS ARTICLE SEGMENT]' not in restored
                body_reference = rel(OUT / 'bodies' / (aid.replace(':', '_') + '.txt'))
                files[pathlib.Path(body_reference).relative_to(OUT.relative_to(REPO)).as_posix()] = restored.encode()
                version_hash = digest(restored.encode())
                correction = {'article_id': aid, 'identity_unchanged': True, 'source_url': actual_link, 'issue_url': canonical, 'title': r['title'], 'publication_date': r['publication_date'], 'old_body_reference': rel(body_path), 'old_body_sha256': original_body_hash, 'corrected_body_reference': body_reference, 'corrected_body_sha256': version_hash, 'changes': ['Removed generated geometric segment markers', 'Moved printed continuation/page-turn cues to sidecar evidence'] + (['Restored missing department line from retained 1991 first-page scan; Vision box had merged neighbouring columns'] if i == 51 else []), 'coordinate_system': 'PDF points, top-left origin; page numbers one-based', 'segments_with_new_body_offsets': offsets, 'continuation_evidence': r['continuation_evidence'], 'raw_reference': rel(raw_path), 'raw_sha256_reused': r['raw_sha256'], 'transcription_status': 'Whole identified article span in one derivative; remaining OCR corruption and join uncertainty explicitly pending, not a verified clean complete body', 'one_article_not_segment_count': True, 'sidecar_boundary_cues_original': [part for part in parts if 'turn to' in part or 'Continued' in part]}
            elif tranche == 'successor' and i in [18,24,29,32,37]:
                leads = [n.get_text(' ', strip=True) for n in dom.select('.uk-panel.uk-text-lead')]
                assert len(leads) == 1
                lead = leads[0]
                if ' '.join(lead.split()) not in ' '.join(body.split()):
                    restored = lead + '\n\n' + body.rstrip() + '\n'
                    body_reference = rel(OUT / 'bodies' / (aid.replace(':', '_') + '.txt'))
                    files[pathlib.Path(body_reference).relative_to(OUT.relative_to(REPO)).as_posix()] = restored.encode()
                    version_hash = digest(restored.encode())
                    correction = {'article_id': aid, 'identity_unchanged': True, 'source_url': actual_link, 'title': r['title'], 'old_body_reference': rel(body_path), 'old_body_sha256': original_body_hash, 'corrected_body_reference': body_reference, 'corrected_body_sha256': version_hash, 'changes': ['Restored unique native standfirst preceding the same article body; exact standfirst already present in body would not be added'], 'raw_reference': rel(raw_path), 'raw_sha256_reused': r['raw_sha256'], 'selectors_in_reading_order': ['.uk-panel.uk-text-lead', '.uk-panel.uk-text-large.uk-margin'], 'one_article_not_segment_count': True}
            elif tranche == 'prior' and i == 96:
                tail = '\n\nWant to comment?'
                assert body.count(tail) == 1
                restored = body.split(tail)[0].rstrip() + '\n'
                body_reference = rel(OUT / 'bodies' / (aid.replace(':', '_') + '.txt'))
                files[pathlib.Path(body_reference).relative_to(OUT.relative_to(REPO)).as_posix()] = restored.encode()
                version_hash = digest(restored.encode())
                correction = {'article_id': aid, 'identity_unchanged': True, 'source_url': actual_link, 'title': r['title'], 'old_body_reference': rel(body_path), 'old_body_sha256': original_body_hash, 'corrected_body_reference': body_reference, 'corrected_body_sha256': version_hash, 'changes': ['Removed demonstrated publisher comment-submission footer following author biography; all article paragraphs retained'], 'raw_reference': rel(raw_path), 'raw_sha256_reused': r['raw_sha256'], 'boundary_anchor': 'Want to comment?', 'one_article_not_segment_count': True}
            if correction:
                correction['sidecar_reference'] = rel(OUT / 'sidecars' / (aid.replace(':', '_') + '.json'))
                files[pathlib.Path(correction['sidecar_reference']).relative_to(OUT.relative_to(REPO)).as_posix()] = (json.dumps(correction, indent=2) + '\n').encode()
                corrections.append(correction)
            date_candidates = [r.get('publication_date')]
            if tranche == 'prior' and i == 16:
                date_candidates.append('2007-04-20')
            for key in ['publication_date_candidates', 'timestamp_date_candidates']:
                if r.get(key):
                    date_candidates.extend(r[key])
            date_candidates = list(dict.fromkeys(date_candidates))
            interval_eligible = bool(r.get('publication_date') and '1988-01-01' <= r['publication_date'] <= '2026-09-21')
            body_for_evidence = files.get(pathlib.Path(body_reference).relative_to(OUT.relative_to(REPO)).as_posix(), body_data).decode() if body_reference and body_reference.startswith(rel(OUT) + '/') else body
            if status == 'confirmed_complete' and dom is not None:
                content_nodes = nodes if selector_matches else []
                assert len(content_nodes) == 1, (tranche, i, 'No unique source-native article body container')
                normalized = lambda value: re.sub(r'\s+', '', value)
                body_normalized = normalized(body_for_evidence)
                paragraphs = [p.get_text() for p in content_nodes[0].select('p') if normalized(p.get_text())]
                deliberately_removed = []
                if tranche == 'prior' and i == 96:
                    deliberately_removed = paragraphs[-2:]
                    paragraphs = paragraphs[:-2]
                missing_paragraphs = [p for p in paragraphs if normalized(p) not in body_normalized]
                assert not missing_paragraphs, (tranche, i, 'Native paragraph absent from complete body', missing_paragraphs[:1])
                body_boundary_qa.append({'candidate_record_id': tranche + ':' + str(i), 'article_id': aid, 'raw_reference': rel(raw_path), 'body_reference': body_reference, 'source_native_body_containers': len(content_nodes), 'nonempty_native_paragraphs_checked': len(paragraphs), 'missing_native_paragraphs': len(missing_paragraphs), 'normalization_for_comparison_only': 'Ignore whitespace from inline element rendering; saved bodies not normalized by this check', 'deliberately_removed_publisher_footer_paragraphs': len(deliberately_removed), 'standfirst_recovery_sidecar': correction['sidecar_reference'] if correction and sid == 'mancunion' else None, 'limit': 'Paragraph presence supplements source-boundary/opening/ending inspection; does not prove historical-version equivalence or correctness of every source claim'})
            record = {'article_id': aid, 'candidate_record_id': tranche + ':' + str(i), 'identity_key': identity_key, 'identity_kind': 'original publication article' if status == 'confirmed_complete' else 'persisted candidate publication item; disposition does not certify article status', 'disposition': status, 'disposition_reason': reason, 'source_url': actual_link, 'link_kind': 'actual publisher issue PDF; no native article permalink' if is_scan else 'observed publisher canonical article/item URL' if observed_canonical else 'saved publisher request/article URL', 'observed_canonical_url': observed_canonical or canonical, 'raw_source_url': r['url'], 'url_aliases': aliases, 'title': r['title'], 'source_id': sid, 'source': r['source'], 'edition': r.get('edition') or r.get('source_frame'), 'source_frame': r.get('source_frame'), 'stratum': r['stratum'], 'publication_date': r.get('publication_date'), 'publication_date_candidates': date_candidates, 'date_mapping_evidence': {k: r[k] for k in ['displayed_date','publisher_timestamp','date_field','date_mapping_status','url_date','timestamp_fields','date_candidates','date_conflict','printed_date_evidence'] if k in r}, 'date_mapping_limit': 'Cross-month original publication/content-version conflict; excluded pending adjudication' if tranche == 'prior' and i == 16 else r.get('date_conflict') or 'Existing supported publication month reused; day-level archive cutoff does not prove end-of-day completeness', 'eligible_publication_interval': interval_eligible, 'complete_body_reference': body_reference if status == 'confirmed_complete' else None, 'candidate_body_reference': body_reference, 'original_body_reference': rel(body_path), 'original_body_sha256': original_body_hash, 'body_version_sha256': version_hash, 'version_id': aid + ':body:' + (version_hash[:16] if version_hash else 'missing'), 'article_boundary_evidence': {'native_body_boundary': r.get('body_boundary') or r.get('body_completeness') or r.get('boundary_evidence'), 'selected_raw_reference': rel(raw_path), 'raw_sha256_reused': r.get('raw_sha256'), 'body_selector_matches_observed': selector_matches, 'native_headings_observed': headings, 'opening_passage': body_for_evidence[:240], 'closing_passage': body_for_evidence[-300:], 'native_item_note': native_item_note, 'continuation_evidence': r.get('continuation_evidence') or (early['boundary_evidence'] if is_scan and tranche == 'prior' else None), 'page_column_locator': geometry, 'correction_sidecar_reference': correction['sidecar_reference'] if correction else None, 'review_basis': 'Selected source-native DOM/body opening-ending structure inspected; no full old-corpus body rescan' if not is_scan else 'Retained scans/mapped coordinates and identified source text, with unresolved transcription explicitly annotated'}, 'canonical_article_id': aid, 'work_family_id': aid, 'known_duplicate_version_relations': [], 'journalistic_global_novelty_status': 'Not required; no claim of exhaustive global originality', 'provenance': r.get('provenance') or r.get('adapter', {}).get('provenance'), 'retrieved_at_utc': r.get('retrieved_at_utc'), 'content_version_time': r.get('content_version_time'), 'historical_body_equivalence': r.get('historical_body_equivalence'), 'body_fidelity_limit': r.get('ocr_uncertainty') or r.get('ocr_limit') or 'Source boundary evidence and saved rendition; not historical byte equivalence', 'semantic_labels_executed': False, 'length_filter_used': False, 'reviewed_at_utc': now()}
            record['date_mapping_evidence'].update({k: r[k] for k in ['current_raw_displayed_date','current_raw_timestamp','other_date_evidence','publisher_content_version_timestamp'] if k in r})
            if r.get('publisher_content_version_timestamp'):
                record['content_version_time'] = r['publisher_content_version_timestamp']
            record['byline'] = r.get('byline')
            record['derivative_snapshot_time'] = now()
            record['duplicate_relation_limit'] = 'Only known canonical/native identities and existing exact saved-body matches inspected; no unselected-body, fuzzy, global syndication or semantic search'
            records.append(record)
            inspected.append({'candidate_record_id': record['candidate_record_id'], 'raw_reference': rel(raw_path), 'body_reference': rel(body_path), 'body_bytes': len(body_data), 'source_container_kind': 'scan' if is_scan else 'HTML', 'disposition': status})
    assert len({r['article_id'] for r in records}) == len(records), 'Canonical aliases must be merged before reporting unique article rows'
    # Reuse metadata hashes only. No unselected raw/body reads or semantic similarity.
    all_meta = read_rows(BASE / 'PUBLICATION_UNITS.jsonl') + selected['new_candidates']
    known_by_hash = collections.defaultdict(set)
    for r in all_meta:
        if r.get('body_sha256') and r.get('body_characters', 1) != 0:
            known_by_hash[r['body_sha256']].add(canon(r['url']))
    confirmed_by_hash = {}
    for r in records:
        h = r['original_body_sha256']
        copies = sorted(known_by_hash.get(h, set())) if h else []
        if len(copies) > 1:
            r['known_duplicate_version_relations'].append({'relation': 'known exact saved-body match; source rendition/copy relation', 'native_urls_from_existing_metadata': copies, 'body_hash_comparison_only_not_identity_rule': True})
        if r['disposition'] == 'confirmed_complete' and h:
            if h in confirmed_by_hash:
                first = confirmed_by_hash[h]
                r['disposition'] = 'duplicate'
                r['disposition_reason'] = 'Known exact same saved article body as ' + first['article_id'] + '; cannot provide another distinct article'
                r['canonical_article_id'] = first['article_id']
                r['work_family_id'] = first['work_family_id']
            else:
                confirmed_by_hash[h] = r
    months = [f'{year:04d}-{month:02d}' for year in range(1988,2027) for month in range(1,13) if '1988-01' <= f'{year:04d}-{month:02d}' <= '2026-09']
    assert len(months) == 465
    ledgers = {}
    summaries = {}
    for geo in ['pooled'] + GEOS:
        rows = []
        for month in months:
            local = [r for r in records if r.get('publication_date','')[:7] == month and (geo == 'pooled' or r['stratum'] == geo)]
            good = [r for r in local if r['disposition'] == 'confirmed_complete' and r['eligible_publication_interval']]
            work_ids = sorted({r['work_family_id'] for r in good})
            count = len(work_ids)
            rows.append({'month': month, 'stratum': geo, 'confirmed_distinct_articles': count, 'count_state': '2+' if count >= 2 else str(count), 'meets_two_article_minimum': count >= 2, 'deficit_to_two': max(0, 2-count), 'confirmed_article_ids': ';'.join(r['article_id'] for r in good), 'known_distinct_work_family_ids': ';'.join(work_ids), 'pending_candidates': sum(r['disposition'] == 'pending' and r['eligible_publication_interval'] for r in local), 'non_article_components': sum(r['disposition'] == 'non_article' for r in local), 'duplicate_candidates': sum(r['disposition'] == 'duplicate' for r in local), 'observed_candidates': len(local), 'publication_cutoff': '2026-09-21', 'partial_month': month == '2026-09', 'completeness_limit': 'selected local evidence only; pooled does not certify geographic/archive completeness'})
        ledgers[geo] = rows
        summaries[geo] = {'months': 465, 'state_0': sum(r['count_state'] == '0' for r in rows), 'state_1_below_minimum': sum(r['count_state'] == '1' for r in rows), 'state_2plus_meets_article_count_minimum': sum(r['count_state'] == '2+' for r in rows), 'total_confirmed_distinct_articles': sum(r['confirmed_distinct_articles'] for r in rows), 'total_deficit_to_two': sum(r['deficit_to_two'] for r in rows)}
    dispositions = collections.Counter(r['disposition'] for r in records)
    tranche_counts = {t: dict(collections.Counter(r['disposition'] for r in records if r['candidate_record_id'].startswith(t + ':'))) for t in ['prior','successor']}
    summary = {'derived_at_utc': now(), 'fixed_publication_interval': ['1988-01-01','2026-09-21'], 'calendar_months': 465, 'hard_monthly_minimum': 2, 'article_count_cap': None, 'selected_prior_candidates': 133, 'prior_pooled_months_with_selected_evidence': len(month_selections), 'selection_limit_per_prior_month': 3, 'successor_candidates_required': 48, 'successor_nonreadable_or_outside_interval_reference_rows': 4, 'register_rows': len(records), 'dispositions': dict(dispositions), 'tranche_dispositions': tranche_counts, 'corrections': len(corrections), 'all_qualified_surplus_retained': True, 'ledgers': summaries, 'before_after_unit_clarification': {'frozen_successor_readable_units': 48, 'frozen_combined_pooled_readable_months': 86, 'these_are_not_complete_article_counts': True, 'new_successor_confirmed_complete_articles': tranche_counts['successor'].get('confirmed_complete', 0), 'selected_combined_article_presence_months': 465-summaries['pooled']['state_0'], 'selected_combined_months_meeting_two_article_minimum': summaries['pooled']['state_2plus_meets_article_count_minimum'], 'old_frozen_reports_unchanged': True}, 'remaining_frontier': 'Obtain/adjudicate additional complete distinct articles in 0/1 months through a separately authorised bounded successor; no refill or collection in this correction. Resolve named OCR, aggregate-item and cross-month date cases separately.'}
    checks = {'at_utc': now(), 'scope_v2_sha256': digest(SCOPE_PATH.read_bytes()), 'selection_sha256': digest((OUT/'SELECTION_v1.json').read_bytes()), 'input_checks': input_checks, 'all_frozen_inputs_unchanged': all(r['unchanged'] for r in input_checks), 'unique_persistent_article_ids': len({r['article_id'] for r in records}) == len(records), 'all_nonempty_traceable_source_links': all(urlsplit(r['source_url']).scheme in ['http','https'] and urlsplit(r['source_url']).netloc for r in records), 'IDs_not_derived_from_body_hash_or_retrieval_time': True, 'correction_identity_invariant': all(c['identity_unchanged'] for c in corrections), 'PDF_links_are_real_issue_links_without_fabricated_article_fragments': all('#' not in r['source_url'] for r in records if r['article_boundary_evidence']['page_column_locator']), 'six_465_month_ledgers': len(ledgers) == 6 and all(len(rows)==465 for rows in ledgers.values()), 'hard_minimum_consistency': all(row['meets_two_article_minimum'] == (row['confirmed_distinct_articles'] >= 2) for rows in ledgers.values() for row in rows), 'pooled_counts_not_used_to_certify_geography': True, 'selected_prior_max_per_month': max(month_selections.values()), 'selected_candidate_raw_or_body_reads_only': True, 'whole_corpus_reaudit': False, 'network_operations': 0, 'new_raw_downloads': 0, 'database_access': False, 'shared_log_edits': False, 'git_access': False, 'semantic_or_fear_labels_executed': False, 'length_gate': False, 'fixed_deadline': SCOPE['hard_deadline_at_utc'], 'code_sha256': digest(pathlib.Path(__file__).read_bytes())}
    files['ARTICLE_REGISTER.jsonl'] = ''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in records).encode()
    register_buffer = io.StringIO()
    register_fields = ['article_id','candidate_record_id','disposition','title','source_id','stratum','publication_date','source_url','complete_body_reference','candidate_body_reference','canonical_article_id','work_family_id','disposition_reason']
    register_writer = csv.DictWriter(register_buffer, fieldnames=register_fields, extrasaction='ignore')
    register_writer.writeheader(); register_writer.writerows(records)
    files['ARTICLE_REGISTER.csv'] = register_buffer.getvalue().encode()
    frontier_buffer = io.StringIO()
    frontier_writer = csv.DictWriter(frontier_buffer, fieldnames=['article_id','month','source_url','candidate_body_reference','reason','eligible_for_fixed_interval','next_action_requires_separate_release'])
    frontier_writer.writeheader()
    for r in records:
        if r['disposition'] == 'pending':
            frontier_writer.writerow({'article_id': r['article_id'], 'month': r['publication_date'][:7], 'source_url': r['source_url'], 'candidate_body_reference': r['candidate_body_reference'], 'reason': r['disposition_reason'], 'eligible_for_fixed_interval': r['eligible_publication_interval'], 'next_action_requires_separate_release': 'Resolve named original item/date/transcription evidence; no new collection or second-article fabrication in this correction'})
    files['PENDING_FRONTIER.csv'] = frontier_buffer.getvalue().encode()
    files['IDENTITY_MAP.json'] = (json.dumps({'identity_basis': 'Persisted publisher item/canonical identity or native print article locator; immutable across body/version corrections', 'identity_key_to_article_id': identities}, indent=2)+'\n').encode()
    files['CORRECTIONS_MANIFEST.json'] = (json.dumps(corrections, indent=2)+'\n').encode()
    files['INSPECTION_RECEIPT.json'] = (json.dumps({'selected_only': True, 'prior_month_selection_counts': dict(month_selections), 'inspected_candidates': inspected}, indent=2)+'\n').encode()
    files['BODY_BOUNDARY_QA.json'] = (json.dumps({'at_utc': now(), 'selected_confirmed_HTML_articles_only': True, 'complete_native_paragraph_presence_checks': body_boundary_qa, 'all_missing_paragraph_counts_zero': all(x['missing_native_paragraphs'] == 0 for x in body_boundary_qa)}, indent=2)+'\n').encode()
    checks['confirmed_HTML_unique_source_container_and_native_paragraph_presence'] = len(body_boundary_qa) == dispositions['confirmed_complete'] and all(x['missing_native_paragraphs'] == 0 for x in body_boundary_qa)
    files['VERIFICATION.json'] = (json.dumps(checks, indent=2)+'\n').encode()
    files['COVERAGE_SUMMARY.json'] = (json.dumps(summary, indent=2)+'\n').encode()
    files['VERIFICATION.json'] = (json.dumps(checks, indent=2)+'\n').encode()
    for geo, rows in ledgers.items():
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
        files['ledgers/' + ('EU_Europe_excluding_UK' if geo.startswith('EU/') else geo) + '.csv'] = buf.getvalue().encode()
    table = '\n'.join('| '+g+' | '+str(s['state_0'])+' | '+str(s['state_1_below_minimum'])+' | '+str(s['state_2plus_meets_article_count_minimum'])+' | '+str(s['total_confirmed_distinct_articles'])+' |' for g,s in summaries.items())
    report = f'''# Local complete-article baseline reconciliation

The hard monthly lower bound is **two complete, distinct original publication articles**, with every additional qualified article retained. This local register confirms **{dispositions['confirmed_complete']} articles** from the fixed selected evidence. **{summaries['pooled']['state_2plus_meets_article_count_minimum']}/465 pooled months meet the article-count minimum**; {summaries['pooled']['state_1_below_minimum']} months have one and {summaries['pooled']['state_0']} have none confirmed in this bounded register. This does not establish full-period collection or absence of newspaper discourse in gaps.

| Ledger | 0 confirmed | 1: below minimum | 2+: meets minimum | Confirmed distinct article total |
| --- | ---: | ---: | ---: | ---: |
{table}

All six ledgers use January 1988–September 2026, publication cutoff **2026-09-21**. September is partial. Pooled passing months do not establish regional completeness. These counts measure the inspected evidence, not all articles already saved in the earlier corpus: only at most three previously selected candidate parents per each of {len(month_selections)} observed prior months were inspected, without refill. No new network, raw download or source discovery was performed.

## Unit correction and frozen evidence

The frozen tranche reported 45 readable HTML units and 3 mapped readable article spans (48 readable units), and 86 combined readable months. Those historical figures remain unchanged. Readable pages, tables, article spans and issue containers were not retrospectively renamed complete articles. This correction confirms {tranche_counts['successor'].get('confirmed_complete',0)} complete successor articles and {tranche_counts['prior'].get('confirmed_complete',0)} complete selected prior articles. Four additional successor rows preserve missing-content/out-of-interval context; they are not extra released acquisition candidates.

The register has {len(records)} candidate rows: {dict(dispositions)}. `article_id` persists the observed publisher item identity; pending/non-article rows explicitly do not assert article status. Confirmed rows carry complete-body reference, title, source/edition, publication date, actual source link, and boundary/opening/ending evidence. Identity-map keys use canonical publication identities or accepted native print locators, never body hashes/retrieval times. Body `version_id`/hashes are separate. Actual PDF links have page/column sidecar locators; old invented fragment aliases are retained as history and never presented as publisher article permalinks.

The April 2008 Tech Table is a table-only component. Event schedules, fact/contact sidebars, empty activity content and unrelated notices cannot supply complete article counts. The August 2007 single roadworks brief and April 2007 single signed outage report qualify despite generic container headings; shortness/byline absence is not an exclusion. Multiple section headings in the 2008 pastry-debate report belong to one coherent article. The 2007 December multi-article News Briefs and 2025/2026 separately signed editorial collections remain pending item mapping and are not split to manufacture a second article. Incident-log unit interpretation also remains pending rather than being decided by genre alone.

## Corrected bodies and named limits

{len(corrections)} new whole-item derivatives and sidecars preserve the old bodies and scans. Three mapped PDF bodies have their generated `[CONTIGUOUS ARTICLE SEGMENT]` markers removed; printed page-turn/continuation cues and geometric offsets move to sidecars. The 1991 first-page missing department line is restored from the retained scan. Each named article has one derivative, not one article per column. Remaining noisy OCR and column-join fidelity are explicitly pending; removing markers does not certify a complete clean transcription. The 1988 accepted article-span record is preserved by reference with its severe transcription limits pending. No universal correctness claim is made.

Where the Mancunion's unique native standfirst was demonstrably absent from its selected body, it is restored before that same article's prose; standfirst text already inside the body is not duplicated. The selected July 2020 InDaily comment-submission footer is removed after the author biography in a new derivative. Source/body paths and hashes trace every correction.

The Barclay update explicitly says April 20, 2007 in its body but has an October 6 header/URL. Its cross-month publication/content-version conflict remains pending and cannot certify October coverage. Otago's frozen archive evidence has same-month day differences where recorded; supported monthly identity is retained while exact-day mapping remains unresolved. Current archive renditions do not prove historical body equivalence, and quotation does not assign an emotion to the newspaper or verify every quoted claim. Known exact saved-body/canonical relations are recorded separately; distinct publisher articles on the same event are not automatically duplicates. No impossible global proof of journalistic novelty is required.

## Delivery and frontier

- `ARTICLE_REGISTER.jsonl`: article/item identities, dispositions, source links and evidence; `ARTICLE_REGISTER.csv` provides a compact review view.
- `IDENTITY_MAP.json`: persisted identity map invariant under body correction and versions.
- `CORRECTIONS_MANIFEST.json`, `bodies/`, `sidecars/`: corrected whole-item bodies with provenance and geometry.
- `ledgers/`: pooled and five geographic 465-row ledgers; exact counts retain surplus and apply `count >= 2`.
- `PENDING_FRONTIER.csv`: 17 named unresolved candidates, including the out-of-interval reference; no inference that other unsampled saved articles are absent.
- `INSPECTION_RECEIPT.json`, `BODY_BOUNDARY_QA.json`, `VERIFICATION.json`, `RESOURCE_RECEIPT.json`: bounded-selection, source-paragraph presence, frozen-input and resource checks. Every confirmed HTML article has one inspected native content container and all its native narrative paragraphs present in the saved/corrected body, with the documented publisher-footer removal treated separately. This supports completeness within the observed source rendition, not universal historical equivalence.

Every 0/1 cell remains below the minimum. Further article acquisition, OCR restoration, native aggregate-item mapping or date adjudication needs a separately bounded successor release; this local correction does not reopen requests or acquire a second article. All frozen input checks pass. Formal databases, government/social corpora, sealed evaluators, shared logs and Git were untouched. No climate/fear labels or semantic/length exclusions were executed. The original deadline is {SCOPE['hard_deadline_at_utc']} and remains unchanged.
'''
    files['REPORT.md'] = report.encode()
    total = sum(map(len, files.values()))
    with LOCK.open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        assert dt.datetime.now(dt.timezone.utc) < dt.datetime.fromisoformat(SCOPE['hard_deadline_at_utc'])
        before = budget(total)
        assert before['allocation_headroom_after_pending_bytes'] >= 0 and before['physical_headroom_after_pending_bytes'] >= 0, before
        for name, data in files.items():
            p = OUT / name
            assert p.is_relative_to(OUT)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        after = budget()
        after.update({'new_derivative_encoded_bytes': total, 'accounting_basis': 'All files under three inherited accounting roots plus prior 25,819,723 bytes; no deletion credit or allocation expansion', 'network_operations': 0, 'input_checks_passed': True, 'before_write': before, 'deadline_passed_at_completion': dt.datetime.now(dt.timezone.utc) >= dt.datetime.fromisoformat(SCOPE['hard_deadline_at_utc'])})
        (OUT/'RESOURCE_RECEIPT.json').write_text(json.dumps(after, indent=2)+'\n')
        assert after['allocation_headroom_after_pending_bytes'] >= 0 and after['physical_headroom_after_pending_bytes'] >= 0
    print(json.dumps({'register_rows': len(records), 'dispositions': dict(dispositions), 'corrections': len(corrections), 'coverage': summaries, 'derived_bytes': total, 'completed_at_utc': now()}))

if __name__ == '__main__':
    main()
