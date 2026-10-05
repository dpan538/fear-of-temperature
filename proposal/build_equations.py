"""Numbered vector display equations with matching HTML and plain-text forms."""
from pathlib import Path
import os, sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.runtime'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'qa/matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import Flowable
from pdfrw import PdfReader
from pdfrw.buildxobj import pagexobj
from pdfrw.toreportlab import makerl

SPECS={
 'attention':(1,r'S_{rt}=\frac{\sum_{i\in\mathcal{U}_{rt}}w_i R_i}{\sum_{i\in\mathcal{U}_{rt}}w_i}', 'S_rt = sum(w_i R_i) / sum(w_i)'),
 'emotion':(2,r'q_p=\frac{1}{|\mathcal{A}|}\sum_{a\in\mathcal{A}}\cos(\boldsymbol{z}_p,\boldsymbol{z}_a)', 'q_p = mean cosine similarity to fixed reference set A'),
 'joint':(3,r'Q_{rt}=\frac{\sum_{i\in\mathcal{U}_{rt}}w_i R_i \bar{q}_i}{\sum_{i\in\mathcal{U}_{rt}}w_i R_i}', 'Q_rt = sum(w_i R_i mean_passage_q_i) / sum(w_i R_i)'),
 'ccf':(4,r'C_{XY}(k)=\operatorname{Corr}\,\left(X_t,\,Y_{t+k}\right)', 'C_XY(k) = Corr(X_t, Y_(t+k)); positive k: X precedes Y'),
 'its':(5,r'Y_t=\beta_0+\beta_1t+\beta_2D_t+\beta_3(tD_t)+u_t', 'Y_t = beta_0 + beta_1 t + beta_2 D_t + beta_3 (t D_t) + u_t'),
}
class Equation(Flowable):
 def __init__(self,path,width,height):
  super().__init__();self.width=width;self.height=height
  self.page=pagexobj(PdfReader(str(path)).pages[0]);self.spaceBefore=4;self.spaceAfter=7
 def draw(self):self.canv.doForm(makerl(self.canv,self.page))

def build(width):
 out={};dest=ROOT/'assets/equations';dest.mkdir(exist_ok=True)
 with matplotlib.rc_context({'font.family':'STIXGeneral','mathtext.fontset':'stix','svg.fonttype':'path','pdf.fonttype':42}):
  for key,(number,formula,plain) in SPECS.items():
   height=49 if number<4 else 35
   fig=plt.figure(figsize=(width/72,height/72),facecolor='white')
   fig.text(.50,.48,'$'+formula+'$',ha='center',va='center',fontsize=14,color='#17222B')
   fig.text(.99,.48,f'({number})',ha='right',va='center',fontsize=12,color='#17222B')
   for ext in ['pdf','svg']:fig.savefig(dest/f'{key}.{ext}')
   plt.close(fig);out[key]=Equation(dest/f'{key}.pdf',width,height)
 return out
