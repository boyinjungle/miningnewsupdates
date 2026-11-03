#!/usr/bin/env python3
"""Compile a tagged, cross-edition article index from public newspaper HTML files.
Standard-library-only so GitHub Pages deployments have no extra dependencies.
"""
import html
import json
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_site" / "newspaper"
TOPICS = [
    ("gold", "Gold & Markets", "◆", "Gold prices, discoveries and Jomu"),
    ("graphite", "Graphite & Markets", "◈", "Natural and synthetic graphite"),
    ("exploration", "Exploration & Geology", "⌁", "Drilling, resources and technology"),
    ("finance", "Finance & Investment", "▤", "Funding, investors and ownership"),
    ("offtake", "Offtake & Downstream", "▥", "Buyers, anodes, steel and refractories"),
    ("policy", "Mining Policy & Regulation", "⚖", "Law, licences, trade and compliance"),
    ("tanzania", "Tanzania & East Africa", "◎", "Regional projects and infrastructure"),
    ("india", "India Mining & Industry", "▦", "India exploration and critical minerals"),
    ("competitors", "Projects & Competitors", "◉", "Junior miners and project milestones"),
    ("opportunities", "Deals & Geo Services", "↗", "Partnerships, tenders and contracts"),
    ("social", "Natural Graphite Social Pulse", "◌", "LinkedIn, X, Reddit and forums"),
    ("events", "Conferences & Events", "▣", "Industry events and deadlines"),
]
NAMES = {a:b for a,b,_,_ in TOPICS}
PATTERNS = {
  "gold": r"\bgold\b|\bbullion\b|\bjomu\b|\bau\b",
  "graphite": r"\bgraphite\b|\bflake\b|\bspheri[sz]|\bsynthetic anode\b",
  "exploration": r"\bexplor|\bgeolog|\bdrill|\bmineralis|\bresource\b|\breserve\b|\bassay|\bgeophys|\bmetallurg|\bJORC\b|\bNI 43-101\b",
  "finance": r"\binvest|\bfinanc|\bfund|\bequity\b|\bdebt\b|\bIPO\b|\bcapital\b|\bJV\b|\bjoint venture\b|\bM&A\b",
  "offtake": r"\bofftake\b|\bbuyer\b|\bdownstream\b|\banode\b|\bsteel\b|\brefractor|\bbattery\b|\bpurif|\bprocessing\b|\bqualification\b",
  "policy": r"\bpolic|\bregulat|\bexport\b|\broyalt|\blicen[cs]|\bcompliance\b|\bgovernment\b|\bministry\b|\bpermit\b|\bstockpil",
  "tanzania": r"\btanzania\b|\btanga\b|\blindi\b|\bgeita\b|\bkahama\b|\bnzega\b|\beast africa\b|\bdar es salaam\b",
  "india": r"\bindia\b|\bindian\b|\bchhattisgarh\b|\bNMET\b|\bGSI\b|\bdeccan\b",
  "competitors": r"\bcompetitor\b|\bjunior\b|\bproject\b|\boperator\b|\bdevelop|\bmilestone\b|\bplant\b|\bconstruction\b|\bcommission",
  "opportunities": r"\btender\b|\bprocure|\bcontract\b|\bpartner|\bfarm-in\b|\bservices\b|\bsurvey\b|\bdeal\b",
  "social": r"\bsocial pulse\b|\blinkedin\b|\breddit\b|\bforum\b|\bposted\b|\bsocial discussion\b",
  "events": r"\bconference\b|\bexhibition\b|\bevent\b|\bregister|\bexhibitor\b|\bdeadline\b|\bTMIC\b",
}
def plain(fragment):
    txt = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html.unescape(txt).split())
def excerpt(s, length=230):
    return s if len(s) <= length else s[:length].rsplit(" ", 1)[0] + "…"
def attr(attrs, key):
    m = re.search(r'\b'+re.escape(key)+r'=["\x27]([^"\x27]*)', attrs)
    return html.unescape(m.group(1)) if m else ""
