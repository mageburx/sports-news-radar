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

class DanishQualityTests(unittest.TestCase):
 def article(self,title,section="campeonato-dinamarques",publisher="Dansk sport",publisher_url="https://sport.tv2.dk"):
  return {"id":"test","title":title,"section":section,
          "publisher":publisher,"publisher_url":publisher_url}
 def test_norway_domains(self):
  from sports_radar.quality import nordic_rejection
  a=self.article("Betoro Herreligaen",publisher="TV 2 Play",publisher_url="https://play.tv2.no")
  self.assertEqual(nordic_rejection(a),"origem_norueguesa")
 def test_norwegian_language(self):
  from sports_radar.quality import nordic_rejection
  self.assertEqual(nordic_rejection(self.article("Håndball kvinner: Odense - Aalborg")),"origem_norueguesa")
 def test_norwegian_publishers(self):
  from sports_radar.quality import nordic_rejection
  self.assertEqual(nordic_rejection(self.article("Aalborg håndbold","campeonato-dinamarques","Nettavisen")),"origem_norueguesa")
 def test_ambiguous_tv2(self):
  from sports_radar.quality import nordic_rejection
  self.assertEqual(nordic_rejection(self.article("Herreligaen",publisher="TV 2 Play",publisher_url="")),"origem_indeterminada")
 def test_external_tournaments(self):
  from sports_radar.quality import nordic_rejection
  self.assertEqual(nordic_rejection(self.article("EHF Champions League: Aalborg - Celje")),"outra_competicao")
  self.assertEqual(nordic_rejection(self.article("UEFA Conference League: FC København - Chelsea","superliga-dinamarquesa")),"outra_competicao")
 def test_unrelated_international_football(self):
  from sports_radar.quality import nordic_rejection
  self.assertEqual(nordic_rejection(self.article("UEFA har modkandidat til Infantino på vej","superliga-dinamarquesa")),"outra_competicao")
 def test_danish_league_headline(self):
  from sports_radar.quality import nordic_rejection
  self.assertIsNone(nordic_rejection(self.article("Rundens Hold #12, Betoro Herreligaen")))
  self.assertIsNone(nordic_rejection(self.article("Preview: Randers FC - FC Nordsjælland","superliga-dinamarquesa")))
 def test_danish_club_news(self):
  from sports_radar.quality import nordic_rejection
  self.assertIsNone(nordic_rejection(self.article("GOG slår Aalborg i topkampen")))
  self.assertIsNone(nordic_rejection(self.article("Odense Håndbold forlænger kontrakten")))
 def test_no_false_football_from_city(self):
  from sports_radar.quality import nordic_rejection
  self.assertEqual(nordic_rejection(self.article("Odense restaurant festival åbner i morgen","superliga-dinamarquesa")),"sem_ligacao_a_liga")
 def test_other_sections_unchanged(self):
  from sports_radar.quality import nordic_rejection
  self.assertIsNone(nordic_rejection(self.article("EHF Champions League","ehf")))
 def test_existing_noise_samples(self):
  from sports_radar.quality import nordic_rejection
  self.assertIsNotNone(nordic_rejection(self.article("Kaptein Torbjørn: - Enormt stort. Virkelig en ære",publisher="Norges Håndballforbund | handball.no")))
  self.assertIsNotNone(nordic_rejection(self.article("Sønderjyske Fodbold - FC København live resultat, H2H og lagoppstilling","superliga-dinamarquesa",publisher="Sofascore")))
 def test_feed_parse_publisher_domain(self):
  from sports_radar.quality import publisher_hostname
  from sports_radar.collector import feed_parse
  xml=b'<rss><channel><item><title>Betoro Herreligaen: GOG vandt</title><link>https://news.google.com/rss/articles/x</link><source url="https://tophaandbold.dk">Tophaandbold</source></item></channel></rss>'
  a=feed_parse(xml,SRC,datetime.now(timezone.utc))
  self.assertEqual(publisher_hostname(a[0]),"tophaandbold.dk")


