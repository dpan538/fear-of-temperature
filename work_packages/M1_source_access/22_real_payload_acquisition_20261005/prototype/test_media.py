"""Dates and visible body identity are separate from JSONLD/preview presence."""
import unittest
import media
from unittest.mock import patch
class ArticleBoundaries(unittest.TestCase):
    def test_saved_search_leading_newlines_do_not_drop_dated_entries(self):
        raw='First (https://a.org/first)\nPublished: July 01, 2025, 1pm\n'+'-'*80+'\n\nSecond (https://a.org/second)\nPublished: July 02, 2025, 2pm\n'+'-'*80+'\nOther (https://b.org/third)\nPublished: July 03, 2025'
        self.assertEqual([x['url'] for x in media.dated_search_inventory(raw,['a.org'],'2025-07')],['https://a.org/first','https://a.org/second'])
    def test_archive_navigation_is_not_an_article_frame(self):
        with patch.object(media.t,'read',side_effect=[{'original_months':['2015-12']},{'candidates':[{'source_id':'test','founded_year':2009}]}]):
            with self.assertRaisesRegex(RuntimeError,'Navigation URL'):
                media.freeze_frame('test','2015-12',[{'url':'https://example.org/2015/12/01/page/2'}],[],'archive','synthetic')
    def data(self,extra='',date='2025-07-01T23:30:00-05:00',body=True):
        return (f'<link rel="canonical" href="https://a.org/one"><h1>Title</h1><script type="application/ld+json">{{"@type":"NewsArticle","url":"https://a.org/one","datePublished":"{date}"{extra}}}</script>'+('<article><div class="body"><p>First paragraph.</p><p>Last paragraph.</p></div><aside>Other stories.</aside></article>' if body else '')).encode()
    def test_local_day_not_utc_reassignment(self):
        r=media.parse(self.data(),'https://a.org/one','2025-07','.body');self.assertTrue(r['eligible_month']);self.assertEqual(r['first_publication']['local_day'],'2025-07-01')
    def test_jsonld_without_visible_body_not_complete(self):
        r=media.parse(self.data(body=False),'https://a.org/one','2025-07','.body');self.assertIsNone(r['body_text']);self.assertFalse(r['visible_body_verified'])
    def test_preview_not_complete(self):
        r=media.parse(self.data(extra=',"isAccessibleForFree":false'),'https://a.org/one','2025-07','.body');self.assertTrue(r['paywall_or_preview']);self.assertIsNone(r['body_text'])
    def test_wrong_month_not_included(self):
        self.assertFalse(media.parse(self.data(date='2025-08-01'),'https://a.org/one','2025-07','.body')['eligible_month'])
    def test_actual_visible_body_still_requires_review(self):
        r=media.parse(self.data(),'https://a.org/one','2025-07','.body');self.assertEqual(r['body_text'],'First paragraph.\nLast paragraph.');self.assertFalse(r['visible_body_verified']);self.assertEqual(r['jsonld_identity'],'canonical_match')
    def test_real_separator_boundary_with_nested_widgets(self):
        data=b'<article><div class="body"><p>Newsletter</p><hr><p>First</p><aside><form>Signup</form></aside><p>Last</p><hr><p>Event promotion</p></div></article>'
        r=media.parse(data,'https://a.org/one','2025-07','.body',{'mode':'between_direct_separators','after_separator_index':0,'before_separator_index':1})
        self.assertEqual(r['body_text'],'First\nLast')
    def test_article_table_text_is_preserved_once_and_widgets_excluded(self):
        data=b'<div class="body"><p>First</p><table><tr><td>Event date</td><td><p>Event detail</p></td></tr></table><section class="below-content"><p>Donate</p></section><p>Last</p></div>'
        r=media.parse(data,'https://a.org/one','2025-07','.body',{'exclude_selectors':['.below-content']})
        self.assertEqual(r['body_text'],'First\nEvent date Event detail\nLast')
if __name__=='__main__':unittest.main()
