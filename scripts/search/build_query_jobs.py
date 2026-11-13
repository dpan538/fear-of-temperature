"""Offline reproduction of the closed round31 query generator.

Adapted from the production build_jobs function, retaining its query and effort
algorithm. Replaces local runtime reads/writes with explicit frozen inputs.
No HTTP, collector dispatch, database connection or corpus mutation occurs.
"""
import argparse
import hashlib
import json
from pathlib import Path


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def build_jobs(config, policy, matrix, years, executed):
    children = {r['term']: r for r in matrix['children']}
    assert len(matrix['children']) == 638
    minimum = min(years.values())
    executed_texts={' '.join(e['query']['query'].split()).casefold() for e in executed.values()}
    jobs = []
    for family, profile in config['families'].items():
        weight = policy['theme_weights'].get(family, profile.get('fallback_weight'))
        assert weight and all(term in children for term in profile['matrix_terms'])
        for year, count in years.items():
            cities=sorted(config['cities'],key=lambda city:fingerprint((year,family,city)))
            for i, city in enumerate(cities):
                expression = profile['expressions'][i % len(profile['expressions'])]
                surfaces=config.get('document_search_terms','diary OR blog OR forum')
                query = f'"{year}" {city} Australia ({expression}) ({surfaces})'
                query_id=fingerprint(dict(query=query, family=family))[:24]
                jobs.append(dict(query_id=query_id,
                                 query=query, family=family, family_weight=weight,
                                 discovery_year=year, city=city, full_corpus_year_count=count,
                                 year_effort_weight=minimum/count,
                                 weighted_finish=(i+1)/(weight*minimum/count),
                                 matrix_child_ids=[children[term]['child_id'] for term in profile['matrix_terms']],
                                 status='search_completed' if query_id in executed or ' '.join(query.split()).casefold() in executed_texts else 'pending_search', year_is_discovery_hint_only=True))
            if config.get('year_deficit_include_city_genre_free_variant'):
                # Keep actual full-corpus deficit weights, while letting a
                # year hint find narratives without a mandatory city/genre.
                places=config['broad_geographic_OR_terms']
                geographic='('+' OR '.join('"'+s+'"' if ' ' in s else s for s in places)+')'
                for j,expression in enumerate(profile['expressions']):
                    query=f'"{year}" {geographic} ({expression})'
                    query_id=fingerprint(dict(query=query,family=family))[:24]
                    jobs.append(dict(query_id=query_id,query=query,family=family,family_weight=weight,
                        discovery_year=year,city=None,full_corpus_year_count=count,
                        year_effort_weight=minimum/count,weighted_finish=(j+1)/(weight*minimum/count),
                        matrix_child_ids=[children[term]['child_id'] for term in profile['matrix_terms']],
                        search_shape='relaxed_full_corpus_year_deficit',mandatory_city_or_genre=False,
                        status='search_completed' if query_id in executed or ' '.join(query.split()).casefold() in executed_texts else 'pending_search',
                        year_is_discovery_hint_only=True,weight_not_an_admission_threshold=True))
    jobs.sort(key=lambda r: (r['weighted_finish'], r['query_id']))
    if config.get('broad_matrix_queries_enabled'):
        # Breadth queries use the complete canonical children without a forced
        # year/city/genre/heat/emotion conjunction. Deficit jobs remain explicit
        # supplementary search effort, never an admission quota.
        grouped={}
        for child in matrix['children']:grouped.setdefault(child['parent_cluster'],[]).append(child)
        mapping={'warming_seasons':'broad_forum_exploration','acute_heat':'somatic_daily_impact',
                 'body_daily_life':'somatic_daily_impact','climate_anxiety_anticipation':'psychological_cultural_response',
                 'exhaustion_aversion':'psychological_cultural_response','heat_irritability_anger':'psychological_cultural_response',
                 'homes_costs_inequality':'somatic_daily_impact','individual_household_coping':'somatic_daily_impact',
                 'systemic_policy_collective_action':'psychological_cultural_response','weather_uv_fire_risk_context':'ecological_grief_memory'}
        broad=[]
        chunk_size=int(config.get('broad_matrix_query_terms_per_job',6))
        assert 1<=chunk_size<=6
        surfaces=config.get('broad_matrix_query_surfaces',[''])
        assert surfaces and all(isinstance(s,str) for s in surfaces)
        for parent,values in grouped.items():
            family=mapping[parent];weight=policy['theme_weights'].get(family,config['families'][family].get('fallback_weight'))
            for start in range(0,len(values),chunk_size):
                chunk=values[start:start+chunk_size]
                query='Australia '+('(' if len(chunk)>1 else '')+' OR '.join('"'+r['term'].replace('"','')+'"' for r in chunk)+(')' if len(chunk)>1 else '')
                surface=surfaces[(start//chunk_size)%len(surfaces)]
                if surface:query+=' '+surface
                if config.get('broad_search_publication_window'):
                    query+=' '+config['broad_search_publication_window']
                query_id=fingerprint(dict(query=query,family=family))[:24]
                broad.append(dict(query_id=query_id,query=query,family=family,family_weight=weight,
                                  search_shape='broad_canonical_matrix_no_mandatory_year_city_genre',parent_cluster=parent,
                                  matrix_child_ids=[r['child_id'] for r in chunk],weighted_finish=(start//chunk_size+1)/weight,
                                  status='search_completed' if query_id in executed or ' '.join(query.split()).casefold() in executed_texts else 'pending_search',
                                  year_is_discovery_hint_only=True,weight_not_an_admission_threshold=True))
        if config.get('broad_matrix_include_genre_free_variant'):
            # Preserve every prior job and execution. Add missing plain-query
            # variants so blog/essay/diary words do not limit discovery.
            seen_ids={r['query_id'] for r in broad}
            extra=[]
            for original in broad:
                surface=next((s for s in surfaces if s and original['query'].endswith(' '+s)),None)
                if surface is None:continue
                query=original['query'][:-len(surface)-1]
                query_id=fingerprint(dict(query=query,family=original['family']))[:24]
                if query_id in seen_ids:continue
                seen_ids.add(query_id)
                variant=dict(original,query=query,query_id=query_id,
                             genre_free_expansion_of_query_id=original['query_id'],
                             status='search_completed' if query_id in executed or ' '.join(query.split()).casefold() in executed_texts else 'pending_search')
                extra.append(variant)
            broad.extend(extra)
        if config.get('broad_matrix_include_base_parent_queries'):
            # The body matcher already accepts these original cluster terms.
            # Children are additions, not replacements for the parent scope.
            seen_texts={' '.join(r['query'].split()).casefold() for r in broad}
            base_by_text={}
            child_terms={r['term'] for r in matrix['children']}
            for parent,cluster in matrix['clusters'].items():
                family=mapping[parent]
                weight=policy['theme_weights'].get(family,config['families'][family].get('fallback_weight'))
                for i,term in enumerate(cluster['terms']):
                    if term in child_terms:continue
                    query='Australia "'+term.replace('"','')+'"'
                    normal=' '.join(query.split()).casefold()
                    if normal in seen_texts:
                        if normal in base_by_text:
                            base_by_text[normal]['matrix_base_parent_clusters'].append(parent)
                        continue
                    seen_texts.add(normal)
                    query_id=fingerprint(dict(query=query,family=family))[:24]
                    base_job=dict(query_id=query_id,query=query,family=family,family_weight=weight,
                        search_shape='broad_original_base_parent_term',parent_cluster=parent,
                        matrix_child_ids=[],matrix_base_terms=[term],matrix_base_parent_clusters=[parent],weighted_finish=(i+1)/weight,
                        status='search_completed' if query_id in executed or normal in executed_texts else 'pending_search',
                        year_is_discovery_hint_only=True,weight_not_an_admission_threshold=True)
                    broad.append(base_job);base_by_text[normal]=base_job
        if config.get('broad_matrix_include_relaxed_discovery_variants'):
            # Discovery alternatives only. Native Australian context and the
            # unchanged original matrix still have to match in the real body.
            geographic=config['broad_geographic_OR_terms']
            assert geographic and all(isinstance(s,str) and s and '"' not in s for s in geographic)
            prefix='('+' OR '.join('"'+s+'"' if ' ' in s else s for s in geographic)+')'
            seen_ids={r['query_id'] for r in broad}
            extra=[]
            for original in broad:
                if not original['query'].startswith('Australia "'):continue
                if original.get('search_shape')!='broad_original_base_parent_term' and original.get('genre_free_expansion_of_query_id') is None:
                    # Plain original queries have exactly one quoted term too.
                    if original['query'].count('"')!=2 or not original['query'].endswith('"'):continue
                quoted=original['query'][len('Australia '):]
                if quoted.count('"')!=2 or not quoted.endswith('"'):continue
                term=quoted[1:-1]
                variants=[('geographic_OR',prefix+' '+quoted)]
                if len(term.split())>1:variants.append(('nonphrase','Australia '+term))
                for kind,query in variants:
                    query_id=fingerprint(dict(query=query,family=original['family']))[:24]
                    if query_id in seen_ids:continue
                    seen_ids.add(query_id)
                    extra.append(dict(original,query=query,query_id=query_id,
                        search_shape='broad_relaxed_discovery_'+kind,
                        relaxed_discovery_of_query_id=original['query_id'],
                        native_admission_unchanged=True,
                        status='search_completed' if query_id in executed or ' '.join(query.split()).casefold() in executed_texts else 'pending_search'))
            broad.extend(extra)
        broad.sort(key=lambda r:(r['weighted_finish'],r['query_id']))
        deficit=iter(jobs);breadth=iter(broad);merged=[]
        breadth_share=int(config.get('broad_search_jobs_per_cycle',3))
        deficit_share=int(config.get('deficit_search_jobs_per_cycle',2))
        assert breadth_share>0 and deficit_share>0
        for _ in range(max(len(jobs),len(broad))):
            for stream,n in [(breadth,breadth_share),(deficit,deficit_share)]:
                for _ in range(n):
                    job=next(stream,None)
                    if job is not None:merged.append(job)
        jobs=merged
    return jobs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    read = lambda name: json.loads((root / 'config/search' / name).read_text())
    weights = read('weights.json')
    jobs = build_jobs(read('profiles.json'), {'theme_weights': weights['family_weights']},
                      read('current.json'), weights['saved_scheduler_year_counts'], {})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({'role': 'offline-designed-not-executed',
        'search_dispatch_enabled': False, 'query_jobs': jobs}, indent=2) + '\n')
    print(f'{len(jobs)} designed jobs written; no searches executed')


if __name__ == '__main__':
    main()
