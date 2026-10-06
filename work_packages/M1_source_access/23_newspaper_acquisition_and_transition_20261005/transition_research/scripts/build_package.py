"""Build bounded, manually verified literature evidence tables. No corpus access."""
import csv
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARCHIVE = "https://reutersinstitute.politics.ox.ac.uk/digital-news-report/archive/survey/"
sources = []

def source(sid, family, authors, title, year, kind, doi, url, files, read_scope, verification):
    record = dict(source_id=sid, evidence_family=family, authors=authors, title=title,
                  publication_year=year, publication_type=kind, doi=doi, primary_url=url,
                  local_source_files=files, read_scope=read_scope, metadata_verification=verification)
    sources.append(record)
    return record

R01 = source("R01", "core_01", "Nic Newman; David A. L. Levy; Rasmus Kleis Nielsen",
    "Reuters Institute Digital News Report 2015: Tracking the Future of News", 2015,
    "Institutional survey report", "10.60625/risj-y3dr-t653",
    ARCHIVE+"2015/executive-summary-and-key-findings-2015/index.html",
    "sources/dnr2015_summary.html; sources/dnr2015_method_correct.html; sources/dnr2015_doi.json",
    "Original executive summary, numerical chart configuration and methodology read; full PDF not read",
    "Title/authors/year/DOI cross-checked against Oxford landing page and DataCite; numbers from original chart arrays")
R02a = source("R02a", "core_02", "Nic Newman", "United Kingdom, Digital News Report 2016", 2016,
    "Institutional survey country chapter", "", ARCHIVE+"2016/united-kingdom-2016/index.html",
    "sources/dnr2016_uk.html; sources/dnr2016_summary.html; sources/dnr2016_method.html",
    "Original country table, executive summary category label and methodology read", "Original chapter identity and table verified")
R02b = source("R02b", "core_02", "Nic Newman", "United Kingdom, Digital News Report 2017", 2017,
    "Institutional survey country chapter", "", ARCHIVE+"2017/united-kingdom-2017/index.html",
    "sources/dnr2017_uk.html; sources/uk2017_sources_chart_v7.html; sources/dnr2017_full.pdf; sources/dnr2017_page55.png",
    "Original country text, embedded numerical data, PDF pp.6 and 54-55 read; p.55 visually checked",
    "Online chart 41/41 agrees with original PDF plot; full report credited Newman, Fletcher, Kalogeropoulos, Levy and Nielsen")
R02c = source("R02c", "core_02", "Nic Newman", "United Kingdom, Digital News Report 2018", 2018,
    "Institutional survey country chapter", "", ARCHIVE+"2018/united-kingdom-2018/index.html",
    "sources/dnr2018_uk.html; sources/uk2018_sources_chart_v3.html; sources/dnr2018_method.html",
    "Original country text, numerical chart data and methodology read",
    "Chart title/category/United Kingdom identity verified; no full-report DOI claimed")
R03 = source("R03", "core_03", "Sascha Hölig; Uwe Hasebrink", "Germany, Digital News Report 2020", 2020,
    "Institutional survey country chapter", "", ARCHIVE+"2020/germany-2020/index.html",
    "sources/dnr2020_germany.html; sources/germany2020_chart_v4.html; sources/germany2020_chart_v4_data.csv",
    "Original country chapter and embedded annual chart data read",
    "Country authors, survey wave and chart identity verified; chart metadata published 2020-06-16")
R04 = source("R04", "core_04", "Elisa Shearer", "Social media outpaces print newspapers in the U.S. as a news source", 2018,
    "Original research organization survey article", "",
    "https://www.pewresearch.org/short-reads/2018/12/10/social-media-outpaces-print-newspapers-in-the-u-s-as-a-news-source/",
    "sources/pew2018.html; sources/pew2018_method_parent.html",
    "Original article and its linked parent survey report read",
    "Author/date/title and linked field dates/N verified on Pew; not the separate N=4581 social-media survey")
R05 = source("R05", "core_05", "Ofcom; Jigsaw Research", "News Consumption in the UK: 2019", 2019,
    "Regulator survey report", "",
    "https://www.ofcom.org.uk/__data/assets/pdf_file/0027/157914/uk-news-consumption-2019-report.pdf",
    "Browser-readable original PDF; no local PDF saved",
    "Original PDF pp.1,13-17 and121 read in web reader; local download returned 403",
    "Title/date/producer/base/question/figures checked in original PDF; no DOI identified")
