"""Whole public WordPress.com posts; site-specific permission precedes Load."""
import json,urllib.parse
import transport as t,entities as e

DOC='https://developer.wordpress.com/docs/api/1.1/get/sites/$site/posts/'
API='https://public-api.wordpress.com/rest/v1.1/sites/'
CANDIDATES=[
 ('ladyinieda.wordpress.com','/about/','CC-BY-NC-ND-4.0','All work on this blog is licensed','individual freelance writer self-presentation'),
 ('grantmebookshelves.wordpress.com','/about/','CC-BY-NC-SA-3.0','Grant Me Bookshelves is licensed','individual reader/editor self-presentation'),
 ('mybin.wordpress.com','/legalese/','author_explicit_copy_reuse_with_attribution','free for copying and reusing','author explicitly claims own personal ideas/thoughts'),
 ('nethahussain.wordpress.com','/about/','CC-BY-SA-4.0','All contents in this blog are shared','individual leisure writer self-presentation'),
 ('mithriluna.wordpress.com','/about/','CC-BY-NC-ND-4.0','This work is licensed','personal family-life author self-presentation; images not collected'),
 ('katealamode.wordpress.com','/about/','CC-BY-NC-SA-3.0','original content and images are licensed','individual style/lifestyle author self-presentation'),
 ('sorbowriter.wordpress.com','/about/','CC-BY-ND-3.0','Original and Edited Works','individual freelance writer/fan blog; original authors separate'),
 ('cenantua.wordpress.com','/about-me/','CC-BY-NC-ND-3.0','is licensed under a Creative Commons','individual historian personal-reflection blog'),
]

def prepare(cursors,actors,block):
    registry=t.read_json(t.WORK/'source_registry.json',[])
    for domain,path,license_,needle,role_basis in CANDIDATES:
        sid='wordpress_'+domain.split('.')[0]
        if any(s['source_id']==sid for s in registry):continue
        url='https://'+domain+path
        rec=t.fetch(url,sid,'policy')
        # Follow only source-returned HTTPS same-site canonical redirects.
        if rec.get('status')=='http_stop' and rec.get('http_status') in (301,302,307,308):
            loc=urllib.parse.urljoin(url,rec.get('location') or '')
            if urllib.parse.urlsplit(loc).hostname==domain and loc.startswith('https://'):rec=t.fetch(loc,sid,'policy')
        if rec['status']!='saved':block(sid,url,'site_permission_page_unavailable',rec);continue
        text=t.clean(t.payload(rec).decode('utf8','replace'))
        if needle.lower() not in text.lower() or ('Creative Commons' not in text and license_!='author_explicit_copy_reuse_with_attribution'):
            block(sid,url,'named_license_not_verified_in_actual_site_response',rec);continue
        # Native metadata establishes the actual site ID and public status.
        metadata=t.fetch(API+domain+'/',sid,'source_metadata')
        if metadata['status']!='saved':block(sid,API+domain+'/','native_site_identity_unavailable',metadata);continue
        site=t.json_payload(metadata)
        if not site.get('ID') or site.get('is_private') or site.get('is_deleted'):
            block(sid,API+domain+'/','native_site_not_public_or_identity_unresolved',metadata);continue
        siteid=str(site['ID']);cohort=sid+':site:'+siteid
        source={'source_id':sid,'title':site.get('name',domain),'base_url':'https://'+domain,'platform':'WordPress.com','carrier':'personal_blog','genre':'blog_post','collection_retention':'permitted','retention_basis':'Source-visible original-work license or explicit copying/reuse permission, verified on the named actual source response. Local noncommercial research snapshot with attribution, original HTML retained; no media download or public full-text release. Quoted/guest rights remain separate.','permission_url':url,'permission_request_id':rec['request_id'],'permission_raw_reference':rec['raw_reference'],'permission_raw_sha256':rec['raw_sha256'],'api_documentation':[DOC],'native_site_metadata_reference':metadata['raw_reference'],'native_site_id':siteid,'public_access':'documented_no_auth_public_posts','content_license':license_,'redistribution':'license_conditional; no public raw/body release in this task','stratum':'GLOBAL_UNKNOWN','author_country':'unknown','site_role_evidence':role_basis,'selection_rule':'source-license/personal-role public search and named result order; no climate/fear/emotion selection','comment_retention':'pending; site-owner license is not automatically other commenters license'}
        registry.append(source);t.atomic(t.WORK/'source_registry.json',registry)
        actor={'source_id':sid,'actor_id':'site_owner_not_yet_native_author_matched','site_id':siteid,'cohort_id':cohort,'carrier':'personal_blog','genre':'blog_post','role_status':'individual_blog_self_presentation','role_evidence':role_basis,'profile_raw_reference':rec['raw_reference'],'profile_receipt':rec['request_id'],'observed_at':rec['retrieved_at'],'selection_rule':source['selection_rule'],'source_context_country':'unknown','source_context_region':'unknown','source_context_evidence_ref':metadata['raw_reference'],'source_context_observed_at':metadata['retrieved_at'],'community_context_scope':'personal_blog_site','author_country':'unknown','author_country_status':'unmeasured','author_country_evidence_type':'no_country_inference_from_place_names_or_site','author_country_evidence_ref':rec['raw_reference'],'author_country_observed_at':rec['retrieved_at'],'parent_independence':'unresolved'}
        actors.append(actor)
        cursor={'source_id':sid,'actor_id':actor['actor_id'],'site_id':siteid,'cohort_id':cohort,'carrier':'personal_blog','genre':'blog_post','page':0,'page_handle':None,'state':'active','oldest_publication':None,'new_core_bodies':0,'returned_native_rows':0,'permission_request_id':rec['request_id']}
        cursors.append(cursor)
        with t.shared(t.footprint(0,50000,2)):
            c=e.db();e.register(c,source,{'frame_id':cohort,'frame_type':'personal_blog_site_native_posts','selection_rule':source['selection_rule'],'actor_role_basis':role_basis});c.close()
        t.atomic(t.WORK/'ACTOR_COHORTS.json',actors);t.atomic(t.WORK/'NATIVE_CURSORS.json',cursors)
        plan=t.read_json(t.WORK/'ACTIVE_SOURCE_ROUTE_PLAN.json');plan['routes'].append({'source_id':sid,'carrier':'personal_blog','site_id':siteid,'cohort_id':cohort,'admission_evidence':rec['raw_reference'],'collection_retention':'permitted','executable_route':API+siteid+'/posts/?status=publish&type=post&order=DESC','content_license':license_});assert all(x['carrier']!='technical_list' for x in plan['routes']);t.atomic(t.WORK/'ACTIVE_SOURCE_ROUTE_PLAN.json',plan)

