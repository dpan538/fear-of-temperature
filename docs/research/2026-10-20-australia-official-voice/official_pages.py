"""Public official indexes and releases; originals exist only in request memory.

Index membership, publication dates and reference/event periods are distinct.
No count target controls traversal. HTTP403 is pending, never a last page.
"""

import io
import json
import re
import urllib.error
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

import pdfplumber
from bs4 import BeautifulSoup

core = None
ENGLISH_DATE = re.compile(
    r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b",
    re.I,
)


def english_date(text):
    hit = ENGLISH_DATE.search(text or "")
    return datetime.strptime(hit.group(), "%d %B %Y").date().isoformat() if hit else None


def visible(soup):
    for element in soup.select("script,style,nav,header,footer,form"):
        element.decompose()
    return soup.get_text(" ", strip=True)


def page_content(body):
    if body.startswith(b"%PDF"):
        with pdfplumber.open(io.BytesIO(body)) as doc:
            return "\n".join(page.extract_text() or "" for page in doc.pages), "pdf_extracted_text"
    soup = BeautifulSoup(body, "html.parser")
    main = soup.select_one("#content, #main-content, #qg-primary-content, main, article") or soup
    return visible(main), "html_visible_text"


def pending(store, job, source, exc):
    # A real missing target is recorded; denied/failed access remains incomplete.
    state = (
        "exhausted"
        if isinstance(exc, urllib.error.HTTPError) and exc.code == 404
        else "blocked_or_paused"
    )
    store.job(job, source, state, detail=f"{type(exc).__name__}: {exc}")
    return state == "exhausted"


def collect_bom_scs(store, client):
    source = "bom_scs"
    root_url = "https://www.bom.gov.au/climate/current/statements/"
    root_body = client.get(root_url)
    root = BeautifulSoup(root_body, "html.parser")
    indexes = sorted(
        {
            urllib.parse.urljoin(root_url, a["href"])
            for a in root.select("a[href]")
            if re.search(r"/statements/(national|nsw|vic|qld|wa|sa|tas|nt)\.html$", a["href"])
        }
    )
    if len(indexes) != 8:
        raise RuntimeError("SCS regional index contract changed; incomplete")
    store.page("bom_scs:root", source, "index", root_url, root_body, len(indexes), 0, None)
    store.job("bom_scs:root", source, "exhausted")
    documents = {}
    complete = True
    for url in indexes:
        try:
            body = client.get(url)
            soup = BeautifulSoup(body, "html.parser")
            links = soup.select("a[href]")
            for a in links:
                # An official regional index contains whitespace inside 'statements'.
                # Remove HTML link whitespace; retain the raw href in metadata.
                path = urllib.parse.urlparse(re.sub(r"\s+", "", a["href"])).path
                match = re.search(r"/(scs(\d+)[a-z]*)\.pdf$", path, re.I)
                if not match:
                    continue  # Supplements are related attachments, not new statements.
                doc_url = urllib.parse.urljoin(url, path)
                context = a.parent.get_text(" ", strip=True)
                documents.setdefault(
                    doc_url,
                    {
                        "native": "scs" + match[2],
                        "title": a.get_text(" ", strip=True),
                        "date": english_date(context),
                        "index": url,
                        "index_dates": re.findall(ENGLISH_DATE, context),
                        "raw_index_href": a["href"],
                    },
                )
            store.page(
                "bom_scs:index:" + core.digest(url), source, "index", url, body, len(links), 0, None
            )
            store.job("bom_scs:index:" + core.digest(url), source, "exhausted")
        except Exception as exc:
            complete = pending(store, "bom_scs:index:" + core.digest(url), source, exc) and complete
    master_titles = {}
    for info in documents.values():
        if not re.match(r"(?:Issued|Updated)\b", info["title"], re.I):
            master_titles.setdefault(info["native"], info["title"])
    for url, info in documents.items():
        job = "bom_scs:document:" + core.digest(url)
        if (old := store.cursor(job)) and old["state"] == "exhausted":
            continue
        text, body, kind = "", b"", "title_only"
        try:
            body = client.get(url)
            text, kind = page_content(body)
        except Exception as exc:
            complete = pending(store, job, source, exc) and complete
        dates = [
            r[0]
            for r in store.db.execute(
                "SELECT publication_date FROM source_documents WHERE "
                "source_channel=? AND native_id=?",
                (source, info["native"]),
            )
            if r[0]
        ]
        date_value = min([info["date"], *dates]) if info["date"] else (dates[0] if dates else None)
        saved = store.save(
            source,
            info["native"],
            master_titles.get(info["native"], info["title"]),
            text,
            date_value,
            url,
            tier="agency_bom",
            unit="official_statement_document",
            speaker="Bureau of Meteorology",
            role="agency_official_publication",
            basis="first issued date on official SCS index; update dates retained separately",
            excerpt_kind=kind,
            version=core.digest(body) if body else "index_only",
            extra={
                "index_url": info["index"],
                "index_dates": info["index_dates"],
                "document_response_hash": core.digest(body) if body else None,
            },
        )
        if body:
            store.page(job, source, "document", url, body, 1, saved, None)
            store.job(job, source, "exhausted")
        else:
            store.db.commit()
    store.job(
        "bom_scs:all_index_documents",
        source,
        "exhausted" if complete else "blocked_or_paused",
        detail=f"discovered unique document URLs={len(documents)}; native SCS "
        f"number merges revisions; supplements excluded",
    )
    return None if complete else "blocked_or_paused"