R06 = source("R06", "core_06", "Ofcom; Jigsaw Research", "News Consumption in the UK 2024 Report", 2024,
    "Regulator survey report", "",
    "https://www.ofcom.org.uk/siteassets/resources/documents/research-and-data/tv-radio-and-on-demand-research/tv-research/news/news-consumption-2024/news-consumption-in-the-uk-2024-report.pdf?v=379621",
    "Browser-readable original PDF; no local PDF saved",
    "Original PDF pp.3-8 and21 read in web reader; local download returned 403",
    "Original Figure 1 and methods verified; internal base discrepancy and category changes retained")
R07 = source("R07", "core_07", "Sora Park; Caroline Fisher; Kieran McGuinness; Jee Young Lee; Momoko Fujita; Ashleigh Haw; Kerry McCallum; G. Nardi",
    "Digital News Report: Australia 2025", 2025, "University survey report, original university release consulted",
    "10.60836/md4e-k570", "https://researchprofiles.canberra.edu.au/en/publications/digital-news-report-australia-2025/",
    "sources/au2025_landing.html; sources/au2025_doi.json; sources/au2025_release.html",
    "Report metadata and original university release read; report PDF inaccessible; exact survey base/field dates pending",
    "DOI/year/title verified via DataCite and university; full author list from university, DataCite lists first three plus Et Al.")
R08 = source("R08", "core_08", "NZ On Air; Glasshouse Consulting", "Where Are the Audiences? 2024", 2024,
    "Original public-agency commissioned audience survey", "",
    "https://www.nzonair.govt.nz/documents/1183/Where_are_the_Audiences_2024_Report_Final_21_08_24.pdf",
    "sources/nzoa2024.pdf; sources/nzoa2024.txt; sources/nzoa2024_page75.png",
    "PDF background/methods and news-source pp.73-76 read; p.75 visually verified",
    "Agency/consultant, field dates, age frame and original news figure checked; background and figure bases differ")
R09 = source("R09", "core_09", "Oscar Westlund; Mathias A. Färdigh",
    "Accessing the news in an age of mobile media: Tracing displacing and complementary effects of mobile news on newspapers and online news", 2015,
    "Peer-reviewed journal article", "10.1177/2050157914549039", "https://doi.org/10.1177/2050157914549039",
    "sources/crossref_westlund.json; original publisher abstract read in browser",
    "Publisher abstract only; full text unavailable",
    "Crossref and publisher: Mobile Media & Communication 3(1),53-74; issue 2015, online 2014")
R10 = source("R10", "core_10", "Richard Fletcher; Rasmus Kleis Nielsen",
    "Are people incidentally exposed to news on social media? A comparative analysis", 2018,
    "Peer-reviewed journal article, author accepted manuscript", "10.1177/1461444817724170", "https://doi.org/10.1177/1461444817724170",
    "sources/crossref_fletcher.json; sources/fletcher2018.pdf; sources/fletcher2018.txt",
    "Accepted manuscript methods/results/discussion and Table 1 read; not every reference inspected",
    "Crossref/publisher/Oxford repository: New Media & Society 20(7),2450-2468; issue 2018, online 2017")
R11 = source("R11", "core_11", "Neil Thurman; Richard Fletcher",
    "Are Newspapers Heading Toward Post-Print Obscurity? A Case Study of The Independent's Transition to Online-only", 2018,
    "Peer-reviewed journal article, repository full text", "10.1080/21670811.2018.1504625", "https://doi.org/10.1080/21670811.2018.1504625",
    "sources/crossref_thurman.json; sources/thurman2018.pdf; sources/thurman2018.txt",
    "Original full text methods/results/conclusion read",
    "Crossref/publisher/university PDF: Digital Journalism 6(8),1003-1017; Crossref title omits subtitle present in PDF")
R12 = source("R12", "core_12", "Alessio Cornia; Annika Sehl; David A. L. Levy; Rasmus Kleis Nielsen",
    "Private Sector News, Social Media Distribution, and Algorithm Change", 2018,
    "Institutional research report", "10.60625/risj-cg3f-he14", "https://doi.org/10.60625/risj-cg3f-he14",
    "sources/cornia2018_doi.json; sources/cornia2018_landing.html; sources/cornia2018.pdf; sources/cornia2018.txt",
    "Original report executive summary, methods and distribution/referral sections read",
    "Original PDF and DataCite/Oxford title/authors/date/DOI verified; not classified as a journal article")
S01 = source("S01", "supplementary", "W. Russell Neuman; Lauren Guggenheim; S. Mo Jang; Soo Young Bae",
    "The Dynamics of Public Attention: Agenda-Setting Theory Meets Big Data", 2014,
    "Peer-reviewed journal article", "10.1111/jcom.12088", "https://doi.org/10.1111/jcom.12088",
    "sources/crossref_neuman.json; original publisher abstract read in browser",
    "Publisher abstract only; repository PDF inaccessible",
    "Crossref and original publisher: Journal of Communication 64(2),193-214; author name segmentation normalized to original byline")
