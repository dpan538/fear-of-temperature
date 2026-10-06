"""Acquire a frozen successor AU tranche before assessing retained bodies."""
import datetime as dt
import json
import re
from bs4 import BeautifulSoup
from public_capture import capture,ROOT

plan=json.loads((ROOT/'AU_SECOND_BATCH_PLAN.json').read_text())
frame_path=ROOT/'AU_SECOND_FROZEN_FRAME.json'
frames=json.loads(frame_path.read_text()) if frame_path.exists() else []
selected_count=0
for url in plan['sitemaps']:
    raw,receipt=capture(url,'au_sitemap','indaily')
    seen=set();targets=[]
    for node in BeautifulSoup(raw,'xml').find_all('loc'):
        article=node.get_text();match=re.search(r'https://www.indailysa.com.au/news/[^/]+/(\d{4})/(\d{2})/(\d{2})/',article)
        if not match:continue
        day='-'.join(match.groups())
        try:dt.date.fromisoformat(day)
        except ValueError:continue
        if not '1988-01-01'<=day<='2026-09-21' or day[:7] in seen:continue
        seen.add(day[:7]);targets.append(dict(url=article,url_date=day))
    targets=targets[:plan['max_new_articles']-selected_count]
    prior=next((x for x in frames if x['sitemap_receipt']==receipt['request_id']),None)
    if prior and prior['selected']!=targets:raise RuntimeError('Frozen native selection conflict')
    if not prior:
        frames.append(dict(sitemap_receipt=receipt['request_id'],sitemap_url=url,
                      selected=targets,frozen_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                      selection='first native dated news URL per observed month',
                      complete_frame=False,topic_or_emotion_filter=None,failed_target_replacement=False))
        frame_path.write_text(json.dumps(frames,indent=2)+'\n')
    for target in targets:
        data,response=capture(target['url'],'au_article','indaily')
        print(json.dumps(dict(url=response['url'],status=response['status'],raw_bytes=response['raw_bytes'])),flush=True)
    selected_count+=len(targets)
    if selected_count>=plan['max_new_articles']:break
