"""Documented public mailing archives and HN native records; no inferred dates."""
import datetime as dt
import email.policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
import html
import re
import urllib.parse

import entities as e
import transport as t

def safe_metadata(value):
    """Raw bytes stay in source objects; derived metadata must be valid UTF-8."""
    value=str(value)
    return value.encode("utf8", "surrogateescape").decode("utf8", "replace")


def dated(value):
    try:
        value = re.sub(r"\bGMT([+-]\d{4})\b", r"\1", value)
        stamp = parsedate_to_datetime(value)
        if stamp.tzinfo is None:
            return None
        return stamp.astimezone(dt.timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError):
        return None


def mbox_records(raw, sid, url):
    chunks = re.split(br"(?m)^From [^\n]*\n", raw)
    if chunks[0].strip():
        raise t.Stop("native_mbox_separator_not_observed")
    rows = []
    for ordinal, chunk in enumerate(chunks[1:]):
        msg = BytesParser(policy=email.policy.default).parsebytes(chunk)
        message_id = str(msg.get("Message-ID", "")).strip()
        body_parts = []
        native_parts = []; encoding_limits=[]
        for part in msg.walk():
            if part.is_multipart():
                continue
            typ = part.get_content_type()
            native_parts.append({"mime_type": typ, "charset": part.get_content_charset(),
                "attachment_name": part.get_filename(), "content_disposition": part.get_content_disposition()})
            if typ == "text/plain" and part.get_content_disposition() != "attachment":
                payload = part.get_payload(decode=True) or b""
                try:decoded=payload.decode(part.get_content_charset() or "utf8", "replace")
                except LookupError:
                    decoded=payload.decode("utf8", "replace");encoding_limits.append({"declared_charset":part.get_content_charset(),"fallback":"utf8_with_replacement; original_bytes_retained"})
                body_parts.append(decoded)
        body = "\n".join(body_parts)
        notice = re.fullmatch(r"\s*-{14} next part -{14}\s*An HTML attachment was scrubbed[^\n]*\nURL:\s*<([^>]+)>\s*", body)
        attachment_url = notice.group(1) if notice else None
        refs = re.findall(r"<[^>]+>", str(msg.get("References", "")))
        parent = str(msg.get("In-Reply-To", "")).strip()
        native_id = message_id or url + "#member=" + str(ordinal)
        ns = "message_id" if message_id else "archive_member"
        edges = []
        if parent:
            edges.append(e.edge("reply", parent, "message_id"))
        if refs:
            edges.append(e.edge("root", refs[0], "message_id"))
        rows.append(dict(source_id=sid, native_namespace=ns, native_post_id=native_id,
            source_url=url, native_unit="mailing_list_message", native_created_at=dated(str(msg.get("Date", ""))),
            native_edited_at=None, body_original=body, body_format="plain", content_state="archive_generated_attachment_notice" if notice else None, author_id=str(msg.get("From", "")) or None,
            author_role="unknown", thread_id=refs[0] if refs else message_id or "unresolved",
            reply_to_post_id=parent or None, parent_namespace="message_id", edges=edges,
            content_license="no_open_content_grant_verified",
            license_basis="public source-provided downloadable archive; local research snapshot; author ownership and redistribution unresolved",
            native_fields={"mail_headers": [(safe_metadata(k),safe_metadata(v)) for k,v in msg.raw_items()], "archive_member_ordinal": ordinal,
                "archive_url": url, "mime_parts": native_parts, "source_scrubbed_attachment_url": attachment_url},
            attachments=[{"type":"source_archive_scrubbed_HTML_attachment","url":attachment_url,"original_authored_body_mapping":"unrecovered; source notice retained"}] if notice else [],
            flags={"archival_reproduction_of_original_public_message": True,
                "date_is_source_Date_header_not_archive_folder_or_retrieval": True,
                "later_archive_snapshot_does_not_prove_historical_bytes": True,
                "missing_native_message_id": not bool(message_id),
                "native_metadata_invalid_utf8_replaced_in_derived_fields": any(safe_metadata(v)!=v for k,v in msg.raw_items()),
                "body_encoding_limitations": encoding_limits,
                "source_archive_generated_notice_only": bool(notice),
                "authored_attachment_body_not_established": bool(notice)}))
    return rows