S02 = source("S02", "supplementary", "Ester de Waal; Klaus Schoenbach",
    "News sites' position in the mediascape: Uses, evaluations and media displacement effects over time", 2010,
    "Peer-reviewed journal article", "10.1177/1461444809341859", "https://doi.org/10.1177/1461444809341859",
    "sources/crossref_dewaal.json; original publisher abstract and footnote read in browser",
    "Publisher abstract and study-date footnote only; full text unavailable",
    "Crossref/publisher: New Media & Society 12(3),477-496; issue and online publication both 2010")

evidence = []
def row(eid, src, stratum, geography, period, population, design, n, metric, denominator,
        finding, locator, reported="", inferred="", timing="none", limits="", relevance=""):
    evidence.append(dict(evidence_id=eid, source_id=src["source_id"], evidence_family=src["evidence_family"],
        authors=src["authors"], title=src["title"], publication_year=src["publication_year"], doi=src["doi"],
        primary_url=src["primary_url"], stratum=stratum, geography=geography, study_period_or_field_dates=period,
        population=population, design=design, sample_size_or_units=n, measure=metric, denominator=denominator,
        verified_finding=finding, author_reported_crossover=reported, reviewer_inferred_interval=inferred,
        timing_status=timing, primary_locator=locator, limitations_or_pending=limits,
        full_text_read_scope=src["read_scope"], metadata_verification=src["metadata_verification"],
        provenance="Original research producer for findings; journal accepted manuscripts are author archival reproductions where stated",
        corpus_implication=relevance))

DN = "Quota-sampled weighted online panel; excludes respondents with no news use in past month; offline non-users under-represented"
DL = "Self-report; overlapping weekly categories; 2014 estimated after questionnaire randomisation error; rounded point values; no within-person or monthly transition identified"
row("E01",R01,"US","United States","2012-2015 waves; 2015 field end January/start February",
    "Internet-access news consumers",DN,"USA 2012/13/14/15: 845/2028/2197/2295",
    "Q3 sources used in past week: Print vs Social media","All final survey respondents, weighted percent",
    "2013 social 27%, print 41%; estimated 2014 33% vs 32%; 2015 40% vs 23%",
    "Executive summary Sources of news 2012-15 USA; embedded line-chart-1",inferred="2013-2015 observed-wave bracket; 2014 first sampled inversion uses estimated data",timing="reviewer inference from original values",limits=DL,relevance="Diagnostic window only; do not weight article/post counts by audience share")
row("E02",R04,"US","United States","2018 field July 30-August 12; comparison with 2017",
    "US adults 18+","American Trends Panel, nationally representative adult survey","3425 in linked parent survey",
    "Often gets news from social media vs print newspapers","All US adults; weighted percent",
    "2018 social 20%, print 16%; original article says first exceedance in its question series, with 2017 approximately equal",
    "Original article opening and platform chart; linked December 3 survey report",reported="2018, explicitly reported as first in question series",timing="author-reported series milestone",limits="Often differs from weekly use and main source; series start and all previous waves not re-audited; no transfer to print-plus-digital brands",relevance="Keep separate from E01; different survey frame and frequency")
row("E03",R04,"US","United States","2018 field July 30-August 12","US adults aged 18-29",
    "Age subgroup of American Trends Panel","Subgroup N not verified","Often uses social vs print for news",
    "Adults 18-29, not all adults","Social 36%, print 2%","Original article age-group chart",timing="cross-sectional age contrast",limits="Age comparison does not identify cohort effects or subgroup crossover year",relevance="Prepare later age sensitivity where audience information exists; corpus authors' ages may be unknown")
row("E04",R02a,"UK","United Kingdom","2013-2016 waves; 2016 field end January/start February",
    "Internet-access monthly news consumers",DN,"2016 UK 2024",
    "Past-week Print/Printed Newspaper vs Social","All final online survey respondents",
    "2015 social 36%, print 39%; 2016 social 35%, print 35%",
    "Country SOURCE OF NEWS 2013-16 table; overview labels Printed Newspaper",inferred="Rounded parity in 2016, not strict exceedance",timing="reviewer observation",limits="Historical values differ from 2015 report vintage; do not silently harmonise; rounded equality does not prove statistical equivalence",relevance="Retain report vintage and exact category")
row("E05",R02b,"UK","United Kingdom","2017 field end January/start February; annual chart 2013-2017",
    "Internet-access monthly news consumers",DN,"UK 2112",
    "Past-week Print vs Social","All final online survey respondents",
    "2017 Print 41%, Social 41%; current chart values agree with original PDF plot",
    "PDF pp.6,55; Datawrapper uECvo/7 data",inferred="Rounded parity also in 2017",timing="reviewer observation",limits="Print rise from 2016 is preserved; cause/category mapping not independently explained; no above-print claim for 2017",relevance="Preserve raw published values rather than imposing a monotonic transition")
