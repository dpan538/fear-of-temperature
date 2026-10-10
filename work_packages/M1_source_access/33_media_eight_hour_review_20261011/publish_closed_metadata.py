"""Copy selected closed acquisition deliverables, preserving original hashes.

Run once from the repository root after accepted changed-tranche settlement.
This reads named finalized metadata/code only; never bodies, stores or raw trees.
Runtime leases, queues, checkpoints and owner handoffs remain local.
"""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parent
MEDIA = ROOT / 'work_packages/M1_source_access/27_newspaper_context_recovery_20261008'
PHASES = {
    'broader_history': '20261010_broader_history_four_hour',
    'eight_hour': '20261010_eight_hour_focused_repair',
}
NP_OMIT = {'CONTINUATION_DIGEST.md', 'TERMINAL_WRITER_EXIT.json'}
SOCIAL_OMIT = {
    'new_native_entities.csv.gz', 'changed_entity_versions.csv.gz',
    'new_entity_observations.csv.gz', 'new_relations.csv.gz',
    'affected_incoming_relations.csv.gz', 'affected_native_aliases.csv.gz',
    'affected_publication_memberships.csv.gz',
    'changed_source_provenance.csv.gz', 'new_attachment_metadata.csv.gz',
    'focused_repair_evidence.json',
}
NP_CODE_OMIT = {'bind_predecessor.py', 'start.py', 'prepare_focused.py', 'watch_deadline.py'}
SOCIAL_CODE_OMIT = {'bootstrap.py'}
NP_VALIDATION = {
    'broader_history': ['NATIVE_MAPPING_CHECK.json', 'FINAL_ID_CONSERVATION_CHECK.json',
                       'SCHEDULER_AGING_CHECK.json'],
    'eight_hour': ['CHANGED_CHAIN_CHECK.json', 'FOCUSED_REGRESSION_CHECK.json',
                   'NAMED_ROUTE_REGRESSION_CHECK.json', 'NATIVE_ALIAS_AND_HTML_CHANGED_CHAIN_CHECK.json',
                   'BERKELEY_CHANGED_CHAIN_CHECK.json', 'BERKELEY_MULTI_CARRIER_CHANGED_CHAIN_CHECK.json',
                   'BERKELEY_NAMED_CARRIER_PREP_CHECK.json', 'PROGRESS_CAPACITY_LOCK_CHANGED_CHECK.json'],
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publish():
    records = []

    def copy(src, destination, expected=None, kind='final_metadata'):
        actual = digest(src)
        if expected is not None:
            assert actual == expected, str(src)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            assert digest(destination) == actual, f'Frozen destination differs: {destination}'
        else:
            shutil.copyfile(src, destination)
        records.append({
            'source': str(src.relative_to(ROOT)),
            'published': str(destination.relative_to(ROOT)),
            'bytes': src.stat().st_size, 'sha256': actual, 'kind': kind,
        })

    for label, phase in PHASES.items():
        npw = MEDIA / 'continuations' / phase / 'worker'
        sw = MEDIA / 'social_public_api/continuations' / phase / 'worker'
        nmanifest = json.loads((npw / 'DELIVERY_FILE_RECEIPTS.json').read_text())
        for name, entry in nmanifest.items():
            if name in NP_OMIT:
                continue
            copy(npw / name, PACKAGE / 'closed' / label / 'newspaper' / name, entry['sha256'])
        for code in sorted(npw.glob('*.py')):
            if code.name not in NP_CODE_OMIT:
                copy(code, PACKAGE / 'closed' / label / 'newspaper/implementation' / code.name,
                     kind='closed_implementation')
        for name in NP_VALIDATION[label]:
            src = npw / name
            if src.exists():
                copy(src, PACKAGE / 'closed' / label / 'newspaper/validation' / name,
                     kind='accepted_changed_code_validation')
        for manifest_name in ['delivery_file_manifest.json', 'implementation_source_manifest.json']:
            manifest = json.loads((sw / 'summaries' / manifest_name).read_text())
            for entry in manifest['files']:
                name = Path(entry['path']).name
                if manifest_name.startswith('delivery'):
                    if name in SOCIAL_OMIT:
                        continue
                    destination = PACKAGE / 'closed' / label / 'social' / name
                    kind = 'final_metadata'
                else:
                    if name in SOCIAL_CODE_OMIT:
                        continue
                    destination = PACKAGE / 'closed' / label / 'social/implementation' / name
                    kind = 'closed_implementation'
                copy(sw / entry['path'], destination, entry['sha256'], kind)
    result = {
        'publication_boundary': 'Finalized tables/manifests and implementation only; runtime controls, queues, stores, raw and large entity/body exports remain local.',
        'original_bytes_preserved': True, 'raw_body_database_scan': False,
        'files': records, 'published_bytes': sum(x['bytes'] for x in records),
    }
    (PACKAGE / 'CLOSED_PUBLICATION_MANIFEST.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'copied_files': len(records), 'published_bytes': result['published_bytes']}))


if __name__ == '__main__':
    publish()
