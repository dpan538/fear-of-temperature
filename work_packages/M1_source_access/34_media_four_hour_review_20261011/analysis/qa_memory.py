"""Audit a generated PDF supplied on stdin, without persisting an extra QA asset."""
from pathlib import Path
import json,sys
sys.path.insert(0,'/Users/jarlgiovanni/.codex/skills/nature-figure/scripts')
from audit_pdf_text import audit_pdf as audit_text
import audit_figure_collisions as collision
try:
    import pymupdf as fitz
except ImportError:
    import fitz

def main():
    data=sys.stdin.buffer.read()
    if not data.startswith(b'%PDF-'):raise ValueError('Only a newly rendered PDF is accepted on stdin')
    native_open=fitz.open
    sentinel=Path('__generated_in_memory_pdf__')
    def memory_open(path,*args,**kwargs):
        if path==sentinel:return native_open(stream=data,filetype='pdf')
        return native_open(path,*args,**kwargs)
    fitz.open=memory_open
    text=audit_text(data,minimum_pt=5)
    rendered=collision.audit_pdf(sentinel)
    result={'pdf_text':text,'collision':rendered,'PDF_persisted':False}
    ok=text['auditable'] and text['below_minimum_count']==0 and collision.exit_code(rendered)==0
    print(json.dumps(result))
    return 0 if ok else 1
if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print(json.dumps({'error':str(exc)}));sys.exit(1)