def classify(title, body, region, attrs):
    declared = [s.strip().lower() for s in attr(attrs,"data-topics").split(",") if s.strip()]
    if declared:
        cats = [s for s in declared if s in NAMES]
    else:
        probe = (title + " " + body[:900]).lower()
        cats = [k for k,p in PATTERNS.items() if re.search(p,probe, re.I)]
        if region == "INDIA": cats.append("india")
        if region == "TANZANIA / EAST AFRICA": cats.append("tanzania")
        cats = list(dict.fromkeys(cats))
        # Keep category assignment broad but meaningful, avoiding generic project hits.
        if len(cats) > 5:
            cats = [x for x in cats if x not in ("competitors", "opportunities")][:5] or cats[:5]
        if not cats: cats = ["exploration"]
    tags = [s.strip() for s in attr(attrs,"data-tags").split(",") if s.strip()]
    if not tags:
        tags = [NAMES[k] for k in cats[:4]]
        for tag,pat in [("Tanga",r"\btanga\b"),("Jomu",r"\bjomu\b"),("Tanzania",r"\btanzania\b"),("India",r"\bindia\b"),("Natural Flake",r"\bnatural flake\b"),("Offtake",r"\bofftake\b"),("Lithium-ion Batteries",r"\bbatter(y|ies)\b")]:
            if re.search(pat,(title+" "+body),re.I) and tag not in tags: tags.append(tag)
    return cats,tags[:7]
def pill_markup(tags):
    links = "".join('<a class="story-chip" href="index.html?tag='+quote(x,safe="")+'">'+html.escape(x)+'</a>' for x in tags)
    return '<div class="story-tags" aria-label="Article tags">'+links+'</div>'
def context_at(source, pos):
    sec = list(re.finditer(r'<section\b[^>]*\bid=["\x27]([^"\x27]+)["\x27]',source[:pos],re.I))
    section = sec[-1].group(1) if sec else ""
    reg = list(re.finditer(r"<h2[^>]*>\s*(WORLD|INDIA|TANZANIA\s*/\s*EAST AFRICA)\s*</h2>",source[:pos],re.I))
    region = reg[-1].group(1).upper() if reg and section=="major" else ""
    return section,region

def compile_issue(day, original):
    records=[]
    story=0
    def story_sub(m):
        nonlocal story
        attrs,inner=m.group(1),m.group(2)
        title_match=re.search(r"<h[34][^>]*>(.*?)</h[34]>",inner,re.I|re.S)
        if not title_match: return m.group(0)
        story+=1
        title=plain(title_match.group(1))
        section,region=context_at(original,m.start())
        content=plain(inner)
        body=re.sub(r"^.*?Why it matters:\s*","",content) if "Why it matters:" in content else content
        cats,tags=classify(title,content,region,attrs)
        source_link=re.search(r'<a\b[^>]*href=["\x27](https?://[^"\x27]+)',inner,re.I)
        anchor=attr(attrs,"id") or f"story-{story}"
        records.append({"date":day,"title":title,"summary":excerpt(content,260),"topics":cats,"tags":tags,"region":region or "GLOBAL","section":section,"url":f"{day}.html#{anchor}","source":html.unescape(source_link.group(1)) if source_link else ""})
        attrs_new = attrs if attr(attrs,"id") else attrs+' id="'+anchor+'"'
        return "<article"+attrs_new+">"+inner+pill_markup(tags)+"</article>"
    annotated=re.sub(r"<article\b([^>]*)>(.*?)</article>",story_sub,original,flags=re.I|re.S)

    # Standalone short news briefs: one identified topic per short, substantive paragraph.
    brief=0
    def section_sub(m):
        nonlocal brief
        tag,attrs,inner=m.group(1),m.group(2),m.group(3)
        sid=attr(attrs,"id")
        if sid not in ("markets","intelligence","social-pulse"): return m.group(0)
        def brief_sub(p):
            nonlocal brief
            p_attrs,p_inner=p.group(1),p.group(2)
            heading=re.match(r"\s*<strong>(.*?)</strong>\s*:\s*",p_inner,re.I|re.S)
            if not heading: return p.group(0)
            title=plain(heading.group(1))
            body=plain(p_inner)
            if len(body)<80: return p.group(0)
            # Do not market absence of public social discussion as an actual social-media article.
            if "no qualifying" in body.lower() or "no sufficiently verified" in body.lower(): return p.group(0)
            brief+=1
            cats,tags=classify(title,body,"",p_attrs)
            if sid=="social-pulse" and "social" not in cats: cats.insert(0,"social")
            anchor=attr(p_attrs,"id") or f"brief-{brief}"
            mlink=re.search(r'<a\b[^>]*href=["\x27](https?://[^"\x27]+)',p_inner,re.I)
            records.append({"date":day,"title":title,"summary":excerpt(body,260),"topics":cats,"tags":tags,"region":"GLOBAL","section":sid,"url":f"{day}.html#{anchor}","source":html.unescape(mlink.group(1)) if mlink else ""})
            updated=p_attrs if attr(p_attrs,"id") else p_attrs+' id="'+anchor+'"'
            return "<p"+updated+">"+p_inner+"</p>"+pill_markup(tags)
        inner=re.sub(r"<p\b([^>]*)>(.*?)</p>",brief_sub,inner,flags=re.I|re.S)
        return "<"+tag+attrs+">"+inner+"</"+tag+">"
    annotated=re.sub(r"<(section)\b([^>]*)>(.*?)</section>",section_sub,annotated,flags=re.I|re.S)
    css=("""
<style id="sakariya-tag-styles">
.story-tags{display:flex;flex-wrap:wrap;gap:6px;margin:9px 0 13px}
.story-chip{display:inline-block;border:1px solid #bd9c88;color:#71320f;background:#fff3e9;
 padding:3px 9px;border-radius:16px;font:600 12px/1.6 'Proxima Nova',Arial,sans-serif;text-decoration:none}
.story-chip:hover,.story-chip:focus-visible{background:#41200E;color:#fff;outline:2px solid #C7551B;outline-offset:1px}
article[id],p[id^="brief-"]{scroll-margin-top:30px}
@media(prefers-color-scheme:dark){.story-chip{background:#422c22;color:#ffe4d2;border-color:#bf835e}}
</style>""")
    annotated=annotated.replace("</head>",css+"</head>",1)
    return annotated,records

