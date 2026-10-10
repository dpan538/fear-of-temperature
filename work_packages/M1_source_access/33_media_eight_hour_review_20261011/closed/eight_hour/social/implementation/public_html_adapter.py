"""Source-observed public HTML native units. External linked articles stay metadata."""
import re
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlsplit,parse_qs,unquote
from bs4 import BeautifulSoup
import entities as e

def same_site(url, base):
    p=urlsplit(urljoin(base,url))
    if p.scheme!='https' or p.hostname!=urlsplit(base).hostname:
        raise ValueError('native link leaves approved HTTPS source')
    return urljoin(base,url)

def text_time(node,selector):
    x=node.select_one(selector)
    return x.get('datetime') if x else None

def tildes_index(raw,url):
    soup=BeautifulSoup(raw,'html.parser');rows=[];topics=[]
    for a in soup.select('article.topic[id^="topic-"]'):
        tid=a['id'][6:];link=a.select_one('.topic-info-comments a');tm=text_time(a,'footer.topic-info time[datetime]')
        if not link:continue
        native_url=same_site(link['href'],url)
        title=a.select_one('.topic-title');excerpt=a.select_one('.topic-text-excerpt')
        rows.append(dict(source_id='tildes',native_namespace='topic',native_post_id=tid,native_unit='forum_topic',source_url=native_url,native_created_at=tm,author_id=a.get('data-topic-posted-by'),author_role='unknown',thread_id=tid,body_original=str(excerpt) if excerpt else '',content_state='truncated_index_preview',content_license='no_open_content_grant_verified',license_basis='ordinary authors retain copyright; docs/wiki CC BY-SA does not apply to posts',native_fields={'title':title.get_text(' ',strip=True) if title else None,'index_url':url,'preview_only':True,'source_group':urlsplit(native_url).path.split('/')[1]},flags={'no_external_article_body_acquired':True}))
        # Fixed publication dates decide eligibility; no title/topic/emotion selection.
        if tm and '1988-01-01'<=tm[:10]<='2026-09-21':topics.append(native_url)
    nxt=next((a['href'] for a in soup.select('.pagination a[href]') if a.get_text(' ',strip=True).lower()=='next'),None)
    return rows,{'topic_urls':topics,'native_next_url':same_site(nxt,url) if nxt else None,'returned_topic_ids':[r['native_post_id'] for r in rows]}

def tildes_topic(raw,url):
    soup=BeautifulSoup(raw,'html.parser');root=soup.select_one('article.topic-full[id^="topic-"]')
    if root is None:raise ValueError('native whole-topic container missing')
    tid=root['id'][6:];body=root.select_one('.topic-full-text');user=root.select_one('.topic-full-byline .link-user');title=root.select_one('h1');link=root.select_one('.topic-full-link a[href]')
    comments=root.select('article.comment[id^="comment-"]');count=root.select_one('.topic-comments-header h2');m=re.search(r'([0-9,]+)',count.get_text()) if count else None
    context={'source_group':urlsplit(url).path.split('/')[1],'title':title.get_text(' ',strip=True) if title else None,'linked_url':link.get('href') if link else None,'observed_comments':len(comments),'source_declared_comments':int(m[1].replace(',','')) if m else None,'whole_page_return_does_not_prove_historical_body_version':True}
    rows=[dict(source_id='tildes',native_namespace='topic',native_post_id=tid,native_unit='forum_topic',source_url=url,native_created_at=text_time(root,'.topic-full-byline time[datetime]'),author_id=user.get_text(strip=True) if user else None,author_role='unknown',thread_id=tid,body_original=body.decode_contents() if body else '',content_state='complete_native_text' if body else 'bodyless_native_entity',content_license='no_open_content_grant_verified',license_basis='ordinary authors retain copyright; bounded informational research access separately documented',native_fields=context,flags={'link_only_title_retained_as_metadata':bool(link and not body),'no_external_article_body_acquired':True},edges=[e.edge('link',None,url=link['href'])] if link else [])]
    for a in comments:
        # Nested comment articles include descendants. Read only this unit's own div.
        own=a.find('div',class_='comment-itself',recursive=False)
        if own is None:raise ValueError('comment own-body boundary missing')
        cid=a.get('data-comment-id36') or a['id'][8:];body=own.select_one('.comment-text');user=own.select_one('header .link-user');parent=own.select_one('[data-js-comment-parent-button]');permalink=next((x for x in own.select('a.comment-nav-link[href]') if x.get_text(strip=True)=='Link'),None)
        pid=parent['href'].split('#comment-',1)[1] if parent and '#comment-' in parent['href'] else None
        edges=[e.edge('root',tid,'topic',url=url)]
        if pid:edges.append(e.edge('reply',pid,'comment',url=same_site(parent['href'],url)))
        original=body.decode_contents() if body else ''
        rows.append(dict(source_id='tildes',native_namespace='comment',native_post_id=cid,native_unit='forum_reply',source_url=same_site(permalink['href'],url) if permalink else url+'#comment-'+cid,native_created_at=text_time(own,'time.comment-posted-time[datetime]'),native_edited_at=text_time(own,'.comment-edited-time time[datetime]'),author_id=user.get_text(strip=True) if user else None,author_role='unknown',thread_id=tid,reply_to_post_id=pid,body_original=original,content_state='complete_native_text' if original else 'bodyless_native_entity',content_license='no_open_content_grant_verified',license_basis='ordinary authors retain copyright; bounded informational research access separately documented',native_fields={'depth':a.get('data-comment-depth'),'source_declared_replies':a.get('data-comment-replies'),'source_group':context['source_group'],'body_serialization':'HTML subtree serialization; exact response bytes retained in raw'},flags={'native_parent_link_present':bool(parent),'nested_descendant_text_excluded_from_this_body':True,'quoted_and_spoiler_text_preserved':True},edges=edges))
    return rows,context

