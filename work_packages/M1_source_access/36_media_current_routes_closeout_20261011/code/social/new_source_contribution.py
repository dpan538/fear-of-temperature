"""Finalized changed-tranche source facts; no executable frontier/owner data."""
import collections,json
import transport as t
P=t.WORK/'new_source_preparation'
def source_rows(ledger):
 plans=t.read_json(P/'NATIVE_WEB_CHANNEL_PREPARED.json',{}).get('plans',[]);by=collections.defaultdict(list)
 for row in ledger:by[row['source_id']].append(row)
 rows=[]
 for plan in plans:
  s=plan['source'];a=plan['actor'];data=by[s['source_id']];dates=[r['publication_at'] for r in data]
  rows.append([s['source_id'],s['title'],s['platform'],s['carrier'],s['genre'],s.get('author_source_family'),a.get('parent_independence','unresolved'),len(data),min(dates,default=None),max(dates,default=None),s['content_license'],s['permission_url'],s['permission_raw_reference'],s.get('permission_retrieved_at'),json.dumps(s.get('source_license_history') or {},ensure_ascii=False),json.dumps(s.get('documented_migration_history') or {},ensure_ascii=False),a['role_status'],'unmeasured; current declarations not historical body-country assignment','site/native author identity is not independently verified people or publishing parents'])
 return rows
HEADER=['source_id','source_title','platform','carrier','genre','named_author_source_family','parent_independence_status','actual_new_dated_authored_bodies','first_source_declared_publication_date','last_source_declared_publication_date','currently_observed_licence_or_permission','permission_url','permission_raw_reference','permission_observed_at','licence_variant_evidence_json','migration_history_evidence_json','role_evidence_status','historical_author_country_status','unit_limit']
def export(ledger,csvfile):
 files=[csvfile('new_native_blog_contribution_summary.csv',HEADER,source_rows(ledger))]
 facts=t.read_json(P/'SOURCE_CURRENT_SELF_DECLARATIONS.json',{}).get('facts',[])
 fields=['source_id','declaration_field','literal_self_declaration','declaration_scope','evidence_url','raw_reference','observed_at_utc','publication_date_of_declaration','historical_body_country_assignment','identity_and_assertion_truth_independently_verified']
 files.append(csvfile('source_current_self_declarations.csv',fields,([r.get(k) for k in fields] for r in facts)))
 return files