def job(cursor):
    args={'number':cursor.get('number',50),'order':'DESC','order_by':'date','status':'publish','type':'post','before':'2026-09-22T00:00:00Z'}
    if cursor.get('page_handle'):args['page_handle']=cursor['page_handle']
    else:args['page']=cursor['page']+1
    return API+cursor['site_id']+'/posts/?'+urllib.parse.urlencode(args)

def records(data,cursor,actor,source):
    rows=[]
    for p in data.get('posts',[]):
        author=p.get('author') or {};aid=str(author.get('ID')) if author.get('ID') is not None else None
        body=p.get('content') or '';protected=bool(p.get('password')) or p.get('status') not in (None,'publish')
        meta={k:v for k,v in p.items() if k not in ('content','excerpt','attachments','featured_image')}
        evidence={k:actor.get(k) for k in ['cohort_id','carrier','genre','site_id','source_context_country','source_context_region','source_context_evidence_ref','source_context_observed_at','community_context_scope','author_country','author_country_evidence_type','author_country_evidence_ref','author_country_observed_at','author_country_status']}
        evidence.update(role_status='personal_blog_native_author; identity_to_site_owner_pending',role_evidence_ref=actor['profile_raw_reference'])
        meta['source_expansion_evidence']=evidence
        rows.append({'source_id':cursor['source_id'],'native_namespace':'blog_post','native_post_id':str(p['ID']),'source_url':p.get('URL'),'native_unit':'blog_post','native_created_at':p.get('date'),'native_edited_at':p.get('modified'),'native_revision':None,'author_id':aid,'author_role':'personal_blog_native_author','body_original':'' if protected else body,'body_format':'html','content_state':'password_protected_preview' if protected else 'complete_native_text' if body else 'bodyless_native_entity','content_license':source['content_license'],'license_basis':source['retention_basis']+'; permission raw '+source['permission_raw_reference'],'thread_id':cursor['site_id']+':'+str(p['ID']),'flags':{'quoted_guest_embedded_material_not_automatically_author_owned':True,'current_body_not_verified_historical_version':True},'native_fields':meta,'edges':[]})
    return rows