row("E06",R02c,"UK","United Kingdom","2018 field end January/start February; chart 2013-2018",
    "Internet-access monthly news consumers",DN,"2018 country N pending; prior wave 2112",
    "Past-week Printed newspapers vs Social media","All final online survey respondents",
    "2018 Social media 39%, Printed newspapers 36%; 2016 and 2017 published chart values show parity",
    "Changing Media source chart LQmnD/3 embedded data and methodology",inferred="2017-2018 wave bracket; 2018 first strict exceedance in displayed 2013-2018 series",timing="reviewer inference from original chart",limits="No exact continuous date or significance of between-category difference established; not newspaper brands including digital editions",relevance="Early-2018 diagnostic window; retain separate newspaper and platform carriers")
row("E07",R05,"UK","United Kingdom","November/December 2018 and March 2019",
    "UK adults 16+","Weighted face-to-face plus online survey","4691 (2156 F2F,2535 online)",
    "C1 news use nowadays: social; print-only; newspaper print+web/apps","All adults 16+; multi-response reach",
    "Social 49%, print-only 38%, newspaper print+web/apps 49%",
    "PDF p.13 Figure 2.1, p.14 Figure 2.2, p.17 Figure 2.5, p.121 methods",inferred="2019 rounded parity with combined newspaper brands; already above print-only",timing="reviewer observation",limits="Caption main platforms is not single main-source choice; different base/mode from Reuters; not proof of permanent switch",relevance="Carrier and newspaper brand need separate fields")
row("E08",R06,"UK","United Kingdom","Comparable waves 2018,2019,2020,2022 W2,2023,2024",
    "UK adults 16+","F2F+online; only March/April 2022 wave included after mode interruption",
    "Figure 1 2024 N=5545; methods N=5466 (2149+3317); discrepancy unresolved",
    "C1 nowadays social vs newspaper print+online","All adults 16+; weighted multi-response reach",
    "2020 social 45%, newspapers 47%; 2022 W2 46% vs 38%; 2024 52% vs 34%",
    "PDF p.5 Figure 1; p.21 methods",inferred="2020-2022 comparable-wave inversion interval; 2022 W2 first above in displayed comparable waves",timing="reviewer inference, not exact-year continuous crossover",limits="2019 parity did not persist in 2020; 2021 telephone+online not comparable in this figure; online-newspaper question changes in 2023 and YouTube category move in 2024; internal N conflict",relevance="Treat survey mode/category changes as external context; no interpolation or imposed corpus breakpoint")
row("E09",R01,"AU","Australia","2015 field end January/start February","Internet-access monthly news consumers",DN,
    "Final survey 2042; Q4 conditional base not listed","Q4 single MAIN source: Social media vs Print",
    "Respondents who used a news source in past week; conditional weighted percentage",
    "Social 12%, Print 7%","Executive summary Main source of news by country; embedded column-chart-5",
    inferred="Social already above Print by 2015; earliest crossover not identified",timing="bounded by-year observation",limits="Main-source share is not weekly reach; no earlier Australia series verified here",relevance="Do not postpone social context until a later social-versus-web milestone")
row("E10",R07,"AU","Australia","2025 report; exact field dates pending","Australian survey population; exact eligibility/base pending full report",
    "University Digital News Report survey; release only consulted","Not verified from inaccessible PDF",
    "Single main news source: social media vs online news, with television separately",
    "Release's respondent percentages; precise questionnaire/base not independently verified",
    "University release reports social 26%, online news 23%, TV 37%, first social-over-online milestone in its series",
    "University original June 17 release, Digital News Report Australia 2025",
    reported="2025 for social versus online news; not social versus print newspapers",timing="producer-reported different-category milestone",limits="Full report methods/table inaccessible; terminology must not be expanded to newspaper brands; DataCite author indexing incomplete",relevance="Late checkpoint complements early print comparison; preserve uncertainty rather than treating as acquisition coverage evidence")
row("E11",R01,"EU_Europe_excluding_UK","Denmark","2012-2015 waves; 2015 field end January/start February",
    "Internet-access monthly news consumers",DN,"2015 final 2019",
    "Q3 past-week Print vs Social media","All final online survey respondents",
    "2013 social 31%, print 47%; estimated 2014 38% vs 39%; 2015 47% vs 33%",
    "Executive summary Sources of news Denmark; embedded line-chart-4",inferred="2014-2015 displayed-wave bracket; robust non-estimated bracket 2013-2015",timing="reviewer inference",limits=DL,relevance="Danish population evidence is not evidence about an English-language European corpus")
