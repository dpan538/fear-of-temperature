"""Targeted offline boundaries; synthetic data never enter acquisition outputs."""
import unittest
from unittest.mock import patch
import transport as t
class Boundaries(unittest.TestCase):
    def test_no_credentials_or_cross_host(self):
        for u in ['http://a.org/x','https://user:pass@a.org/x','https://a.org/x?api_key=secret','https://b.org/x']:
            with self.assertRaises(RuntimeError): t.validate_url(u,['a.org'])
        t.validate_url('https://a.org/2025/07/',['a.org'])
    def test_specific_robots_and_article_challenge(self):
        self.assertFalse(t.robots_allowed('User-agent: *\nDisallow: /blocked/', 'https://a.org/blocked/x'))
        self.assertTrue(t.robots_allowed('User-agent: *\nDisallow: /blocked/', 'https://a.org/news/x'))
        self.assertFalse(t.robots_allowed('User-agent: *\nAllow: /\nUser-agent: ChatGPT-User\nDisallow: /','https://a.org/news/x'))
        self.assertTrue(t.challenge(b'<title>Access denied</title>'))
        self.assertFalse(t.challenge(b'<article>A story about captcha and access denied</article>'))
    def test_reserve_and_deadline(self):
        with patch.object(t.shutil,'disk_usage',return_value=type('D',(),{'free':16*1024**3})()):
            with self.assertRaises(RuntimeError): t.budget(2097152)
        s=t.read(t.SCOPE);s['network_deadline_utc']='2000-01-01T00:00:00+00:00'
        with patch.object(t,'read',return_value=s):
            with self.assertRaises(RuntimeError): t.deadline()
if __name__=='__main__': unittest.main()
