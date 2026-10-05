"""Reproduce local checks of only the11 new selected PDFs; no network or database."""
import fitz
from PIL import Image,ImageDraw
import transport as t

def main():
 targets=t.read(t.OUT/'government/TARGET_SEQUENCE.json')['targets'];receipts=[t.read(p) for p in sorted((t.OUT/'government/attempts').glob('*.json'))]
 if len(receipts)!=11 or [r['request_url'] for r in receipts]!=[x['request_url'] for x in targets]:raise RuntimeError('Exact new bounded sequence required')
 out=t.OUT/'government/evidence';out.mkdir(exist_ok=True);rows=[];tiles=[]
 with t.lock():
  t.budget(8*1024*1024,lane='government')
  for i,r in enumerate(receipts,1):
   raw=t.OUT/r['raw_path']
   if r['status']!='saved' or t.digest(raw)!=r['sha256']:raise RuntimeError('New PDF raw identity differs')
   d=fitz.open(raw);texts=[page.get_text() for page in d];(out/f'{i:02d}.txt').write_text('\n\f\n'.join(texts))
   rows.append(dict(sequence=i,request_id=r['request_id'],item_uri=r['item_uri'],parent_id=r['parent_id'],cdm_publication_dates=r['publication_dates'],pages=d.page_count,page_text_chars=[len(x.strip()) for x in texts],first_page=texts[0][:3200],last_page_end=texts[-1][-600:],metadata=d.metadata))
   pix=d[0].get_pixmap(matrix=fitz.Matrix(.7,.7));im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples);im.thumbnail((420,570));tile=Image.new('RGB',(440,610),'white');tile.paste(im,((440-im.width)//2,30));ImageDraw.Draw(tile).text((10,8),f'{i:02d} | {d.page_count} pages | CDM {r["publication_dates"]}',fill='black');tiles.append(tile);d.close()
  for n in range(3):
   contact=Image.new('RGB',(880,1220),'#ddd')
   for j,im in enumerate(tiles[n*4:(n+1)*4]):contact.paste(im,((j%2)*440,(j//2)*610))
   contact.save(out/f'first_pages_{n+1}.png')
  t.save(out/'inspection.json',rows)
 # Outputs support manual visual/identity/date inspection; no automatic complete Work approval.
if __name__=='__main__':main()