def hn_records(data, sid="hackernews", requested_id=None):
    if data is None:
        return [dict(source_id=sid, native_namespace="item", native_post_id=str(requested_id),
            source_url="https://news.ycombinator.com/item?id=" + str(requested_id),
            native_unit="unavailable_native_item", native_created_at=None, body_original="",
            content_state="native_null_item", flags={"no_content_or_time_invented": True}, native_fields={"native_response": None})]
    nid = data["id"]
    stamp = dt.datetime.fromtimestamp(data["time"], dt.timezone.utc).isoformat() if data.get("time") else None
    body = data.get("text", "")
    state = "tombstone" if data.get("deleted") else "complete_native_text" if body else "title_or_link_only_native_submission"
    edges = [e.edge("reply", data["parent"], "item")] if data.get("parent") else []
    edges += [e.edge("native_child", child, "item") for child in data.get("kids", [])]
    if data.get("url"):
        edges.append(e.edge("link", None, url=data["url"]))
    return [dict(source_id=sid, native_namespace="item", native_post_id=str(nid),
        source_url="https://news.ycombinator.com/item?id=" + str(nid), native_unit="tombstone" if data.get("deleted") else data.get("type", "unresolved_native_item"),
        native_created_at=stamp, native_edited_at=None, body_original=body, content_state=state,
        author_id=data.get("by"), author_role="unknown", thread_id="unresolved" if data.get("parent") else str(nid),
        reply_to_post_id=str(data["parent"]) if data.get("parent") else None, parent_namespace="item",
        content_license="no_open_content_grant_verified",
        license_basis="official API expressly exposes public native records; local research snapshot; no post redistribution grant asserted",
        native_fields={k: v for k, v in data.items() if k != "text"}, edges=edges,
        flags={"native_dead": data.get("dead"), "native_deleted": data.get("deleted"),
            "linked_external_article_not_acquired": bool(data.get("url")), "title_not_promoted_to_authored_body": True})]


def html_links(raw, base):
    text = raw.decode("utf8", "replace")
    return list(dict.fromkeys(urllib.parse.urljoin(base, html.unescape(x))
        for x in re.findall(r'href=[\"\']([^\"\']+)[\"\']', text, flags=re.I)))


def w3_records(raw, url, sid="w3_wwwtalk"):
    text = raw.decode("utf8", "replace")
    headers = {k: html.unescape(v).strip() for k, v in re.findall(
        r'<!--\s*(received|sent|name|email|subject|id|inreplyto)="(.*?)"\s*-->', text, flags=re.S)}
    match = re.search(r'<!--\s*body="start"\s*-->(.*?)<!--\s*body="end"\s*-->', text, flags=re.S)
    if not match:
        raise t.Stop("native_archive_body_boundary_not_observed")
    original = match.group(1).strip()
    rendered = t.clean(original)
    # Early Hypermail pages repeat the RFC message headers in the preserved pre.
    # Retain that exact native representation and keep headers as sidecar facts.
    native_id = headers.get("id") or url
    ns = "message_id" if headers.get("id") else "archive_message_url"
    parent = headers.get("inreplyto")
    return [dict(source_id=sid, native_namespace=ns, native_post_id=native_id,
        source_url=url, native_unit="mailing_list_message", native_created_at=dated(headers.get("sent", "")),
        native_edited_at=None, body_original=original, body_format="html",
        author_id=headers.get("name") or None, author_role="unknown", thread_id="unresolved",
        reply_to_post_id=parent or None, parent_namespace="message_id",
        edges=[e.edge("reply", parent, "message_id")] if parent else [],
        content_license="no_open_content_grant_verified",
        license_basis="documented public mailing archive with source archive consent policy; local research snapshot; author rights and redistribution unresolved",
        native_fields={"archive_headers": headers, "archive_url": url},
        flags={"archival_reproduction_of_original_public_message": True,
            "source_sent_and_received_times_separate": True,
            "source_reception_at": headers.get("received"),
            "native_sent_header": headers.get("sent"),
            "later_archive_snapshot_does_not_prove_historical_bytes": True,
            "early_archive_body_may_repeat_RFC_headers": bool(re.match(r"^Date:", rendered))})]
