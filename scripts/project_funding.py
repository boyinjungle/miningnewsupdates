#!/usr/bin/env python3
"""Public project/plant and funding registries. No CMS, database or third-party dependencies."""
import json,html,re
from pathlib import Path
from datetime import date
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"_site"
PROJECT_FIELDS=("id","name","type","country","region","location","company","commodities","stage","summary","source_url","last_verified","news_articles")
FUND_FIELDS=("id","project_id","funder","funder_country","recipient","instrument","status","amount","currency","source_url","context","last_verified","disbursement_verified","disbursement_note")
def load(name,key):
    data=json.loads((ROOT/"data"/name).read_text(encoding="utf-8"))
    if data.get("schema_version")!=1 or not isinstance(data.get(key),list):raise ValueError(name+" invalid schema")
    return data[key]
def url(s):
    return isinstance(s,str) and urlparse(s).scheme in ("http","https") and bool(urlparse(s).netloc)
def validate(projects,funds):
    ids=set();fids=set()
    for p in projects:
        if any(k not in p for k in PROJECT_FIELDS):raise ValueError("Incomplete project: "+str(p.get("name")))
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",p["id"]) or p["id"] in ids:raise ValueError("Invalid/duplicate project ID")
        ids.add(p["id"])
        if not url(p["source_url"]) or not p["commodities"] or any(not isinstance(x,str) or not x.strip() for x in p["commodities"]):raise ValueError("Unverified project")
        date.fromisoformat(p["last_verified"])
    for f in funds:
        if any(k not in f for k in FUND_FIELDS):raise ValueError("Incomplete funding: "+str(f.get("id")))
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",f["id"]) or f["id"] in fids:raise ValueError("Invalid/duplicate funding ID")
        fids.add(f["id"])
        if f["project_id"] not in ids:raise ValueError("Funding refers to missing project: "+f["project_id"])
        if not url(f["source_url"]) or not isinstance(f["amount"],(int,float)) or f["amount"]<0:raise ValueError("Funding amount/source invalid")
        if not isinstance(f["disbursement_verified"],bool):raise ValueError("Funding disbursement field invalid")
        if f["status"] not in ("Indicative / non-binding","Selected / award not verified","Proposed / announced","Committed / signed","Closed financing","Disbursed / received","Cancelled / withdrawn"):
            raise ValueError("Unrecognized funding state")
        if f["disbursement_verified"] and f["status"]!="Disbursed / received":raise ValueError("Disbursement status contradictory")
        if f.get("announced_date"):date.fromisoformat(f["announced_date"])
        date.fromisoformat(f["last_verified"])
    # No silently mixing capital commitments with deposits / received funds.
    return True

