"""Reviewable round22 commands; requests remain subject to live scope and budget."""
import argparse,json
import transport as t
import government,media
INITIAL=[
    ('edjnet','https://www.europeandatajournalism.eu/sitemap_index.xml','discovery','sitemap'),
    ('opendemocracy','https://www.opendemocracy.net/en/about/','identity','policy'),
    ('opendemocracy','https://www.opendemocracy.net/sitemap.xml','discovery','sitemap'),
    ('indaily','https://www.indaily.com.au/robots.txt','robots','robots'),
    ('texastribune','https://www.texastribune.org/robots.txt','robots','robots'),
    ('spinoff','https://thespinoff.co.nz/robots.txt','robots','robots')]
def initialise_requests(environment_variant='initial'):
    results=[]
    for source,url,purpose,route in INITIAL:
        try:
            results.append(t.fetch(source,url,purpose,route,environment_variant=environment_variant))
        except RuntimeError as e:
            if any(x in str(e) for x in ['Storage','deadline','digest','lock']):raise
            print(json.dumps({'source_id':source,'route':route,'pre_request_local_stop':str(e)}),flush=True)
    return results
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['budget','preflight','initial-discovery','request','freeze-frame','inspect','certify','government-prepare','government-execute'])
    p.add_argument('--source');p.add_argument('--url');p.add_argument('--purpose');p.add_argument('--route');p.add_argument('--month');p.add_argument('--selector');p.add_argument('--input');p.add_argument('--request-id')
    p.add_argument('--environment-variant',default='initial',choices=['initial','network_enabled_after_dns_failure'])
    p.add_argument('--boundary-spec',help='JSON file with inspected source-specific exclusions/separators')
    p.add_argument('--source-timezone');p.add_argument('--observed-local-day')
    p.add_argument('--source-date-evidence',help='JSON file with exact visible date selector/text')
    a=p.parse_args()
    if a.action=='budget':print(json.dumps(t.budget(),indent=2))
    elif a.action=='preflight':print(json.dumps(t.preflight_receipt(t.OUT/'control/REQUEST_POLICY.json'),indent=2))
    elif a.action=='initial-discovery':initialise_requests(a.environment_variant)
    elif a.action=='request':t.fetch(a.source,a.url,a.purpose,a.route,environment_variant=a.environment_variant)
    elif a.action=='freeze-frame':
        x=t.read(a.input);media.freeze_frame(a.source,a.month,x['candidates'],x['evidence'],a.route,x['notes'])
    elif a.action=='inspect':
        receipt=t.read(t.OUT/'media/requests'/f'{a.request_id}.json');result=media.inspect_request(receipt,a.month,a.selector,
            t.read(a.boundary_spec) if a.boundary_spec else None,a.source_timezone,a.observed_local_day,
            t.read(a.source_date_evidence) if a.source_date_evidence else None)
        print(json.dumps({k:result.get(k) for k in ['request_id','title','first_publication','eligible_month','body_selector_matches','boundary_status']},ensure_ascii=False,indent=2))
    elif a.action=='certify':media.certify(a.request_id,t.read(a.input))
    elif a.action=='government-prepare':government.prepare()
    elif a.action=='government-execute':government.execute()
if __name__=='__main__':main()