class OfficialPagesTests(unittest.TestCase):
 def test_numeric_date(self):
  from sports_radar.collector import listing_date
  self.assertEqual(listing_date("05.11.2026").date().isoformat(),"2026-11-05")
 def test_danish_month(self):
  from sports_radar.collector import listing_date
  self.assertEqual(listing_date("6 nov. 2026").date().isoformat(),"2026-11-06")
  self.assertEqual(listing_date("5. nov. 2026").date().isoformat(),"2026-11-05")
 def test_superliga_index(self):
  from sports_radar.collector import listing_rows
  from sports_radar.quality import filter_nordic
  src={"id":"superliga-web","sport":"futebol","section":"superliga-dinamarquesa","name":"3F Superliga · notícias oficiais","url":"https://www.superliga.dk/nyheder"}
  html='<html><a href="/nyheder/optakter/2026-27/preview-fck-brondby"><h2>Preview: FC København - Brøndby IF</h2><time>05.11.2026</time></a></html>'
  now=datetime(2026,11,8,tzinfo=timezone.utc)
  rows=listing_rows(html,src,now)
  self.assertEqual(len(rows),1)
  self.assertEqual(len(filter_nordic(rows)[0]),1)
 def test_handball_index(self):
  from sports_radar.collector import listing_rows
  from sports_radar.quality import filter_nordic
  src={"id":"tophaandbold-web","sport":"andebol","section":"campeonato-dinamarques","name":"Tophåndbold · notícias oficiais","url":"https://tophaandbold.dk/alle-nyheder"}
  html='<html><a href="/herreligaen-artikler/rundens-hold-12-betoro-herreligaen"><h3>Rundens Hold #12, Betoro Herreligaen</h3><time>6 nov. 2026</time></a><a href="/1-division-herrer-artikler/a"><h3>1. division</h3><time>6 nov. 2026</time></a></html>'
  now=datetime(2026,11,8,tzinfo=timezone.utc)
  rows=listing_rows(html,src,now)
  self.assertEqual(len(rows),1)
  self.assertEqual(len(filter_nordic(rows)[0]),1)
 def test_official_overrides_generic_title(self):
  from sports_radar.quality import nordic_rejection
  a={"title":"Dommerpåsætning i 14. spillerunde","source_id":"superliga-web","section":"superliga-dinamarquesa","publisher_url":"https://www.superliga.dk/nyheder"}
  self.assertIsNone(nordic_rejection(a))
 def test_official_excludes_international_news(self):
  from sports_radar.quality import nordic_rejection
  a={"title":"Optakt til VM: Spanien i EHF Euro Cup","source_id":"tophaandbold-web","section":"campeonato-dinamarques","publisher_url":"https://tophaandbold.dk/alle-nyheder"}
  self.assertEqual(nordic_rejection(a),"outra_competicao")


class OfficialTitleTests(unittest.TestCase):
 def test_listing_date_and_category_removed(self):
  from sports_radar.collector import tidy_official_title
  self.assertEqual(tidy_official_title("Månedens Spiller: Hjalte Langmack Betoro Herreligaen 3. nov. 2026","tophaandbold-web"),"Månedens Spiller: Hjalte Langmack")
 def test_preserve_original_league_word(self):
  from sports_radar.collector import tidy_official_title
  self.assertEqual(tidy_official_title("Rundens Hold #12, Betoro Herreligaen Betoro Herreligaen 2. nov. 2026","tophaandbold-web"),"Rundens Hold #12, Betoro Herreligaen")
 def test_clean_preview_prefix(self):
  from sports_radar.collector import tidy_official_title
  self.assertEqual(tidy_official_title("5. nov. Match of the Round: ny rivalisering Bambuni Kvindeligaen 5. nov. 2026","tophaandbold-web"),"Match of the Round: ny rivalisering")
 def test_leave_superliga_title(self):
  from sports_radar.collector import tidy_official_title
  self.assertEqual(tidy_official_title("Dommerpåsætning i 14. spillerunde","superliga-web"),"Dommerpåsætning i 14. spillerunde")

if __name__=="__main__":unittest.main()
