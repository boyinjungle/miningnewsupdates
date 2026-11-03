#!/usr/bin/env python3
"""Publish a verified, public, cross-linked Sakariya People Directory.

Records are explicitly curated and source-cited: no name/entity guessing.
Run after archive_search.py so article IDs/anchors have been built.
"""
from pathlib import Path
from datetime import date
import json, html, re
from urllib.parse import urlparse, quote

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"_site"
BASE="https://boyinjungle.github.io/miningnewsupdates/"
REG=ROOT/"data/people.json"

def check_url(u):
    p=urlparse(u)
    return p.scheme in ("https","http") and bool(p.netloc)

def validate(registry, articles):
    if not isinstance(registry,dict) or registry.get("schema_version")!=1 or not isinstance(registry.get("people"),list):
        raise ValueError("people.json requires schema_version=1 and people array")
    known={(a["date"],a["url"]) for a in articles}
    used_ids=set()
    for p in registry["people"]:
        if not isinstance(p,dict): raise ValueError("Person entry must be an object")
        for field in ("id","name","designation","company","country","commodities","last_verified","verification_url","mentions"):
            if field not in p: raise ValueError(f"Person missing {field}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",p["id"]): raise ValueError("Invalid person ID")
        if p["id"] in used_ids: raise ValueError(f"Duplicate person id: {p['id']}")
        used_ids.add(p["id"])
        if any(not isinstance(p[x],str) or not p[x].strip() for x in ("name","designation","company","country")):
            raise ValueError(f"Incomplete identity: {p['id']}")
        if not isinstance(p["commodities"],list) or not p["commodities"] or any(not isinstance(c,str) or not c.strip() for c in p["commodities"]):
            raise ValueError(f"No verified commodities: {p['id']}")
        date.fromisoformat(p["last_verified"])
        if not check_url(p["verification_url"]): raise ValueError(f"No public verifying URL for {p['id']}")
        if not isinstance(p["mentions"],list) or not p["mentions"]:
            raise ValueError(f"No verified newspaper article mention for {p['id']}")
        seen_mentions=set()
        for m in p["mentions"]:
            for field in ("date","article_url","source_url","kind","context"):
                if not isinstance(m.get(field),str) or not m[field].strip():
                    raise ValueError(f"Missing {field} mention on {p['id']}")
            date.fromisoformat(m["date"])
            if m["kind"] not in ("quoted","mentioned"): raise ValueError(f"Unsupported mention kind on {p['id']}")
            if not check_url(m["source_url"]): raise ValueError("Unverified public mention source URL")
            if (m["date"],m["article_url"]) not in known:
                raise ValueError(f"Person mention not linked to a generated article: {p['id']} {m['article_url']}")
            if m["article_url"] in seen_mentions: raise ValueError("Duplicate person-article mention")
            seen_mentions.add(m["article_url"])
    return used_ids

