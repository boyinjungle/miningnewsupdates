#!/usr/bin/env python3
"""Build public directory from approved source JSON, preserving the Sakariya UI."""
from pathlib import Path
import json, re, html
root = Path(__file__).resolve().parents[1]
data = json.loads((root / "data/sources.json").read_text(encoding="utf-8"))
required = {"Source Name", "Website URL", "Primary Category", "Geographic Focus", "Sakariya Priority"}
for i, item in enumerate(data, 1):
    if not required.issubset(item):
        raise ValueError(f"Source {i} missing required keys")
    if not str(item["Website URL"]).startswith(("https://", "http://")):
        raise ValueError(f"Source {i} has invalid URL")
# Only approved public-facing fields are embedded in the website.
allowed = ["Source Name", "Website URL", "Primary Category", "Geographic Focus",
           "Source Type", "Sakariya Priority", "What to Monitor", "Last Reviewed", "Status"]
public = [{key: item.get(key, "") for key in allowed} for item in data]
source = (root / "index.html").read_text(encoding="utf-8")
replacement = "<script>const data=" + json.dumps(public, ensure_ascii=False).replace("</", "<\\/") + ";const icons="
new, count = re.subn(r"<script>const data=\[[\s\S]*?\];const icons=", lambda _: replacement, source, count=1)
if count != 1:
    raise ValueError("Website source data marker was not found")
dest = root / "_site"
dest.mkdir(exist_ok=True)
# Add an automatic, dated entry point to the newest newspaper issue.
# The daily publishing agent only writes dated HTML + the index; this link
# updates on the next Pages build without a manual homepage edit.
issue_meta = json.loads((root / "data/newspaper-index.json").read_text(encoding="utf-8"))
listed_issues = issue_meta.get("issues", [])
if listed_issues and 'class="publication-nav"' in new:
    latest = max(listed_issues, key=lambda item: item["date"])
    latest_day = latest["date"]
    latest_desc = html.escape(latest.get("description", ""), quote=True)
    new = new.replace("</style>",
        """.latest-newspaper{background:#fff8f2;border:1px solid #e3c6b3;
        border-left:4px solid #C7551B;border-radius:7px;padding:13px 16px;
        margin:0 0 18px;display:flex;gap:12px;justify-content:space-between;
        align-items:center;flex-wrap:wrap;color:#41200E}
        .latest-newspaper strong{display:block;font-size:15px}
        .latest-newspaper p{margin:3px 0 0;color:#645247;font-size:12px}
        .latest-newspaper a{display:inline-block;background:#C7551B;color:#fff;
        border-radius:5px;padding:9px 13px;text-decoration:none;font-weight:700}
        .latest-newspaper a:hover,.latest-newspaper a:focus-visible{background:#41200E}
        @media(max-width:590px){.latest-newspaper a{width:100%;text-align:center}}
        </style>""", 1)
    strip = ('<aside class="latest-newspaper"><div>'
            '<strong>Latest Sakariya Mining &amp; Graphite Daily · '+latest_day+'</strong>'
            '<p>'+latest_desc+'</p></div>'
            '<a href="newspaper/'+latest_day+'.html">Read latest edition ↗</a>'
            '</aside>')
    new = new.replace('</nav><div class="intro">', '</nav>'+strip+'<div class="intro">', 1)
new = new.replace("</head>",
    '<link rel="alternate" type="application/rss+xml" title="Sakariya Mining Daily RSS" href="feed.xml">'
    +"</head>",1)
(dest / "index.html").write_text(new, encoding="utf-8")
(dest / ".nojekyll").write_text("", encoding="utf-8")
print(f"Built public site with {len(public)} source records.")

# Newspaper archive: each issue is stored as an independent HTML document.
from urllib.parse import quote
from datetime import date
import shutil
idx = json.loads((root / "data/newspaper-index.json").read_text(encoding="utf-8"))
issues = idx.get("issues", [])
valid = []
for item in issues:
    day = item["date"]
    date.fromisoformat(day)
    path = root / "newspaper" / f"{day}.html"
    if not path.exists():
        raise ValueError(f"Archive issue missing: {path}")
    target = dest / "newspaper" / f"{day}.html"
    target.parent.mkdir(exist_ok=True)
    shutil.copyfile(path, target)
    valid.append({"date": day, "title": item.get("title", f"Mining Newspaper — {day}"),
                  "description": item.get("description", ""), "url": f"{day}.html"})
valid.sort(key=lambda i: i["date"], reverse=True)
entries = []
for i in valid:
    d = html.escape(i["date"])
    title = html.escape(i["title"])
    desc = html.escape(i["description"])
    entries.append(f'<tr><td>{d}</td><td><a href="{i["url"]}">{title}</a></td><td>{desc}</td></tr>')
rows = "\\n".join(entries) if entries else '<tr><td colspan="3">New editions will appear here after publication.</td></tr>'
archive = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sakariya Mining Daily — Archive</title><style>
:root{color-scheme:light}*{box-sizing:border-box}body{font:16px 'Proxima Nova',Arial,sans-serif;max-width:1100px;margin:auto;padding:30px 20px;background:#F5F3F0;color:#41200E}header{background:#020100;color:white;padding:24px;border-bottom:4px solid #C7551B}h1{margin:0}a{color:#C7551B}table{width:100%;border-collapse:collapse;background:#fff;margin-top:24px}td,th{padding:14px;border-bottom:1px solid #dfd8d2;text-align:left}th{background:#eee3dc}input{font:inherit;padding:12px;width:100%;margin:20px 0 0;border:1px solid #A89C94;border-radius:6px}</style></head>
<body><header><div>SAKARIYA MINES &amp; MINERALS · RESHAPING RESOURCES</div><h1>Mining &amp; Graphite Daily</h1><p>Newspaper Archive</p></header><p><a href="../">← Source Intelligence Directory</a></p><label for="q">Search archived editions</label><input id="q" placeholder="Filter by date, title or description" oninput="const q=this.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q))"><table><thead><tr><th>Date (IST)</th><th>Edition</th><th>Topics</th></tr></thead><tbody>""" + rows + """</tbody></table></body></html>"""
out = dest / "newspaper" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(archive, encoding="utf-8")
print(f"Published newspaper archive with {len(valid)} editions.")

# Build tagged article archive and annotate edition pages with clickable topic tags.
import subprocess, sys
subprocess.run([sys.executable, str(root / "scripts/archive_search.py")], check=True)
# Publish source-linked people directory after article IDs exist.
subprocess.run([sys.executable, str(root / "scripts/people_directory.py")], check=True)
# Build publicly sourced project and funding directories as linked research views.
subprocess.run([sys.executable, str(root / "scripts/project_funding.py")], check=True)
