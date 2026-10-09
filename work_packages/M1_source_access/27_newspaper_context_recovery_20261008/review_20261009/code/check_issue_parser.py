"""Focused regression tests for the observed sidebar contamination defect."""
from green_left_issue_candidates import issue_candidates

def run():
    html='''<main><div class="layout-content"><div class="region-content"><h1>Issue 374</h1><a href="/1999/374/news/a">A</a><a href="/1999/374/news/a">A duplicate link</a><a href="/1993/575/news/b">B</a></div></div><aside><a href="/2026/1463/news/latest">Latest</a></aside></main>'''
    r=issue_candidates(html,'https://www.greenleft.org.au/issue/374')
    assert len(r['candidates'])==2
    assert all('/2026/' not in x['url'] for x in r['candidates'])
    assert r['candidates'][1]['issue_relation']=='pending_path_issue_relation'
    assert all(x['date_assignment']=='pending_independent_article_date_check' for x in r['candidates'])
    assert issue_candidates('<h1>Issue 374</h1>','https://www.greenleft.org.au/issue/374')['status']=='pending_issue_content_container'
    assert issue_candidates(html,'https://www.greenleft.org.au/issue/379')['status']=='pending_issue_identity'
    empty=html.replace('<a href="/1999/374/news/a">A</a><a href="/1999/374/news/a">A duplicate link</a><a href="/1993/575/news/b">B</a>','')
    assert issue_candidates(empty,'https://www.greenleft.org.au/issue/374')['status']=='observed_empty_issue_directory'
    print('Passed: sidebar exclusion, deduplicated links, unresolved issue relation, no date inference, missing container, wrong identity, empty directory.')
if __name__=='__main__':run()