def bom_date(soup):
    stamp = soup.select_one("time[datetime], #pDateStamp")
    if stamp:
        raw = stamp.get("datetime") or stamp.get_text(" ", strip=True)
        if re.match(r"\d{4}-\d{2}-\d{2}", raw):
            return raw[:10]
        if value := english_date(raw):
            return value
    # Publication headers only; arbitrary table .date cells contain event/record dates.
    for node in soup.select("p.date, p.dateline"):
        if value := english_date(node.get_text(" ", strip=True)):
            return value
    # Older summaries have a dated heading, never infer release from report year.
    for node in soup.select("h1,h2,h3,.product,.dateStamp"):
        text = node.get_text(" ", strip=True)
        if re.search(r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)", text) and (
            value := english_date(text)
        ):
            return value
    return None


def collect_bom_annual(store, client):
    source = "bom_annual"
    base = "https://www.bom.gov.au"
    index = base + "/climate/current/annual-aus-list.html"
    body = client.get(index)
    soup = BeautifulSoup(body, "html.parser")
    targets = {}
    for a in soup.select("a[href]"):
        if hit := re.search(r"\b(19\d{2}|20\d{2})\b", a.get_text()):
            targets["aus:" + hit[1]] = urllib.parse.urljoin(index, a["href"])
    script_url = base + "/climate/current/scripts/summary-archive.js?20220207"
    script = client.get(script_url)
    if b"function buildYearLinks" not in script or b"startYear = 2006" not in script:
        raise RuntimeError("BoM archive generation contract changed")
    # These finite paths are generated by the public index's own year/region controls.
    for year in range(2002, 2026):
        targets.setdefault(f"aus:{year}", f"{base}/climate/current/annual/aus/{year}/")
    regions = ["act", "nsw", "nt", "qld", "sa", "tas", "wa", "vic", "tropics", "ria"]
    cities = {"nsw": "sydney", "vic": "melbourne", "sa": "adelaide", "tas": "hobart", "wa": "perth"}
    for region in regions:
        for year in range(2017 if region == "ria" else 2006, 2026):
            targets[f"{region}:{year}"] = (
                f"{base}/climate/current/annual/{region}/archive/{year}.summary.shtml"
            )
            if region in cities and year >= (
                2017 if region == "sa" else 2010 if region in {"vic", "tas"} else 2006
            ):
                targets[f"{cities[region]}:{year}"] = (
                    f"{base}/climate/current/annual/{region}/archive/{year}.{cities[region]}.shtml"
                )
    store.page(
        "bom_annual:index", source, "legacy_list", index, body, len(soup.select("a[href]")), 0, None
    )
    store.page(
        "bom_annual:index",
        source,
        "public_index_generator",
        script_url,
        script,
        len(targets),
        0,
        None,
    )
    store.job("bom_annual:index", source, "exhausted")
    complete = True
    for native, url in targets.items():
        job = "bom_annual:document:" + native
        if (old := store.cursor(job)) and old["state"] == "exhausted":
            continue
        try:
            body = client.get(url)
            soup = BeautifulSoup(body, "html.parser")
            pub = bom_date(soup)
            title = soup.select_one("h1") or soup.title
            title = title.get_text(" ", strip=True) if title else native
            text, kind = page_content(body)
            saved = store.save(
                source,
                native,
                title,
                text,
                pub,
                url,
                tier="agency_bom",
                unit="annual_climate_summary_document",
                speaker="Bureau of Meteorology",
                role="agency_official_publication",
                basis="dated publication heading/time on annual summary; report "
                "reference year is separate",
                excerpt_kind=kind,
                version=core.digest(body),
                extra={
                    "reference_region_year": native,
                    "index_url": index,
                    "archive_generator": script_url,
                },
            )
            store.page(job, source, "document", url, body, 1, saved, None)
            store.job(job, source, "exhausted")
        except Exception as exc:
            complete = pending(store, job, source, exc) and complete
    store.job(
        "bom_annual:all_index_documents",
        source,
        "exhausted" if complete else "blocked_or_paused",
        detail=f"all {len(targets)} public-index targets attempted;404 "
        f"missing,403 pending; no pre-1996 index claim",
    )
    return None if complete else "blocked_or_paused"


