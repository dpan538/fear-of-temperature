"""One read-only verification of the 20 saved EU Items, never a corpus extractor."""
import csv
import fcntl
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WP = ROOT / 'work_packages/M1_source_access'
SOURCE = WP / '18_bounded_supplementation_execution_20261005/02_eu_staging/STAGING_INGESTION_HANDOFF.csv'
LOCK = WP / '14_structural_validation_20261004/control/heavy_io.lock'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def save_csv(name, rows):
    with (HERE / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)


def main():
    rows = list(csv.DictReader(SOURCE.open()))
    assert len(rows) == 20 and len({r['item_uri'] for r in rows}) == 20
    shapes, page_rows, first_pages, images = [], [], [], []
    (HERE / 'evidence').mkdir(exist_ok=True)
    with LOCK.open('a+') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for i, row in enumerate(rows, 1):
            path = ROOT / row['raw_path']
            assert not path.is_symlink()
            before = path.stat()
            raw_hash = digest(path)
            assert raw_hash == row['raw_sha256'] and before.st_size == int(row['raw_bytes'])
            with path.open('rb') as f:
                signature = f.read(1024).lstrip(b'\xef\xbb\xbf \r\n\t').startswith(b'%PDF-')
            assert signature
            doc = pdfium.PdfDocument(str(path))
            assert len(doc) > 0
            texts, per_page = [], []
            for n in range(len(doc)):
                page = doc[n]
                tp = page.get_textpage()
                text = tp.get_text_range()
                texts.append(text)
                p = {'item_uri': row['item_uri'], 'pdf_page_number': n + 1,
                     'text_codepoints': len(text), 'nonspace_codepoints': sum(not c.isspace() for c in text),
                     'whitespace_tokens': len(text.split()), 'empty_text': not text.strip(),
                     'width_pt': round(page.get_width(), 3), 'height_pt': round(page.get_height(), 3),
                     'unit': 'PDF page; not document parent'}
                per_page.append(p); page_rows.append(p)
                if n == 0:
                    thumb = page.render(scale=0.75).to_pil().convert('RGB')
                    thumb.thumbnail((440, 620))
                    images.append((i, thumb.copy()))
                tp.close(); page.close()
            doc.close()
            assert before.st_size == path.stat().st_size and before.st_mtime_ns == path.stat().st_mtime_ns
            body = '\n'.join(texts)
            first_pages.append({'sequence': i, 'item_uri': row['item_uri'], 'raw_path': row['raw_path'],
                                'evidence_page': 1, 'first_page_text': texts[0],
                                'scope': 'identity/date/genre evidence only; not full-text corpus ingestion'})
            shape = {k: row[k] for k in ['parent_id','expression_uri','manifestation_uri','item_uri','source_id',
                      'jurisdiction','issuer','genre','language','publication_dates','publication_month',
                      'metadata_checkpoint_utc','retrieved_at_utc','format','raw_path','raw_sha256','raw_bytes',
                      'selected_manifestation_item_count','content_version_etag','content_version_last_modified'] if k in row}
            shape.update(sequence=i, raw_sha256_rechecked=raw_hash, sha256_matches=True, signature_pdf=True,
                         pdf_page_count=len(per_page), text_codepoints=len(body),
                         nonspace_codepoints=sum(not c.isspace() for c in body), whitespace_tokens=len(body.split()),
                         empty_text_page_count=sum(p['empty_text'] for p in per_page),
                         replacement_codepoint_count=body.count('\ufffd'),
                         text_layer_status='nonempty_text_layer' if body.strip() else 'no_text_layer',
                         visual_check='pending', ocr_status='not_run',
                         ocr_need='unresolved_for_empty_pages' if any(p['empty_text'] for p in per_page) else 'no_empty_text_pages',
                         content_identity_status='pending_first_page_check', printed_issue_date='',
                         printed_reference='', printed_title='', printed_component_role='',
                         complete_work_status='unestablished: one selected Item, no all-component verification',
                         historical_version_equivalence='unknown', parent_statistics_eligible=False,
                         length_unit='one saved PDF Item; whitespace tokens are structural counts',
                         new_parent_created=False, formal_database_writes=0)
            shapes.append(shape)
        fcntl.flock(lock, fcntl.LOCK_UN)
    save_csv('CHANGED_ITEM_TEXT_SHAPE.csv', shapes)
    save_csv('PDF_PAGE_SHAPE.csv', page_rows)
    (HERE / 'evidence/FIRST_PAGE_IDENTITY.json').write_text(json.dumps(first_pages, ensure_ascii=False, indent=2)+'\n')
    for batch in range(2):
        sheet = Image.new('RGB', (5*460, 2*680), 'white')
        draw = ImageDraw.Draw(sheet)
        for j, (i, thumb) in enumerate(images[batch*10:(batch+1)*10]):
            x, y = j%5*460, j//5*680
            draw.text((x+8, y+8), f'Item {i:02d} - first page', fill='black')
            sheet.paste(thumb, (x+8, y+35))
        sheet.save(HERE / f'evidence/FIRST_PAGES_{batch+1:02d}.png')
    result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'input_sha256': digest(SOURCE),
              'item_count': len(shapes), 'raw_bytes_rechecked': sum(int(r['raw_bytes']) for r in shapes),
              'pages': len(page_rows), 'empty_text_pages': sum(p['empty_text'] for p in page_rows),
              'all_raw_hashes_match': True, 'raw_modified': False,
              'network_requests': 0, 'formal_database_reads': 0, 'formal_database_writes': 0,
              'full_corpus_reads': False, 'visual_identity_check': 'pending',
              'page_count_distribution': dict(Counter(r['pdf_page_count'] for r in shapes))}
    (HERE / 'CHANGED_ITEM_CHECK.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
