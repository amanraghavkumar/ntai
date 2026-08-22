"""RSS / Atom parser for live feeds."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_text(value: str | None, limit: int | None = None) -> str:
    if not value:
        return ""
    text = unescape(TAG_RE.sub(" ", value))
    text = SPACE_RE.sub(" ", text).strip()
    if limit:
        return text[:limit]
    return text


def parse_rss(xml_text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if not xml_text or "<" not in xml_text:
        return items
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    nodes = root.findall(".//item")
    if nodes:
        for node in nodes:
            title = clean_text(node.findtext("title"))
            link = clean_text(node.findtext("link"))
            if not link:
                guid = node.find("guid")
                if guid is not None and (guid.text or "").startswith("http"):
                    link = clean_text(guid.text)
            summary = clean_text(node.findtext("description") or node.findtext("summary"), 420)
            published = clean_text(node.findtext("pubDate") or node.findtext("updated")) or utc_now()
            source = clean_text(node.findtext("source"))
            if title:
                items.append(
                    {
                        "headline": title,
                        "summary": summary,
                        "source_url": link,
                        "published": published,
                        "publisher": source,
                    }
                )
        return items

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", ns):
        title = clean_text(entry.findtext("atom:title", default="", namespaces=ns))
        link_el = entry.find("atom:link", ns)
        link = link_el.get("href", "") if link_el is not None else ""
        summary = clean_text(
            entry.findtext("atom:summary", default="", namespaces=ns)
            or entry.findtext("atom:content", default="", namespaces=ns),
            420,
        )
        published = entry.findtext("atom:updated", default="", namespaces=ns) or utc_now()
        if title:
            items.append(
                {
                    "headline": title,
                    "summary": summary,
                    "source_url": link,
                    "published": published,
                    "publisher": "",
                }
            )
    return items