def render_archive(records,issues):
    payload=json.dumps(records,ensure_ascii=False,separators=(",",":")).replace("<",r"\u003c")
    tiles="".join('<button class="topic-card" type="button" data-topic="'+key+'" aria-pressed="false"><span class="topic-icon" aria-hidden="true">'+icon+'</span><span><strong>'+html.escape(name)+'</strong><small>'+html.escape(desc)+'</small></span><b class="count" id="count-'+key+'">0</b></button>' for key,name,icon,desc in TOPICS)
    date_links="".join('<tr><td>'+html.escape(i["date"])+'</td><td><a href="'+html.escape(i["date"])+'.html">'+html.escape(i.get("title",i["date"]))+'</a></td><td>'+html.escape(i.get("description",""))+'</td></tr>' for i in issues)
    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Search every Sakariya mining newspaper article by topic, tag, keyword or date"><title>Sakariya Mining Daily | Article Library & Archive</title><style>
:root{color-scheme:light;--bg:#F5F3F0;--ink:#24170e;--muted:#66584f;--panel:#fff;--line:#d8c9bd;--accent:#C7551B;--link:#9e3b0a;--dark:#41200E}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.52 'Proxima Nova','Avenir Next','Segoe UI',Arial,sans-serif}a{color:var(--link);text-decoration-thickness:1px;text-underline-offset:3px}a:hover{text-decoration-thickness:2px}button,input,select{font:inherit}button{cursor:pointer}header{background:#020100;color:#F5F3F0;border-bottom:5px solid var(--accent)}header .inner{max-width:1200px;padding:24px 22px;margin:auto}.overline{font-size:11px;font-weight:700;letter-spacing:2px;color:#E9AE88}h1{font:700 clamp(26px,4vw,43px)/1.15 Georgia,serif;margin:6px 0}header p{color:#DFD4CD;margin:5px 0}.shell{max-width:1200px;margin:auto;padding:24px 20px 60px}.nav{display:flex;gap:20px;flex-wrap:wrap;padding:10px 0 18px}.nav a{font-weight:650}.kicker{font-size:11px;letter-spacing:1.6px;color:var(--link);font-weight:800;text-transform:uppercase}h2{font:700 24px Georgia,serif;margin:7px 0 8px}p.sub{margin:0 0 18px;color:var(--muted)}.topics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.topic-card{border:1px solid var(--line);background:var(--panel);color:var(--ink);text-align:left;padding:14px 11px;border-radius:8px;display:flex;gap:10px;align-items:center;min-width:0;box-shadow:none}.topic-card:hover{border-color:var(--accent)}.topic-card[aria-pressed="true"]{border:2px solid var(--accent);background:#fff0e4;color:#28170c;padding:13px 10px}.topic-icon{flex:0 0 32px;height:32px;display:grid;place-items:center;border-radius:7px;background:#f2e2d5;color:#8e380e;font-size:20px;font-weight:bold}.topic-card strong{display:block;font-size:13px;line-height:1.25}.topic-card small{display:block;color:var(--muted);font-size:11px;line-height:1.3;margin-top:4px}.topic-card .count{font-size:12px;margin-left:auto;align-self:flex-start;color:var(--link)}.controls{display:flex;gap:9px;flex-wrap:wrap;align-items:center;margin:19px 0 12px}.controls input,.controls select{color:var(--ink);background:var(--panel);border:1px solid var(--line);padding:11px;border-radius:6px;min-height:42px}.controls input{flex:2 1 250px;min-width:200px}.controls select{flex:1 1 135px;max-width:230px}button.clear{border:1px solid var(--line);background:var(--panel);color:var(--ink);padding:10px 15px;border-radius:6px}.panel{border:1px solid var(--line);background:var(--panel);border-radius:8px;overflow:hidden}.panel-heading{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:12px 15px;border-bottom:1px solid var(--line);font-weight:700}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;min-width:750px}th{font-size:11px;letter-spacing:.6px;text-transform:uppercase;color:var(--muted);text-align:left;background:#f2ebe6}th,td{padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}tbody tr:last-child td{border-bottom:0}td a.article{font-size:14px;font-weight:750}td .summary{color:var(--muted);font-size:12px;margin:5px 0 0;max-width:660px}.chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:6px}.chip{border:1px solid var(--line);background:#f8f0e9;color:var(--ink);border-radius:15px;padding:2px 8px;font-size:11px}.chip:hover{border-color:var(--accent)}.meta{color:var(--muted);white-space:nowrap;font-size:12px}.empty{padding:24px;color:var(--muted)}section.dates{margin-top:35px}.dates table{min-width:560px}footer{background:#020100;color:#F5F3F0;padding:20px;text-align:center;font-size:12px}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
@media(max-width:860px){.topics{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:530px){.topics{grid-template-columns:1fr 1fr;gap:7px}.topic-card{padding:9px 7px;gap:6px}.topic-card[aria-pressed="true"]{padding:8px 6px}.topic-icon{flex-basis:24px;height:27px;font-size:16px}.topic-card strong{font-size:12px}.topic-card small{display:none}.topic-card .count{font-size:11px}.shell{padding:15px 12px 40px}h2{font-size:21px}}
@media(prefers-color-scheme:dark){:root{color-scheme:dark;--bg:#16100D;--ink:#F5F3F0;--muted:#D0C0B4;--panel:#291B15;--line:#675044;--accent:#EF8B52;--link:#FFB382}.topic-card[aria-pressed="true"]{background:#53301e;color:#fff3e9}.topic-icon{background:#52301d;color:#ffb382}th{background:#3c2a20;color:#F1DDD0}.chip{background:#473024;color:#F5F3F0}.controls input,.controls select{color:#fff}.topic-card .count{color:#FFB382}}
</style></head><body><header><div class="inner"><div class="overline">SAKARIYA MINES &amp; MINERALS · RESHAPING RESOURCES</div><h1>Mining &amp; Graphite Daily</h1><p>Searchable Article Library &amp; Newspaper Archive</p></div></header>
<main class="shell"><nav class="nav"><a href="../">Source Directory</a><a href="#topics">Browse Topics</a><a href="#articles">All Articles</a><a href="#dates">Editions by Date</a></nav><section id="topics"><span class="kicker">Research desks</span><h2>Browse by topic</h2><p class="sub">Select a topic to see related reporting across every newspaper edition. One story can appear in several relevant topics.</p><div class="topics">""" + tiles + """</div></section>
<section id="articles" aria-label="Search archived articles"><div class="controls"><input id="query" type="search" aria-label="Search articles" placeholder="Search articles, people, projects, keywords…"><select id="tag" aria-label="Filter by tag"><option value="">All tags</option></select><select id="date" aria-label="Filter by edition"><option value="">All dates</option></select><select id="region" aria-label="Filter by geography"><option value="">All regions</option></select><button type="button" class="clear" id="reset">Clear filters</button></div><div class="panel"><div class="panel-heading"><span id="filter-title">All Articles</span><span id="result-count" aria-live="polite"></span></div><div class="scroll"><table><thead><tr><th>Edition</th><th>Story &amp; tags</th><th>Region</th></tr></thead><tbody id="results"></tbody></table></div><p class="empty" id="no-results" hidden>No matching articles. Try another topic, keyword, tag or date.</p></div></section>
<section class="dates" id="dates"><span class="kicker">Complete issues</span><h2>Browse editions by date</h2><p class="sub">Read the original full newspapers, including executive summaries and research notes.</p><div class="panel scroll"><table><thead><tr><th>Date (IST)</th><th>Edition</th><th>Coverage</th></tr></thead><tbody>""" + date_links + """</tbody></table></div></section></main><footer>SAKARIYA MINES &amp; MINERALS · RESHAPING RESOURCES · A curated public mining research archive</footer>
<script type="application/json" id="article-data">""" + payload + """</script><script>
const data=JSON.parse(document.getElementById("article-data").textContent);
const topicButtons=[...document.querySelectorAll(".topic-card")];
const $=id=>document.getElementById(id);
const params=new URLSearchParams(location.search);
let topic=params.get("topic")||"";
const input=$("query"),tag=$("tag"),date=$("date"),region=$("region"),out=$("results");
input.value=params.get("q")||"";
function unique(values){return [...new Set(values.filter(Boolean))].sort((a,b)=>a.localeCompare(b));}
function options(node,values){values.forEach(value=>{const o=document.createElement("option");o.value=value;o.textContent=value;node.append(o);});}
options(tag,unique(data.flatMap(x=>x.tags)));
options(date,unique(data.map(x=>x.date)).reverse());
options(region,unique(data.map(x=>x.region)));
tag.value=params.get("tag")||"";date.value=params.get("date")||"";region.value=params.get("region")||"";
const names=Object.fromEntries(topicButtons.map(b=>[b.dataset.topic,b.querySelector("strong").textContent]));
if(!names[topic])topic="";
function el(n,cl,txt){const x=document.createElement(n);if(cl)x.className=cl;if(txt!==undefined)x.textContent=txt;return x;}
function show(){
  const q=input.value.toLowerCase().trim(),t=tag.value,d=date.value,r=region.value;
  topicButtons.forEach(b=>{b.setAttribute("aria-pressed",String(b.dataset.topic===topic));const n=data.filter(x=>x.topics.includes(b.dataset.topic)).length;b.querySelector(".count").textContent=n;});
  const found=data.filter(x=>(!topic||x.topics.includes(topic))&&(!t||x.tags.includes(t))&&(!d||x.date===d)&&(!r||x.region===r)&&(!q||[x.title,x.summary,x.region,x.date,...x.tags,...x.topics].join(" ").toLowerCase().includes(q)));
  found.sort((a,b)=>b.date.localeCompare(a.date)||a.title.localeCompare(b.title));
  $("filter-title").textContent=topic?names[topic]:"All Articles";
  $("result-count").textContent=found.length+" article"+(found.length===1?"":"s");
  out.replaceChildren();
  for(const x of found){
     const tr=el("tr"),dt=el("td","meta",x.date),main=el("td"),a=el("a","article",x.title);
     a.href=x.url;main.append(a,el("p","summary",x.summary));
     const chips=el("div","chips");for(const t of x.tags){const b=el("button","chip",t);b.type="button";b.onclick=()=>{tag.value=t;show();};chips.append(b);}main.append(chips);
     tr.append(dt,main,el("td","meta",x.region));out.append(tr);
  }
  $("no-results").hidden=found.length!==0;
  const updated=new URLSearchParams();if(topic)updated.set("topic",topic);if(q)updated.set("q",input.value);if(t)updated.set("tag",t);if(d)updated.set("date",d);if(r)updated.set("region",r);
  history.replaceState(null,"",location.pathname+(updated.toString()?"?"+updated:"")+location.hash);
}
topicButtons.forEach(b=>b.onclick=()=>{topic=topic===b.dataset.topic?"":b.dataset.topic;show();$("articles").scrollIntoView({behavior:"smooth",block:"start"});});
[input,tag,date,region].forEach(n=>n.addEventListener(n===input?"input":"change",show));
$("reset").onclick=()=>{topic="";input.value="";tag.value="";date.value="";region.value="";show();};
show();
</script></body></html>"""

def main():
    idx=json.loads((ROOT/"data/newspaper-index.json").read_text(encoding="utf-8"))
    issues=sorted(idx.get("issues",[]),key=lambda x:x["date"],reverse=True)
    records=[]
    OUT.mkdir(parents=True,exist_ok=True)
    for issue in issues:
        day=issue["date"]
        src=ROOT/"newspaper"/(day+".html")
        if not src.is_file(): raise FileNotFoundError(src)
        rendered,found=compile_issue(day,src.read_text(encoding="utf-8"))
        (OUT/(day+".html")).write_text(rendered,encoding="utf-8")
        records.extend(found)
    (OUT/"article-index.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"index.html").write_text(render_archive(records,issues),encoding="utf-8")
    print(f"Built searchable archive: {len(issues)} editions, {len(records)} indexed articles/briefs.")

if __name__=="__main__":
    main()
