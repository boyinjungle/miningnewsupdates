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
    ("critical-minerals", "Critical Minerals", "◇", "Exploration, supply chains, policy and markets"),
    ("exploration", "Exploration & Geology", "⌁", "Drilling, resources and technology"),
    ("finance", "Finance & Investment", "▤", "Funding, investors and ownership"),
    ("offtake", "Offtake & Downstream", "▥", "Buyers, anodes, steel and refractories"),
    ("policy", "Mining Policy & Regulation", "⚖", "Law, licences, trade and compliance"),
    ("tanzania", "Tanzania & East Africa", "◎", "Regional projects and infrastructure"),
    ("india", "India Mining & Industry", "▦", "India exploration and critical minerals"),
    ("competitors", "Projects & Competitors", "◉", "Junior miners and project milestones"),
    ("opportunities", "Deals & Geo Services", "↗", "Partnerships, tenders and contracts"),
    ("global-opportunities", "Global Mining Opportunities", "🌐", "Africa beyond Tanzania and opportunities worldwide"),
    ("social", "Natural Graphite Social Pulse", "◌", "LinkedIn, X, Reddit and forums"),
    ("events", "Conferences & Events", "▣", "Industry events and deadlines"),
]
NAMES = {a:b for a,b,_,_ in TOPICS}
PATTERNS = {
  "gold": r"\bgold\b|\bbullion\b|\bjomu\b|\bau\b",
  "graphite": r"\bgraphite\b|\bflake\b|\bspheri[sz]|\bsynthetic anode\b",
  "critical-minerals": r"\bcritical mineral[s]?\b|\bstrategic mineral[s]?\b|\brare earth[s]?\b|\bREEs?\b|\b(?:lithium|nickel|cobalt|copper|manganese|tungsten|vanadium|tantalum|niobium|gallium|germanium|indium|tellurium|antimony|beryllium|titanium|zirconium|hafnium|scandium|platinum group|PGEs?|potash|phosphate)\b|\b(?:neodymium|praseodymium|dysprosium|terbium|NdPr)\b",
  "exploration": r"\bexplor|\bgeolog|\bdrill|\bmineralis|\bresource\b|\breserve\b|\bassay|\bgeophys|\bmetallurg|\bJORC\b|\bNI 43-101\b",
  "finance": r"\binvest|\bfinanc|\bfund|\bequity\b|\bdebt\b|\bIPO\b|\bcapital\b|\bJV\b|\bjoint venture\b|\bM&A\b",
  "offtake": r"\bofftake\b|\bbuyer\b|\bdownstream\b|\banode\b|\bsteel\b|\brefractor|\bbattery\b|\bpurif|\bprocessing\b|\bqualification\b",
  "policy": r"\bpolic|\bregulat|\bexport\b|\broyalt|\blicen[cs]|\bcompliance\b|\bgovernment\b|\bministry\b|\bpermit\b|\bstockpil",
  "tanzania": r"\btanzania\b|\btanga\b|\blindi\b|\bgeita\b|\bkahama\b|\bnzega\b|\beast africa\b|\bdar es salaam\b",
  "india": r"\bindia\b|\bindian\b|\bchhattisgarh\b|\bNMET\b|\bGSI\b|\bdeccan\b",
  "competitors": r"\bcompetitor\b|\bjunior\b|\bproject\b|\boperator\b|\bdevelop|\bmilestone\b|\bplant\b|\bconstruction\b|\bcommission",
  "opportunities": r"\btender\b|\bprocure|\bcontract\b|\bpartner|\bfarm-in\b|\bservices\b|\bsurvey\b|\bdeal\b",
  "global-opportunities": r"\bglobal mining opportunit|\bmineral asset sale\b|\bfarm-in opportunit|\bprospecting licence auction\b|\bmineral block auction\b|\bexploration tender\b|\binternational mining tender\b",
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
            cats = ([x for x in cats if x in ("critical-minerals", "graphite", "gold")] + [x for x in cats if x not in ("critical-minerals", "graphite", "gold", "competitors", "opportunities")])[:6] or cats[:5]
        if not cats: cats = ["exploration"]
    tags = [s.strip() for s in attr(attrs,"data-tags").split(",") if s.strip()]
    if not tags:
        tags = [NAMES[k] for k in cats[:4]]
        for tag,pat in [("Tanga",r"\btanga\b"),("Jomu",r"\bjomu\b"),("Tanzania",r"\btanzania\b"),("India",r"\bindia\b"),("Natural Flake",r"\bnatural flake\b"),("Offtake",r"\bofftake\b"),("Lithium-ion Batteries",r"\bbatter(y|ies)\b"),("Rare Earths",r"\brare earth|\bREEs?\b"),("Lithium",r"\blithium\b"),("Nickel",r"\bnickel\b"),("Copper",r"\bcopper\b"),("Cobalt",r"\bcobalt\b"),("Manganese",r"\bmanganese\b"),("Critical Minerals",r"\bcritical minerals?\b")]:
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
            heading=re.match(r"\s*<strong>(.*?)</strong>\s*:?\s*",p_inner,re.I|re.S)
            if not heading: return p.group(0)
            title=plain(heading.group(1)).rstrip(":")
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

</style>""")
    annotated=annotated.replace("</head>",css+"</head>",1)
    # Cross-site navigation is assembled at build time so it appears in every
    # historic and future edition without modifying the original news content.
    crossnav = ('<nav class="sakariya-site-nav" aria-label="Sakariya websites">'
                '<a href="../">Source Intelligence Directory</a>'
                '<a href="./">Newspaper Archive</a>'
                '<a href="index.html#topics">Browse Topics</a>'
                '<a href="index.html#articles">Search All News</a><a href="../people/">People Directory</a><a href="../companies/">Company Directory</a><a href="../projects/">Projects &amp; Plants</a><a href="../funding/">Funding Directory</a>'
                '</nav>')
    navcss = ("""
<style id="sakariya-site-nav-styles">
.sakariya-site-nav{display:flex;align-items:center;flex-wrap:wrap;gap:9px;
 padding:12px max(16px,calc((100vw - 1120px)/2));background:#F5F3F0;
 border-bottom:1px solid #d7c7ba;font:600 13px/1.4 'Proxima Nova',Arial,sans-serif}
.sakariya-site-nav a{display:inline-block;padding:8px 12px;background:#fff;color:#41200E;
 border:1px solid #d7c7ba;border-radius:6px;text-decoration:none}
.sakariya-site-nav a:hover,.sakariya-site-nav a:focus-visible{border-color:#C7551B;
 background:#fff1e7;color:#72310f;outline-offset:2px}
@media(max-width:580px){.sakariya-site-nav{padding:10px 12px;gap:6px}
 .sakariya-site-nav a{flex:1 1 42%;text-align:center;padding:8px 6px;font-size:12px}}
</style>""")
    annotated=annotated.replace("</head>",navcss+"</head>",1)
    if not re.search(r'<nav\b[^>]*class=["\x27][^"\x27]*sakariya-site-nav',annotated,re.I):
        if re.search(r"</header\s*>",annotated,re.I):
            annotated=re.sub(r"</header\s*>",lambda m:m.group(0)+crossnav,annotated,count=1,flags=re.I)
        else:
            annotated=re.sub(r"<body([^>]*)>",lambda m:m.group(0)+crossnav,annotated,count=1,flags=re.I)
    # Within-edition navigation: tag/topic filters list article links that jump
    # directly to their original anchors. Other tag chips still open all dates.
    jump_items = [{"title":x["title"],"anchor":x["url"].split("#")[-1],
                   "tags":x["tags"],"topics":x["topics"]} for x in records]
    jump_json = json.dumps(jump_items,ensure_ascii=False).replace("<",r"\u003c")
    topic_labels = [(key,label) for key,label,_,_ in TOPICS
                    if any(key in item["topics"] for item in records)]
    tag_values = sorted({t for item in records for t in item["tags"]},key=str.lower)
    topic_options = "".join('<option value="'+html.escape(key,quote=True)+'">'+
                            html.escape(label)+'</option>' for key,label in topic_labels)
    tag_options = "".join('<option value="'+html.escape(tag,quote=True)+'">'+
                          html.escape(tag)+'</option>' for tag in tag_values)
    jump = ("""
<section class="issue-jump" id="jump-to-news" aria-label="Jump to news by topic or tag">
<div class="issue-jump-head"><strong>Find an article in this edition</strong>
<a href="index.html#articles">Search all dates ↗</a></div>
<div class="issue-jump-controls">
<label>Topic <select id="issue-topic"><option value="">All topics</option>""" +
            topic_options + """</select></label>
<label>Tag <select id="issue-tag"><option value="">All tags</option>""" +
            tag_options + """</select></label>
<label class="issue-query-label">Headline search
<input id="issue-query" type="search" placeholder="Search this edition…"></label>
<button id="issue-clear" type="button">Clear</button></div>
<div class="issue-jump-picker"><label for="issue-story-select">Jump to article</label>
<select id="issue-story-select" aria-describedby="issue-jump-count"><option value="">Select a headline…</option></select>
<div class="issue-jump-status" id="issue-jump-count" aria-live="polite"></div>
</div></section>""" )
    jumpcss = """
<style id="sakariya-issue-jump-styles">
.issue-jump{max-width:1120px;margin:18px auto 10px;padding:16px 18px;
 background:#fff;border:1px solid #dacbbf;border-left:4px solid #C7551B;
 border-radius:6px;color:#281b12;font:14px/1.45 'Proxima Nova',Arial,sans-serif}
.issue-jump-head{display:flex;gap:12px;justify-content:space-between;align-items:center;flex-wrap:wrap}
.issue-jump-head strong{font-size:17px;color:#41200E}
.issue-jump-head a{color:#914014;font-weight:650}
.issue-jump-controls{display:flex;flex-wrap:wrap;align-items:end;gap:10px;margin:12px 0}
.issue-jump-controls label{display:flex;flex-direction:column;gap:4px;flex:1 1 150px;font-size:12px;font-weight:700;color:#41200E}
.issue-jump-controls select,.issue-jump-controls input{width:100%;min-width:0;border:1px solid #bba99c;border-radius:5px;
 background:#fff;color:#21140e;padding:8px 9px;font:14px/1.4 'Proxima Nova',Arial,sans-serif}
.issue-jump-controls button{padding:9px 14px;border:1px solid #ae8b76;background:#F5F3F0;
 color:#41200E;border-radius:5px;font-weight:650}
.issue-jump-status{color:#6d5344;font-size:12px}
.issue-jump-picker{display:flex;align-items:center;gap:12px;padding-top:7px;border-top:1px solid #e5d7cd;flex-wrap:wrap}
.issue-jump-picker label{font-weight:700;color:#41200E;white-space:nowrap}
.issue-jump-picker select{flex:1 1 330px;min-width:0;border:1px solid #bba99c;border-radius:5px;background:#fff;color:#21140e;padding:10px 11px;font:14px/1.4 'Proxima Nova',Arial,sans-serif}
.issue-jump-picker select:disabled{background:#eee9e4;color:#6c625c}
.issue-jump-status{margin:0;white-space:nowrap}
.issue-jump-picker select:focus-visible{outline:3px solid #C7551B;outline-offset:2px}
.issue-jump select:focus-visible,.issue-jump input:focus-visible,.issue-jump a:focus-visible,
.issue-jump button:focus-visible{outline:3px solid #C7551B;outline-offset:2px}
@media(max-width:700px){.issue-jump{margin:12px;padding:13px}.issue-jump-picker{align-items:stretch}.issue-jump-picker select{flex-basis:100%}
.issue-jump-controls label{flex-basis:44%}.issue-jump-controls .issue-query-label{flex-basis:100%}}
.back-to-tags{position:fixed;right:clamp(14px,3vw,30px);bottom:calc(18px + env(safe-area-inset-bottom,0px));z-index:1000;display:inline-flex;align-items:center;gap:8px;border:2px solid #fff;box-shadow:0 3px 15px #41200e40;background:#C7551B;color:#fff!important;border-radius:30px;padding:11px 16px;text-decoration:none!important;font:750 13px/1.3 'Proxima Nova',Arial,sans-serif;opacity:0;pointer-events:none;transform:translateY(10px);transition:opacity .18s ease,transform .18s ease}
.back-to-tags.is-visible{opacity:1;pointer-events:auto;transform:translateY(0)}
.back-to-tags:hover,.back-to-tags:focus-visible{background:#41200E;color:#fff!important;outline:3px solid #C7551B;outline-offset:2px}
.back-to-tags svg{width:18px;height:18px;flex-shrink:0}
#jump-to-news{scroll-margin-top:12px}
@media(max-width:540px){.back-to-tags{right:12px;bottom:calc(14px + env(safe-area-inset-bottom,0px));padding:10px 13px}}
@media(prefers-reduced-motion:reduce){.back-to-tags{transition:none}}
@media print{.issue-jump,.back-to-tags{display:none}}
</style>"""
    jumpscript = """<script type="application/json" id="issue-story-data">""" + jump_json + """</script>
<script>
(()=>{
const data=JSON.parse(document.getElementById('issue-story-data').textContent);
const topic=document.getElementById('issue-topic'),tag=document.getElementById('issue-tag');
const query=document.getElementById('issue-query'),picker=document.getElementById('issue-story-select');
const count=document.getElementById('issue-jump-count');
const allTopics=[...topic.options].map(x=>({value:x.value,label:x.textContent}));
const allTags=[...tag.options].map(x=>({value:x.value,label:x.textContent}));
const makeOptions=(select,all,allowed)=>{
 const previous=select.value;
 select.replaceChildren();
 for(const item of all){
   if(item.value&&!allowed.has(item.value))continue;
   const opt=document.createElement('option');opt.value=item.value;opt.textContent=item.label;
   select.append(opt);
 }
 select.value=allowed.has(previous)?previous:'';
};
const filter=()=>{
 let t=topic.value,g=tag.value,q=query.value.toLocaleLowerCase().trim();
 const matchingTopic=data.filter(x=>(!g||x.tags.includes(g))&&(!q||[x.title,...x.tags].join(' ').toLocaleLowerCase().includes(q)));
 makeOptions(topic,allTopics,new Set(matchingTopic.flatMap(x=>x.topics)));
 t=topic.value;
 const matchingTags=data.filter(x=>(!t||x.topics.includes(t))&&(!q||[x.title,...x.tags].join(' ').toLocaleLowerCase().includes(q)));
 makeOptions(tag,allTags,new Set(matchingTags.flatMap(x=>x.tags)));
 g=tag.value;
 const subset=data.filter(item=>(!t||item.topics.includes(t))&&(!g||item.tags.includes(g))
   &&(!q||[item.title,...item.tags].join(' ').toLocaleLowerCase().includes(q)));
 picker.replaceChildren();
 const placeholder=document.createElement('option');
 placeholder.value='';placeholder.textContent=subset.length?'Select a headline…':'No matching articles';
 picker.append(placeholder);
 subset.forEach(item=>{
  const opt=document.createElement('option');
  opt.value=item.anchor;opt.textContent=item.title;picker.append(opt);
 });
 picker.disabled=subset.length===0;
 count.textContent=subset.length+' matching article'+(subset.length===1?'':'s');
};
[topic,tag].forEach(x=>x.addEventListener('change',filter));
query.addEventListener('input',filter);
picker.addEventListener('change',()=>{
 if(!picker.value)return;
 const target=document.getElementById(picker.value);
 if(target){target.scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});history.replaceState(null,'','#'+encodeURIComponent(picker.value));}
});
document.getElementById('issue-clear').addEventListener('click',()=>{
 topic.value='';tag.value='';query.value='';filter();
});
filter();
})();
</script>"""
    annotated=annotated.replace("</head>",jumpcss+"</head>",1)
    if re.search(r"<main\b[^>]*>",annotated,re.I):
        annotated=re.sub(r"<main\b[^>]*>",lambda m:m.group(0)+jump,annotated,count=1,flags=re.I)
    else:
        annotated=re.sub(r"</nav\s*>",lambda m:m.group(0)+jump,annotated,count=1,flags=re.I)
    # Fixed return-to-filters action appears after scrolling into the articles.
    back_link = ('<a href="#jump-to-news" class="back-to-tags" id="back-to-tags" '
                 'aria-label="Go to top of newspaper" title="Go to top">'
                 '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                 'stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round" '
                 'aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>'
                 '<span>Go to top</span></a>')
    back_script = """<script>
(()=>{
 const action=document.getElementById('back-to-tags');
 const filters=document.getElementById('jump-to-news');
 if(!action||!filters)return;
 const refresh=()=>{
   const box=filters.getBoundingClientRect();
   const show=box.bottom<80;
   action.classList.toggle('is-visible',show);
   action.setAttribute('aria-hidden',String(!show));
   action.tabIndex=show?0:-1;
 };
 window.addEventListener('scroll',refresh,{passive:true});
 window.addEventListener('resize',refresh);
 refresh();
 action.addEventListener('click',event=>{
  if(window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  event.preventDefault();
  filters.scrollIntoView({behavior:'smooth',block:'start'});
  history.replaceState(null,'','#jump-to-news');
 });
})();
</script>"""
    # Editorial brand bridge: visitors sharing public news can discover the
    # company's official website, without confusing reported news with an ad.
    brandcss = """
<style id="sakariya-brand-bridge-style">
:root{--brand-orange:#C7551B}
.sakariya-brand-bridge{max-width:1120px;margin:14px auto 18px;padding:12px 18px;
 background:#fffaf5;border:1px solid #ddc9bb;border-radius:8px;display:flex;
 align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;
 color:#41200E;font:14px/1.5 'Proxima Nova',Arial,sans-serif}
.sakariya-brand-bridge .brand-name{display:block;font-weight:800;font-size:15px;color:#41200E}
.sakariya-brand-bridge .brand-desc{font-size:12px;color:#735949}
.sakariya-brand-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.sakariya-brand-actions a,.sakariya-brand-actions button{border:1px solid #C7551B;border-radius:6px;
 padding:9px 12px;text-decoration:none;font:700 13px/1.35 'Proxima Nova',Arial,sans-serif;cursor:pointer}
.sakariya-brand-actions a{background:#C7551B;color:#fff}
.sakariya-brand-actions a:hover,.sakariya-brand-actions a:focus-visible{background:#41200E;border-color:#41200E;color:#fff}
.sakariya-brand-actions button{background:#fff;color:#80350e}
.sakariya-brand-actions button:hover,.sakariya-brand-actions button:focus-visible{background:#fff0e4}
.sakariya-brand-actions :is(a,button):focus-visible{outline:3px solid #C7551B;outline-offset:2px}
.sakariya-brand-outro{max-width:1120px;margin:28px auto 38px;border-left:4px solid #C7551B;
 border-radius:8px;background:#fff;padding:20px 22px;box-shadow:0 1px 4px #41200e12;
 color:#41200E;font:15px/1.6 'Proxima Nova',Arial,sans-serif}
.sakariya-brand-outro h2{border:0!important;padding:0!important;margin:0 0 6px!important;
 font:700 24px/1.2 Georgia,serif!important}
.sakariya-brand-outro p{margin:6px 0 14px}
.sakariya-brand-outro .brand-desc{font-size:13px;color:#685349}
.sakariya-reading-progress{position:fixed;top:0;left:0;height:3px;width:0;z-index:1050;
 background:#C7551B;pointer-events:none}
.sakariya-section-symbol{font:normal 20px/1 sans-serif;margin-right:9px;vertical-align:baseline}
.sakariya-share-status{font-size:12px;min-height:1em;color:#41200E}
@media(max-width:750px){.sakariya-brand-bridge{margin:12px;padding:12px}
.sakariya-brand-outro{margin:22px 12px;padding:16px}.sakariya-brand-actions{width:100%}
.sakariya-brand-actions a,.sakariya-brand-actions button{flex:1;text-align:center}}
@media print{.sakariya-brand-bridge,.sakariya-reading-progress{display:none}}
</style>"""
    topbridge = ("""
<aside class="sakariya-brand-bridge" aria-label="Explore Sakariya Mines and Minerals">
<div><span class="brand-name">Explore Sakariya Mines &amp; Minerals</span>
<span class="brand-desc">Gold, graphite and mineral exploration · Reshaping Resources</span></div>
<div class="sakariya-brand-actions">
<a href="https://www.sakariyamines.com/" target="_blank" rel="noopener noreferrer">Visit Sakariya ↗</a>
<button type="button" class="sakariya-share-news" aria-label="Share this newspaper">↗ Share edition</button>
</div></aside>""")
    outro = ("""
<aside class="sakariya-brand-outro" aria-label="About Sakariya">
<div class="brand-desc">FROM THE PUBLISHER · SAKARIYA MINES &amp; MINERALS</div>
<h2>Curious about the exploration work behind the news?</h2>
<p>Explore Sakariya's gold and graphite projects, technical approach and partnership opportunities.</p>
<div class="sakariya-brand-actions">
<a href="https://www.sakariyamines.com/" target="_blank" rel="noopener noreferrer">Explore our projects ↗</a>
<a href="https://www.sakariyamines.com/contact" target="_blank" rel="noopener noreferrer">Contact Sakariya ↗</a>
<button type="button" class="sakariya-share-news">↗ Share this edition</button>
</div><div class="sakariya-share-status" role="status" aria-live="polite"></div></aside>""")
    # The archive builder operates on the published copy only, never the
    # underlying editorial source saved to the repository.
    annotated=annotated.replace("</head>",brandcss+"</head>",1)
    if "</header>" in annotated:
        annotated=annotated.replace("</header>","</header>"+topbridge,1)
    if "</main>" in annotated:
        annotated=annotated.replace("</main>",outro+"</main>",1)
    else:
        annotated=annotated.replace("</footer>",outro+"</footer>",1)
    # Search engine and social share previews link to the source edition.
    description=("Sakariya Mining & Graphite Daily | "+day+
                 " — gold, graphite, critical minerals and global mining intelligence.")
    share_meta=('<meta name="description" content="'+html.escape(description,quote=True)+'">'
      '<meta property="og:type" content="article">'
      '<meta property="og:title" content="Sakariya Mining &amp; Graphite Daily — '+day+'">'
      '<meta property="og:description" content="'+html.escape(description,quote=True)+'">'
      '<meta property="og:url" content="https://boyinjungle.github.io/miningnewsupdates/newspaper/'+day+'.html">'
      '<meta name="twitter:card" content="summary">')
    annotated=annotated.replace("</head>",share_meta+"</head>",1)
    # Section symbols are deliberately small and limited to navigation headings.
    # Do not add fabricated photos or visually dominate financial reporting.
    icons={
       "MAJOR NEWS UPDATES":"📰","WORLD":"🌐","INDIA":"🇮🇳",
       "TANZANIA / EAST AFRICA":"🌍","Markets & technical watch":"📈",
       "Business & investment intelligence":"🤝",
       "Natural Graphite Social Pulse | Last 24 Hours":"💬",
       "Critical Minerals Intelligence":"💎",
       "GLOBAL MINING OPPORTUNITIES — AFRICA & OTHER CONTINENTS":"🧭",
       "Today's actionable intelligence":"✓",
       "Research & verification notes":"📋",
       "WEEKLY DEEP DIVE":"🔎"}
    def adorn_heading(m):
        raw=m.group(2)
        text_title=plain(raw)
        symbol=icons.get(text_title)
        if not symbol:return m.group(0)
        return m.group(1)+'<span class="sakariya-section-symbol" aria-hidden="true">'+symbol+'</span>'+raw+m.group(3)
    annotated=re.sub(r'(<h2\b[^>]*>)(.*?)(</h2>)',adorn_heading,annotated,flags=re.I|re.S)
    interactions = """<div class="sakariya-reading-progress" id="sakariya-reading-progress" aria-hidden="true"></div>
<script>
(()=>{
 const bar=document.getElementById('sakariya-reading-progress');
 const update=()=>{
  if(!bar)return;
  const height=document.documentElement.scrollHeight-window.innerHeight;
  const pct=height>0?Math.max(0,Math.min(100,window.scrollY/height*100)):0;
  bar.style.width=pct+'%';
 };
 window.addEventListener('scroll',update,{passive:true});
 window.addEventListener('resize',update);
 update();
 document.querySelectorAll('.sakariya-share-news').forEach(button=>{
  button.addEventListener('click',async()=>{
   const url=location.href.split('#')[0];
   const title=document.title;
   try{
    if(navigator.share){await navigator.share({title,url});return;}
    if(navigator.clipboard&&window.isSecureContext){
      await navigator.clipboard.writeText(url);
      button.textContent='✓ Link copied';
      setTimeout(()=>button.textContent='↗ Share edition',2500);
      return;
    }
    window.prompt('Copy the newspaper link:',url);
   }catch(error){if(error.name!=='AbortError')window.prompt('Copy the newspaper link:',url);}
  });
 });
})();
</script>"""
    annotated=annotated.replace("</body>",interactions+"</body>",1)
    annotated=annotated.replace("</body>",back_link+jumpscript+back_script+"</body>",1)
    return annotated,records

def render_archive(records,issues):
    payload=json.dumps(records,ensure_ascii=False,separators=(",",":")).replace("<",r"\u003c")
    tiles="".join('<button class="topic-card" type="button" data-topic="'+key+'" aria-pressed="false"><span class="topic-icon" aria-hidden="true">'+icon+'</span><span><strong>'+html.escape(name)+'</strong><small>'+html.escape(desc)+'</small></span><b class="count" id="count-'+key+'">0</b></button>' for key,name,icon,desc in TOPICS)
    date_links="".join('<tr data-edition-date="'+html.escape(i["date"],quote=True)+'"><td>'+html.escape(i["date"])+'</td><td><a href="'+html.escape(i["date"])+'.html">'+html.escape(i.get("title",i["date"]))+'</a></td><td>'+html.escape(i.get("description",""))+'</td></tr>' for i in issues)
    latest=max(issues,key=lambda i:i["date"]) if issues else None
    latest_banner=('<aside class="latest-edition" aria-label="Latest published newspaper">'
                   '<div><span class="latest-eyebrow">📰 LATEST PUBLISHED EDITION</span>'
                   '<strong>'+html.escape(latest.get("title",latest["date"]))+'</strong>'
                   '<small>Published '+html.escape(latest["date"])+' (IST) · '
                   +html.escape(latest.get("description",""))+'</small></div>'
                   '<a href="'+html.escape(latest["date"],quote=True)+'.html">Read latest newspaper ↗</a>'
                   '</aside>') if latest else ''

    return """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Search every Sakariya mining newspaper article by topic, tag, keyword or date"><title>Sakariya Mining Daily | Article Library & Archive</title><link rel="alternate" type="application/rss+xml" title="Sakariya Mining Daily RSS" href="../feed.xml"><style>
:root{color-scheme:light;--bg:#F5F3F0;--ink:#24170e;--muted:#66584f;--panel:#fff;--line:#d8c9bd;--accent:#C7551B;--link:#9e3b0a;--dark:#41200E}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.52 'Proxima Nova','Avenir Next','Segoe UI',Arial,sans-serif}a{color:var(--link);text-decoration-thickness:1px;text-underline-offset:3px}a:hover{text-decoration-thickness:2px}button,input,select{font:inherit}button{cursor:pointer}header{background:#020100;color:#F5F3F0;border-bottom:5px solid var(--accent)}header .inner{max-width:1200px;padding:24px 22px;margin:auto}.overline{font-size:11px;font-weight:700;letter-spacing:2px;color:#E9AE88}h1{font:700 clamp(26px,4vw,43px)/1.15 Georgia,serif;margin:6px 0}header p{color:#DFD4CD;margin:5px 0}.shell{max-width:1200px;margin:auto;padding:24px 20px 60px}.nav{display:flex;gap:20px;flex-wrap:wrap;padding:10px 0 18px}.nav a{font-weight:650}.kicker{font-size:11px;letter-spacing:1.6px;color:var(--link);font-weight:800;text-transform:uppercase}h2{font:700 24px Georgia,serif;margin:7px 0 8px}p.sub{margin:0 0 18px;color:var(--muted)}.topics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.fold-section{margin:12px 0}.fold-section details{background:#fff;border:1px solid var(--line);border-radius:9px;overflow:hidden}.fold-section details[open]{border-color:#d2b49c}.fold-section summary{list-style:none;display:flex;align-items:center;justify-content:space-between;gap:12px;cursor:pointer;padding:15px 18px;color:var(--dark);user-select:none}.fold-section summary::-webkit-details-marker{display:none}.fold-section summary:hover,.fold-section summary:focus-visible{background:#fff5ee}.fold-label{display:flex;flex-direction:column;gap:4px}.fold-label strong{font:700 21px/1.3 Georgia,serif}.fold-state{border:1px solid #ddc5b3;background:#fff2e7;border-radius:20px;padding:6px 12px;font-weight:750;font-size:12px;white-space:nowrap}.fold-state::after{content:"Show section  +";}.fold-section details[open] .fold-state::after{content:"Hide section  −";}.fold-section details[open]>summary{border-bottom:1px solid var(--line);background:#fffaf7}.fold-body{padding:15px 18px 18px}.fold-body .controls{margin-top:4px}.fold-body .date-controls{margin-top:4px}.fold-body>.sub{margin-bottom:13px}.fold-section{scroll-margin-top:16px}@media(max-width:530px){.fold-section summary{padding:12px}.fold-label strong{font-size:18px}.fold-state{padding:5px 8px;font-size:11px}.fold-body{padding:12px}}.topic-card{border:1px solid var(--line);background:var(--panel);color:var(--ink);text-align:left;padding:14px 11px;border-radius:8px;display:flex;gap:10px;align-items:center;min-width:0;box-shadow:none}.topic-card:hover{border-color:var(--accent)}.topic-card[aria-pressed="true"]{border:2px solid var(--accent);background:#fff0e4;color:#28170c;padding:13px 10px}.topic-icon{flex:0 0 32px;height:32px;display:grid;place-items:center;border-radius:7px;background:#f2e2d5;color:#8e380e;font-size:20px;font-weight:bold}.topic-card strong{display:block;font-size:13px;line-height:1.25}.topic-card small{display:block;color:var(--muted);font-size:11px;line-height:1.3;margin-top:4px}.topic-card .count{font-size:12px;margin-left:auto;align-self:flex-start;color:var(--link)}.controls{display:flex;gap:9px;flex-wrap:wrap;align-items:center;margin:19px 0 12px}.controls input,.controls select{color:var(--ink);background:var(--panel);border:1px solid var(--line);padding:11px;border-radius:6px;min-height:42px}.controls input{flex:2 1 250px;min-width:200px}.controls select{flex:1 1 135px;max-width:230px}button.clear{border:1px solid var(--line);background:var(--panel);color:var(--ink);padding:10px 15px;border-radius:6px}.panel{border:1px solid var(--line);background:var(--panel);border-radius:8px;overflow:hidden}.panel-heading{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:12px 15px;border-bottom:1px solid var(--line);font-weight:700}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;min-width:750px}th{font-size:11px;letter-spacing:.6px;text-transform:uppercase;color:var(--muted);text-align:left;background:#f2ebe6}th,td{padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}tbody tr:last-child td{border-bottom:0}tr[hidden]{display:none!important}td a.article{font-size:14px;font-weight:750}td .summary{color:var(--muted);font-size:12px;margin:5px 0 0;max-width:660px}.chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:6px}.chip{border:1px solid var(--line);background:#f8f0e9;color:var(--ink);border-radius:15px;padding:2px 8px;font-size:11px}.chip:hover{border-color:var(--accent)}.meta{color:var(--muted);white-space:nowrap;font-size:12px}.empty{padding:24px;color:var(--muted)}.latest-edition{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px;padding:16px 18px;margin:4px 0 23px;background:#fffaf5;border:1px solid #dbba9f;border-left:4px solid var(--accent);border-radius:8px}.latest-edition strong{display:block;font:700 18px/1.3 Georgia,serif;color:var(--dark);margin:4px 0}.latest-edition small{display:block;color:var(--muted);font-size:12px}.latest-eyebrow{font-size:11px;color:var(--link);font-weight:800;letter-spacing:1px}.latest-edition>a{background:var(--accent);color:white;text-decoration:none;font-weight:750;padding:11px 15px;border-radius:6px}.latest-edition>a:hover{background:var(--dark)}.date-controls{display:flex;flex-wrap:wrap;gap:12px;align-items:end;background:white;border:1px solid var(--line);border-radius:8px;padding:13px 15px;margin:12px 0}.date-controls label{display:flex;flex-direction:column;gap:4px;font-size:12px;font-weight:700;color:var(--dark)}.date-controls input{border:1px solid #bea99a;border-radius:5px;padding:9px;background:white;color:var(--ink);min-width:155px}.date-controls button{border:1px solid var(--line);background:#fff5ed;color:var(--dark);padding:10px 13px;border-radius:5px;font-weight:700}.date-controls span{margin-left:auto;color:var(--muted);font-size:12px}.archive-go-top{position:fixed;right:clamp(12px,3vw,28px);bottom:calc(16px + env(safe-area-inset-bottom,0px));z-index:1000;display:inline-flex;gap:8px;align-items:center;padding:11px 15px;border-radius:40px;background:var(--accent);color:white!important;text-decoration:none;font-weight:800;font-size:13px;box-shadow:0 4px 18px #41200e48;border:2px solid white;opacity:0;transform:translateY(12px);pointer-events:none;transition:opacity .18s,transform .18s}.archive-go-top.visible{opacity:1;transform:translateY(0);pointer-events:auto}.archive-go-top:hover{background:var(--dark)}.archive-go-top svg{width:17px;height:17px}.dates{scroll-margin-top:16px}section.dates{margin-top:35px}.dates table{min-width:560px}footer{background:#020100;color:#F5F3F0;padding:20px;text-align:center;font-size:12px}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
@media(max-width:580px){.latest-edition>a{width:100%;text-align:center}.date-controls label{flex:1 1 42%}.date-controls input{width:100%;min-width:0}.date-controls span{width:100%;margin-left:0}.archive-go-top{right:12px;bottom:calc(12px + env(safe-area-inset-bottom,0px))}}@media(prefers-reduced-motion:reduce){.archive-go-top{transition:none}}@media print{.archive-go-top,.date-controls,.latest-edition{display:none}}@media(max-width:860px){.topics{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:530px){.topics{grid-template-columns:1fr 1fr;gap:7px}.topic-card{padding:9px 7px;gap:6px}.topic-card[aria-pressed="true"]{padding:8px 6px}.topic-icon{flex-basis:24px;height:27px;font-size:16px}.topic-card strong{font-size:12px}.topic-card small{display:none}.topic-card .count{font-size:11px}.shell{padding:15px 12px 40px}h2{font-size:21px}}

</style></head><body id="top"><header><div class="inner"><div class="overline">SAKARIYA MINES &amp; MINERALS · RESHAPING RESOURCES</div><h1>Mining &amp; Graphite Daily</h1><p>Searchable Article Library &amp; Newspaper Archive</p></div></header>
<main class="shell"><nav class="nav"><a href="https://www.sakariyamines.com/" target="_blank" rel="noopener noreferrer">🌐 Visit Sakariya ↗</a><a href="../">Source Directory</a><a href="../people/">People Directory</a><a href="../companies/">Company Directory</a><a href="../projects/">Projects &amp; Plants</a><a href="../funding/">Funding Directory</a><a href="#topics">Browse Topics</a><a href="#articles">All Articles</a><a href="#dates">Editions by Date</a><a href="../feed.xml">RSS Feed</a></nav>""" + latest_banner + """<section id="topics" class="fold-section"><details id="fold-topics"><summary><span class="fold-label"><span class="kicker">Research desks</span><strong>Browse by topic</strong></span><span class="fold-state" aria-hidden="true"></span></summary><div class="fold-body"><p class="sub">Select a topic to see related reporting across every newspaper edition. One story can appear in several relevant topics.</p><div class="topics">""" + tiles + """</div></div></details></section>
<section id="articles" class="fold-section" aria-label="Search archived articles"><details id="fold-articles"><summary><span class="fold-label"><span class="kicker">Article search</span><strong>All articles</strong></span><span class="fold-state" aria-hidden="true"></span></summary><div class="fold-body"><div class="controls"><input id="query" type="search" aria-label="Search articles" placeholder="Search articles, people, projects, keywords…"><select id="tag" aria-label="Filter by tag"><option value="">All tags</option></select><select id="date" aria-label="Filter by edition"><option value="">All dates</option></select><select id="region" aria-label="Filter by geography"><option value="">All regions</option></select><button type="button" class="clear" id="reset">Clear filters</button></div><div class="panel"><div class="panel-heading"><span id="filter-title">All Articles</span><span id="result-count" aria-live="polite"></span></div><div class="scroll"><table><thead><tr><th>Edition</th><th>Story &amp; tags</th><th>Region</th></tr></thead><tbody id="results"></tbody></table></div><p class="empty" id="no-results" hidden>No matching articles. Try another topic, keyword, tag or date.</p></div></div></details></section>
<section class="dates fold-section" id="dates"><details id="fold-dates"><summary><span class="fold-label"><span class="kicker">Complete issues</span><strong>Browse editions by date</strong></span><span class="fold-state" aria-hidden="true"></span></summary><div class="fold-body"><p class="sub">Read the original full newspapers, including executive summaries and research notes.</p><div class="date-controls" role="search" aria-label="Filter newspaper editions by date"><label>From date <input type="date" id="edition-from"></label><label>To date <input type="date" id="edition-to"></label><button id="edition-clear" type="button">Clear dates</button><span id="edition-count" aria-live="polite"></span></div><div class="panel scroll"><table><thead><tr><th>Date (IST)</th><th>Edition</th><th>Coverage</th></tr></thead><tbody>""" + date_links + """</tbody></table></div><p class="empty" id="edition-none" hidden>No newspapers in this date range.</p></div></details></section></main><a href="#top" class="archive-go-top" id="archive-go-top" aria-label="Go to top of archive"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>Go to top</a><footer>SAKARIYA MINES &amp; MINERALS · RESHAPING RESOURCES · A curated public mining research archive</footer>
<script type="application/json" id="article-data">""" + payload + """</script><script>
const data=JSON.parse(document.getElementById("article-data").textContent);
const topicButtons=[...document.querySelectorAll(".topic-card")];
const folds={topics:document.getElementById("fold-topics"),articles:document.getElementById("fold-articles"),dates:document.getElementById("fold-dates")};
function openFold(name){if(folds[name])folds[name].open=true;}
function openHashSection(){
 const target=location.hash.replace("#","");
 if(folds[target])openFold(target);
}
document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener("click",()=>{
 const section=a.getAttribute("href").slice(1);if(folds[section])openFold(section);
}));
window.addEventListener("hashchange",openHashSection);
openHashSection();
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
topicButtons.forEach(b=>b.onclick=()=>{topic=topic===b.dataset.topic?"":b.dataset.topic;openFold("articles");show();$("articles").scrollIntoView({behavior:"smooth",block:"start"});});
[input,tag,date,region].forEach(n=>n.addEventListener(n===input?"input":"change",show));
$("reset").onclick=()=>{topic="";input.value="";tag.value="";date.value="";region.value="";show();};
if(topic||params.has("q")||params.has("tag")||params.has("date")||params.has("region"))openFold("articles");
show();
const editionRows=[...document.querySelectorAll("#dates tbody tr[data-edition-date]")];
const from=$("edition-from"),to=$("edition-to");
function filterEditions(){
 const begin=from.value,end=to.value;
 let n=0;
 editionRows.forEach(row=>{
  const d=row.dataset.editionDate;
  const match=(!begin||d>=begin)&&(!end||d<=end);
  row.hidden=!match;if(match)n++;
 });
 $("edition-count").textContent=n+" of "+editionRows.length+" editions";
 $("edition-none").hidden=n!==0;
}
const fromParams=new URLSearchParams(location.search);
from.value=fromParams.get("edition_from")||"";
to.value=fromParams.get("edition_to")||"";
[from,to].forEach(x=>x.addEventListener("change",filterEditions));
$("edition-clear").addEventListener("click",()=>{from.value="";to.value="";filterEditions();});
if(from.value||to.value)openFold("dates");
filterEditions();
const goTop=$("archive-go-top");
const updateGoTop=()=>{
 const visible=window.scrollY>420;
 goTop.classList.toggle("visible",visible);
 goTop.tabIndex=visible?0:-1;
 goTop.setAttribute("aria-hidden",String(!visible));
};
window.addEventListener("scroll",updateGoTop,{passive:true});
window.addEventListener("resize",updateGoTop);
updateGoTop();
goTop.addEventListener("click",event=>{
 if(window.matchMedia("(prefers-reduced-motion: reduce)").matches)return;
 event.preventDefault();
 window.scrollTo({top:0,behavior:"smooth"});
});
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
