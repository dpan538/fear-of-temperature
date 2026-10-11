"""Preserve reduced publication dates; no first-day imputation or schema change."""
import calendar,datetime as dt,re
LOW='1988-01-01';HIGH='2026-09-21'
def bounds(value):
 if re.fullmatch(r'\d{4}-\d{2}',value or ''):
  year,month=map(int,value.split('-'));last=calendar.monthrange(year,month)[1]
  return dt.date(year,month,1).isoformat(),dt.date(year,month,last).isoformat()
 day=dt.date.fromisoformat(value);assert day.isoformat()==value;return value,value
def eligible_record(record):
 try:
  value=record.get('publication_date');low,high=bounds(value)
  if len(value)==7:
   proof=record.get('publication_date_reference') or {}
   if record.get('source_id')!='about_time' or record.get('publication_date_precision')!='month':return False
   if not all(proof.get(k) for k in ['publisher_issue_url','publisher_issue_request_id','publisher_issue_raw_sha256']):return False
   if proof.get('observed_publication_month')!=value:return False
   if record.get('publication_date_lower_bound')!=low or record.get('publication_date_upper_bound')!=high:return False
  return LOW<=low<=high<=HIGH
 except (ValueError,TypeError,AssertionError):return False
