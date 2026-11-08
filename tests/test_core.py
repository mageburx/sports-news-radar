import unittest
from datetime import datetime,timezone
from sports_radar.core import clean,canonical,identifier,merge,news_url
from sports_radar.collector import feed_parse,translation_target,translation_source,translate_budget

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
 def test_danish_translates_to_english(self):
  self.assertEqual(translation_target({"language":"da"}),"en")
  self.assertEqual(translation_target({"language":"en"}),"pt")
  self.assertIsNone(translation_target({"language":"pt"}))
 def test_norwegian_detection(self):
  self.assertEqual(translation_source("Håndball kvinner fra Norge","da"),"no")
  self.assertEqual(translation_source("Fodbold i København","da"),"da")
 def test_danish_translator_with_mock_session(self):
  from unittest.mock import Mock,patch
  now=datetime.now(timezone.utc)
  row={"title":"Dansk fodbold i København","summary":"","language":"da","translated_title":"Velho título em português","translation_status":"translated","published_at":now.isoformat(),"last_translation_attempt_at":"","id":"a"}
  mock=Mock()
  response=Mock()
  response.json.return_value={"responseStatus":200,"responseData":{"translatedText":"Danish football in Copenhagen"}}
  response.raise_for_status.return_value=None
  mock.get.return_value=response
  status={}
  with patch("sports_radar.collector.time.sleep"):
   translate_budget(mock,[row],status,now)
  self.assertEqual(row["translated_title"],"Danish football in Copenhagen")
  self.assertEqual(row["translated_lang"],"en")
  self.assertEqual(status["danish_english_translated"],1)
  self.assertEqual(mock.get.call_args.kwargs["params"]["langpair"],"da|en")
 def test_translation_budget_cap(self):
  now=datetime.now(timezone.utc)
  row={"title":"Notícia dinamarquesa","summary":"","language":"da","translated_title":"","last_translation_attempt_at":""}
  status={"translation_budget":{"date":now.date().isoformat(),"characters":4200}}
  mock=__import__("unittest.mock",fromlist=["Mock"]).Mock()
  translate_budget(mock,[row],status,now)
  mock.get.assert_not_called()
  self.assertEqual(status["danish_english_pending"],1)
 def test_merge(self):
  self.assertEqual(len(merge([],[],datetime.now(timezone.utc))),0)
if __name__=="__main__":unittest.main()
