"""One changed-tranche verification and consolidated metadata-only delivery."""
import collections
import csv
import gzip
import io
import json
import social_elt as e

OUT=e.ROOT/'summaries'

def csv_text(rows,fields=None):
    fields=fields or list(rows[0])
    f=io.StringIO();w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows);return f.getvalue()

def months():
    return [f'{y:04d}-{m:02d}' for y in range(1988,2027) for m in range(1,13) if f'{y:04d}-{m:02d}'<='2026-09']

def quality_rows(posts,versions,contexts,source_lookup):
    by_source=collections.Counter(p['source_id'] for p in posts.values())
    quality=[]
    for sid in by_source:
        pp=[p for p in posts.values() if p['source_id']==sid];vv=[v for v in versions if posts[v['persistent_post_id']]['source_id']==sid]
        quality.append(dict(source_id=sid,native_posts=len(pp),versions=len(vv),questions=sum(p['native_unit']=='question' for p in pp),answers=sum(p['native_unit']=='answer' for p in pp),comments=sum(p['native_unit']=='comment' for p in pp),forum_roots=sum(p['native_unit']=='forum_post' for p in pp),forum_replies=sum(p['native_unit']=='forum_reply' for p in pp),platform_posts=sum(p['native_unit']=='public_platform_post' for p in pp),observed_months=len({p['native_created_at'][:7] for p in pp}),earliest_native_created_at=min(p['native_created_at'] for p in pp),latest_native_created_at=max(p['native_created_at'] for p in pp),supported_exact_content_license=sum(v['content_license'] not in ('unknown','no_open_content_grant_verified') for v in vv),native_license_fields_known=sum(bool(json.loads(v['native_fields_json']).get('content_license')) for v in vv),license_version_unknown=sum(v['content_license']=='unknown' for v in vv),no_open_grant=sum(v['content_license']=='no_open_content_grant_verified' for v in vv),native_update_or_edit_time_known=sum(bool(v['native_edited_at']) for v in vv),native_update_or_edit_time_absent=sum(not v['native_edited_at'] for v in vv),author_role_unknown=sum(p['author_role']=='unknown' for p in pp),author_role_institutional=sum(p['author_role']=='institutional' for p in pp),author_country_known=0,duplicate_body_hash_groups=sum(n>1 for n in collections.Counter(v['body_sha256'] for v in vv).values()),root_context_unresolved=sum(contexts[p['persistent_post_id']]['root_thread_id'] in (None,'unresolved') for p in pp),complete_saved_body_hashes_verified=len(vv),historical_body_version_certified=False))
    for q in quality:
        inception=source_lookup[q['source_id']].get('existence_at')
        q['native_dates_before_current_source_inception']=sum(p['native_created_at'][:10]<inception[:10] for p in posts.values() if p['source_id']==q['source_id']) if inception else 'source_inception_unknown'
        q['source_date_limit']='Native creation precedes current-site beta for some Earth Science records; migration/original-source history unresolved. Native dates retained, not overwritten.' if q['native_dates_before_current_source_inception'] not in (0,'source_inception_unknown') else 'Native field mapping verified; historical version and complete source history unestablished.'
    assert len(quality)==len(by_source)
    assert sum(q['native_posts'] for q in quality)==len(posts)
    return quality