def qld_next(soup, current_url):
    current = int(
        urllib.parse.parse_qs(urllib.parse.urlparse(current_url).query).get("pageIndex", ["1"])[0]
    )
    candidates = []
    for a in soup.select("a[href]"):
        url = urllib.parse.urljoin(current_url, a["href"])
        page = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("pageIndex")
        if page and int(page[0]) > current:
            candidates.append((int(page[0]), url))
    return min(candidates)[1] if candidates else None


def collect_qld_statements(store, client):
    source, base = "qld_statements", "https://statements.qld.gov.au/"
    body = client.get(base + "?Search=True")
    soup = BeautifulSoup(body, "html.parser")
    terms = sorted(core.EXTENDED_TERMS)
    governments = [x["value"] for x in soup.select("select[name=t] option[value]")]
    if not governments:
        raise RuntimeError(
            "Government-term selector missing; do not silently use default current term"
        )
    store.page(
        "qld_statements:scope",
        source,
        "government_terms",
        base + "?Search=True",
        body,
        len(governments),
        0,
        None,
    )
    store.job("qld_statements:scope", source, "exhausted")
    for government in governments:
        for term in terms:
            job = f"qld_statements:t{government}:{term}"
            old = store.cursor(job)
            if old and old["state"] == "exhausted":
                continue
            cursor = json.loads(old["cursor"]) if old else None
            url = cursor or base + "?" + urllib.parse.urlencode(
                {
                    "Search": "True",
                    "Text": '"' + term + '"',
                    "FromDate": "01/01/1988",
                    "ToDate": "21/09/2026",
                    "t": government,
                }
            )
            seen = set()
            while url:
                if url in seen or urllib.parse.urlparse(url).hostname != "statements.qld.gov.au":
                    raise RuntimeError("Repeated/off-host official-release page; incomplete")
                seen.add(url)
                body = client.get(url)
                soup = BeautifulSoup(body, "html.parser")
                if not soup.select_one("select[name=t]"):
                    raise RuntimeError("Search response contract changed")
                cards = soup.select(".card-body")
                docs = [
                    (a, card) for card in cards if (a := card.select_one('a[href^="/statements/"]'))
                ]
                next_url = qld_next(soup, url)
                if not docs and next_url:
                    raise RuntimeError("Empty search page with next link")
                saved = 0
                for a, _card in docs:
                    doc_url = urllib.parse.urljoin(base, a["href"])
                    native = a["href"].rstrip("/").rsplit("/", 1)[-1]
                    prior = store.db.execute(
                        "SELECT * FROM source_documents WHERE source_channel=? AND native_id=?",
                        (source, native),
                    ).fetchone()
                    doc_job = "qld_statements:document:" + native
                    # Reuse saved records, with all locally observed phrases already retained.
                    if prior and (done := store.cursor(doc_job)) and done["state"] == "exhausted":
                        continue
                    raw = client.get(doc_url)
                    doc = BeautifulSoup(raw, "html.parser")
                    metadata = doc.select_one('script[type="application/ld+json"]')
                    if not metadata:
                        raise RuntimeError("Release lacks expected NewsArticle metadata")
                    item = json.loads(metadata.string or metadata.get_text())
                    if item.get("@type") != "NewsArticle":
                        raise RuntimeError("Unexpected release type")
                    # Publication day in Queensland, never UTC truncation near midnight.
                    stamp = datetime.fromisoformat(item["datePublished"].replace("Z", "+00:00"))
                    published = stamp.astimezone(ZoneInfo("Australia/Brisbane")).date().isoformat()
                    text = core.words(item.get("articleBody", ""))
                    saved += store.save(
                        source,
                        native,
                        item.get("headline") or a.get_text(" ", strip=True),
                        text,
                        published,
                        doc_url,
                        tier="state_qld",
                        unit="ministerial_media_statement",
                        speaker=(item.get("author") or {}).get("name"),
                        role="state_executive_official_release",
                        basis="NewsArticle.datePublished converted to Australia/Brisbane; "
                        "dateModified separate",
                        excerpt_kind="official_release_text",
                        version=item.get("dateModified", "live"),
                        extra={
                            "government_term": government,
                            "datePublished": item["datePublished"],
                            "dateModified": item.get("dateModified"),
                            "discovery_query": term,
                        },
                    )
                    store.page(doc_job, source, "document", doc_url, raw, 1, saved, None)
                    store.job(doc_job, source, "exhausted")
                key = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get(
                    "pageIndex", ["1"]
                )[0]
                store.page(job, source, key, url, body, len(docs), saved, next_url)
                store.job(
                    job,
                    source,
                    "running" if next_url else "exhausted",
                    next_url,
                    "all government terms; fixed FromDate/ToDate plus local "
                    "publication check; next-link traversal",
                )
                url = next_url


