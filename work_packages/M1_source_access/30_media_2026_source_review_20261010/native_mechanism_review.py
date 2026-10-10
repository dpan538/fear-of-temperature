"""Native metadata descriptions only; no semantic noise/bot labels or weights."""
import csv
import json
from collections import Counter,defaultdict
from pathlib import Path

OUT=Path(__file__).resolve().parent
PIN=OUT/'worker/pinned'

def read(name):
    with (PIN/name).open(newline='') as f:return list(csv.DictReader(f))

def main():
    rows=[]; summaries={}
    for label,snapshot in [('s9','s9_closed'),('s4','s4_closed_pre_resume')]:
        manifest=json.loads((PIN/(label+'_collection_manifest.json')).read_text())
        types=read(label+'_source_native_type_counts.csv')
        bysource=defaultdict(Counter)
        for r in types:bysource[r['source_id']][r['native_unit']]+=int(r['entities'])
        assert sum(sum(c.values()) for c in bysource.values())==manifest['counts']['native_entities']
        states=read(label+'_content_states.csv');version_extra=Counter()
        for r in states:version_extra[r['source_id']]+=int(r['versions'])-int(r['entities'])
        cal=read(label+'_source_month_calendar.csv');all_dated=Counter();yr26=Counter()
        for r in cal:
            value=int(r['usable_dated_independent_bodies']);all_dated[r['source_id']]+=value
            if r['month'].startswith('2026-'):yr26[r['source_id']]+=value
        total=sum(all_dated.values());total26=sum(yr26.values())
        assert total==manifest['publication_month_qualified_independent_body_entities']
        for source,c in sorted(bysource.items()):
            replies=c['forum_reply']+c['comment']+c['answer']
            roots=c['context_container']
            rows.append({'snapshot_id':snapshot,'snapshot_at_utc':manifest['snapshot_at_utc'],'source_id':source,
                         'usable_dated_bodies_all_years':all_dated[source],'share_of_pooled_dated_bodies':all_dated[source]/total,
                         'usable_dated_bodies_2026':yr26[source],'share_of_2026_dated_bodies':yr26[source]/total26,
                         'native_entities_all_times':sum(c.values()),'reply_comment_answer_tagged_entities_all_times':replies,
                         'forum_first_post_entities_all_times':c['forum_post'],'context_container_entities_all_times':roots,
                         'repost_wrapper_entities_all_times':c['repost_wrapper'],'quote_post_entities_all_times':c['quote_post'],
                         'mailing_list_message_entities_all_times':c['mailing_list_message'],
                         'excess_entity_versions_from_content_state_aggregates':version_extra[source],
                         'reply_to_container_ratio_diagnostic':replies/roots if roots else '',
                         'count_scope':'native type/state aggregates include non-core, outside-interval/context units; not joined to 2026 body IDs',
                         'evidence_status':'confirmed','mechanism_interpretation':'unresolved; native unit tags do not measure semantic noise or feedback causality',
                         'automation_marker_status':'unknown; no bot/automation field present in pinned entity/type/state schemas',
                         'thread_fanout_status':'individual root degrees and body memberships unreviewed; aggregate ratio only',
                         'recommended_next_action':'retain_with_context; later closed source/thread/publication sensitivity validation',
                         'evidence_locator':'worker/pinned/'+label+'_source_native_type_counts.csv|'+label+'_content_states.csv|'+label+'_source_month_calendar.csv'})
        summaries[snapshot]={'counts':manifest['counts'],'year2026_share':total26/total,
                             'body_top_source':all_dated.most_common(1),'year2026_top_source':yr26.most_common(1),
                             'native_type_counts':dict(sum(bysource.values(),Counter())),
                             'extra_entity_versions':manifest['counts']['entity_versions']-manifest['counts']['native_entities'],
                             'extra_entity_observations':manifest['counts']['entity_observations']-manifest['counts']['native_entities']}
    rel=read('p29_changed_relation_resolution.csv')
    summaries['s9_changed_relation_edges_only']=[r for r in rel if r['relation_type'] in ['reply','root','repost','quote']]
    summaries['limitations']=['Annual/source reweighting is a sensitivity view, not a collector control or deletion rule',
                              'No record-level bot marker verified; missing evidence remains unknown',
                              'No 2026-specific reply-degree, same-utterance federation or work/version join performed',
                              'A wrapper/entity/version/edge is not an additional independently authored dated body',
                              'Source/parent/thread leave-one-out sensitivity must preserve native units and applicable-era denominators',
                              'Native forum labels support mechanism bookkeeping; they do not identify semantic noise or infer emotional effects']
    with (OUT/'NATIVE_MECHANISM_REVIEW.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with (OUT/'NATIVE_MECHANISM_LIMITS.json').open('x') as f:f.write(json.dumps(summaries,indent=2)+'\n')
    print(json.dumps(summaries,indent=2))

if __name__=='__main__':main()
