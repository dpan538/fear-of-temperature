"""Separate parent dimensions. Curated primary assertions never update collectors."""
import csv
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
PIN=OUT/'worker/pinned'

def main():
    registry={r['source_id']:r for r in json.loads((PIN/'s4_source_registry.json').read_text())}
    named=json.loads((OUT/'worker/NAMED_PRIMARY_PARENT_EVIDENCE.json').read_text())['rows']
    by_source={}
    for r in named:by_source.setdefault(r['source_id'],[]).append(r)
    sources=['devonport_flagstaff','northern_rivers_times','aussie_zone','bluesky','lemmy_nz',
             'mastodon_au','mastodon_ie','mastodon_uk','mastodon_us','osm_discourse','python_discourse',
             'se_earthscience','se_sustainability','straight_dope']
    bases={s:registry[s]['base_url'] for s in sources if s in registry}
    bases.update(devonport_flagstaff='https://devonportflagstaff.co.nz',northern_rivers_times='https://thenorthernriverstimes.com.au')
    primary={
        'devonport_flagstaff':('https://devonportflagstaff.co.nz/contact-us/','Heading Devonport Publishing Ltd; Auckland address; copyright 2026','Devonport Publishing Ltd','confirmed'),
        'northern_rivers_times':('https://thenorthernriverstimes.com.au/contact-us/','Contact Us addresses in Casino/Tweed Heads, NSW; heartlandmedia.com.au contacts','Northern Rivers Times; Heartland Media association; legal organization unresolved','supported_candidate'),
        'bluesky':('https://bsky.social/about/support/tos','2025-08-14 terms introduction names Bluesky Social, PBC; AT Protocol','Bluesky Social, PBC','confirmed'),
        'osm_discourse':('https://osmfoundation.org/wiki/Terms_of_Use','Introduction lists OSMF forums among Foundation-operated services','OpenStreetMap Foundation','confirmed'),
        'python_discourse':('https://discuss.python.org/tos','Opening paragraph states Website owned and operated by PSF','Python Software Foundation','confirmed'),
        'straight_dope':('https://boards.straightdope.com/tos','Disclaimer identifies Sun-Times Media, LLC as operator; posters express own views','Sun-Times Media, LLC (current terms assertion; operational ownership continuity unresolved)','supported_candidate'),
        'se_earthscience':('https://stackoverflow.com/legal/terms-of-service/public','2025-11-13 terms opening identifies Stack Exchange, Inc. as Network operator','Stack Exchange, Inc.','confirmed'),
        'se_sustainability':('https://stackoverflow.com/legal/terms-of-service/public','2025-11-13 terms opening identifies Stack Exchange, Inc. as Network operator','Stack Exchange, Inc.','confirmed')}
    primary['mastodon_ie']=('https://mastodonie.github.io/mastodaoine-clg.html','Company duties list procurement and appointment of admins; saved extended description Ownership heading','Mastodaoine CLG','confirmed')
    rows=[]
    def add(source,dimension,parent,status,url,locator,summary,validity='current accessed assertion; historical continuity not established',source_observed='2026-10-10',provenance='primary_public_document',action='retain'):
        rows.append({'assertion_id':source+':'+dimension,'source_id':source,'stream':'newspaper' if source in sources[:2] else 'social',
                     'relation_dimension':dimension,'parent_id_or_label':parent,'evidence_status':status,'provenance_category':provenance,
                     'primary_url':url,'review_accessed_date':'2026-10-10','source_observation_time':source_observed,
                     'evidence_text_locator':locator,'evidence_summary':summary,'valid_time_start':'unknown','valid_time_end':'unknown',
                     'valid_time_limit':validity,'recommended_next_action':action,'invalidity_confirmed':False,
                     'author_role_country_limit':'Host/operator/community location does not identify individual author role or country',
                     'truth_verification':'not_established_by_provenance'})
    for source in sources:
        base=bases[source]
        source_native=by_source.get(source,[])
        if source in primary:
            url,loc,operator,status=primary[source]
        else:
            evidence=next((r for r in source_native if '/api/v2/instance' in r['primary_url']),source_native[0])
            url=evidence['primary_url'];loc='worker/NAMED_PRIMARY_PARENT_EVIDENCE.json#source_id='+source
            operator='unresolved legal organization; source-administered instance'
            status='unresolved'
        # Acquisition method identity is a snapshot assertion, not a corporate ownership claim.
        family={'devonport_flagstaff':'devonport_publishing recorded acquisition family',
                'northern_rivers_times':'northern_rivers_regional_media recorded acquisition family'}.get(source,base+' documented native interface')
        add(source,'acquisition_family',family,'confirmed',base,
            'worker/pinned/np9_parent.csv' if source in sources[:2] else 'worker/pinned/s4_source_registry.json#source_id='+source,
            'Recorded source/interface frame retained independently from publisher and individual works.',
            'closed acquisition snapshot only; not a verified ownership history',provenance='closed_metadata_assertion')
        add(source,'operator_organization',operator,status,url,loc,
            'Operator assertion or unresolved legal identity. A contact, administrator or software vendor is not automatically a publishing corporation.',
            action='derive_corrected_mapping' if source in ['northern_rivers_times','straight_dope'] else 'retain')
        if source=='devonport_flagstaff':
            add(source,'publisher_organization','Devonport Publishing Ltd','confirmed',url,loc,
                'Publisher-host identity is source-supported at the current observation; historical interval continuity remains unverified.')
        elif source=='northern_rivers_times':
            add(source,'publisher_organization','unresolved legal publisher; Northern Rivers Regional Media is a recorded family/brand','unresolved',url,loc,
                'Heartland Media contact association and current media-network brand do not prove corporate identity or an ownership start date.',action='derive_corrected_mapping')
        else:
            add(source,'publisher_organization','multiple native authors; source-wide publisher mapping unresolved','unresolved',url,loc,
                'The carrier or forum operator is distinct from the holder of each utterance. Record-level authorship not independently reviewed.')
        software=registry.get(source,{}).get('platform','unresolved')
        if source in sources[:2]:
            software='unresolved implementation';software_url=base;software_loc='No implementation claim verified in this bounded parent review';soft_status='unresolved'
        elif software=='Discourse':
            software_url=base+('/about' if source=='osm_discourse' else '/tos');software_loc='Footer Powered by Discourse';soft_status='confirmed'
        elif software=='Mastodon':
            e=next(r for r in source_native if '/api/v2/instance' in r['primary_url'])
            software_url=e['primary_url'];software_loc=loc+'; projection.version';soft_status='confirmed'
        elif software=='Lemmy':
            software_url=base+'/api/v3/site';software_loc=loc+'; projection.version/site';soft_status='confirmed'
        elif software=='Stack Exchange':
            software='Stack Exchange platform; underlying implementation/version unresolved'
            software_url=base+'/tour';software_loc='Site title and Stack Exchange/Stack Overflow network framing';soft_status='supported_candidate'
        else:
            software_url='https://raw.githubusercontent.com/bluesky-social/atproto/main/lexicons/app/bsky/feed/post.json';software_loc='app.bsky.feed.post lexicon';soft_status='confirmed'
        add(source,'software_family',software,soft_status,software_url,software_loc,
            'Software/platform implementation dimension only; sharing it does not establish a shared publisher, operator or independent work.')
        if software=='Mastodon':network='Fediverse / ActivityPub';neturl='https://joinmastodon.org/about';netloc='Decentralized network/server description';netstatus='confirmed'
        elif software=='Lemmy':network='Fediverse; source reports federation enabled';neturl=base+'/api/v3/site';netloc=loc+'; projection.local_site.federation_enabled';netstatus='confirmed'
        elif software=='Bluesky':network='AT Protocol; Bluesky application separate';neturl=url;netloc='Terms introduction';netstatus='confirmed'
        elif software.startswith('Stack Exchange'):network='Stack Exchange / Stack Overflow Network';neturl=url;netloc='Terms introduction and site tour';netstatus='confirmed'
        else:network='unresolved / no common discourse network asserted';neturl=base;netloc='No network identity inferred from domain or Discourse software';netstatus='unresolved'
        add(source,'platform_network',network,netstatus,neturl,netloc,
            'Network relationship preserved separately from software, instance and the original utterance author.')
        add(source,'instance',base,'confirmed',base,
            loc if source_native else 'Closed source registry URL and primary source page',
            'This observed domain is a source/interface host. Federation replicas and archives require separate original-work relations.',
            'observed source endpoint only; no claim of uninterrupted history')
        community={'devonport_flagstaff':'Devonport / Auckland community newspaper',
                   'northern_rivers_times':'Northern Rivers / NSW regional newspaper',
                   'bluesky':'Declared collected actor/feed frame; not the entire network',
                   'osm_discourse':'OpenStreetMap community; child categories not exhaustively mapped',
                   'python_discourse':'Python discussion community; child categories not exhaustively mapped',
                   'straight_dope':'Straight Dope Message Board; child forums not exhaustively mapped',
                   'se_earthscience':'Earth Science Q&A community','se_sustainability':'Sustainable Living Q&A community'}.get(source,registry[source].get('geographic_evidence','source-described community')) if source in registry else ('Devonport / Auckland community newspaper' if source=='devonport_flagstaff' else 'Northern Rivers / NSW regional newspaper')
        community_url=(base+'/tour') if software.startswith('Stack Exchange') else url
        add(source,'community',community,'confirmed' if source!='bluesky' else 'supported_candidate',community_url,
            'Site/community description; terms; saved native description; Bluesky collector frame remains bounded',
            'Describes the source community opportunity. Child-community inventory and all actor memberships remain unreviewed; nationality is not inferred.')
    for row in rows:
        saved=next((r for r in by_source.get(row['source_id'],[]) if r['primary_url']==row['primary_url']),None)
        row['saved_primary_payload_sha256']=saved['payload_sha256'] if saved else ''
        row['saved_primary_raw_locator']=saved['raw_locator'] if saved else ''
        if saved:
            row['source_observation_time']=saved['source_observed_at_utc'] or 'unknown retrieval timestamp in inherited registry; review access 2026-10-10'
            row['provenance_category']='saved_primary_public_source_metadata'
        row['corpus_directness_relative_to_utterance']='direct publisher-host media discourse; quotation and syndication origins record-specific' if row['stream']=='newspaper' else 'source-native authored expression or federation/context reproduction; record-level directness unresolved here'
        row['identity_date_content_verification']='source relation evidence only; corpus mapping checked separately for named records'
    target=OUT/'PARENT_SOURCE_EVIDENCE.csv'
    with target.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps({'sources':len(sources),'dimension_rows':len(rows),'unresolved_rows':sum(r['evidence_status']=='unresolved' for r in rows)}))

if __name__=='__main__':main()
