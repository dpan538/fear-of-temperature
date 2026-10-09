"""Package finalized collection/schema/storage documentation with closed results."""
import csv,datetime as dt,json,statistics
import transport as t

def write():
 out=t.WORK/'summaries';m=t.read_json(out/'collection_manifest.json');quality={r['source_id']:r for r in csv.DictReader((out/'quality_by_source.csv').open())}
 months={}
 for r in csv.DictReader((out/'source_month_calendar.csv').open()):
  if int(r['publication_month_qualified_independent_bodies']):months.setdefault(r['source_id'],set()).add(r['month'])
 registry=t.read_json(out/'source_registry_final.json');sources={s['source_id']:s for s in registry}
 table='\n'.join(f"| {sources[sid]['title']} | {sources[sid]['stratum']} | {n['qualified_native_units']:,} | {len(months.get(sid,set()))} |" for n in m['qualified_by_source'] for sid in [n['source_id']])
 receipts={r['request_id']:r for r in (t.read_json(p) for p in (t.WORK/'receipts').glob('*.json'))};first={}
 for line in (t.WORK/'LOADS.jsonl').read_text().splitlines():
  r=json.loads(line);first.setdefault(r['request_id'],r)
 lag=[(dt.datetime.fromisoformat(r['at_utc'])-dt.datetime.fromisoformat(receipts[key]['retrieved_at'])).total_seconds() for key,r in first.items() if key in receipts]
 storage={'observed_first_load_requests':len(lag),'raw_saved_to_first_load_seconds':{'median':statistics.median(lag),'p95':sorted(lag)[int(len(lag)*.95)],'max':max(lag)},'interpretation':'end-to-end raw-to-Load interval includes shared-lock waits, registry work and recovery; not isolated SQLite write latency','lock_wait_or_commit_latency_separately_instrumented':False,'metadata_query_issue':'Unindexed correlated anti-join read did not return within more than 160 seconds; only the identified read was terminated and replaced by a bounded metadata pass. No database write was in that process.','power_failure_cross_file_atomicity_tested':False,'database_choice':'SQLite current collector; PostgreSQL next-stage catalog candidate if concurrent/network writers or indexed JSON/join needs warrant it'}
 t.atomic(t.WORK/'STORAGE_OBSERVATIONS.json',storage)
 report=f"""# Closed public native social collection and storage assessment

The continuation added **{m['new_qualified_native_units']:,} retained core text identities**, taking the independent social store from 1,566 to **{m['counts']['posts']:,} core records across 14 sources**. It reached the authorized **50,000 additional distinct native-object** boundary and stopped at **14:27:56 AEST on 9 October 2026**, before its fixed 16:41:51 deadline. No further collection or rolling successor is implied by unused request, byte or time allowance.

The publication interval remains **1988-01-01 through 2026-09-21**, with September partial. Native creation, edit/revision, retrieval, correction and snapshot times remain separate. API bodies retrieved on 9 October do not certify historical body versions or end-of-day completeness on 21 September.

## Closed measures and temporal limits

| Measure | Cumulative closed result |
|---|---:|
| Charged HTTP requests | {m['lifetime_charged_requests']:,} (971 in this continuation) |
| Distinct returned native-object ledger | {m['lifetime_distinct_returned_objects']:,} (50,000 additional) |
| Persisted typed entities | {m['counts']['native_entities']:,} |
| Immutable entity/state versions | {m['counts']['entity_versions']:,} |
| Retained core text records / core body versions | {m['counts']['posts']:,} / {m['counts']['versions']:,} |
| Complete independently authored body entities | {m['complete_independently_authored_body_entities']:,} |
| Independent bodies usable in the current dated-source view | {m['publication_month_qualified_independent_body_entities']:,} |
| Pooled usable observed native-time months | {m['pooled_observed_months']}/465 |
| Typed relations / attachment metadata records | {m['counts']['native_edges']:,} / {m['counts']['native_attachments']:,} |

The full 465-month source calendar remains visible. **165 months** have usable observed dating; the remaining **300** do not establish acquired historical social expression. Applicable eras differ by source. Months before evidenced platform existence are structurally inapplicable, and unknown founding/community eras are marked unknown rather than zero expression.

The uncorrected native-timestamp view contains **167 months**. Six Bluesky records report pre-2019 timestamps, before the documented project lower bound; three Earth Science records precede the documented beta day and need original/migration date mapping. All nine identities, raw responses and bodies remain retained. They do not establish source publication in those earlier bins. The 165-month view withholds these named date conflicts; it is observed corpus presence, not verified historical population coverage. One preserved Python native action remains in the core history but is excluded from independent-authorship counts. Other current API timestamps retain their source-specific uncertainty.

Every additional charged native identity is in the catalog. The 45-object difference between the lifetime ledger and catalog consists entirely of inherited first-wave returned objects outside its accepted text core that were not reobserved into the catalog. Persistent IDs are distinct from observations, wrappers, versions and canonical original-publication URI keys. Exact body equality alone does not merge published works.

| Source | Source opportunity stratum | Retained core texts | Usable observed months |
|---|---|---:|---:|
{table}

These strata describe source opportunities, not author nationality. There are 156 institutional Bluesky account records and {m['counts']['posts']-156:,} unknown-role core records; author country remains unknown. Source/native-type tables provide the separate body, entity, author, context, state and date measures. Version-state rows may overlap for an entity that moves from preview to complete text, and must not be summed as independent posts.

## Source frames and access evidence

The opportunity register contains 32 entries, including blocked or unresolved candidates. Regional entry counts remain within six per stratum; nine global entries represent eight platform/API families. Fourteen sources contribute core bodies. This is a bounded frame expansion, not exhaustive national or public coverage.

Stack Exchange uses annual native question pagination plus question/answer/comment chains. The source annual inventory and API page/quota restrictions remain explicit; no topical search or emotion screen selects bodies. Python, Straight Dope and OpenStreetMap use native Discourse indexes, full returned topic streams and bounded remaining-post routes. A complete native post is distinct from a complete thread: many parent/quote/reply endpoints remain unresolved.

Four Mastodon instance-local timelines continue backward by native IDs from the accepted cutoff observations. Their acquired span is still a few September 2026 days. Bluesky continues all queued actor-feed cursors from the official account's public following/follower graph. This contemporary graph frame includes people and organizations, and many accounts return no eligible text. It is neither random public sampling nor evidence of historical graph membership. Bluesky contributes most core records; collection composition must remain visible in later analyses.

Lemmy NZ, Aussie Zone, Feddit.org and Midwest.social use documented anonymous v3 local listings. Comment responses retain their returned root-post context with the root creator identity. A local community listing does not imply local authors or exclusively local original publications. The NZ/AU/EU/US descriptions are source-declared regional opportunities. Native title-only, deleted/removed, bot-account, language, media/link and federation fields remain evidence rather than rejection classifiers. Feddit.org's comment-route timeout and Midwest.social's post-route timeout remain stops; their other working routes continued.

Feddit UK's native metadata declares a private instance; no ordinary post/comment collection followed. Fairphone's current terms explicitly prohibit automated scraping; Monzo's personal-use condition remains unresolved for this project; Freetrade's forum route redirects to a company page. These candidates did not enter ordinary body collection. Inherited denials, source restrictions, quota/error stops and unavailable credential/application routes were preserved without retries or bypass.

Public reachability, the operational bounded local-retention assessment, native content licensing and redistribution remain separate source fields. Missing Creative Commons licensing alone is not an exclusion rule. Straight Dope and OpenStreetMap use documented current source-condition assessments for bounded local research retention; no general republication grant is asserted. Lemmy software licensing, a sidebar/rules licence or OSM map licensing does not license posts. Stack Exchange's returned content-licence fields remain version-specific evidence.

## Provenance, checks and structural corrections

Directness is relative to each utterance. Original native records obtained through the documented source API are distinguished from federated reproductions, repost wrappers and context containers. The source-provenance table records these dimensions separately from native identity/date/content mapping and original external-body verification. Federated originals were not separately fetched. Archival-reproduction, indirect/secondary and mixed provenance remain unresolved where independent origin or historical-version mapping was not established; the native-API mapping label does not certify historical originalness. A user's post can be direct evidence of that user's expression while indirectly reporting an external event or another speaker's claim. A verified raw-to-native mapping does not establish that every statement is true, that an author is an ordinary member of the public, or that a later body matches its historical version. No opaque quality score ranks these sources.

The changed-chain checks cover typed numeric collisions, preview-to-body identity stability, bodyless/missing-date states, nullable embeds/attachments, nested quote/reblog context, root creators, idempotent transactions, and source-specific field meaning. First-wave acceptance checks were reused. The terminal check verified SQLite integrity and foreign keys, **961 new saved raw responses**, **54,846 native return-observation mappings**, and the new body digests, with **zero pending mapping/parse issues** in this closed tranche. It reused 421 accepted body-hash references and preserved the first 50 legacy identities and all 1,566 first-wave IDs/versions. Accepted old raw/body evidence was not swept again.

Necessary repairs stayed local and additive. Preview type and nullable nested/attachment omissions were corrected with saved evidence. A named embedded-context recovery added 19 catalog entities and two core bodies without HTTP. The final source-field check found that Stack Exchange comment `post_type` means parent question/answer, whereas numeric Discourse `post_type` describes an event. Scoping the Discourse rule correctly appended **1,293 already-retained comments** to the core and preserved their prior entity versions, raw bytes, counters and correction evidence. Only those affected new bodies were checked for that repair; the accepted full terminal raw/body checks were reused when derived tables refreshed.

## Lightweight data-pool assessment

**Keep SQLite as the current separate transactional collector.** The present design already implements the useful local parts of a data pool: lossless original HTTP entity bytes in separately hashed gzip objects; a minimal response/provenance catalog; stable typed entities, immutable versions, native relations and source-native extension JSON; and reproducible derived coverage/quality views. Normalized JSON and stripped text are derivatives, not substitutes for original bytes. Unknown fields remain recoverable from raw objects. Bodyless, noisy, truncated, unavailable and parse-pending states can remain catalog evidence without fabricating readable-body coverage; this tranche has no remaining parse-pending content responses. Binary media was not downloaded.

Observed operation evidence supports this choice within the single-writer release. For {len(lag)} first-Load requests, raw-save to first durable Load had a median of **{statistics.median(lag):.2f}s**, a 95th percentile of **{sorted(lag)[int(len(lag)*.95)]:.2f}s**, and a maximum of **{max(lag):.2f}s**. These include shared-lock, registry and recovery work, and are not isolated database latency. Lock wait and commit time were not independently instrumented. The original terminal derivation, annotation, raw mapping and export processing took 21.60s; the named comment repair took 43.25s. Integrity/foreign-key checks passed after the meaningful append repair.

A real metadata anti-join without an entity-version lookup index did not return within more than 160 seconds. That read-only process was stopped and the view was obtained through a bounded metadata pass. The observation identifies a query/index issue rather than proving SQLite is inadequate. Repeated startup migration scans were also avoided by the accepted schema marker. No synthetic benchmark or old corpus audit was run.

SQLite permits one writer per database file; its official guidance favors local low-concurrency stores and recommends a client/server engine when network access or concurrent writers require it. This matches the present collector mutex. [SQLite appropriate uses](https://www.sqlite.org/whentouse.html), [SQLite transactions](https://www.sqlite.org/lang_transaction.html).

**Evaluate PostgreSQL for the next-stage shared metadata/entity catalog** if several collectors/analysts need simultaneous network access or writes, managed access/backup, or frequent indexed native-JSON and relation queries. Relational identity/provenance columns plus source-native JSONB are a suitable candidate; PostgreSQL supports JSONB querying/indexing and concurrency control. JSONB does not preserve whitespace, key order or duplicate keys, so immutable original response bytes must stay separate. This is a conditional recommendation, not an installed server, migration or claim of measured PostgreSQL superiority. [PostgreSQL JSON types](https://www.postgresql.org/docs/current/datatype-json.html), [PostgreSQL concurrency control](https://www.postgresql.org/docs/current/mvcc.html).

For continued single-owner local work, SQLite plus targeted entity/version/observation indexes and compact derived tables remains a reasonable option. A future migration should preserve source IDs, native namespaces, all persistent/body/version IDs, raw/stored digests, timestamps, relations and permissions; prove a reversible incremental cutover and recovery rather than copying the old corpus now. Raw objects, catalog and analytical views remain separate layers whichever catalog engine is chosen. Raw-file, SQLite-commit and JSON-counter writes are sequential durable steps, not one cross-file transaction; crash reconciliation remains an explicit design need. This run's idempotent replay and counter reconciliation support restartability but do not certify all power-failure points.

Future personal-voice material is a new source/role requirement. It does not establish ordinary-public roles for current records or authorize private, audio or additional source-family acquisition. Newspaper and campus-publication units remain outside this social store. No server was installed, no old corpus was copied and no stream was merged.

## Research and publication boundaries

1. **Dated presence and readable source text:** the source/native measures, 165-month view, provenance and named pending date mappings above are the present evidence.
2. **Climate/warming relevance and similarity:** deferred to a defined, validated analysis unit and source frame. Current volume is not climate relevance.
3. **Affect, risk, future-harm or responsibility association:** unexecuted and unvalidated here; these would not automatically measure fear.
4. **Fear-specific interpretation:** deferred to traceable original passages with holder, target, horizon, quotation and negation checked. No fear prevalence or comparable three-role time series is claimed.

There was no semantic, topic, emotion, fear, spam/bot or length-based exclusion; no flattening/downsampling or entropy/HHI optimization. High counts remain collection observations without event or causal attribution. Raw, stores, per-request receipts, controls, queues, leases, archived implementation states and runtime checkpoints stay local. Acquisition implementation, source/schema documentation, consolidated final manifests/tables and this English summary form the closed deliverable. The coordinator owns main publication and the shared English project-log update. This owner changed neither Git nor the shared log/control files.
"""
 with t.shared(t.footprint(0,len(report.encode())+262144)):
  (out/'COLLECTION_REPORT.md').write_text(report)
  schema=t.WORK/'NATIVE_SCHEMA_V2.md'
  add="""

## Closed source-native extensions and derived date view

Lemmy uses distinct `post` and `comment` namespaces. `lemmy.post`, `lemmy.comment`, `lemmy.creator`, `lemmy.community` and `lemmy.counts` retain their source meaning; a returned comment root uses the post's creator ID. A post name/title with no native body is `native_title_only_text`, retained as original title evidence rather than a complete article/post body. Native local/deleted/removed/bot/language flags are provenance, not semantic exclusion scores.

`post_type` is scoped by native namespace: Stack Exchange's comment parent-type string is distinct from Discourse's numeric regular/action/moderation event enum. The named repair preserves prior versions and logs derived values. `native_aliases` resolves Discourse topic/post-number endpoints. `publication_memberships` uses native original URIs where returned, otherwise typed source identity; exact text equality alone does not merge works. A Bluesky repost view without its native record URI uses an explicit derived event fingerprint, which may change with mutable returned profile metadata; it is not a guaranteed native persistent repost ID and never inflates authored-body coverage.

`entity_quality_annotations` records directness, independent-body evidence and temporal limits without a confidence ranking. `native_date_mapping_limits.csv` records nine named source-era conflicts. `source_month_calendar.csv` separates retained core text by reported native time, title-only evidence, unresolved date counts and usable independent-body dating. The underlying raw/body/creation fields are preserved. Current API dating and later body retrieval remain narrower evidence than a historically verified publication snapshot.

The minimal raw catalog records source, endpoint, retrieval/format, raw and stored hashes/bytes, and mapped or pending state. Unknown source fields remain in original raw responses; normalized extension JSON need not pretend to be a byte-exact payload. Raw-object storage, the transactional catalog and derived analytical views are separate layers. SQLite remains the current collector; the PostgreSQL-versus-SQLite next-stage assessment is included with the closed collection report.
"""
  if '## Closed source-native extensions and derived date view' not in schema.read_text():schema.write_text(schema.read_text()+add)
  (out/'README.md').write_text("# Closed public-native social continuation\n\nRead [COLLECTION_REPORT.md](COLLECTION_REPORT.md) for final collection counts, source/era limits, corrections, checks and the next-stage data-pool assessment. [collection_manifest.json](collection_manifest.json) binds the consolidated tables; [source_registry_final.json](source_registry_final.json) records separate access/retention/licensing/source conditions. [NATIVE_SCHEMA_V2.md](../NATIVE_SCHEMA_V2.md) documents units, versions and native extensions.\n\nThe corpus interval is 1988-01-01 through 2026-09-21. The continuation closed at its 50,000-additional-object limit. Scripts require the original local owner/release controls; implementation publication does not authorize another run. Raw bytes, SQLite, runtime/per-target receipt files, queues and archives remain local. Consolidated manifests retain traceable local evidence references.\n")
  m=t.read_json(out/'collection_manifest.json');m['storage_assessment_observations']=storage;m['final_documentation_at_utc']=t.utc()
  for p in [out/'COLLECTION_REPORT.md',out/'README.md',schema]:
   item={'path':str(p.relative_to(t.WORK)),'bytes':p.stat().st_size,'sha256':t.sha(p.read_bytes())};m['files']=[x for x in m['files'] if x['path']!=item['path']]+[item]
  m['implementation_hashes'].update({p.name:t.sha(p.read_bytes()) for p in list(t.WORK.glob('*.py'))+list(t.WORK.glob('schema*.sql'))})
  t.atomic(out/'collection_manifest.json',m);t.atomic(t.WORK/'CLOSED.json',{'at_utc':t.utc(),'manifest_sha256':t.sha((out/'collection_manifest.json').read_bytes()),'snapshot':m})
  selected=[t.WORK/name for name in ['collect.py','transport.py','entities.py','lemmy_adapter.py','schema_legacy.sql','schema_v2.sql','check_changed.py','closeout.py','raw_catalog.py','enrich_relations.py','finalize_metadata.py','finalize_dated_coverage.py','repair_native_post_type.py','refresh_after_named_repairs.py','write_collection_report.py','NATIVE_SCHEMA_V2.md']]+list(out.glob('*.csv'))+[out/'collection_manifest.json',out/'source_registry_final.json',out/'README.md',out/'COLLECTION_REPORT.md']
  package={'finalized_at_utc':t.utc(),'collection_manifest_sha256':t.sha((out/'collection_manifest.json').read_bytes()),'selected_files':[{'path':str(p.relative_to(t.WORK)),'sha256':t.sha(p.read_bytes()),'bytes':p.stat().st_size} for p in selected],'raw_stores_controls_runtime_receipts_queues_archives_local':True,'git_or_shared_project_log_changed':False}
  t.atomic(out/'delivery_file_manifest.json',package)
 print(json.dumps({'report':str(out/'COLLECTION_REPORT.md'),'selected_final_files':len(selected),'pooled_months':m['pooled_observed_months'],'core_records':m['counts']['posts']}))
if __name__=='__main__':
 with t.writer():write()
