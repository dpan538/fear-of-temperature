"""Prepared native-issue parser repair; no transport or write side effects.

Integration belongs to a newly released collector. Frozen collectors are intact.
The issue directory's empty state is distinct from successful HTTP transport.
"""
import re
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup


def issue_candidates(html, issue_url):
    soup=BeautifulSoup(html,'html.parser')
    expected=re.fullmatch(r'/issue/(\d+)',urlsplit(issue_url).path)
    if not expected: raise ValueError('Expected a native Green Left issue URL')
    heading=soup.select_one('h1')
    if not heading or not re.fullmatch(r'Issue\s+'+expected[1],heading.get_text(' ',strip=True),re.I):
        return {'status':'pending_issue_identity','candidates':[]}
    # The observed Drupal historical issue directory is inside layout-content.
    # main also contains asides and is therefore too broad.
    region=soup.select_one('main .layout-content .region-content')
    if region is None:
        return {'status':'pending_issue_content_container','candidates':[]}
    for node in region.select('aside,nav,header,footer,.view-sidebar-content'):
        node.decompose()
    candidates=[];seen=set()
    for a in region.select('a[href]'):
        url=urljoin(issue_url,a['href']);u=urlsplit(url)
        m=re.match(r'^/(\d{4})/(\d+)/',u.path)
        if u.hostname!='www.greenleft.org.au' or not m or url in seen:continue
        seen.add(url)
        candidates.append({'url':url,'title':a.get_text(' ',strip=True),'native_issue_url':issue_url,
                           'issue_relation':'path_issue_matches' if m[2]==expected[1] else 'pending_path_issue_relation',
                           'date_assignment':'pending_independent_article_date_check'})
    return {'status':'native_candidates_found' if candidates else 'observed_empty_issue_directory',
            'candidates':candidates,'HTTP_success_is_not_directory_success':True}
