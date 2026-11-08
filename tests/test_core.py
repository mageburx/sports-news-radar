import unittest
from datetime import datetime,timezone
from sports_radar.core import clean,canonical,identifier,merge,news_url
from sports_radar.collector import feed_parse

SRC={"id":"x","sport":"futebol","section":"manchester-united","name":"Manchester United","language":"en","query":"Manchester United","hl":"en-GB","gl":"GB","ceid":"GB:en","official_domain":"manutd.com"}
class Tests(unittest.TestCase):
 def test_cleanup(self):
  self.assertEqual(clean("<b> Olá </b> mundo"),"Olá mundo")
 def test_canonical(self):
  self.assertNotIn("utm_source",canonical("https://example.com/x?utm_source=abc"))
 def test_id_stable(self):
  self.assertEqual(identifier("mu","BBC","Test","https://a.com"),identifier("mu","BBC","Test","https://b.com"))
 def test_search_url(self):
  self.assertIn("news.google.com",news_url(SRC))
 def test_rss(self):
  xml=b'<rss><channel><item><title>Matchday</title><link>https://example.com/a</link><source url="https://www.manutd.com">MU</source></item></channel></rss>'
  a=feed_parse(xml,SRC,datetime.now(timezone.utc))
  self.assertEqual(len(a),1)
  self.assertTrue(a[0]["official"])
 def test_unverified(self):
  xml=b'<rss><channel><item><title>Matchday</title><link>https://example.com/a</link><source url="https://example.com">Other</source></item></channel></rss>'
  self.assertFalse(feed_parse(xml,SRC,datetime.now(timezone.utc))[0]["official"])
 def test_merge(self):
  self.assertEqual(len(merge([],[],datetime.now(timezone.utc))),0)
if __name__=="__main__":unittest.main()