def collect_qld_resources(store, client):
    source = "qld_resources"
    records = list(
        store.db.execute(
            "SELECT doc_id,native_id,source_context_json FROM "
            "source_documents WHERE source_channel='qld_opendata'"
        )
    )
    complete = True
    seen = set()
    for record in records:
        for resource in json.loads(record["source_context_json"]).get("resources", []):
            url = resource.get("url") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            job = "qld_resources:" + core.digest(url)
            if (old := store.cursor(job)) and old["state"] == "exhausted":
                continue
            # Numerical/spatial data rows are not publication/utterance nodes.
            if resource.get("format", "").upper() not in {"PDF", "HTML", "HTM"}:
                store.job(
                    job,
                    source,
                    "exhausted",
                    detail="resource classified: structured/spatial data, not historical "
                    "notice; no row-to-speech inflation",
                )
                continue
            host = urllib.parse.urlparse(url).hostname or ""
            if not (host.endswith(".qld.gov.au") or host == "qld.gov.au"):
                store.job(
                    job,
                    source,
                    "pending_publisher",
                    detail="not verified Queensland official publisher",
                )
                complete = False
                continue
            try:
                body = client.get(url)
                text, kind = page_content(body)
                soup = BeautifulSoup(body, "html.parser") if not body.startswith(b"%PDF") else None
                pub = bom_date(soup) if soup else None
                saved = store.save(
                    source,
                    url,
                    resource.get("name"),
                    text,
                    pub,
                    url,
                    tier="state_qld",
                    unit="official_linked_resource_document",
                    speaker="Queensland government; specific holder pending",
                    role="linked_official_resource",
                    parent=record["native_id"],
                    basis="explicit published/time field only; data years/file "
                    "URL/catalogue timestamps not substituted",
                    excerpt_kind=kind,
                    version=core.digest(body),
                    extra={"catalogue_doc_id": record["doc_id"], "resource_id": resource.get("id")},
                )
                store.page(job, source, "resource", url, body, 1, saved, None)
                store.job(job, source, "exhausted")
            except Exception as exc:
                complete = pending(store, job, source, exc) and complete
    store.job(
        "qld_resources:all_saved_catalogue_resources",
        source,
        "exhausted" if complete else "blocked_or_paused",
        detail=f"classified/attempted all {len(seen)} unique saved catalogue "
        f"resources; does not establish a historical-warning archive",
    )
    return None if complete else "blocked_or_paused"


