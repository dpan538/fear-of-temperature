"""Pin only named closed exports. Never open a corpus DB or scan body/raw trees."""
import csv
import fcntl
import gzip
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PKG = ROOT / 'work_packages/M1_source_access/27_newspaper_context_recovery_20261008'
NP = PKG / 'continuations/20261009_nine_hour_newspaper/worker'
S9 = PKG / 'social_public_api/continuations/20261009_nine_hour_social/worker'
S4 = PKG / 'social_public_api/continuations/20261010_four_hour_historical_repair/worker'
P29 = ROOT / 'work_packages/M1_source_access/29_media_round_review_20261010'
PIN = OUT / 'worker/pinned'
BOUND = 16 * 1024 * 1024

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write_csv(path, rows, fields):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def main():
    lockpath = ROOT / 'work_packages/M1_source_access/14_structural_validation_20261004/control/heavy_io.lock'
    with lockpath.open('rb') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        free = shutil.disk_usage(OUT).free
        if free - BOUND < 16106127360 + 50331648:
            raise RuntimeError('physical floor / recovery would be breached')
        PIN.mkdir(parents=True, exist_ok=False)
        manifest = {'pinned_at_utc': datetime.now(timezone.utc).isoformat(),
                    'physical_free_before_bytes': free, 'bounded_write_reserve_bytes': BOUND,
                    'input_files': [], 'copies': [], 'metadata_read_counts': {},
                    'corpus_database_reads': 0, 'raw_body_reads': 0,
                    'shared_accounting': 'All package30 retained bytes are charged within the shared 30GB; no counter/control change or separate allocation.'}
        paths = [(P29/'analysis.json','p29_analysis.json'), (P29/'input_manifest.json','p29_input_manifest.json'),
                 (P29/'ERRATUM_20261010.md','p29_erratum.md'), (NP/'DELIVERY_SUMMARY.json','np9_summary.json'),
                 (NP/'SOURCE_PARENT_IDENTITY_REGISTER.csv','np9_parent.csv'),
                 (NP/'EXACT_BODY_OVERLAP_REVIEW_REGISTER.csv','np9_overlap.csv')]
        paths += [(p, 'p29_'+p.name) for p in sorted((P29/'tables').glob('*.csv'))]
        for base, label in [(S9,'s9'),(S4,'s4')]:
            paths += [(base/'summaries'/name,label+'_'+name) for name in
                      ['collection_manifest.json','delivery_file_manifest.json','source_month_calendar.csv',
                       'native_date_mapping_limits.csv','adjacent_month_flags.csv','COLLECTION_REPORT.md',
                       'source_native_type_counts.csv','content_states.csv','role_summary.csv']]
            paths += [(base/'source_registry.json', label+'_source_registry.json')]
        paths += [(S4/'NAMED_DATE_VERIFICATION.json','s4_named_date.json'),
                  (S4/'INHERITED_MASTODON_CURSOR_DIAGNOSTIC.json','s4_mastodon_diagnostic.json'),
                  (S4/'summaries/changed_date_resolution_limits.csv.gz','s4_changed_date_limits.csv.gz'),
                  (S4/'summaries/round_source_year_deltas.csv','s4_year_deltas.csv')]
        for original, name in paths:
            before = digest(original)
            shutil.copyfile(original, PIN/name)
            after = digest(original)
            assert before == after == digest(PIN/name), original
            manifest['input_files'].append({'path':str(original.relative_to(ROOT)), 'bytes': original.stat().st_size, 'sha256':before})
            manifest['copies'].append({'path':str((PIN/name).relative_to(OUT)), 'sha256':before})
        # One streaming pass over a closed newspaper metadata register; no body text copied.
        fields = ['article_id','source_id','source_url','title','publication_date','stratum','work_family_id',
                  'version_id','body_sha256','body_reference','raw_reference','retrieved_at_utc','content_version_time',
                  'publisher_timestamp','date_field','url_date','date_limit','publisher_sidebar_metadata',
                  'source_native_article_id','canonical_mapping_status','source_native_post_id','native_listing_month']
        original = NP/'CURRENT_NEWSPAPER_ARTICLE_REGISTER.csv'
        before = digest(original)
        rows=[]; count=0
        with original.open(newline='') as f:
            for row in csv.DictReader(f):
                count += 1
                if row['publication_date'].startswith('2026-'):
                    rows.append({k: row.get(k,'') for k in fields})
        assert before == digest(original)
        write_csv(PIN/'np9_2026_metadata.csv', rows, fields)
        manifest['input_files'].append({'path':str(original.relative_to(ROOT)), 'bytes':original.stat().st_size, 'sha256':before, 'derived_subset':'worker/pinned/np9_2026_metadata.csv'})
        manifest['metadata_read_counts']['newspaper_register_rows']=count
        manifest['metadata_read_counts']['newspaper_2026_rows']=len(rows)
        # Closed 8.95MB compressed entity metadata only: pick first/last 2026 native entity per source.
        # Endpoints after the study cutoff intentionally diagnose catalog/body-unit separation.
        # This sample does not assert membership in qualified-body counts.
        original=S9/'summaries/native_entities_manifest.csv.gz'
        before=digest(original); selected={}; counts={}; metadata_fields=None; count=0
        with gzip.open(original,'rt',newline='') as f:
            reader=csv.DictReader(f); metadata_fields=reader.fieldnames
            for row in reader:
                count += 1
                if not row['native_created_at'].startswith('2026-'):continue
                source=row['source_id']; counts[source]=counts.get(source,0)+1
                key=(row['native_created_at'],row['entity_id'])
                pair=selected.setdefault(source,[row,row])
                if key < (pair[0]['native_created_at'],pair[0]['entity_id']):pair[0]=row
                if key > (pair[1]['native_created_at'],pair[1]['entity_id']):pair[1]=row
        assert before==digest(original)
        unique={row['entity_id']:row for pair in selected.values() for row in pair}
        write_csv(PIN/'s9_2026_endpoint_sample.csv',sorted(unique.values(),key=lambda x:(x['source_id'],x['native_created_at'])),metadata_fields)
        manifest['input_files'].append({'path':str(original.relative_to(ROOT)), 'bytes':original.stat().st_size,'sha256':before,'derived_subset':'worker/pinned/s9_2026_endpoint_sample.csv'})
        manifest['metadata_read_counts']['social_native_entity_rows']=count
        manifest['metadata_read_counts']['social_2026_native_entity_rows_by_source']=counts
        manifest['metadata_read_counts']['social_selected_native_entities']=len(unique)
        manifest['pinned_retained_bytes_before_manifest']=sum(p.stat().st_size for p in PIN.iterdir())
        assert manifest['pinned_retained_bytes_before_manifest'] < BOUND
        (OUT/'worker/INPUT_PIN_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(json.dumps({'retained_bytes':manifest['pinned_retained_bytes_before_manifest'],'rows':manifest['metadata_read_counts']},indent=2))

if __name__=='__main__':main()
