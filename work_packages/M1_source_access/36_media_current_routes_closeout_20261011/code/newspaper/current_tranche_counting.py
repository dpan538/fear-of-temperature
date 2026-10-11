"""Explicit named dispositions affect current counts, not historical receipts."""
import json
from pathlib import Path
W=Path(__file__).resolve().parent
def countable_rows(loads):
 p=W/'NAMED_BOUNDARY_CORRECTION_DONE.json';hold=json.loads(p.read_text()) if p.exists() else {}
 return {r['article_id']:r for r in loads if r.get('load_status')=='confirmed_complete' and not (r['article_id']==hold.get('article_id') and hold.get('current_countable') is False)}

def reporting_subframe(r):
 if r['article_id'].startswith('workers_advocate:supplement:'):return 'workers_advocate_Supplement_separate'
 if r.get('stratum')=='English-region expansion':return 'expanded_english_newspaper_frame'
 if r.get('source_id')!='about_time':return 'regular_newspaper_frame'
 genre=r.get('publisher_native_genre')
 if genre in {'Poetry','Creative'}:return 'creative_work_separate'
 if genre=='Letters':return 'reader_letters_separate'
 if genre=='Experiences':return 'firsthand_experiences_separate'
 if genre=='Play':return 'puzzles_play_separate'
 if not genre:return 'native_genre_unresolved_separate'
 return 'regular_newspaper_frame'
def regular_rows(rows):return {aid:r for aid,r in rows.items() if reporting_subframe(r) in ['regular_newspaper_frame','expanded_english_newspaper_frame']}
