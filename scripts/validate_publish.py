#!/usr/bin/env python3
"""Validate and finish the public Sakariya static site.

Runs after scripts/build.py. Standard library only. Designed for an
automation-only publisher using a public GitHub repository.
"""
from __future__ import annotations
import json
import re
import sys
from datetime import date, datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"
BASE = "https://boyinjungle.github.io/miningnewsupdates"
PUBLIC_SOURCE = ROOT / "newspaper"
def fail(msg):
    raise ValueError("Publication validation failed: " + msg)
def read_json(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        fail(f"could not read {p.relative_to(ROOT)}: {e}")
def valid_url(u):
    p = urlparse(u)
    return p.scheme in ("http","https") and bool(p.netloc)
def xml_write(path, root):
    ET.indent(root, space="  ")
    path.write_bytes(b'<?xml version="1.0" encoding="utf-8"?>\n' +
                     ET.tostring(root, encoding="utf-8"))
def main():
    issues = read_json(ROOT / "data/newspaper-index.json").get("issues", [])
    if not isinstance(issues, list):
        fail("newspaper index issues must be a list")
    seen = set()
    for issue in issues:
        if not isinstance(issue, dict):
            fail("newspaper issue must be an object")
        day = issue.get("date")
        try:
            parsed = date.fromisoformat(day)
        except (ValueError, TypeError) as e:
            fail(f"invalid edition date {day!r}: {e}")
        if day != parsed.isoformat() or day in seen:
            fail(f"duplicate or invalid edition date: {day}")
        seen.add(day)
        for key in ("title","description"):
            if not isinstance(issue.get(key), str) or not issue[key].strip():
                fail(f"missing {key} on issue {day}")
        html_path = PUBLIC_SOURCE / (day + ".html")
        rendered = SITE / "newspaper" / (day + ".html")
        if not html_path.is_file() or not rendered.is_file():
            fail(f"missing public source or rendered newspaper for {day}")
        text = rendered.read_text(encoding="utf-8")
        for required in ("<html", "</html>", "<main", "id=\"jump-to-news\"",
                         "id=\"issue-story-select\"", "sakariya-brand-bridge",
                         "href=\"../\""):
            if required not in text:
                fail(f"{day} is missing required published UI: {required}")
        if "prefers-color-scheme:dark" in text or "color-scheme:dark" in text:
            fail(f"{day} unexpectedly enables dark page theme")
        if len(text.encode("utf-8")) > 2_000_000:
            fail(f"{day} HTML exceeds 2 MB; split/compress media and markup")
    source_rows = read_json(ROOT / "data/sources.json")
    if not isinstance(source_rows, list):
        fail("sources.json must be an array")
    for row in source_rows:
        if not isinstance(row, dict):
            fail("source directory row must be an object")
        u = row.get("Website URL")
        if not isinstance(u, str) or not valid_url(u):
            fail(f"invalid directory URL: {u}")
    if not (SITE / "index.html").is_file():
        fail("source directory not generated")
    archive = SITE / "newspaper/index.html"
    if not archive.is_file() or "issue-story-select" in archive.read_text(encoding="utf-8"):
        fail("archive homepage missing or is not the search library")
    articles = read_json(SITE / "newspaper/article-index.json")
    if not isinstance(articles, list):
        fail("article-index.json must be an array")
    for entry in articles:
        if entry.get("date") not in seen:
            fail(f"article has unindexed issue date: {entry.get('date')}")
        for field in ("title","url","topics","tags"):
            if not entry.get(field):
                fail(f"article missing {field}: {entry.get('title')}")
        if not entry["url"].startswith(entry["date"]+".html#"):
            fail(f"invalid article anchor URL: {entry['url']}")
    # Require the people directory and validate all source-linked public entries.
    people_page = SITE / "people/index.html"
    people_data_path = SITE / "people/people.json"
    if not people_page.is_file() or not people_data_path.is_file():
        fail("People Directory not generated")
    people_data = read_json(people_data_path)
    if people_data.get("schema_version") != 1 or not isinstance(people_data.get("people"), list):
        fail("Invalid published people directory format")
    for person in people_data["people"]:
        for field in ("name","designation","company","country","verification_url","commodities","mentions"):
            if not person.get(field):
                fail(f"People record missing {field}: {person.get('name')}")
        if not valid_url(person["verification_url"]):
            fail(f"People verification URL is invalid: {person.get('name')}")
        for mention in person["mentions"]:
            if not valid_url(mention.get("source_url", "")):
                fail(f"People news source URL is invalid: {person.get('name')}")
    # Require functional project/plant and funding directories.
    projects_page = SITE / "projects/index.html"
    funding_page = SITE / "funding/index.html"
    if not projects_page.is_file() or not funding_page.is_file():
        fail("Project and Funding Directory pages not generated")
    projects_reg = read_json(SITE / "projects/register.json")
    funding_reg = read_json(SITE / "funding/register.json")
    if projects_reg.get("schema_version") != 1 or funding_reg.get("schema_version") != 1:
        fail("Invalid project/funding manifest version")
    projs = projects_reg.get("projects",[])
    trans = funding_reg.get("funding",[])
    ids = {p["id"] for p in projs}
    if len(ids) != len(projs):
        fail("Duplicate project IDs")
    txids = [t["id"] for t in trans]
    if len(set(txids)) != len(txids):
        fail("Duplicate funding transaction IDs")
    for t in trans:
        if t["project_id"] not in ids:
            fail("Funding is not linked to an existing project")
        if t["status"]=="Disbursed / received" and not t.get("disbursement_verified"):
            fail("Disbursed funding record lacks evidence flag")
        if not valid_url(t["source_url"]):
            fail("Funding transaction missing source URL")
    # Sitemap is for publication pages, not every anchor fragment.
    ns="http://www.sitemaps.org/schemas/sitemap/0.9"
    sitemap = ET.Element("urlset", xmlns=ns)
    pages = [("",None),("newspaper/",None),("people/",None),("projects/",None),("funding/",None)] + [
        ("newspaper/"+i["date"]+".html",i["date"])
        for i in sorted(issues,key=lambda i:i["date"],reverse=True)
    ]
    for uri,lastmod in pages:
        item=ET.SubElement(sitemap,"url")
        ET.SubElement(item,"loc").text=BASE+"/"+uri
        if lastmod: ET.SubElement(item,"lastmod").text=lastmod
    xml_write(SITE/"sitemap.xml",sitemap)
    (SITE/"robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: "+BASE+"/sitemap.xml\n",
        encoding="utf-8")
    # RSS exposes short originally authored summaries with source links.
    rss=ET.Element("rss",version="2.0")
    channel=ET.SubElement(rss,"channel")
    for tag,value in (
        ("title","Sakariya Mining & Graphite Daily"),
        ("link",BASE+"/newspaper/"),
        ("description","Public gold, graphite, critical minerals and global mining news from Sakariya Mines & Minerals."),
        ("language","en-IN"),
        ("generator","Sakariya GitHub Pages automated publisher")):
        ET.SubElement(channel,tag).text=value
    count=0
    for entry in sorted(articles,key=lambda x:(x["date"],x["title"]),reverse=True)[:100]:
        item=ET.SubElement(channel,"item")
        url=BASE+"/newspaper/"+entry["url"]
        ET.SubElement(item,"title").text=entry["title"]
        ET.SubElement(item,"link").text=url
        ET.SubElement(item,"guid",isPermaLink="true").text=url
        ET.SubElement(item,"description").text=entry.get("summary","")
        for topic in entry.get("topics",[])[:5]:
            ET.SubElement(item,"category").text=topic
        published=datetime.fromisoformat(entry["date"]).replace(tzinfo=timezone.utc)
        ET.SubElement(item,"pubDate").text=format_datetime(published,usegmt=True)
        count+=1
    xml_write(SITE/"feed.xml",rss)
    # Standalone public index provides a stable machine-readable contract.
    (SITE/"newspaper/manifest.json").write_text(json.dumps({
        "schema_version":1,
        "site":BASE+"/newspaper/",
        "total_issues":len(issues),
        "total_articles":len(articles),
        "issues":[{"date":i["date"],"url":i["date"]+".html"}
                  for i in sorted(issues,key=lambda i:i["date"],reverse=True)],
        "article_index":"article-index.json",
        "rss":"../feed.xml"
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    size=sum(p.stat().st_size for p in SITE.rglob("*") if p.is_file())
    print(f"Validated {len(issues)} editions, {len(articles)} searchable articles, "
          f"{len(source_rows)} sources; RSS contains {count} entries; "
          f"total generated site {size/1024/1024:.2f} MB.")
    if size>150*1024*1024:
        print("WARNING: generated site exceeds 150 MB; review static assets.")
if __name__=="__main__":
    try: main()
    except ValueError as exc:
        print(exc,file=sys.stderr)
        sys.exit(1)