for eid,country,sv,pv,n in [("E12","France",5,3,1991),("E13","Italy",10,8,2006),("E14","Ireland",12,6,1501),("E15","Spain",9,8,2026)]:
    row(eid,R01,"EU_Europe_excluding_UK",country,"2015 field end January/start February",
        "Internet-access monthly news consumers",DN,f"Final sample {n}; Q4 conditional base not listed",
        "Q4 single MAIN source Social media vs Print","Past-week news-source users; conditional weighted percentage",
        f"Social {sv}%, Print {pv}%","Executive summary Main source of news by country; embedded column-chart-5",
        inferred="Already above by 2015; earliest crossover not identified",timing="bounded by-year observation",
        limits="One wave; narrow percentage differences are not significance tests; national-language sample is not English-only corpus",relevance="Country-specific background only; no pooled European switch year")
row("E16",R01,"EU_Europe_excluding_UK","Denmark; Germany; Finland","2015 field end January/start February",
    "Internet-access monthly news consumers",DN,"Final N Denmark2019,Germany1969,Finland1509; Q4 bases conditional",
    "Q4 single MAIN source Social media vs Print","Past-week news-source users",
    "Denmark 5% vs 9%; Germany 5% vs 7%; Finland 5% vs 14%",
    "Executive summary Main source of news by country; embedded column-chart-5",timing="social below Print in this wave",
    limits="Denmark weekly comparison E11 already inverted while its main-source comparison had not; no inference to later years",relevance="Demonstrates metric dependence within the same survey year")
row("E17",R03,"EU_Europe_excluding_UK","Germany","2013-2020 chart; 2020 survey January",
    "Reuters online news survey respondents","Weighted online survey; country chart January wave, not April COVID follow-up",
    "Country wave N not independently verified","Past-week Social vs Print, exact source labels",
    "Chart's final survey respondents; not all newspaper brands",
    "2018 social31%, print37%; 2019 34% vs34%; 2020 37% vs33%",
    "Country Sources of News 2013-2020 chart 94VtM/4, embedded chartData",
    inferred="2019-January2020 wave bracket; 2020 first strict exceedance in displayed series",timing="reviewer inference",
    limits="Rounded parity; historical Print values differ from 2015 report vintage; exact taxonomy/weight changes unresolved; no universal German-media switch",relevance="Retain source vintage and check comparability before any segmentation")
row("E18",R09,"EU_Europe_excluding_UK","Sweden","1986-2012 annual omnibus datasets",
    "Swedish nationally representative omnibus respondents; evening tabloid users",
    "Longitudinal repeated annual omnibus surveys","N not available in abstract",
    "Print/computer/mobile evening-tabloid news repertoires by cohort","Survey audience repertoires, not social-platform post counts",
    "Abstract describes both displacement and complementarity; 2012 mobile/cross-media use highest and print-only use lowest in series",
    "Original publisher abstract",timing="format/cohort trend, no social crossover",
    limits="Abstract only; evening tabloids are a specific genre; no verified quantitative effect sizes or social-versus-newspaper year",relevance="Historical formats coexist; newspaper acquisition should retain print and digital eras")
row("E19",S02,"EU_Europe_excluding_UK","Netherlands","Two survey waves 2002 and2005",
    "Representative Dutch adult samples","Two-wave audience survey; original abstract and study-date footnote",
    "N not verified","Newspaper and other news sites, media displacement","Audience use/evaluation, not social media",
    "Abstract reports some substitution and differentiated media repertoires",
    "Original publisher abstract and footnote8",timing="pre-social comparison, no social crossover",
    limits="Full text unavailable; no magnitudes verified; internet-news substitution cannot stand in for social-platform adoption",relevance="Useful historical comparison only")
row("E20",R08,"NZ","New Zealand","2023/2024 comparison; 2024 field April10-May13",
    "New Zealand residents15+","Mixed telephone/online survey, weighted and stratified",
    "News figure N=1404; background N=1408, unexplained difference",
    "Regular use to keep up to date: news brands and three separate social categories",
    "All respondents; multi-response, not daily reach or main source",
    "2024 Herald print/online35%; social news-media33%, friends/family29%, community24%; other NZ newspaper print/online9%",
    "PDF p.5 background and p.75 original chart; rendered page checked",timing="national newspaper/social crossover unresolved",
    limits="No union of all social categories or all newspaper brands; cannot sum overlapping categories or treat Herald as all papers; wider report's yesterday media reach is a different question",relevance="Maintain NZ gap explicitly; source availability and audience use remain separate")