STYLE=r"""<style>
:root{color-scheme:light;--cream:#F5F3F0;--ink:#22150d;--muted:#65534a;--line:#dbcfc5;--orange:#C7551B;--brown:#41200E}
*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font:14px/1.55 'Proxima Nova','Avenir Next','Segoe UI',Arial,sans-serif}a{color:#8e370e;text-underline-offset:3px}button,select,input{font:inherit}
header{background:#020100;color:white;border-bottom:5px solid var(--orange)}.head{max-width:1200px;margin:auto;padding:26px 22px}.eyebrow{font-size:11px;letter-spacing:1.5px;font-weight:800;color:#e8b08a}h1{font:700 clamp(28px,4vw,43px)/1.14 Georgia,serif;margin:8px 0 5px}header p{margin:0;color:#d9cec7}.container{max-width:1200px;margin:auto;padding:19px 18px 58px}.links{display:flex;gap:9px;flex-wrap:wrap;margin-bottom:15px}.links a{border:1px solid var(--line);border-radius:6px;padding:8px 12px;background:white;text-decoration:none;color:var(--brown);font-weight:750}.links a:hover,.links a.active{border-color:var(--orange);background:#fff0e2}.intro{color:var(--muted);margin:9px 0 16px;max-width:1000px}
.filters{display:grid;grid-template-columns:minmax(210px,2fr) repeat(3,minmax(135px,1fr)) auto;gap:9px;padding:13px;border:1px solid var(--line);border-radius:8px;background:#fff}
.filters label{font-size:12px;font-weight:750;color:var(--brown);display:grid;gap:4px;min-width:0}.filters select,.filters input{width:100%;min-width:0;padding:10px;border:1px solid #bba899;border-radius:5px;background:white;color:#25150d}.filters button{background:#fff5ee;color:#74320e;border:1px solid var(--line);border-radius:5px;font-weight:700;padding:10px}
.meta{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin:17px 0 12px}.meta h2{font:700 23px Georgia,serif;margin:0;color:var(--brown)}.meta span{color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.card{padding:18px;border-radius:8px;border:1px solid var(--line);background:#fff;min-width:0;scroll-margin-top:15px}.card h3{font:700 22px/1.2 Georgia,serif;margin:0 0 8px;color:var(--brown)}.sub{font-size:12px;color:var(--muted)}.card p{margin:9px 0 11px}.tags{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}.tag{display:inline-block;background:#fff0e6;border:1px solid #e2bea6;border-radius:15px;color:#773313;padding:3px 9px;font-size:11px;font-weight:650}.tags button{cursor:pointer}.status{display:inline-block;border:1px solid #c9ab95;background:#f7eee6;color:#623c28;border-radius:4px;padding:3px 7px;font:700 11px/1.5 'Proxima Nova',sans-serif}
details{border-top:1px solid var(--line);margin-top:12px;padding-top:10px}summary{cursor:pointer;font-weight:750;color:var(--brown)}.ledger{padding:11px 0;border-bottom:1px solid #eee3db}.ledger:last-child{border:0}.ledger h4{margin:0;font-size:14px;color:#41200e}.figure{font-weight:800;color:#9b3d10;font-size:17px}.note{border-left:3px solid var(--orange);padding-left:9px;color:var(--muted);font-size:12px}.empty{background:#fff;padding:25px;border:1px solid var(--line);border-radius:8px;color:var(--muted)}.footer{padding:20px;background:#020100;color:#f5f3f0;text-align:center;font-size:12px}a:focus-visible,button:focus-visible,select:focus-visible,input:focus-visible{outline:3px solid var(--orange);outline-offset:2px}
@media(max-width:950px){.filters{grid-template-columns:repeat(2,minmax(0,1fr))}.filters label:first-child{grid-column:1/-1}.cards{grid-template-columns:1fr}}
@media(max-width:540px){.container{padding:13px 11px 40px}.filters label{grid-column:1/-1}.filters button{grid-column:1/-1}}
</style>"""
def shell(kind, title, desc, payload):
    nav='''<nav class="links" aria-label="Sakariya research navigation">
<a href="../">Source Directory</a><a href="../newspaper/">Newspaper</a><a href="../people/">People</a>
<a href="../projects/" class="PROJECTACTIVE">Projects &amp; Plants</a><a href="../funding/" class="FUNDINGACTIVE">Funding Tracker</a>
<a href="https://www.sakariyamines.com/" target="_blank" rel="noopener noreferrer">Visit Sakariya ↗</a></nav>'''.replace('class="PROJECTACTIVE"','class="active"' if kind=="projects" else '').replace('class="FUNDINGACTIVE"','class="active"' if kind=="funding" else '')
    return ('''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="'''+html.escape(desc,quote=True)+'''"><title>'''+html.escape(title)+''' | Sakariya Mining Intelligence</title>'''+STYLE+'''</head><body>
<header><div class="head"><div class="eyebrow">SAKARIYA MINES &amp; MINERALS · RESHAPING RESOURCES</div>
<h1>'''+html.escape(title)+'''</h1><p>'''+html.escape(desc)+'''</p></div></header><main class="container">'''+nav+'''
<p class="intro">Source-verified public records, with original links and dated disclosures. <strong>Announced, non-binding, closed and disbursed financing are not equivalent.</strong> Project and transaction status may have changed since the cited documents.</p>
<section class="filters" aria-label="Directory search and filters">
<label>Search <input id="q" type="search" placeholder="Project, investor, country, mineral…"></label>
<label>Country <select id="country"><option value="">All countries</option></select></label>
<label>Commodity <select id="commodity"><option value="">All commodities</option></select></label>
<label>'''+("Facility type" if kind=="projects" else "Funding status")+''' <select id="type"><option value="">All types</option></select></label>
<button id="clear" type="button">Clear filters</button></section>
<div class="meta"><h2>'''+("Projects and facilities" if kind=="projects" else "Funding and investment events")+'''</h2><span id="count" aria-live="polite"></span></div>
<div class="cards" id="results"></div><div class="empty" id="empty" hidden>No matching verified records. New records are added after confirming an authoritative public disclosure.</div>
</main><footer class="footer">SAKARIYA MINES &amp; MINERALS · PUBLIC RESEARCH DIRECTORY · RESHAPING RESOURCES</footer>
<script type="application/json" id="registry">'''+json.dumps(payload,ensure_ascii=False,separators=(",",":")).replace("<",r"\u003c")+'''</script>
<script>''')
JS= r"""
(()=>{
const mode=MODE, data=JSON.parse(document.getElementById('registry').textContent);
const $=id=>document.getElementById(id), q=$('q'),country=$('country'),commodity=$('commodity'),type=$('type'),results=$('results');
const params=new URLSearchParams(location.search);
function E(tag,cls,txt){const x=document.createElement(tag);if(cls)x.className=cls;if(txt!==undefined)x.textContent=txt;return x;}
function link(text,url){const a=E('a','',text);a.href=url;if(url.startsWith('http')){a.target='_blank';a.rel='noopener noreferrer';}return a;}
function unique(values){return [...new Set(values.filter(Boolean))].sort((a,b)=>a.localeCompare(b));}
function options(select,values){for(const value of unique(values)){const x=E('option','',value);x.value=value;select.add(x);}}
const projects=mode==='projects'?data.projects:data.projects;
const funds=data.funding;
const byId=Object.fromEntries(projects.map(p=>[p.id,p]));
const list=mode==='projects'?projects:funds;
const projectFor=f=>byId[f.project_id];
options(country,list.map(x=>mode==='projects'?x.country:projectFor(x).country));
options(commodity,list.flatMap(x=>mode==='projects'?x.commodities:projectFor(x).commodities));
options(type,list.map(x=>mode==='projects'?x.type:x.status));
q.value=params.get('q')||'';country.value=params.get('country')||'';commodity.value=params.get('commodity')||'';type.value=params.get('type')||'';
const selected=params.get(mode==='projects'?'project':'funding');
function money(t){const symbol=t.currency==='USD'?'US$':t.currency==='AUD'?'A$':t.currency+' ';return symbol+(t.amount>=1e9?(t.amount/1e9).toLocaleString('en-US',{maximumFractionDigits:2})+'bn':t.amount>=1e6?(t.amount/1e6).toLocaleString('en-US',{maximumFractionDigits:2})+'m':t.amount.toLocaleString('en-US'));}
function addTags(card,values){const row=E('div','tags');values.forEach(v=>{const b=E('button','tag',v);b.type='button';b.onclick=()=>{commodity.value=v;render();};row.append(b)});card.append(row);}
function fundingRow(t){const div=E('div','ledger');div.append(E('div','figure',money(t)),E('h4','',t.funder),E('div','sub',t.instrument+' · '+t.status+(t.announced_date?' · '+t.announced_date:'')));
 div.append(E('p','',t.context),E('p','note',t.disbursement_note));div.append(link('Original financing source ↗',t.source_url));return div;}
function drawProject(p){
 const card=E('article','card');card.id='project-'+p.id;
 card.append(E('h3','',p.name),E('div','sub',p.type+' · '+p.country+' · '+p.location),E('div','sub',p.company),E('span','status',p.stage),E('p','',p.summary));addTags(card,p.commodities);
 card.append(E('div','sub','Verified: '+p.last_verified+' · '+p.status_as_of));
 card.append(link('Project disclosure ↗',p.source_url));
 const tx=funds.filter(x=>x.project_id===p.id),details=E('details');details.open=selected===p.id;
 details.append(E('summary','',tx.length+' funding event'+(tx.length===1?'':'s')+' (not cumulative cash received)'));
 if(tx.length)tx.forEach(x=>details.append(fundingRow(x)));
 else details.append(E('p','sub','No independently verified funding transaction recorded yet.'));
 card.append(details);
 const foot=E('p','sub');foot.append(link('Funding tracker for this project ↗','../funding/?project='+encodeURIComponent(p.id)));card.append(foot);
 const notes=E('p','note',p.source_note||'');if(p.source_note)card.append(notes);
 if(p.news_articles.length){const n=E('div','sub','Newspaper: ');p.news_articles.forEach(x=>{n.append(link(x.split('#')[0].replace('.html','')+' ↗','../newspaper/'+x),document.createTextNode(' '));});card.append(n);}
 return card;
}
function drawFunding(t){
 const p=projectFor(t),card=E('article','card');card.id='funding-'+t.id;
 card.append(E('div','figure',money(t)),E('h3','',p.name),E('div','sub',p.country+' · '+p.commodities.join(', ')));
 card.append(E('div','sub','Funder: '+t.funder+' · '+t.funder_country));
 card.append(E('div','sub','Recipient: '+t.recipient),E('div','sub','Instrument: '+t.instrument+(t.announced_date?' · '+t.announced_date:'')));
 card.append(E('span','status',t.status),E('p','',t.context),E('p','note',t.disbursement_note));
 const links=E('p');links.append(link('Original disclosure ↗',t.source_url),document.createTextNode(' · '),link('Project profile ↗','../projects/?project='+encodeURIComponent(t.project_id)));card.append(links);
 return card;
}
function render(){
 const term=q.value.trim().toLowerCase(),c=country.value,m=commodity.value,t=type.value,projectFilter=params.get('project');
 const found=list.filter(x=>{const p=mode==='projects'?x:projectFor(x);const all=mode==='projects'?[p.name,p.company,p.location,p.country,p.stage,p.summary,...p.commodities]:[x.funder,x.funder_country,x.recipient,x.instrument,x.status,x.context,p.name,p.country,p.company,...p.commodities];
 return (!c||p.country===c)&&(!m||p.commodities.includes(m))&&(!t||(mode==='projects'?p.type===t:x.status===t))&&(!term||all.join(' ').toLowerCase().includes(term))&&!(mode==='funding'&&projectFilter&&x.project_id!==projectFilter);
 });
 results.replaceChildren();found.forEach(x=>results.append(mode==='projects'?drawProject(x):drawFunding(x)));
 $('empty').hidden=found.length>0;$('count').textContent=found.length+' record'+(found.length===1?'':'s');
 const v=new URLSearchParams();if(term)v.set('q',q.value);if(c)v.set('country',c);if(m)v.set('commodity',m);if(t)v.set('type',t);if(projectFilter&&mode==='funding')v.set('project',projectFilter);
 history.replaceState(null,'',location.pathname+(v.toString()?'?'+v:'')+location.hash);
}
q.addEventListener('input',render);[country,commodity,type].forEach(n=>n.addEventListener('change',render));
$('clear').onclick=()=>{q.value='';country.value='';commodity.value='';type.value='';if(mode==='funding')history.replaceState(null,'',location.pathname);render();};render();
const target=selected?$((mode==='projects'?'project-':'funding-')+selected):null;if(target)target.scrollIntoView();
})();
"""
def main():
    projects=load("projects.json","projects");funds=load("funding.json","transactions")
    validate(projects,funds)
    for kind in ("projects","funding"):
        dst=OUT/kind;dst.mkdir(parents=True,exist_ok=True)
        data={"projects":projects,"funding":funds}
        (dst/"index.html").write_text(shell(kind,"Project & Plant Directory" if kind=="projects" else "Funding & Investment Directory",
          "Global mine, processing and battery supply-chain projects" if kind=="projects" else "Government, institutional and private funding by project",data)+
          JS.replace('MODE',"'"+kind+"'")+"</script></body></html>",encoding="utf-8")
        (dst/"register.json").write_text(json.dumps({"schema_version":1,**data},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Built {len(projects)} verified projects and {len(funds)} funding events with linked project IDs.")
if __name__=="__main__":main()
