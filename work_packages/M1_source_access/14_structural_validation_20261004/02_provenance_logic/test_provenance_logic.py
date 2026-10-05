import unittest
from collections import Counter
from datetime import date, datetime, timezone, timedelta

from validate_provenance_logic import (
    answer_date_outcome, date_clock_role, evaluate, issuer_host_relation,
    parent_key, scope, source_directness, iso_day, fr_number_from_url,
)


def base(kind="UK", frame="UK_DEFRA"):
    return dict(kind=kind, frame=frame, id="p1", canonical="https://example.org/p1",
                source_id="src_ac30b1ae596ab5ab5379", external="e1",
                pub=date(2020, 1, 1), precision="day", basis="GOV.UK Content API first_published_at",
                body_status="downloaded_and_extracted",
                rel=dict(object_count=1, version_count=1, text_version_count=1, attachment_count=2),
                directness="original_utterance", host="GOV.UK", source_version="v1")


def run_one(r, extra=None):
    can=Counter({(r["frame"],r["canonical"]):1})
    ext=Counter({(r["frame"],r.get("fr_number", "")):1})
    if extra:ext.update(extra)
    return evaluate(r,can,ext)


class StructuralRulesTest(unittest.TestCase):
    def test_fixed_cutoff_and_precision(self):
        self.assertEqual(scope("2026-09-21","day"),"supported")
        self.assertEqual(scope("2026-09-22","day"),"conflict")
        self.assertEqual(scope("2026-09","month"),"needs_review")
        self.assertEqual(scope("2026-08","month"),"supported")
        self.assertEqual(scope("2026","year"),"needs_review")
        self.assertEqual(scope("","unknown"),"uncheckable")

    def test_timezone_midnight_is_convention_sensitive(self):
        r=base();r["pub"]=date(2022,7,1)
        r["date_exception"]={"raw_source_first_published_at":"2022-07-01T00:00:00+01:00"}
        r["updated"]=datetime(2022,6,30,23,0,0,tzinfo=timezone.utc)
        self.assertEqual(run_one(r)["DATE_CROSS"][0],"needs_review")
        self.assertEqual(run_one(r)["DATE_CLOCKS"][0],"supported")
        shanghai=datetime(2024,2,7,0,6,52,tzinfo=timezone(timedelta(hours=8)))
        self.assertEqual(iso_day(shanghai),date(2024,2,6))

    def test_au_cms_does_not_supply_publication(self):
        r=base("AU","AU_CATALOGUE")
        r.update(pub="",precision="unknown",basis="Original date unresolved; CMS timestamp excluded",
                 evidence={"cms_created_at":"2026-09-22T11:10:03+10:00","date_value":""},
                 au_candidate="",au_verified="",au_publisher="",host="DCCEEW",rel={})
        e=run_one(r)
        self.assertEqual(e["DATE_SCOPE"][0],"uncheckable")
        self.assertNotEqual(e["DATE_SCOPE"][0],"conflict")
        self.assertNotEqual(date_clock_role(date(2020,1,1),None,None,"Original date unresolved; CMS timestamp excluded"),"conflict")
        r["au_candidate"]="2026-09"
        self.assertEqual(run_one(r)["DATE_SCOPE"][0],"needs_review")

    def test_stale_status_needs_review_not_body_rejection(self):
        r=base();r["body_status"]="blocked_pending_ethics_route"
        self.assertEqual(run_one(r)["STATUS"][0],"needs_review")
        self.assertEqual(run_one(r)["CONTENT_LINK"][0],"supported")
        us=base("US","US_FR");us.update(body_status="source_extracted_and_cleaned",basis="publication_date",evidence={"date_precision":"day","date_value":"2020-01-01","original_publisher":"EPA"})
        self.assertEqual(run_one(us)["STATUS"][0],"supported")

    def test_archive_and_authored_discourse(self):
        self.assertEqual(source_directness("ministerial_answer",False,True),"archival_reproduction")
        self.assertEqual(source_directness("media_article",True,False),"original_utterance")
        self.assertEqual(source_directness("petitioner_text",True,True),"original_utterance")

    def test_host_issuer_scope_not_falsehood(self):
        self.assertEqual(issuer_host_relation("CSIRO Marine Research","DCCEEW",True),"needs_review")
        self.assertEqual(issuer_host_relation("Department of the Environment","DCCEEW",True),"supported")

    def test_repeated_fr_number_distinct_issues(self):
        self.assertNotEqual(parent_key("US_FR","https://x/1995/09/29/95-24211","1995-09-29","95-24211"),
                            parent_key("US_FR","https://x/1995/11/13/95-24211","1995-11-13","95-24211"))
        self.assertEqual(fr_number_from_url("https://www.federalregister.gov/documents/1995/09/29/95-24211/technical-amendments"),"95-24211")
        r=base("US","US_FR");r.update(fr_number="95-24211",evidence={"date_precision":"day","date_value":"2020-01-01","original_publisher":"EPA"},basis="publication_date")
        self.assertEqual(run_one(r,{("US_FR","95-24211"):1})["IDENT"][0],"needs_review")

    def test_answer_deadline_and_future_event_are_not_contradictions(self):
        self.assertEqual(answer_date_outcome("2026-01-14T00:00:00","2026-01-08T00:00:00",date(2026,1,14)),"supported")
        self.assertEqual(date_clock_role(date(2020,1,1),"2021-01-01",None,"official issue date"),"supported")
        r=base();r["mentioned_future_event"]="2050-01-01"
        self.assertEqual(run_one(r)["DATE_CLOCKS"][0],"supported")

    def test_multiple_attachments_remain_one_parent(self):
        r=base();r["rel"]["attachment_count"]=6
        self.assertEqual(run_one(r)["ATTACHMENT"][0],"supported")


if __name__=="__main__":unittest.main()