row("E21",R10,"EU_Europe_excluding_UK;UK;AU;US","Italy; United Kingdom; Australia; United States",
    "Early February2015","Online panel respondents with at least monthly news use",
    "Cross-sectional comparison; propensity-score matching and regressions","8492 before matching,5765 after matching",
    "Number of online news brands used in past week by social-use type","Mean sources per respondent; pooled four-country analysis",
    "Non-users mean1.43; incidentally exposed2.30; intentional social news users3.38",
    "Accepted manuscript pp.11-16,20-22 and Table1 p.28",timing="association/complementarity, no temporal crossover",
    limits="Not random sample; self-report; cross-sectional matching is not causal identification; previews without click-through may be missed",relevance="Shared publisher/platform circulation requires linked provenance and exposure/utterance separation")
row("E22",R11,"UK","United Kingdom, The Independent brand",
    "Daily last print26 March2016; Sunday20 March2016;12 months before/after",
    "British brand readers","NRS PADD fused print survey/comScore digital audience/attention; single-brand observational case",
    "Print survey N=33225; digital panel >80000",
    "Net monthly readership and aggregate reading time","Deduplicated brand readers and total audience-minutes; different denominators",
    "Net monthly readers +7.7%; total annual attention -81% after online-only transition",
    "Original PDF pp.2-7; results figures and conclusion",reported="March2016 brand print cessation, not newspaper/social crossover",timing="documented outlet format transition",
    limits="One brand; observational before/after; recall/fused-panel/app measurement limits; circulation copies and reach do not measure attention equally",relevance="Record edition/format changes without ending the brand's digital acquisition eligibility")
row("E23",R12,"EU_Europe_excluding_UK;UK","Finland; France; Germany; Italy; Poland; United Kingdom",
    "Interviews April-May2018; Facebook algorithm change January2018",
    "Strategic sample of12 news organizations, newspapers and commercial broadcasters",
    "21 editor/manager interviews plus main-account analytics","12 organizations;21 interviews",
    "Distribution objectives: referrals, native off-site reach, subscriptions","Organization strategies and account interactions; not population reach",
    "Publishers combine on-site referrals, off-site audience reach and subscription aims",
    "Original report executive summary and methods; printed pp.6-12 (PDF pp.5-11)",timing="distribution context, no national crossover",
    limits="Strategic sample; broadcasters remain broadcasters; account interaction changes do not identify algorithm causality or total news prevalence",relevance="Carrier does not determine role; record native platform copies and linked newspaper parents")
row("E24",R12,"EU_Europe_excluding_UK","Italy: La Repubblica; France: Le Monde",
    "May11 andMay9 2018 interviews","Two selected newspaper organizations",
    "Editor/manager reported referral estimates","Two organizations",
    "Share of website traffic attributed to social referrals","Outlet web traffic, not people or article/post count",
    "La Repubblica about15% social referral traffic; Le Monde Facebook just under10% total traffic",
    "Original report printed p.11 (PDF p.10)",timing="point estimates, no crossover",
    limits="Self-reported traffic estimates; social referrals versus Facebook only differ; no pooled national inference",relevance="Keep referral metrics out of corpus count weights")
row("E25",S01,"US","United States political attention","2012",
    "Traditional/social media attention to29 political issues","Agenda-flow study; abstract consulted only",
    "29 issues; source-unit volumes unverified","Issue attention across traditional/social media",
    "Attention signals, not audience preference or newspaper-only use",
    "Abstract describes a complex interacting traditional/social attention process rather than a simple one-way agenda",
    "Original publisher abstract",timing="agenda-flow context, no audience crossover",
    limits="Full text unavailable; no detailed lag estimates/model claims verified; no causal emotional influence inferred",relevance="Later descriptive/predictive RQ1/RQ2 must validate units and avoid causal fear attribution")

