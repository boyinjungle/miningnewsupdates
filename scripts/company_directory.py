#!/usr/bin/env python3
"""Compile public company profiles connected to projects, funding, people and news."""
import json,re,html
from pathlib import Path
from urllib.parse import urlparse
from datetime import date

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"_site"
def load(path,key):
    v=json.loads(path.read_text(encoding="utf-8"))
    if key not in v or not isinstance(v[key],list):raise ValueError("Invalid "+str(path))
    return v[key]
def source(url):
    p=urlparse(url);return p.scheme in ("http","https") and bool(p.netloc)
def run():
    companies=load(ROOT/"data/companies.json","companies")
    projects=load(ROOT/"data/projects.json","projects")
    funding=load(ROOT/"data/funding.json","transactions")
    people=load(ROOT/"data/people.json","people")
    articles=load(OUT/"newspaper/article-index.json",None) if False else json.loads((OUT/"newspaper/article-index.json").read_text(encoding="utf-8"))
    pmap={p["id"]:p for p in projects};fmap={p["id"]:p for p in people}
    amap={a["url"]:a for a in articles}
    ids=set();rows=[]
    for c in companies:
        for key in ("id","name","sector","headquarters_country","project_ids","people_ids","article_urls","verification_url","last_verified"):
            if key not in c:raise ValueError("Company missing "+key)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",c["id"]) or c["id"] in ids:raise ValueError("Invalid/duplicate company ID")
        ids.add(c["id"]);date.fromisoformat(c["last_verified"])
        if not source(c["verification_url"]) or not c["name"].strip():raise ValueError("Invalid company identity source")
        if any(x not in pmap for x in c["project_ids"]):raise ValueError("Unknown linked project "+c["id"])
        if any(x not in fmap for x in c["people_ids"]):raise ValueError("Unknown linked person "+c["id"])
        if any(x not in amap for x in c["article_urls"]):raise ValueError("Unknown linked article "+c["id"])
        active=[pmap[x] for x in c["project_ids"]]
        transactions=[t for t in funding if t["project_id"] in c["project_ids"]]
        transactions.sort(key=lambda t:t.get("announced_date") or "",reverse=True)
        commodities=sorted({x for p in active for x in p["commodities"]},key=str.lower)
        countries=sorted({p["country"] for p in active})
        rows.append({**c,"commodities":commodities,"project_countries":countries,
          "projects":[{"id":p["id"],"name":p["name"],"country":p["country"],"stage":p["stage"],
                       "source_url":p["source_url"]} for p in active],
          "funding":[{"id":t["id"],"project_id":t["project_id"],"funder":t["funder"],
                      "amount":t["amount"],"currency":t["currency"],"status":t["status"],
                      "announced_date":t.get("announced_date"),"source_url":t["source_url"]}
                     for t in transactions],
          "people":[{"id":fmap[x]["id"],"name":fmap[x]["name"],"designation":fmap[x]["designation"]}
                    for x in c["people_ids"]],
          "articles":[{"title":amap[x]["title"],"url":"../newspaper/"+x,"date":amap[x]["date"]}
                       for x in c["article_urls"]]})
    rows.sort(key=lambda c:c["name"].casefold())
    dst=OUT/"companies";dst.mkdir(parents=True,exist_ok=True)
    (dst/"companies.json").write_text(json.dumps({"schema_version":1,"companies":rows},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    payload=json.dumps(rows,ensure_ascii=False,separators=(",",":")).replace("<",r"\u003c")
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Company Directory | Sakariya Mining Intelligence</title>
<meta name="description" content="Search source-linked mining companies and connect their projects, financing, people and articles.">
<style>
:root{color-scheme:light;--o:#C7551B;--b:#41200E;--line:#dcccc1;--cream:#F5F3F0}
*{box-sizing:border-box}body{margin:0;background:var(--cream);font:14px/1.55 'Proxima Nova','Segoe UI',Arial,sans-serif;color:#25180f}
header{background:#020100;color:#fff;border-bottom:5px solid var(--o)}
header .head{padding:27px 20px;max-width:1200px;margin:auto}
.eyebrow{font-size:11px;letter-spacing:1.5px;color:#e6b292;font-weight:750}
h1{font:700 clamp(29px,4vw,44px)/1.12 Georgia,serif;margin:8px 0 4px}
header p{margin:0;color:#e0d1c5}
.wrap{max-width:1200px;margin:auto;padding:19px 18px 50px}
nav{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}
nav a{background:#fff;padding:9px 11px;border:1px solid var(--line);border-radius:6px;text-decoration:none;font-weight:700;color:var(--b)}
nav a:hover{background:#fff0e4}nav .active{border-color:var(--o);background:#fff3ea}
a{color:#8f390c;text-underline-offset:3px}
.intro{color:#6a564b;margin-bottom:17px}
.filters{display:grid;grid-template-columns:minmax(230px,2fr) repeat(3,minmax(130px,1fr)) auto;gap:9px;padding:14px;background:white;border:1px solid var(--line);border-radius:8px}
.filters label{display:grid;gap:4px;font-size:12px;color:var(--b);font-weight:750;min-width:0}
.filters :is(select,input){width:100%;min-width:0;padding:10px;background:white;color:#27160e;border:1px solid #bba897;border-radius:5px;font:inherit}
.filters button{background:#fff2e8;color:var(--b);font-weight:750;padding:10px;border:1px solid var(--line);border-radius:5px;cursor:pointer}
.meta{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:20px 0 11px}
.meta h2{font:700 22px Georgia,serif;color:var(--b);margin:0}.meta span{color:#68554b}
.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.company{background:white;padding:18px;border-radius:8px;border:1px solid var(--line);min-width:0;scroll-margin-top:15px}
.company h3{margin:0 0 6px;font:700 23px/1.2 Georgia,serif;color:var(--b)}
.sub{font-size:12px;color:#746056}.tags{display:flex;gap:5px;flex-wrap:wrap;margin:10px 0}
.tag{border:1px solid #e2b89c;background:#fff3e9;border-radius:14px;color:#73320e;padding:3px 8px;font-size:11px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:13px 0}
.stat{background:#faf5f0;border-radius:5px;padding:8px;text-align:center}
.stat strong{display:block;color:var(--b);font-size:20px}
.stat small{font-size:11px;color:#70594b}
details{border-top:1px solid var(--line);padding-top:9px;margin-top:8px}
summary{cursor:pointer;font-weight:750;color:#69310f}
details ul{padding-left:18px;margin:7px 0}li{margin:8px 0}
.foot{margin-top:12px;font-size:12px;color:#665144}
.empty{background:white;padding:25px;border:1px solid var(--line);border-radius:8px}
footer{text-align:center;background:#020100;color:#fff;padding:18px}
:focus-visible{outline:3px solid var(--o);outline-offset:2px}
@media(max-width:930px){.filters{grid-template-columns:repeat(2,minmax(0,1fr))}.filters label:first-child{grid-column:1/-1}.cards{grid-template-columns:1fr}}
@media(max-width:550px){.wrap{padding:12px}.filters label{grid-column:1/-1}.filters button{grid-column:1/-1}}
</style></head><body><header><div class="head"><div class="eyebrow">SAKARIYA MINES &amp; MINERALS · RESHAPING RESOURCES</div><h1>Company Directory</h1><p>Connect companies to projects, financing and industry people</p></div></header>
<main class="wrap">
<nav aria-label="Research directories"><a href="../">Source Directory</a><a href="../newspaper/">Newspaper</a>
<a href="../people/">People</a><a href="./" class="active">Companies</a><a href="../projects/">Projects</a><a href="../funding/">Funding</a>
<a href="https://www.sakariyamines.com/" target="_blank" rel="noopener noreferrer">Visit Sakariya ↗</a></nav>
<p class="intro">Company links are based on named public project disclosures, not inferred ownership or investment recommendations. Country is the verified reporting/home jurisdiction used for this record, not necessarily every operating country. Financing amounts are separate instruments and must not be summed as money received.</p>
<section class="filters" aria-label="Company search and filters">
<label>Search companies &amp; projects<input id="search" type="search" placeholder="Company, project, lender, commodity…"></label>
<label>Company country<select id="country"><option value="">All countries</option></select></label>
<label>Commodity<select id="commodity"><option value="">All commodities</option></select></label>
<label>Business activity<select id="sector"><option value="">All activities</option></select></label>
<button id="clear" type="button">Clear filters</button></section>
<div class="meta"><h2>Organizations &amp; Connections</h2><span id="count" aria-live="polite"></span></div>
<section id="results" class="cards" aria-label="Matching company profiles"></section><div id="empty" class="empty" hidden>No verified companies match these filters.</div>
</main><footer>SAKARIYA MINES &amp; MINERALS · PUBLIC COMPANY INTELLIGENCE · RESHAPING RESOURCES</footer>
<script type="application/json" id="company-data">'''+payload+'''</script>
<script>
(()=>{
const records=JSON.parse(document.getElementById('company-data').textContent);
const $=id=>document.getElementById(id),search=$('search'),country=$('country'),commodity=$('commodity'),sector=$('sector'),results=$('results');
const params=new URLSearchParams(location.search);
function el(tag,text,cls){const x=document.createElement(tag);if(cls)x.className=cls;if(text!==undefined)x.textContent=text;return x;}
function link(title,url){const a=el('a',title);a.href=url;if(url.startsWith('http')){a.target='_blank';a.rel='noopener noreferrer';}return a;}
function options(sel,values){for(const v of [...new Set(values.filter(Boolean))].sort((a,b)=>a.localeCompare(b))){let o=el('option',v);o.value=v;sel.add(o);}}
options(country,records.map(x=>x.headquarters_country));options(commodity,records.flatMap(x=>x.commodities));options(sector,records.map(x=>x.sector));
search.value=params.get('q')||'';country.value=params.get('country')||'';commodity.value=params.get('commodity')||'';sector.value=params.get('sector')||'';
const selected=params.get('company');
function money(f){const symbols={USD:'US$',AUD:'A$',CAD:'C$',EUR:'€',INR:'₹'};return (symbols[f.currency]||f.currency+' ')+f.amount.toLocaleString('en-US');}
function makeDetails(card,title,items,renderItem,expand){
 const details=el('details');details.open=expand;
 details.append(el('summary',title+' ('+items.length+')'));
 const list=el('ul');if(items.length){items.forEach(x=>{const li=el('li');renderItem(li,x);list.append(li);});}
 else{list.append(el('li','No verified linked records yet.','sub'));}
 details.append(list);card.append(details);
}
function renderCard(c){
 const card=el('article',undefined,'company');card.id='company-'+c.id;
 card.append(el('h3',c.name),el('div',c.sector+' · '+c.headquarters_country,'sub'));
 const tags=el('div',undefined,'tags');c.commodities.forEach(x=>{const tag=el('button',x,'tag');tag.type='button';tag.onclick=()=>{commodity.value=x;render();};tags.append(tag);});card.append(tags);
 const stats=el('div',undefined,'stats');for(const [n,label] of [[c.projects.length,'Projects'],[c.funding.length,'Funding events'],[c.people.length,'People']]){const box=el('div',undefined,'stat');box.append(el('strong',String(n)),el('small',label));stats.append(box);}card.append(stats);
 makeDetails(card,'Projects & plants',c.projects,(li,p)=>{li.append(link(p.name,'../projects/?project='+encodeURIComponent(p.id)),el('div',p.country+' · '+p.stage,'sub'));},selected===c.id);
 makeDetails(card,'Funding & finance',c.funding,(li,f)=>{li.append(link(money(f)+' · '+f.funder,'../funding/?project='+encodeURIComponent(f.project_id)),el('div',f.status+(f.announced_date?' · '+f.announced_date:''),'sub'));},false);
 makeDetails(card,'People',c.people,(li,p)=>{li.append(link(p.name,'../people/?person='+encodeURIComponent(p.id)),el('div',p.designation,'sub'));},false);
 makeDetails(card,'News',c.articles,(li,a)=>{li.append(link(a.title,a.url),el('div',a.date,'sub'));},false);
 const foot=el('div',undefined,'foot');foot.append(link('Verify company / project affiliation ↗',c.verification_url),el('div','Last reviewed: '+c.last_verified,'sub'));card.append(foot);
 return card;
}
function render(){
 const q=search.value.trim().toLowerCase(),co=country.value,cm=commodity.value,sec=sector.value;
 const list=records.filter(x=>(!co||x.headquarters_country===co)&&(!cm||x.commodities.includes(cm))&&(!sec||x.sector===sec)&&
  (!q||[x.name,x.sector,x.headquarters_country,...x.commodities,...x.project_countries,...x.projects.map(y=>y.name),...x.funding.map(y=>y.funder),...x.people.map(y=>y.name)].join(' ').toLowerCase().includes(q)));
 results.replaceChildren();list.forEach(x=>results.append(renderCard(x)));
 $('empty').hidden=list.length!==0;$('count').textContent=list.length+' of '+records.length+' verified companies';
 const v=new URLSearchParams();if(q)v.set('q',search.value);if(co)v.set('country',co);if(cm)v.set('commodity',cm);if(sec)v.set('sector',sec);
 history.replaceState(null,'',location.pathname+(v.toString()?'?'+v:'')+location.hash);
}
search.addEventListener('input',render);[country,commodity,sector].forEach(x=>x.addEventListener('change',render));
$('clear').onclick=()=>{search.value='';country.value='';commodity.value='';sector.value='';render();};render();
if(selected){const card=$('company-'+selected);if(card)card.scrollIntoView();}
})();
</script></body></html>'''
    (dst/"index.html").write_text(page,encoding="utf-8")
    print(f"Built Company Directory: {len(rows)} companies linked to {sum(len(c['projects']) for c in rows)} projects and {sum(len(c['funding']) for c in rows)} financing events.")
if __name__=="__main__":run()
