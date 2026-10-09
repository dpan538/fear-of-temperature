"""One structural relation derivation for newly collected versions only.

Explicit HTML quote/link/image attributes are source evidence; text semantics
are not examined. Unresolved topic/post-number endpoints remain traceable.
"""
import json
from html.parser import HTMLParser
import transport as t,entities as e
class Attributes(HTMLParser):
 def __init__(self):super().__init__();self.quotes=[];self.links=[];self.images=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='aside' and 'quote' in a.get('class','').split() and a.get('data-topic') and a.get('data-post'):self.quotes.append((a['data-topic'],a['data-post'],a))
  if tag=='a' and a.get('href'):self.links.append(a['href'])
  if tag=='img' and a.get('src'):self.images.append(a)
def enrich():
 with t.shared(t.footprint()):
  c=e.db();counts={'quotes':0,'links':0,'images':0,'resolved_post_number_endpoints':0};at=t.utc()
  body_bytes=c.execute("SELECT COALESCE(SUM(LENGTH(COALESCE(b.body_original,v.body_original))),0) FROM entity_versions v JOIN native_entities n ON n.entity_id=v.entity_id LEFT JOIN versions b ON b.body_version_id=v.core_body_version_id WHERE n.inherited=0").fetchone()[0]
  t.preflight(t.release(),t.footprint(0,body_bytes))
  with c:
   c.execute('CREATE TABLE IF NOT EXISTS native_aliases(source_id TEXT NOT NULL, native_namespace TEXT NOT NULL, native_id TEXT NOT NULL, entity_id TEXT NOT NULL REFERENCES native_entities, evidence_json TEXT NOT NULL, PRIMARY KEY(source_id,native_namespace,native_id))')
   # Only new source observations are parsed; accepted old bodies are not swept.
   rows=c.execute("SELECT v.entity_version_id,n.entity_id,n.source_id,n.native_namespace,v.core_body_version_id,COALESCE(b.body_original,v.body_original),v.native_fields_json,o.request_id FROM entity_versions v JOIN native_entities n ON n.entity_id=v.entity_id LEFT JOIN versions b ON b.body_version_id=v.core_body_version_id LEFT JOIN entity_observations o ON o.entity_version_id=v.entity_version_id WHERE n.inherited=0 GROUP BY v.entity_version_id")
   for vid,eid,sid,ns,core,body,fields,request in rows:
    meta=json.loads(fields)
    if ns=='forum_post' and meta.get('topic_id') is not None and meta.get('post_number') is not None:c.execute('INSERT OR IGNORE INTO native_aliases VALUES (?,?,?,?,?)',(sid,'topic_post_number',str(meta['topic_id'])+':'+str(meta['post_number']),eid,json.dumps({'native_topic_id':meta['topic_id'],'native_post_number':meta['post_number'],'entity_version_id':vid})))
    if ns!='forum_post' or not body:continue
    p=Attributes();p.feed(body);edges=[e.edge('quote',tid+':'+number,'topic_post_number',meta={'source_html_quote_attributes':a}) for tid,number,a in p.quotes];edges += [e.edge('link',None,url=url) for url in dict.fromkeys(p.links)]
    for edge in edges:
     edgeid=t.sha((eid+'|'+json.dumps(edge,sort_keys=True,ensure_ascii=False)).encode());target=c.execute('SELECT entity_id FROM native_aliases WHERE source_id=? AND native_namespace=? AND native_id=?',(sid,edge.get('target_namespace'),edge.get('target_native_id'))).fetchone();target=target[0] if target else None
     new=c.execute('INSERT OR IGNORE INTO native_edges VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(edgeid,eid,edge['relation_type'],sid,edge.get('target_namespace'),edge.get('target_native_id'),target,edge.get('target_url'),'resolved' if target else 'unresolved_native_endpoint',json.dumps(edge.get('native_fields',{}),ensure_ascii=False),request,at)).rowcount
     counts['quotes' if edge['relation_type']=='quote' else 'links']+=new
    for image in p.images:
     aid=t.sha((vid+'|source_html_image|'+json.dumps(image,sort_keys=True)).encode());counts['images']+=c.execute('INSERT OR IGNORE INTO native_attachments VALUES (?,?,?,?,?,?,?)',(aid,vid,None,'source_html_image',image['src'],'metadata_only_media_not_downloaded',json.dumps(image,ensure_ascii=False))).rowcount
   counts['resolved_post_number_endpoints']=c.execute("UPDATE native_edges SET target_entity_id=(SELECT entity_id FROM native_aliases a WHERE a.source_id=native_edges.target_source_id AND a.native_namespace=native_edges.target_namespace AND a.native_id=native_edges.target_native_id),resolution_state='resolved' WHERE target_entity_id IS NULL AND EXISTS (SELECT 1 FROM native_aliases a WHERE a.source_id=native_edges.target_source_id AND a.native_namespace=native_edges.target_namespace AND a.native_id=native_edges.target_native_id)").rowcount
  c.close();t.atomic(t.WORK/'RELATION_DERIVATION_RECEIPT.json',{'at_utc':at,'scope':'new entities only, explicit HTML attributes','counts':counts,'old_bodies_parsed':False,'semantic_inference':False});return counts
if __name__=='__main__':
 with t.writer():print(enrich())