def write_csv(name, records):
    assert records
    with (ROOT/name).open("w", newline="", encoding="utf-8") as output:
        writer=csv.DictWriter(output,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
write_csv("SOURCE_REGISTRY.csv",sources)
write_csv("EVIDENCE_TABLE.csv",evidence)

annual=[]
def annual_series(sid,country,metric,years,social,print_,base,note=""):
    for year,sv,pv in zip(years,social,print_):
        annual.append(dict(source_id=sid,geography=country,metric=metric,wave=str(year),social_percent=sv,
            newspaper_or_print_percent=pv,denominator=base,report_vintage=sid,comparability_note=note))
annual_series("R01","United States","Weekly Social media vs Print",range(2012,2016),[25,27,33,40],[38,41,32,23],"All final online-panel respondents","2014 estimated; do not merge report vintages")
annual_series("R01","Denmark","Weekly Social media vs Print",range(2012,2016),[23,31,38,47],[51,47,39,33],"All final online-panel respondents","2014 estimated")
annual_series("R01","United Kingdom","Weekly Social media vs Print",range(2012,2016),[18,20,23,36],[50,57,47,38],"All final online-panel respondents","2014 estimated; differs from R02 historical values")
annual_series("R02a","United Kingdom","Weekly Social vs Print",range(2013,2017),[20,28,36,35],[59,49,39,35],"All final online-panel respondents","Original 2016 vintage")
annual_series("R02b","United Kingdom","Weekly Social vs Print",range(2013,2018),[20,28,36,35,41],[59,49,39,35,41],"All final online-panel respondents","Original PDF agrees with current embedded chart; Print2017 rise preserved")
annual_series("R02c","United Kingdom","Weekly Social media vs Printed newspapers",range(2013,2019),[20,28,36,35,41,39],[59,49,39,35,41,36],"All final online-panel respondents","Exact 2018 chart category label retained")
annual_series("R03","Germany","Weekly Social vs Print",range(2013,2021),[18,22,25,31,29,31,34,37],[63,54,45,38,34,37,34,33],"Final online-panel respondents","Historical Print values differ from R01; no silent harmonisation")
annual_series("R05","United Kingdom","Nowadays Social vs newspapers print+web/apps",[2018,2019],[44,49],[51,49],"All UK adults16+ weighted mixed-mode","Not single main-source question")
annual_series("R06","United Kingdom","Nowadays Social vs newspapers print+online",[2018,2019,2020,"2022 W2",2023,2024],[44,49,45,46,47,52],[51,49,47,38,39,34],"All UK adults16+ weighted F2F+online","2021 and2022W1 omitted due mode; 2023/2024 category changes; 2024 base discrepancy")
for country,sv,pv in [("France",5,3),("Germany",5,7),("Italy",10,8),("Ireland",12,6),("United Kingdom",6,10),("Spain",9,8),("United States",11,5),("Denmark",5,9),("Australia",12,7),("Finland",5,14)]:
    annual_series("R01",country,"MAIN source Social media vs Print",[2015],[sv],[pv],"Past-week news-source users; conditional base","Not comparable to weekly reach")
write_csv("LONGITUDINAL_VALUES.csv",annual)

eras=[]
def era(rid,stratum,geo,window,eids,checks,unknown):
    eras.append(dict(recommendation_id=rid,stratum=stratum,geography=geo,external_diagnostic_window=window,
        evidence_ids=eids,recommended_structural_diagnostics=checks,unresolved_or_access_limits=unknown,
        collection_frame="Separate newspaper and social frames; full Jan1988-Sep2026 calendar; cutoff2026-09-21; source-specific applicable eras",
        interpretation="External audience/distribution context only; candidate checkpoint requires independent dated source evidence",
        safeguards="No audience-derived weights or equal-volume quotas; no topic/emotion/fear exclusion; no platform-launch-as-crossover inference; no causal lead/lag claim"))
era("D01","US","United States","2013-2015 weekly;2017-2018 often","E01;E02;E03",
    "Compare source/genre/independent-parent counts around verified windows; check archive pagination/OCR, duplicate IDs/URLs, mirrors, versions and date assignment; keep frequency/age bases distinct",
    "Survey does not certify archive completeness, public-role eligibility, historical body versions or exact monthly turning point")
era("D02","UK","United Kingdom","2016-2018 Reuters;2018-2022 Ofcom;2023-2024 questionnaire","E04;E05;E06;E07;E08",
    "Keep carrier separate from newspaper brand; preserve 2017 Print values and report vintages; check edition changes, syndicated parents, platform copies, method/category-break sensitivity",
    "2017 unusual Print rise unexplained; Ofcom2024 N discrepancy and question changes; incompatible surveys cannot be spliced")
era("D03","AU","Australia","By2015 main print comparison;2025 social-versus-web milestone","E09;E10;E21",
    "Check original newspaper titles/editions and links from editorial platform accounts; retain native article/post units and conditional main-source denominator",
    "Earliest social/print crossover and2025 report field dates/base pending; release does not prove full-calendar acquisition")
era("D04","EU_Europe_excluding_UK","Denmark;France;Italy;Ireland;Spain;Germany;Finland","Country-specific2013-2015;Germany2019-Jan2020","E11;E12;E13;E14;E15;E16;E17",
    "Audit by country, language, title/edition, genre and independent parent before pooling; preserve country-specific measures and Print vintages; investigate peaks with external dates",
    "No pan-European switch year; national-language audience surveys do not certify English-language corpus representativeness; Finland later crossover unresolved")
era("D05","EU_Europe_excluding_UK","Sweden;Netherlands","1986-2012 format/cohort context;2002/2005 website comparison","E18;E19",
    "Retain print, computer and mobile publication eras; register publication/edition genealogy and source language; distinguish format substitution from social adoption",
    "Abstract-only evidence; no verified social/newspaper crossover or effect sizes")
era("D06","NZ","New Zealand","2023-2024 observed regular-use comparison; earlier timing unresolved","E20",
    "Record Herald newspaper brand and separate social news-media/friends/community categories; keep respondents distinct from overlapping category counts; check raw survey bases before future aggregation",
    "No deduplicated social/newspaper unions; 1408 background versus1404 figure; national crossover unresolved; trust is not use")
era("D07","EU_Europe_excluding_UK;UK","Finland;France;Germany;Italy;Poland;United Kingdom","January andApril-May2018 distribution context","E23;E24",
    "Link original articles, platform native copies and syndication parents; preserve editorial/public/government author role; inspect retrieval/interface changes without treating engagement as text volume",
    "Strategic organization sample; referral percentages are traffic metrics; broadcaster outlets remain broadcasters")
era("D08","UK","The Independent","March2016 print cessation","E22",
    "Record last daily/Sunday print separately and continued online brand; inspect parent/version/date mappings and format-specific coverage rather than stop at print cessation",
    "One-brand transition; monthly reach, reading time and article counts cannot be converted into one another")
era("D09","ALL","All five strata","Source-specific historical eras; no universal breakpoint","E01-E25",
    "Register verified source existence, interface availability, recoverable era, dated original text and limitations; report 465-month calendar alongside applicable-period denominators; classify pre-existence as structurally inapplicable and access gaps as unknown",
    "This background package acquires no corpus and authorizes no downstream collection; later topic/affect/fear measurement remains a separate validated stage")
write_csv("SOURCE_ERA_RECOMMENDATIONS.csv",eras)

bib = r'''@article{WestlundFardigh2015,
  author = {Westlund, Oscar and Färdigh, Mathias A.},
  title = {Accessing the news in an age of mobile media: Tracing displacing and complementary effects of mobile news on newspapers and online news},
  journal = {Mobile Media & Communication}, year = {2015}, volume = {3}, number = {1}, pages = {53--74},
  doi = {10.1177/2050157914549039}, url = {https://doi.org/10.1177/2050157914549039},
  note = {Online publication 2014-12-29; abstract consulted, full text not read}
}
@article{FletcherNielsen2018,
  author = {Fletcher, Richard and Nielsen, Rasmus Kleis},
  title = {Are people incidentally exposed to news on social media? A comparative analysis},
  journal = {New Media & Society}, year = {2018}, volume = {20}, number = {7}, pages = {2450--2468},
  doi = {10.1177/1461444817724170}, url = {https://doi.org/10.1177/1461444817724170},
  note = {Online publication 2017-08-17; Oxford author accepted manuscript consulted}
}
@article{ThurmanFletcher2018,
  author = {Thurman, Neil and Fletcher, Richard},
  title = {Are Newspapers Heading Toward Post-Print Obscurity? A Case Study of {The Independent}'s Transition to Online-only},
  journal = {Digital Journalism}, year = {2018}, volume = {6}, number = {8}, pages = {1003--1017},
  doi = {10.1080/21670811.2018.1504625}, url = {https://doi.org/10.1080/21670811.2018.1504625},
  note = {Subtitle verified in original PDF; Crossref indexes short title; university full text consulted}
}
@article{NeumanEtAl2014,
  author = {Neuman, W. Russell and Guggenheim, Lauren and Jang, S. Mo and Bae, Soo Young},
  title = {The Dynamics of Public Attention: Agenda-Setting Theory Meets Big Data},
  journal = {Journal of Communication}, year = {2014}, volume = {64}, number = {2}, pages = {193--214},
  doi = {10.1111/jcom.12088}, url = {https://doi.org/10.1111/jcom.12088},
  note = {Supplementary; original abstract only; full text not read}
}
@article{DeWaalSchoenbach2010,
  author = {de Waal, Ester and Schoenbach, Klaus},
  title = {News sites' position in the mediascape: Uses, evaluations and media displacement effects over time},
  journal = {New Media & Society}, year = {2010}, volume = {12}, number = {3}, pages = {477--496},
  doi = {10.1177/1461444809341859}, url = {https://doi.org/10.1177/1461444809341859},
  note = {Supplementary; original abstract and study-date footnote consulted; full text not read}
}
'''
(ROOT/"references.bib").write_text(bib,encoding="utf-8")
print(json.dumps(dict(source_entries=len(sources),core_families=12,evidence_rows=len(evidence),annual_values=len(annual),era_recommendations=len(eras),journal_references=5)))