def mail_index(raw,url):
    soup=BeautifulSoup(raw,'html.parser');messages=[]
    expected=(parse_qs(urlsplit(url).query).get('l') or [unquote(urlsplit(url).path.split('/')[1])])[0]
    for a in soup.select('a[href]'):
        if re.fullmatch(r'msg[0-9]+\.html',urlsplit(a['href']).path.rsplit('/',1)[-1]):
            target=same_site(a['href'],url)
            if unquote(urlsplit(target).path.split('/')[1])!=expected:raise ValueError('search return crosses established list namespace')
            if target not in messages:messages.append(target)
    older=next((a['href'] for a in soup.select('a[href]') if a.get_text(' ',strip=True)=='Earlier messages'),None)
    if urlsplit(url).path=='/search':
        older=next((a['href'] for a in soup.select('a[href]') if a.get_text(' ',strip=True)=='>' and 'n' in a.get('accesskey',[])),None)
    return [],{'native_message_urls':messages,'native_next_url':same_site(older,url) if older else None}

def mail_message(raw,url,sid):
    soup=BeautifulSoup(raw,'html.parser');head=soup.select_one('.msgHead');body=soup.select_one('.msgBody')
    if head is None or body is None:raise ValueError('public archive own message boundaries missing')
    date=head.select_one('.date');sender=head.select_one('.sender');title=head.select_one('.subject')
    literal=date.get_text(' ',strip=True) if date else None
    when=parsedate_to_datetime(literal) if literal else None
    if when and when.tzinfo is None:raise ValueError('archive date lacks stated time zone')
    canonical=soup.select_one('link[rel="canonical"]');canonical_url=same_site(canonical['href'],url) if canonical else url
    nid=re.search(r'/msg([0-9]+)\.html$',urlsplit(canonical_url).path)
    if nid is None:raise ValueError('source native archive message ID missing')
    previous=soup.select_one('link[rel="prev"]');next_=soup.select_one('link[rel="next"]')
    return [dict(source_id=sid,native_namespace='archive_message',native_post_id='msg'+nid[1],native_unit='public_mailing_list_message',source_url=canonical_url,native_created_at=when.isoformat() if when else None,date_precision='archive_displayed_timestamp_with_offset',author_id=sender.get_text(' ',strip=True) if sender else None,author_role='unknown',body_original=body.decode_contents(),content_state='complete_native_text',thread_id='unresolved',context_status='original_message_ID_and_thread_identity_not_publicly_returned',content_license='no_open_content_grant_verified',license_basis='archive explicitly permits bounded local HTML mirroring; ordinary author ownership and redistribution remain separate',native_fields={'title':title.get_text(' ',strip=True) if title else None,'source_displayed_date_literal':literal,'date_basis':'source archive display; original raw email headers are not publicly available','archive_url':url,'canonical_archive_url':canonical_url,'original_list_address':urlsplit(canonical_url).path.split('/')[1],'original_project_pointer':'https://blog.e-democracy.org/posts/3193','decoded_html_encoding':soup.original_encoding,'previous_archive_message_url':same_site(previous['href'],url) if previous else None,'next_archive_message_url':same_site(next_['href'],url) if next_ else None,'cross_list_alias_and_original_Message_ID':'unresolved; no identity merge'},flags={'archival_reproduction_of_original_public_message':True,'archive_date_not_independently_verified_against_original_email_headers':True,'archive_signature_and_quoted_material_preserved':True,'provider_masked_addresses_preserved_no_reversal':True},edges=[])],{}


