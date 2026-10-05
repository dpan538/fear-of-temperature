"""Vector wrappers for the Python visual research-plan figures."""
from pathlib import Path
import sys, os
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.runtime'))
from reportlab.platypus import Flowable
from pdfrw import PdfReader
from pdfrw.buildxobj import pagexobj
from pdfrw.toreportlab import makerl
import pymupdf as fitz
from visual_redesign import make_all
DESCRIPTIONS={}
class VectorFigure(Flowable):
 def __init__(self,path):
  super().__init__();self.page=pagexobj(PdfReader(str(path)).pages[0]);self.width=float(self.page.BBox[2]);self.height=float(self.page.BBox[3]);self._audit=[]
  with fitz.open(str(path)) as pdf:
   for b in pdf[0].get_text('dict')['blocks']:
    for line in b.get('lines',[]):
     for s in line['spans']:
      bb=s['bbox'];self._audit.append(dict(text=s['text'],x=bb[0],top=bb[1],width=bb[2]-bb[0],size=s['size']))
 def draw(self):self.canv.doForm(makerl(self.canv,self.page))
def make_figures():
 figures={}
 bases=[ROOT/'assets'/name for name in ['figure_01_relationships','figure_06_mechanisms','figure_07_rq_routes','figure_08_sampling','figure_02_pipeline','figure_03_evidence','figure_04_temporal','figure_05_schedule']] if os.environ.get('PROPOSAL_REUSE_FIGURES')=='1' else make_all()
 for base in bases:
  f=VectorFigure(str(base)+'.pdf');figures[base.name]=f;DESCRIPTIONS[base.name]=' | '.join(a['text'] for a in f._audit)
 return figures