def compile_people():
    registry=json.loads(REG.read_text(encoding="utf-8"))
    articles=json.loads((OUT/"newspaper/article-index.json").read_text(encoding="utf-8"))
    validate(registry,articles)
    article_map={(a["date"],a["url"]):a for a in articles}
    people=[]
    mentions_by_issue={}
    for p in registry["people"]:
        item={k:p[k] for k in ("id","name","designation","company","country","commodities","last_verified","verification_url")}
        item["mentions"]=[]
        for m in p["mentions"]:
            article=article_map[(m["date"],m["article_url"])]
            item["mentions"].append({"date":m["date"],"article_url":"../newspaper/"+m["article_url"],
                "title":article["title"],"source_url":m["source_url"],"kind":m["kind"],
                "context":m["context"]})
            mentions_by_issue.setdefault(m["date"],{}).setdefault(m["article_url"].split("#",1)[-1],[]).append(item)
        item["mentions"].sort(key=lambda m:m["date"],reverse=True)
        people.append(item)
    people.sort(key=lambda x:x["name"].casefold())
    dest=OUT/"people"
    dest.mkdir(parents=True,exist_ok=True)
    (dest/"people.json").write_text(json.dumps({"schema_version":1,"people":people},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Show evidence-based links on archived news items. These are generated pages only;
    # do not modify original newspaper sources or invent quotes.
    for day,anchors in mentions_by_issue.items():
        path=OUT/"newspaper"/(day+".html")
        content=path.read_text(encoding="utf-8")
        for anchor,associated in anchors.items():
            pills="".join('<a href="../people/?person='+quote(x["id"])+'">'+
                           html.escape(x["name"])+'</a>' for x in associated)
            markup='<div class="sakariya-people-links"><span>People in this article</span> '+pills+'</div>'
            pattern=r'(<(?:article|p)\b[^>]*\bid=["\x27]'+re.escape(anchor)+r'["\x27][^>]*>)'
            matches=list(re.finditer(pattern,content,re.I))
            if len(matches)!=1:
                raise ValueError(f"Could not associate quoted person with article anchor: {day}#{anchor}")
            idx=matches[0].end()
            # Append inside article after its heading? Place link right at opening to preserve layout.
            content=content[:idx]+markup+content[idx:]
        if 'id="sakariya-people-links-style"' not in content:
            style='''<style id="sakariya-people-links-style">
.sakariya-people-links{display:flex;flex-wrap:wrap;gap:8px;margin:7px 0 10px;align-items:center;font:12px/1.5 'Proxima Nova',Arial,sans-serif;color:#624334}
.sakariya-people-links span{font-weight:700}
.sakariya-people-links a{padding:2px 9px;border-radius:15px;background:#fff4eb;border:1px solid #dbac8e;color:#8f3e16;text-decoration:none}
.sakariya-people-links a:hover{text-decoration:underline}
</style>'''
            content=content.replace("</head>",style+"</head>",1)
        path.write_text(content,encoding="utf-8")
    payload=json.dumps(people,ensure_ascii=False,separators=(",",":")).replace("<",r"\u003c")
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>People Directory | Sakariya Mining Intelligence</title>
<meta name="description" content="Verified public people quoted or mentioned in Sakariya mining news, searchable by organization, country, commodities and articles.">
<style>
:root{color-scheme:light;--ink:#24170e;--muted:#67564c;--line:#dbcabd;--orange:#C7551B}
*{box-sizing:border-box}body{margin:0;background:#F5F3F0;color:var(--ink);font:15px/1.5 'Proxima Nova','Avenir Next','Segoe UI',Arial,sans-serif}
button,input,select{font:inherit}button{cursor:pointer}a{color:#9b390d;text-underline-offset:3px}
header{background:#020100;color:#F5F3F0;border-bottom:5px solid var(--orange)}
header .wrap{max-width:1200px;margin:auto;padding:26px 22px}
.eyebrow{color:#e9b18e;font-weight:700;letter-spacing:1.5px;font-size:11px}
h1{font:700 clamp(28px,4vw,43px)/1.12 Georgia,serif;margin:8px 0 6px}
header p{margin:0;color:#e0d4cd}.wrap-main{max-width:1200px;margin:auto;padding:20px 20px 55px}
nav{display:flex;flex-wrap:wrap;gap:9px;margin-bottom:18px}
nav a{border:1px solid var(--line);background:#fff;padding:9px 12px;border-radius:6px;text-decoration:none;font-weight:700;color:#41200E;font-size:13px}
nav a:first-child{border-color:var(--orange);background:#fff3ea}
nav a:hover{background:#fff0e0}
.summary{margin:0 0 20px;color:var(--muted)}
.filters{display:grid;grid-template-columns:minmax(200px,2fr) repeat(3,minmax(125px,1fr)) auto;gap:9px;align-items:end;background:#fff;border:1px solid var(--line);border-radius:8px;padding:15px}
.filters label{display:grid;gap:5px;font-weight:700;font-size:12px;color:#41200E;min-width:0}
.filters input,.filters select{padding:10px;border:1px solid #bfae9f;border-radius:5px;background:#fff;color:#211711;min-width:0;width:100%}
.filters button{padding:10px 14px;border-radius:5px;border:1px solid var(--line);background:#fff6f0;color:#70300b;font-weight:700}
.results-meta{display:flex;justify-content:space-between;margin:18px 0 10px;gap:12px;align-items:center;color:var(--muted)}
.results-meta strong{font:700 22px Georgia,serif;color:#41200E}
.records{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.person{border:1px solid var(--line);background:#fff;border-radius:8px;padding:18px;scroll-margin-top:20px;min-width:0}
.person h2{font:700 23px/1.2 Georgia,serif;color:#41200E;margin:0 0 7px}
.person .job{font-weight:700;font-size:14px}
.person .org{color:#66534a;font-size:13px}
.mini{color:#735b50;font-size:12px;margin-top:7px}
.tagrow{display:flex;gap:5px;flex-wrap:wrap;margin:11px 0}
.tagrow button{border:1px solid #dfb69b;background:#fff2e7;color:#73320f;padding:3px 8px;border-radius:13px;font-size:11px}
.mentions{border-top:1px solid var(--line);padding-top:10px;margin-top:12px}
.mentions summary{cursor:pointer;font-weight:700;color:#41200E}
.mentions ul{padding-left:17px;margin:8px 0 0}.mentions li{margin-bottom:10px;font-size:13px}
.mentions small{color:#755c4a;display:block}.mentions p{color:#66554a;margin:4px 0;font-size:12px}
.empty{background:#fff;border:1px solid var(--line);border-radius:8px;padding:26px;color:var(--muted)}
footer{padding:20px;text-align:center;background:#020100;color:#fff;font-size:12px}
:focus-visible{outline:3px solid #C7551B;outline-offset:2px}
@media(max-width:850px){.filters{grid-template-columns:repeat(2,minmax(0,1fr))}.filters label:first-child{grid-column:1/-1}.records{grid-template-columns:1fr}}
@media(max-width:530px){.wrap-main{padding:15px 12px 42px}.filters{padding:12px}.filters label{grid-column:1/-1}.filters button{grid-column:1/-1}}
</style></head><body>
<header><div class="wrap"><div class="eyebrow">SAKARIYA MINES &amp; MINERALS · RESHAPING RESOURCES</div><h1>People Directory</h1><p>Public voices in mining, exploration, minerals and investment</p></div></header>
<main class="wrap-main">
<nav aria-label="Sakariya research navigation"><a href="../">Source Directory</a><a href="../newspaper/">Newspaper Archive</a><a href="../newspaper/#topics">Browse News Topics</a><a href="https://www.sakariyamines.com/" target="_blank" rel="noopener noreferrer">Visit Sakariya ↗</a></nav>
<p class="summary">A verified directory of people quoted or named in our news coverage, with their organization, designation, mineral interests and dated source-linked article mentions. Positions are shown as verified at the cited date—not guaranteed current.</p>
<div class="filters" role="search"><label>Search people and articles<input id="search" type="search" placeholder="Name, company, project, designation…"></label>
<label>Country<select id="country"><option value="">All countries</option></select></label>
<label>Commodity<select id="commodity"><option value="">All commodities</option></select></label>
<label>Organization<select id="company"><option value="">All organizations</option></select></label>
<button id="clear" type="button">Clear filters</button></div>
<div class="results-meta"><strong>People &amp; Sources</strong><span id="count" aria-live="polite"></span></div>
<div class="records" id="results"></div>
<div id="empty" class="empty" hidden>No matching verified people. New entries are added only after a public news source confirms the person's identity, role and article association.</div>
</main><footer>SAKARIYA MINES &amp; MINERALS · PUBLIC RESEARCH DIRECTORY · RESHAPING RESOURCES</footer>
<script type="application/json" id="people-data">'''+payload+'''</script>
<script>
(()=>{
const people=JSON.parse(document.getElementById('people-data').textContent);
const $=id=>document.getElementById(id);
const search=$('search'),country=$('country'),commodity=$('commodity'),company=$('company'),results=$('results');
const params=new URLSearchParams(location.search);
function distinct(values){return [...new Set(values)].filter(Boolean).sort((a,b)=>a.localeCompare(b));}
function fill(select,items){for(const item of distinct(items)){const o=document.createElement('option');o.value=item;o.textContent=item;select.add(o);}}
fill(country,people.map(p=>p.country));fill(commodity,people.flatMap(p=>p.commodities));fill(company,people.map(p=>p.company));
search.value=params.get('q')||'';country.value=params.get('country')||'';commodity.value=params.get('commodity')||'';company.value=params.get('company')||'';
function el(tag,cls,content){const x=document.createElement(tag);if(cls)x.className=cls;if(content!==undefined)x.textContent=content;return x;}
function render(){
const q=search.value.trim().toLowerCase(),c=country.value,m=commodity.value,co=company.value;
const matches=people.filter(p=>(!c||p.country===c)&&(!m||p.commodities.includes(m))&&(!co||p.company===co)&&
(!q||[p.name,p.designation,p.company,p.country,...p.commodities,...p.mentions.flatMap(x=>[x.title,x.context])].join(' ').toLowerCase().includes(q)));
results.replaceChildren();$('empty').hidden=matches.length!==0;
$('count').textContent=matches.length+' verified '+(matches.length===1?'person':'people')+' · '+people.length+' total';
for(const p of matches){
const card=el('article','person');card.id='person-'+p.id;
card.append(el('h2','',p.name),el('div','job',p.designation),el('div','org',p.company),el('div','mini',p.country+' · Verified '+p.last_verified));
const tags=el('div','tagrow');for(const c of p.commodities){const b=el('button','',c);b.type='button';b.onclick=()=>{commodity.value=c;render();};tags.append(b);}card.append(tags);
const details=el('details','mentions');details.open=params.get('person')===p.id;
details.append(el('summary','',p.mentions.length+' linked news '+(p.mentions.length===1?'article':'articles')));
const ul=el('ul');for(const item of p.mentions){
const li=el('li');const a=el('a','',item.title);a.href=item.article_url;
li.append(a,el('small','',item.date+' · '+(item.kind==='quoted'?'Quoted':'Mentioned')));
li.append(el('p','',item.context));
const source=el('a','', 'Verify original source ↗');source.href=item.source_url;source.target='_blank';source.rel='noopener noreferrer';li.append(source);ul.append(li);
}details.append(ul);card.append(details);
const verify=el('a','mini','Role/source verification ↗');verify.href=p.verification_url;verify.target='_blank';verify.rel='noopener noreferrer';card.append(verify);
results.append(card);
}
const upd=new URLSearchParams();if(q)upd.set('q',search.value);if(c)upd.set('country',c);if(m)upd.set('commodity',m);if(co)upd.set('company',co);
history.replaceState(null,'',location.pathname+(upd.toString()?'?'+upd:'')+location.hash);
}
search.addEventListener('input',render);[country,commodity,company].forEach(x=>x.addEventListener('change',render));
$('clear').onclick=()=>{search.value='';country.value='';commodity.value='';company.value='';render();};
render();
const id=params.get('person');if(id){const node=$('person-'+id);if(node)node.scrollIntoView();}
})();
</script></body></html>'''
    (dest/"index.html").write_text(page,encoding="utf-8")
    print(f"Built verified people directory with {len(people)} people and {sum(len(p['mentions']) for p in people)} article mentions.")

if __name__=="__main__":
    compile_people()
