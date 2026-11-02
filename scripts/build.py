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
(dest / "index.html").write_text(new, encoding="utf-8")
(dest / ".nojekyll").write_text("", encoding="utf-8")
print(f"Built public site with {len(public)} source records.")
