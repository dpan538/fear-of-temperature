"""Missing-month round-robin opportunity; native order within each month, no labels."""
import collections,csv,json,re
import core

def baseline():
    return list(csv.DictReader((core.BASE/'NEWSPAPER_MONTH_LEDGER.csv').open()))
def present():return {(r['stratum'],r['month']) for r in baseline() if r['stratum']!='pooled' and int(r['readable_saved_units'])>0}
def date_url(url):
    m=re.search(r'/(\d{4})/(\d{2})/(\d{2})(?:/|$)',url)
    return '-'.join(m.groups()) if m and core.eligible('-'.join(m.groups())) else None
def select(candidates,occupied,per_month=1):
    counts=collections.Counter();selected=[];remaining=[]
    # Native DOM order is kept inside a month; missing early months precede later.
    ordered=sorted(enumerate(candidates),key=lambda x:(x[1]['publication_date'][:7],x[0]))
    for _,c in ordered:
        coord=(c['stratum'],c['publication_date'][:7])
        if core.eligible(c['publication_date']) and coord not in occupied and counts[coord]<per_month:
            selected.append(c);counts[coord]+=1
        else:remaining.append(c)
    return selected,remaining
def alternate(queues):
    result=[];qs={s:list(queues.get(s,[])) for s in core.SCOPE['strata']}
    while any(qs.values()):
        for s in core.SCOPE['strata']:
            if qs[s]:result.append(qs[s].pop(0))
    return result
def initial():
    occupied=present();months=sorted({r['month'] for r in baseline()})
    queue=alternate({s:[dict(stratum=s,month=m,state='missing_readable_unit',priority='early_1988_2006' if m<'2007-01' else 'later_missing') for m in months if (s,m) not in occupied] for s in core.SCOPE['strata']})
    core.save('FRONTIER_v1.json',{'version':'source_month_frontier_v1','generated_at_utc':core.utc(),'baseline_reference':str(core.BASE/'NEWSPAPER_MONTH_LEDGER.csv'),'baseline_accepted_receipt':str(core.OWN.parent/'control/BASELINE_RECEIPT.json'),'fixed_interval':core.SCOPE['publication_interval'],'equal_planned_discovery_opportunity':20,'equal_planned_article_transfer_opportunity':12,'opportunity_transfer':False,'selection':'first one to three native-order units per newly observed month; retained native remainder; no topic/fear/length filters','queue':queue})
    print(json.dumps({'pending_regional_cells':len(queue),'baseline_readable_cells':len(occupied)}))
if __name__=='__main__':initial()