def ilxor_thread(raw,url):
    import datetime as dt
    soup=BeautifulSoup(raw,'html.parser');params=parse_qs(urlsplit(url).query)
    board=(params.get('boardid') or [None])[0];thread=(params.get('threadid') or [None])[0]
    if board!='40' or not thread or not thread.isdigit():raise ValueError('unapproved or unresolved native ILX thread namespace')
    canonical='https://www.ilxor.com/ILX/ThreadSelectedControllerServlet?boardid='+board+'&threadid='+thread
    title=soup.select_one('h1');rows=[];seen=set()
    skip=next((a for a in soup.select('a[href]') if 'Skipping ' in a.get_text() and parse_qs(urlsplit(a['href']).query).get('action')==['showall']),None)
    showall=same_site(skip['href'],url).split('#',1)[0] if skip else None
    for post in soup.select('div.firstmessage,div.message'):
        anchor=post.find_previous_sibling('a')
        if anchor is None or not re.fullmatch(r'msg[0-9]+',anchor.get('name','')):raise ValueError('native ILX own-message anchor missing')
        msg=anchor['name'];nid='board'+board+':thread'+thread+':'+msg
        if nid in seen:raise ValueError('repeated native anchor in one thread return')
        seen.add(nid);date=post.select_one('.postcontrol .date');name=post.select_one('.postcontrol .name')
        literal=date.get_text(' ',strip=True) if date else None
        when=dt.datetime.strptime(literal,'%A, %d %B %Y %H:%M').isoformat(timespec='minutes') if literal else None
        clone=BeautifulSoup(str(post),'html.parser').select_one('div')
        for control in clone.select('.postcontrol'):control.decompose()
        original=clone.decode_contents()
        rows.append(dict(source_id='ilxor',native_namespace='board_thread_message',native_post_id=nid,native_unit='forum_post' if 'firstmessage' in post.get('class',[]) else 'forum_reply',source_url=canonical+'#'+msg,native_created_at=when,date_precision='source_displayed_local_timestamp_timezone_unknown',author_id=name.get_text(' ',strip=True) if name else None,author_role='unknown',thread_id='board'+board+':thread'+thread,body_original=original,content_state='complete_native_text',content_license='no_open_content_grant_verified',license_basis='anonymous public forum read and bounded local research snapshot; authors retain rights, no redistribution grant inferred',context_status='default_thread_view_skips_intervening_messages' if skip else 'all_native_messages_returned_in_this_current_view; historical_versions_unverified',native_fields={'title':title.get_text(' ',strip=True) if title else None,'board_id':board,'thread_id':thread,'message_anchor':msg,'source_displayed_date_literal':literal,'source_timezone':'unresolved','source_displayed_author_name':name.get_text(' ',strip=True) if name else None,'stable_author_account_identity':'unresolved; display name is not a verified account ID','source_showall_url':showall,'source_skip_notice':skip.get_text(' ',strip=True) if skip else None},flags={'native_timezone_unknown':True,'midnight_display_may_be_migrated_day_precision':bool(when and when.endswith('00:00')),'per_message_body_complete_thread_context_may_be_partial':True,'quoted_material_preserved':True,'native_metadata_and_relative_ago_excluded_from_body':True,'board_scope_not_author_country':True},edges=[]))
    if not rows:raise ValueError('no verified native ILX own-message units returned')
    return rows,{'source_showall_url':showall,'returned_own_messages':len(rows),'thread_context_incomplete':bool(skip)}