def collect_trove_web(store, client):
    manifest = json.loads((store.output / "trove_web_discovery.json").read_text())
    source = "trove_web_gazette"
    if manifest["interval"] != [core.START, core.END]:
        raise RuntimeError("Trove discovery interval mismatch")
    terms = manifest["terms"]
    if set(terms) != core.EXTENDED_TERMS:
        raise RuntimeError("Trove discovery matrix mismatch")
    ids = {}
    query_pages = {}
    for term_index, offset, total, native_ids, next_offset in manifest["pages"]:
        term = terms[term_index]
        query_pages.setdefault(term, []).append((offset, total, native_ids, next_offset))
        for native in native_ids:
            ids.setdefault(str(native), set()).add(term)
        url = (
            "https://trove.nla.gov.au/search/advanced/category/newspapers?"
            + urllib.parse.urlencode(
                {
                    "keyword.phrase": term,
                    "date.from": core.START,
                    "date.to": core.END,
                    "l-artType": "gazette",
                    **({"startPos": offset} if offset else {}),
                }
            )
        )
        payload = json.dumps([offset, total, native_ids, next_offset]).encode()
        store.page(
            "trove_web:query:" + term, source, offset, url, payload, len(native_ids), 0, next_offset
        )
    completed = set(manifest["completed_terms"])
    for term, pages in query_pages.items():
        pages.sort()
        if term in completed:
            if pages[0][0] != 0 or pages[-1][3] is not None:
                raise RuntimeError("Trove terminal/start page missing")
            if any(a[3] != b[0] for a, b in zip(pages, pages[1:], strict=False)):
                raise RuntimeError("Trove next-page chain broken")
            if sum(len(p[2]) for p in pages) != pages[0][1]:
                raise RuntimeError("Trove advertised total/page count mismatch")
        store.job(
            "trove_web:query:" + term,
            source,
            "exhausted" if term in completed else "running",
            pages[-1][3],
            (
                "public browser DOM; Gazette and fixed dates visibly "
                "verified; page hash is compact DOM IDs, not original HTML"
            ),
        )
    complete = completed == core.EXTENDED_TERMS
    for check in manifest.get("rechecks", []):
        term = check["term"]
        pages = check["pages"]
        if term not in core.EXTENDED_TERMS or not pages or pages[-1][3] is not None:
            raise RuntimeError("Trove independent recheck incomplete")
        if any(a[3] != b[0] for a, b in zip(pages, pages[1:], strict=False)):
            raise RuntimeError("Trove recheck page chain broken")
        for offset, total, native_ids, next_offset in pages:
            for native in native_ids:
                ids.setdefault(str(native), set()).add(term)
            url = (
                "https://trove.nla.gov.au/search/advanced/category/newspapers?"
                + urllib.parse.urlencode(
                    {
                        "keyword.phrase": term,
                        "date.from": core.START,
                        "date.to": core.END,
                        "l-artType": "gazette",
                        "sortBy": check["sortBy"],
                        "startPos": offset,
                    }
                )
            )
            job = "trove_web:recheck:" + term + ":" + check["sortBy"]
            store.page(
                job,
                source,
                offset,
                url,
                core.encode([total, native_ids, next_offset]).encode(),
                len(native_ids),
                0,
                next_offset,
            )
        store.job(
            job,
            source,
            "exhausted",
            detail=(
                "independent public date-sort traversal; overlap deduplicated by native article ID"
            ),
        )
    for native, matched_terms in ids.items():
        job = "trove_web:document:" + native
        prior = store.db.execute(
            "SELECT * FROM source_documents WHERE source_channel=? AND native_id=?",
            (source, native),
        ).fetchone()
        if prior and (old := store.cursor(job)) and old["state"] == "exhausted":
            terms_union = sorted(set(json.loads(prior["query_matched"])) | matched_terms)
            store.db.execute(
                "UPDATE source_documents SET query_matched=?,query_dimensions=? WHERE doc_id=?",
                (
                    core.encode(terms_union),
                    core.encode(
                        sorted(
                            d
                            for d, ts in core.COLLECTION_MATRIX["dimensions"].items()
                            if set(ts) & set(terms_union)
                        )
                    ),
                    prior["doc_id"],
                ),
            )
            store.db.commit()
            continue
        url = "https://trove.nla.gov.au/newspaper/article/" + native
        # A visible search card is sufficient for this metadata-only inventory.
        # Preserve article-access failure; never imply that OCR was inspected.
        if card := manifest.get("public_card_fallback", {}).get(native):
            published = datetime.strptime(card["date"], "%A %d %B %Y").date().isoformat()
            payload = core.encode(card).encode()
            saved = store.save(
                source,
                native,
                card["title"],
                card.get("excerpt", ""),
                published,
                url,
                tier="government_gazette",
                unit="gazette_article",
                speaker=card["publisher"],
                role="gazette_reproduction_holder_unresolved",
                basis="publication date visibly rendered on public Trove Gazette result card",
                excerpt_kind="public_search_card_snippet",
                provider_terms=sorted(matched_terms),
                persistent_id="nla.news-article" + native,
                version=core.digest(payload),
                extra={
                    "gazette_title": card["publisher"],
                    "article_access": "timeout; metadata obtained from public search card",
                    "provenance": "National Library archival reproduction; holder unresolved",
                    "discovery_manifest_version": manifest["version"],
                },
            )
            store.page(job, source, "public_card_metadata", url, payload, 1, saved, None)
            store.job(job, source, "exhausted", detail="Public card metadata; OCR not inspected")
            continue
        try:
            body = client.get(url)
            soup = BeautifulSoup(body, "html.parser")
            meta = soup.select_one('meta[property="og:title"]')
            if not meta:
                raise RuntimeError("Trove public article metadata missing")
            fields = re.fullmatch(
                r"(.*) - ([^-]*?Gazette.*?) - (\d{1,2} [A-Za-z]{3} \d{4})",
                meta["content"],
                re.I | re.S,
            )
            if not fields:
                raise RuntimeError("Expected Gazette title/date mapping not observed")
            title, publisher, raw_date = fields.groups()
            published = datetime.strptime(raw_date.strip(), "%d %b %Y").date().isoformat()
            ocr = "\n".join(
                n.get_text(" ", strip=True) for n in soup.select("#fulltextContents .line .read")
            )
            saved = store.save(
                source,
                native,
                title,
                ocr,
                published,
                url,
                tier="government_gazette",
                unit="gazette_article",
                speaker=publisher,
                role="gazette_reproduction_holder_unresolved",
                basis=(
                    "Trove rendered article og:title date; Gazette public "
                    "search date constraints separately verified"
                ),
                excerpt_kind="public_gazette_ocr",
                provider_terms=sorted(matched_terms),
                persistent_id="nla.news-article" + native,
                version=core.digest(body),
                extra={
                    "gazette_title": publisher,
                    "provenance": (
                        "National Library archival reproduction; notice "
                        "author/holder not inferred from gazette membership"
                    ),
                    "discovery_manifest_version": manifest["version"],
                },
            )
            store.page(job, source, "document", url, body, 1, saved, None)
            store.job(job, source, "exhausted")
        except Exception as exc:
            complete = pending(store, job, source, exc) and complete
    store.job(
        "trove_web:all_discovery_documents",
        source,
        "exhausted" if complete else "running_discovery_or_pending",
        detail=(
            f"{len(completed)}/33 queries terminal; {len(ids)} unique "
            f"article IDs; public web fallback, not an RSS/API claim"
        ),
    )
    return None if complete else "running_discovery_or_pending"


COLLECTORS = {
    "bom_scs": collect_bom_scs,
    "bom_annual": collect_bom_annual,
    "qld_statements": collect_qld_statements,
    "qld_resources": collect_qld_resources,
    "trove_web_gazette": collect_trove_web,
}