def run():
    if (e.WORK/'CLOSED.json').exists():raise e.Stop('closed_tranche; do not rerun accepted closeout')
    registry=e.read_json(e.ROOT/'source_registry.json');scope=e.release()
    with e.shared(e.footprint(0,3*1048576)) as budget:
        c=e.connect();c.row_factory=__import__('sqlite3').Row
        assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert not c.execute('PRAGMA foreign_key_check').fetchall()
        posts={r['persistent_post_id']:dict(r) for r in c.execute('SELECT * FROM posts')}
        versions=[dict(r) for r in c.execute('SELECT * FROM versions')]
        observations=[dict(r) for r in c.execute('SELECT * FROM observations')]
        responses={r['request_id']:dict(r) for r in c.execute('SELECT * FROM responses')}
        identities=[dict(r) for r in c.execute('SELECT * FROM native_identities')]
        primary={r['persistent_post_id']:r for r in identities if r['identity_basis']!='deprecated_adapter_alias_not_native_namespace'}
        assert len(primary)==len(posts)
        identity_to_id={r['source_id']+'|'+r['native_namespace']+'|'+r['native_post_id']:r['persistent_post_id'] for r in primary.values()}
        assert len(identity_to_id)==len(posts)
        assert all(scope['publication_interval'][0]<=r['native_created_at'][:10]<=scope['publication_interval'][1] for r in posts.values())
        assert all(r['author_country'] is None for r in posts.values())
        assert all(e.sha(v['body_original'].encode())==v['body_sha256'] and v['body_text'] for v in versions)
        first=e.read_json(e.WORK/'FIRST_REAL_BATCH.json')
        assert all(x['persistent_post_id'] in posts and x['body_version_id'] in {v['body_version_id'] for v in versions} for x in first['posts'])
        assert len({posts[k]['native_unit'] for k in posts if posts[k]['source_id']=='se_sustainability' and posts[k]['native_post_id']=='1'})==2
        # Verify changed saved responses and ID/date/body mapping exactly once.
        parsed={};field_rows=[]
        for rid,r in responses.items():
            receipt=e.read_json(e.WORK/'receipts'/f'{rid}.json')
            packed=(e.REPO/r['raw_reference']).read_bytes()
            assert e.sha(packed)==r['stored_sha256']
            assert e.sha(gzip.decompress(packed))==r['raw_sha256']
            data=e.json_payload(receipt);sid=receipt['source_id']
            if sid.startswith('se_'):
                rows=e.stackexchange_records(data,sid);native=data.get('items',[])
            elif sid=='python_discourse':
                rows,_=e.discourse_records(data,sid);native=data.get('latest_posts') or data.get('post_stream',{}).get('posts',[])
            elif sid.startswith('mastodon_'):
                rows,_=e.mastodon_records(data,sid);native=data
            else:
                rows,_=e.bluesky_records(data);native=[x['post'] for x in data.get('feed',[])]
            parsed[rid]={e.native_key(x):x for x in rows}
            field_rows.append(dict(request_id=rid,source_id=sid,request_url=r['request_url'],native_objects_returned=len(native),complete_authored_candidates=len(rows),has_more=data.get('has_more') if isinstance(data,dict) else None,cursor_present=bool(data.get('cursor')) if isinstance(data,dict) else False,quota_remaining=data.get('quota_remaining') if isinstance(data,dict) else None,native_license_fields_present=sum(bool(x.get('content_license')) for x in native),native_edited_date_fields_present=sum(bool(x.get('last_edit_date') or x.get('edited_at') or x.get('updated_at')) for x in native),native_fields=';'.join(sorted(set().union(*(x.keys() for x in native)))) if native else '',body_index_only=sid=='python_discourse' and 'latest_posts' in data))
        version_map={v['body_version_id']:v for v in versions}
        for o in observations:
            v=version_map[o['body_version_id']];p=posts[v['persistent_post_id']];i=primary[p['persistent_post_id']]
            key=i['source_id']+'|'+i['native_namespace']+'|'+i['native_post_id']
            row=parsed[o['request_id']][key]
            assert row['native_created_at']==p['native_created_at']
            assert e.sha(row['body_original'].encode())==v['body_sha256']
        # Resolve answer parents only from verified native post metadata.
        context_changes=[]
        with c:
            for p in posts.values():
                if p['native_unit']!='comment' or not p['reply_to_post_id']:continue
                parent=c.execute('SELECT native_unit,thread_id FROM posts WHERE source_id=? AND native_post_id=? AND native_unit IN (\'question\',\'answer\')',(p['source_id'],p['reply_to_post_id'])).fetchone()
                if parent:
                    status='parent_'+parent['native_unit']+'_mapped; thread_context_partial'
                    c.execute('UPDATE parent_context SET root_thread_id=?,parent_namespace=?,context_status=? WHERE persistent_post_id=?',(parent['thread_id'],parent['native_unit'],status,p['persistent_post_id']))
                    context_changes.append(dict(persistent_post_id=p['persistent_post_id'],parent_native_id=p['reply_to_post_id'],verified_parent_type=parent['native_unit'],root_thread_id=parent['thread_id'],basis='same-source native parent identity and question_id metadata'))
        contexts={r['persistent_post_id']:dict(r) for r in c.execute('SELECT * FROM parent_context')}
        urls=[dict(r) for r in c.execute('SELECT * FROM post_urls')]
        c.close()
        by_source=collections.Counter(p['source_id'] for p in posts.values())
        by_source_month=collections.Counter((p['source_id'],p['native_created_at'][:7]) for p in posts.values())
        source_lookup={s['source_id']:s for s in registry}
        post_manifest=[]
        for v in versions:
            p=posts[v['persistent_post_id']];i=primary[p['persistent_post_id']]
            context=contexts[p['persistent_post_id']]
            os=[o for o in observations if o['body_version_id']==v['body_version_id']]
            r=responses[os[0]['request_id']]
            post_manifest.append({**{k:p[k] for k in ('persistent_post_id','source_id','native_post_id','source_url','native_unit','native_created_at','author_id','author_role')},'native_namespace':i['native_namespace'],'source_frame':source_lookup[p['source_id']]['frame'],'source_stratum':source_lookup[p['source_id']]['stratum'],'author_country':'unknown','thread_id_native_at_first_load':p['thread_id'],'root_thread_id_resolved':context['root_thread_id'],'reply_to_post_id':p['reply_to_post_id'],'parent_namespace':context['parent_namespace'],'context_status':context['context_status'],**{k:v[k] for k in ('body_version_id','body_sha256','native_edited_at','native_revision','first_retrieved_at','content_license','license_basis','completeness','provenance')},'cleaned_body_sha256':e.sha(v['body_text'].encode()),'cleaned_characters':len(v['body_text']),'raw_reference':r['raw_reference'],'raw_sha256':r['raw_sha256'],'observation_count':len(os)})
        quality=quality_rows(posts,versions,contexts,source_lookup)
        calendar=[];era_rows=[]
        for s in registry:
            start=s.get('existence_at');start_month=start[:7] if start else None
            observed=sorted(m for sid,m in by_source_month if sid==s['source_id'])
            for month in months():
                count=by_source_month[(s['source_id'],month)]
                if count:status='observed_text'
                elif start_month and month<start_month:status='structural_inapplicable'
                elif s.get('platform_public_start_month') and month<s['platform_public_start_month']:status='structural_inapplicable'
                elif s.get('platform_not_before_month') and month<s['platform_not_before_month']:status='structural_inapplicable'
                elif start_month:status='applicable_unobserved'
                elif s['source_id'] in ('mastodon_nz','mumsnet','boards_ie','citydata_us','gpforums_nz','moneysavingexpert'):status='access_blocked'
                else:status='historical_scope_unknown'
                calendar.append(dict(source_id=s['source_id'],source_stratum=s['stratum'],month=month,status=status,native_posts=count,source_inception=start,platform_start_lower_bound=s.get('platform_public_start_month') or s.get('platform_not_before_month'),era_applicability='structural_inapplicable' if status=='structural_inapplicable' else 'applicable_source_era' if start_month and month>=start_month else 'source_historical_scope_unknown',source_access_status=s['collection_retention'],source_inception_unresolved=not bool(start),september_partial=month=='2026-09'))
            era_rows.append(dict(source_id=s['source_id'],full_calendar_months=465,verified_source_inception=start,applicable_source_months=sum(m>=start_month for m in months()) if start_month else 'unknown',observed_text_months=len(observed),platform_possible_months=sum(m>=(s.get('platform_public_start_month') or s.get('platform_not_before_month')) for m in months()) if s.get('platform_public_start_month') or s.get('platform_not_before_month') else 'unknown',earliest_saved_post_month=observed[0] if observed else '',latest_saved_post_month=observed[-1] if observed else '',historical_scope=s['historical_scope']))
        pooled=[]
        for month in months():
            pp=[p for p in posts.values() if p['native_created_at'][:7]==month]
            pooled.append(dict(month=month,native_posts=len(pp),observed_sources=len({p['source_id'] for p in pp}),**{g:sum(source_lookup[p['source_id']]['stratum']==g for p in pp) for g in ('EU','UK','AU','US','NZ','GLOBAL')},institutional=sum(p['author_role']=='institutional' for p in pp),unknown_role=sum(p['author_role']=='unknown' for p in pp),september_partial=month=='2026-09'))
        source_rows=[{k:s.get(k) for k in ('source_id','title','platform','frame','stratum','base_url','public_read','collection_retention','retention_basis','content_license','open_content','redistribution','geographic_evidence','geographic_verification','existence_at','historical_scope','status')}|{'api_documentation':' | '.join(s.get('api_documentation',[])),'policy_urls':' | '.join(s.get('policy_urls',[]))} for s in registry]
        opportunities=[dict(stratum=g,planned_parents=sum(s.get('planned_source_opportunities',0) for s in registry if s['stratum']==g),actual_native_posts=sum(by_source[s['source_id']] for s in registry if s['stratum']==g),actual_body_sources=sum(by_source[s['source_id']]>0 for s in registry if s['stratum']==g),author_country_inference=False) for g in ('EU','UK','AU','US','NZ')]
        outputs={'native_posts_manifest.csv':csv_text(post_manifest),'responses_manifest.csv':csv_text(list(responses.values())),'source_registry.csv':csv_text(source_rows),'quality_by_source.csv':csv_text(quality),'api_return_quality.csv':csv_text(field_rows),'source_month_calendar.csv':csv_text(calendar),'source_era_summary.csv':csv_text(era_rows),'pooled_month_counts.csv':csv_text(pooled),'regional_opportunities.csv':csv_text(opportunities),'native_identity_map.csv':csv_text(identities),'source_url_aliases.csv':csv_text(urls),'resolved_parent_context.csv':csv_text(context_changes)}
        OUT.mkdir(exist_ok=True)
        for name,text in outputs.items():
            with (OUT/name).open('w',encoding='utf8',newline='') as f:f.write(text)
        result=dict(snapshot_at=e.utc(),closed=True,native_posts=len(posts),body_versions=len(versions),sources_with_actual_bodies=len(by_source),observed_pooled_months=sum(bool(x['native_posts']) for x in pooled),full_calendar_months=465,by_source=dict(by_source),requests_charged=e.state()['requests'],distinct_native_objects_returned=len(e.state()['returned_object_ids']),fixed_publication_interval=scope['publication_interval'],structural_checks_passed=True,accepted_pipeline_check='worker/PIPELINE_CHECK_IDENTITY.json',actual_namespace_collision='worker/ACTUAL_NUMERIC_NAMESPACE_COLLISION.json',first_50_IDs_versions_preserved=True,first_50_native_license_fields_present=47,first_50_license_version_unknown=3,region_opportunities=opportunities,raw_body_mapping_checks=len(observations),checks_scope='only this social wave; no other store or predecessor corpus opened',output_path_resolution='All paths relative to social stream root',outputs={'summaries/'+name:{'sha256':e.sha((OUT/name).read_bytes()),'bytes':(OUT/name).stat().st_size} for name in outputs})
        e.atomic(OUT/'collection_manifest.json',result)
        e.atomic(e.WORK/'CLOSED.json',dict(result,snapshot_budget=budget,writer_active=False,no_successor_or_extension=True))
    print(json.dumps({k:result[k] for k in ('native_posts','body_versions','sources_with_actual_bodies','observed_pooled_months','requests_charged','distinct_native_objects_returned','structural_checks_passed')}))

if __name__=='__main__':
    with e.writer():run()
