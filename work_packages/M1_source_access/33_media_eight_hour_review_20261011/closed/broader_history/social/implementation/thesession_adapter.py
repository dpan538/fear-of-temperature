"""Documented read-only discussion API. Member text rights remain separate."""
import re
import entities as e
from urllib.parse import urlsplit,parse_qs

def index(data):
    rows=sorted(data['discussions'],key=lambda x:(x['date'],x['url']))
    return [],{'topic_urls':[x['url'] for x in rows if '1988-01-01'<=x['date'][:10]<='2026-09-21'],'page':int(data['page']),'pages':int(data['pages']),'declared_total':data['total']}


def records(raw,url):
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin
    soup=BeautifulSoup(raw,'html.parser');path=urlsplit(url).path
    m=re.fullmatch(r'/discussions/([0-9]+)',path)
    if not m:raise ValueError('native individual discussion URL missing')
    tid=m[1];canonical='https://thesession.org/discussions/'+tid
    own=soup.select('article.feed-entry--comment[id^="comment"]');title=soup.select_one('h1');seen=set()
    rows=[dict(source_id='thesession',native_namespace='discussion',native_post_id=tid,native_unit='context_container',source_url=canonical,native_created_at=None,date_precision='unknown_container_creation_time',author_id=None,author_role='unknown',thread_id=tid,body_original='',content_state='context_container',native_fields={'title':title.get_text(' ',strip=True) if title else None},flags={'title_not_duplicated_as_body':True})]
    for post in own:
        cid=post['id'][7:];body=post.select_one('.e-content');footer=post.select_one('footer');date=footer.select_one('time[datetime]') if footer else None;member=footer.select_one('a[href^="/members/"]') if footer else None;permalink=footer.select_one('a[rel="bookmark"]') if footer else None
        if cid in seen or not cid.isdigit() or body is None or date is None or permalink is None:raise ValueError('missing/repeated native own-comment identity/date/body boundaries')
        seen.add(cid);native_url=urljoin(canonical,permalink['href']);when=date['datetime']
        if native_url!=canonical+'#comment'+cid or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',when):raise ValueError('unexpected native permalink/timestamp serialization')
        subject=post.select_one('h3');member_id=member['href'].rsplit('/',1)[-1] if member else None
        rows.append(dict(source_id='thesession',native_namespace='discussion_comment',native_post_id=cid,native_unit='forum_comment',source_url=native_url,native_created_at=when,date_precision='source_rendered_ISO_timestamp_with_UTC_offset',author_id=member_id,author_role='unknown',thread_id=tid,body_original=body.decode_contents(),content_state='complete_native_text',content_license='no_open_content_grant_verified',license_basis='site operator documents public API and exports complete HTML for local browsing/copies; original member text copyright and redistribution remain separately unresolved',context_status='source rendered individual discussion own-comment units; inter-reply parent not explicitly provided',native_fields={'native_discussion_id':tid,'subject':subject.get_text(' ',strip=True) if subject else None,'source_displayed_date_literal':date.get('title'),'native_member_profile_url':urljoin(canonical,member['href']) if member else None,'source_rendered_author_name':member.get_text(' ',strip=True) if member else None,'author_identity_basis':'rendered public footer only; source-anonymous units stay anonymous','no_API_to_reverse_current_rendered_anonymity':True},flags={'quoted_material_preserved':True,'member_identity_not_author_country_or_role':True,'no_separate_member_profile_or_location_request':True,'bundled_inline_member_bio_not_extracted_to_native_metadata':True,'source_rendered_anonymous_author':member is None,'native_title_and_metadata_not_duplicated_in_body':True},edges=[e.edge('root',tid,'discussion',url=canonical)]))
    if not own:raise ValueError('no verified native own-comment HTML units returned')
    nxt=next((a['href'] for a in soup.select('a[rel="next"][href]') if urlsplit(urljoin(canonical,a['href'])).path==path),None)
    return rows,{'native_discussion_id':tid,'returned_own_comments':len(own),'native_next_comment_page_url':urljoin(canonical,nxt) if nxt else None}
