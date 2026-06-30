"""
저탄소에너지 브리핑 - Vercel 서버리스 버전
북마크·아카이브는 브라우저 localStorage에 저장
"""

from flask import Flask, jsonify, request
import urllib.request, urllib.parse
import json, re, os
from datetime import datetime, timedelta

app = Flask(__name__)

NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "")
FROM_DATE   = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

KO_RSS_FEEDS = [
    "https://www.electimes.com/rss/allArticle.xml",
    "https://www.energy-news.co.kr/rss/allArticle.xml",
    "http://www.enewstoday.co.kr/rss/allArticle.xml",
    "https://www.gasnews.com/rss/allArticle.xml",
]

TOPICS = {
    "재생에너지": {"icon": "☀️", "color": "#f59e0b",
                  "rss_keywords": ["재생에너지","태양광","풍력","육상풍력","신재생","전기본","RE100","풍력발전","태양광발전"],
                  "newsapi_queries": ['"renewable energy" policy OR market OR investment OR "RE100" OR "solar" OR "onshore wind"'],
                  "exclude": []},
    "수소혼소":   {"icon": "🔥", "color": "#3b82f6",
                  "rss_keywords": ["수소혼소","암모니아혼소","혼소발전"],
                  "newsapi_queries": ['"hydrogen co-firing" OR "hydrogen blending" OR "ammonia co-firing"'],
                  "exclude": ["hydrogen bond","hydrogen transfer"]},
    "지열에너지": {"icon": "🌋", "color": "#10b981",
                  "rss_keywords": ["지열발전","지열에너지","지열"],
                  "newsapi_queries": ['"geothermal energy" OR "geothermal power" renewable'],
                  "exclude": ["earthquake","seismic","지진"]},
    "SMR":        {"icon": "⚛️", "color": "#8b5cf6",
                  "rss_keywords": ["SMR","소형모듈원자로","소형원전"],
                  "newsapi_queries": ['"small modular reactor" OR "SMR" nuclear'],
                  "exclude": []},
    "탄소배출권": {"icon": "📊", "color": "#6b7280",
                  "rss_keywords": ["탄소배출권","탄소시장","ETS","CBAM"],
                  "newsapi_queries": ['"carbon credit" OR "emission trading" OR "CBAM"'],
                  "exclude": []},
}

# -------------------------------------------------------
# 뉴스 수집
# -------------------------------------------------------
def load_rss():
    SOURCE_MAP = {"electimes": "전기신문", "energy-news": "에너지신문",
                  "enewstoday": "이뉴스투데이", "gasnews": "가스신문"}
    cache = []
    for feed_url in KO_RSS_FEEDS:
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                raw = r.read().decode("utf-8", errors="ignore")
            for item in re.findall(r"<item>(.*?)</item>", raw, re.DOTALL):
                def tag(t):
                    m = re.search(rf"<{t}[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{t}>", item, re.DOTALL)
                    return m.group(1).strip() if m else ""
                title = tag("title")
                link  = (tag("link") or tag("guid")).strip()
                desc  = re.sub(r"<[^>]+>", "", tag("description"))[:150]
                pub   = tag("pubDate")[:16]
                src   = next((v for k, v in SOURCE_MAP.items() if k in feed_url), "국내언론")
                if title and link:
                    cache.append({"title": title, "description": desc, "url": link,
                                  "publishedAt": pub, "source": {"name": src}, "lang": "ko"})
        except:
            pass
    return cache

def fetch_newsapi(query, page_size=2):
    params = {"q": query, "from": FROM_DATE, "sortBy": "publishedAt",
              "pageSize": str(page_size), "language": "en", "apiKey": NEWSAPI_KEY}
    url = "https://newsapi.org/v2/everything?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
            for a in data.get("articles", []):
                a["lang"] = "en"
            return data.get("articles", [])
    except:
        return []

def collect_news():
    rss_cache = load_rss()
    results = {}
    for topic, cfg in TOPICS.items():
        seen, articles = set(), []
        for a in rss_cache:
            if "(인사)" in a.get("title", ""):
                continue
            text = (a["title"] + " " + a["description"]).lower()
            if any(k.lower() in text for k in cfg["rss_keywords"]) and a["url"] not in seen:
                if not any(e.lower() in text for e in cfg["exclude"]):
                    seen.add(a["url"]); articles.append(a)
        for q in cfg["newsapi_queries"]:
            for a in fetch_newsapi(q):
                text = (a.get("title","") + " " + a.get("description","")).lower()
                if a["url"] not in seen and not any(e.lower() in text for e in cfg["exclude"]):
                    seen.add(a["url"]); articles.append(a)
        results[topic] = articles[:5]
    return results

# -------------------------------------------------------
# 공통 CSS / 네비게이션
# -------------------------------------------------------
COMMON_CSS = """
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI','Malgun Gothic',sans-serif;background:#f0f4f8;color:#1a202c}
    header{background:linear-gradient(135deg,#1e3a5f,#2d6a4f);color:white;padding:24px 40px}
    header h1{font-size:1.6rem;font-weight:700}
    header p{margin-top:4px;opacity:.8;font-size:.9rem}
    nav.page-nav{background:#1a2f4a;display:flex;gap:4px;padding:0 36px}
    nav.page-nav a{color:rgba(255,255,255,.65);text-decoration:none;padding:10px 18px;font-size:.88rem;
                   font-weight:600;border-bottom:3px solid transparent;transition:all .2s}
    nav.page-nav a:hover{color:white}
    nav.page-nav a.active{color:white;border-bottom-color:#4ade80}
    .share-btn{margin-left:auto;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);
               color:white;padding:6px 14px;border-radius:6px;cursor:pointer;font-size:.82rem;
               font-weight:600;transition:all .2s;white-space:nowrap}
    .share-btn:hover{background:rgba(255,255,255,.22)}
    .toast{position:fixed;bottom:28px;left:50%;transform:translateX(-50%) translateY(20px);
           background:#1e3a5f;color:white;padding:10px 22px;border-radius:8px;font-size:.88rem;
           opacity:0;transition:all .3s;z-index:999;pointer-events:none}
    .toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
    .toolbar{background:white;border-bottom:1px solid #e2e8f0;padding:12px 40px;display:flex;
             gap:12px;align-items:center;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,.06)}
    .btn{padding:8px 18px;border-radius:6px;border:none;cursor:pointer;font-size:.9rem;font-weight:600;transition:all .2s}
    .btn-primary{background:#2d6a4f;color:white} .btn-primary:hover{background:#1e3a5f}
    .btn-secondary{background:#e2e8f0;color:#4a5568} .btn-secondary:hover{background:#cbd5e0}
    .btn-danger{background:#fff5f5;color:#e53e3e;border:1px solid #fed7d7} .btn-danger:hover{background:#fed7d7}
    main{max-width:1000px;margin:28px auto;padding:0 20px 80px}
    .topic-section{margin-bottom:36px}
    .topic-title{font-size:1.1rem;font-weight:700;margin-bottom:14px;padding-left:12px;border-left:4px solid #ccc}
    .cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:14px}
    .card{background:white;border-radius:10px;padding:16px;box-shadow:0 1px 4px rgba(0,0,0,.08);
          border:2px solid transparent;transition:all .2s}
    .card.bookmarked{border-color:#f59e0b}
    .card-header{display:flex;align-items:flex-start;gap:8px;margin-bottom:10px}
    .card-meta{font-size:.72rem;color:#718096}
    .bm-btn{background:none;border:none;cursor:pointer;font-size:1.1rem;padding:0 2px;
            line-height:1;flex-shrink:0;opacity:.35;transition:opacity .2s}
    .bm-btn:hover{opacity:1} .bm-btn.on{opacity:1}
    .card-title{font-size:.9rem;font-weight:600;color:#2b6cb0;line-height:1.4;margin-bottom:6px}
    .card-title a{color:inherit;text-decoration:none} .card-title a:hover{text-decoration:underline}
    .card-desc{font-size:.8rem;color:#4a5568;line-height:1.5}
    .empty{color:#a0aec0;font-size:.9rem;padding:20px 0;text-align:center}
    .archive-list{display:flex;flex-direction:column;gap:10px;max-width:600px}
    .archive-item{background:white;border-radius:10px;padding:16px 20px;
                  box-shadow:0 1px 4px rgba(0,0,0,.08);display:flex;align-items:center;
                  justify-content:space-between;cursor:pointer;border:2px solid transparent;transition:all .2s}
    .archive-item:hover{border-color:#2d6a4f;background:#f0fff4}
    .archive-date{font-weight:700;font-size:1rem;color:#1e3a5f}
    .archive-count{font-size:.8rem;color:#718096;margin-top:4px}
    .loading-overlay{position:fixed;inset:0;background:rgba(255,255,255,.85);display:flex;
                     flex-direction:column;align-items:center;justify-content:center;z-index:999}
    .spinner{width:40px;height:40px;border:4px solid #e2e8f0;border-top-color:#2d6a4f;
             border-radius:50%;animation:spin 1s linear infinite;margin-bottom:16px}
    @keyframes spin{to{transform:rotate(360deg)}}
    .loading-text{color:#4a5568;font-size:.95rem}
    footer{text-align:center;font-size:.78rem;color:#a0aec0;padding:20px}
"""

def nav_html(active):
    links = [("/", "📰 오늘 브리핑"), ("/bookmarks", "⭐ 북마크"), ("/archive", "📅 아카이브")]
    items = "".join(
        f'<a href="{href}" class="{"active" if href == active else ""}">{label}</a>'
        for href, label in links
    )
    return f'''<nav class="page-nav">
  {items}
  <button class="share-btn" onclick="sharePage()">🔗 공유</button>
</nav>
<div class="toast" id="toast">링크가 복사되었습니다!</div>
<script>
function sharePage() {{
  const url = window.location.href;
  if (navigator.share) {{
    navigator.share({{ title: document.title, url }});
  }} else {{
    navigator.clipboard.writeText(url).then(() => showToast());
  }}
}}
function showToast() {{
  const t = document.getElementById('toast');
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2200);
}}
</script>'''

# -------------------------------------------------------
# 라우트 - 메인 (오늘 브리핑)
# -------------------------------------------------------
@app.route("/")
def index():
    today = datetime.now().strftime("%Y-%m-%d")
    news  = collect_news()
    topics_json     = json.dumps(news, ensure_ascii=False)
    topics_cfg_json = json.dumps(
        {k: {"icon": v["icon"], "color": v["color"]} for k, v in TOPICS.items()},
        ensure_ascii=False
    )
    total = sum(len(v) for v in news.values())

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>저탄소에너지 브리핑 [{today}]</title>
  <style>{COMMON_CSS}</style>
</head>
<body>
<header>
  <h1>저탄소에너지 브리핑</h1>
  <p>{today} · 총 {total}건 수집</p>
</header>
{nav_html("/")}
<div class="toolbar">
  <span style="color:#718096;font-size:.85rem">⭐ 별표를 눌러 중요 기사를 북마크하세요</span>
</div>
<main id="main-content"></main>
<footer>저탄소에너지 브리핑 · RSS + NewsAPI</footer>
<script>
const NEWS = {topics_json};
const CFG  = {topics_cfg_json};
const TODAY = '{today}';

// localStorage 북마크 헬퍼
function getBMs() {{ try {{ return JSON.parse(localStorage.getItem('briefing_bookmarks')||'[]'); }} catch{{return[];}} }}
function saveBMs(bms) {{ localStorage.setItem('briefing_bookmarks', JSON.stringify(bms)); }}

// 오늘 데이터 아카이브에 저장 (localStorage)
function archiveToday() {{
  const key = 'briefing_archive_' + TODAY;
  if (!localStorage.getItem(key)) {{
    localStorage.setItem(key, JSON.stringify({{date: TODAY, news: NEWS, total: {total}}}));
    // 90일 이전 아카이브 정리
    const cutoff = new Date(); cutoff.setDate(cutoff.getDate() - 90);
    Object.keys(localStorage).forEach(k => {{
      if (k.startsWith('briefing_archive_')) {{
        const d = k.replace('briefing_archive_','');
        if (d < cutoff.toISOString().slice(0,10)) localStorage.removeItem(k);
      }}
    }});
  }}
}}

function renderCards() {{
  const main = document.getElementById('main-content');
  main.innerHTML = '';
  const bmUrls = new Set(getBMs().map(b => b.url));
  for (const [topic, articles] of Object.entries(NEWS)) {{
    const cfg = CFG[topic] || {{}};
    const section = document.createElement('section');
    section.className = 'topic-section';
    section.innerHTML = `<h2 class="topic-title" style="border-left-color:${{cfg.color||'#ccc'}}">${{cfg.icon||''}} ${{topic}}</h2>`;
    const grid = document.createElement('div');
    grid.className = 'cards';
    if (!articles.length) {{
      grid.innerHTML = '<p class="empty">수집된 기사 없음</p>';
    }} else {{
      articles.forEach(a => {{
        const flag = a.lang==='ko' ? '🇰🇷' : '🌐';
        const pub  = (a.publishedAt||'').slice(0,10);
        const src  = (a.source||{{}}).name||'';
        const isBm = bmUrls.has(a.url);
        const card = document.createElement('div');
        card.className = 'card' + (isBm ? ' bookmarked' : '');
        card.innerHTML = `
          <div class="card-header">
            <div style="flex:1"><div class="card-meta">${{flag}} ${{src}} · ${{pub}}</div></div>
            <button class="bm-btn${{isBm?' on':''}}" title="북마크">⭐</button>
          </div>
          <div class="card-title"><a href="${{a.url}}" target="_blank">${{a.title||'(제목 없음)'}}</a></div>
          <p class="card-desc">${{(a.description||'').slice(0,120)}}</p>`;
        card.querySelector('.bm-btn').addEventListener('click', function() {{
          let bms = getBMs();
          if (bms.find(b => b.url===a.url)) {{
            bms = bms.filter(b => b.url!==a.url);
            this.classList.remove('on'); card.classList.remove('bookmarked');
          }} else {{
            bms.push({{...a, topic, saved_at: new Date().toLocaleString('ko-KR')}});
            this.classList.add('on'); card.classList.add('bookmarked');
          }}
          saveBMs(bms);
        }});
        grid.appendChild(card);
      }});
    }}
    section.appendChild(grid); main.appendChild(section);
  }}
}}

archiveToday();
renderCards();
</script>
</body>
</html>"""


# -------------------------------------------------------
# 라우트 - 북마크 (localStorage 기반)
# -------------------------------------------------------
@app.route("/bookmarks")
def bookmarks_page():
    topics_cfg_json = json.dumps(
        {k: {"icon": v["icon"], "color": v["color"]} for k, v in TOPICS.items()},
        ensure_ascii=False
    )
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>북마크 · 저탄소에너지 브리핑</title>
  <style>{COMMON_CSS}</style>
</head>
<body>
<header>
  <h1>저탄소에너지 브리핑</h1>
  <p>⭐ 북마크 저장 기사</p>
</header>
{nav_html("/bookmarks")}
<main id="bm-content"></main>
<footer>저탄소에너지 브리핑 · RSS + NewsAPI</footer>
<script>
const CFG = {topics_cfg_json};
function getBMs() {{ try {{ return JSON.parse(localStorage.getItem('briefing_bookmarks')||'[]'); }} catch{{return[];}} }}
function saveBMs(bms) {{ localStorage.setItem('briefing_bookmarks', JSON.stringify(bms)); }}

function render() {{
  const el = document.getElementById('bm-content');
  const bms = getBMs();
  if (!bms.length) {{
    el.innerHTML = '<p class="empty" style="margin-top:60px">저장된 북마크가 없습니다.<br><a href="/" style="color:#2d6a4f">오늘 브리핑</a>에서 ⭐를 눌러 저장하세요.</p>';
    return;
  }}
  const grouped = {{}};
  bms.forEach(b => {{ (grouped[b.topic]=grouped[b.topic]||[]).push(b); }});
  let html = '';
  for (const [topic, arts] of Object.entries(grouped)) {{
    const cfg = CFG[topic]||{{}};
    html += `<section class="topic-section">
      <h2 class="topic-title" style="border-left-color:${{cfg.color||'#ccc'}}">${{cfg.icon||''}} ${{topic}}</h2>
      <div class="cards">`;
    arts.forEach((a,i) => {{
      const flag = a.lang==='ko'?'🇰🇷':'🌐';
      const src  = (a.source||{{}}).name||'';
      html += `<div class="card bookmarked" id="bmc-${{i}}">
        <div class="card-header">
          <div style="flex:1"><div class="card-meta">${{flag}} ${{src}}</div></div>
          <div class="card-meta" style="color:#b7791f">${{a.saved_at||''}}</div>
        </div>
        <div class="card-title"><a href="${{a.url}}" target="_blank">${{a.title||''}}</a></div>
        <p class="card-desc">${{(a.description||'').slice(0,120)}}</p>
        <button class="btn btn-danger" style="margin-top:10px;width:100%;font-size:.8rem"
          onclick="remove('${{encodeURIComponent(a.url)}}',this)">북마크 해제</button>
      </div>`;
    }});
    html += '</div></section>';
  }}
  el.innerHTML = html;
}}

function remove(encodedUrl, btn) {{
  const url = decodeURIComponent(encodedUrl);
  saveBMs(getBMs().filter(b => b.url!==url));
  btn.closest('.card').style.opacity='0.3';
  setTimeout(render, 400);
}}

render();
</script>
</body>
</html>"""


# -------------------------------------------------------
# 라우트 - 아카이브 목록 (localStorage 기반)
# -------------------------------------------------------
@app.route("/archive")
def archive_page():
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>아카이브 · 저탄소에너지 브리핑</title>
  <style>{COMMON_CSS}</style>
</head>
<body>
<header>
  <h1>저탄소에너지 브리핑</h1>
  <p>📅 날짜별 브리핑 아카이브</p>
</header>
{nav_html("/archive")}
<main>
  <div class="archive-list" id="archive-list">
    <p class="empty">아카이브를 불러오는 중...</p>
  </div>
</main>
<footer>저탄소에너지 브리핑 · RSS + NewsAPI</footer>
<script>
function render() {{
  const el = document.getElementById('archive-list');
  const entries = [];
  Object.keys(localStorage).forEach(k => {{
    if (k.startsWith('briefing_archive_')) {{
      try {{
        const data = JSON.parse(localStorage.getItem(k));
        entries.push(data);
      }} catch {{}}
    }}
  }});
  entries.sort((a,b) => b.date.localeCompare(a.date));
  if (!entries.length) {{
    el.innerHTML = '<p class="empty">아카이브가 없습니다.<br>오늘 브리핑 페이지를 방문하면 자동으로 저장됩니다.</p>';
    return;
  }}
  el.innerHTML = entries.map(e => `
    <div class="archive-item" onclick="location.href='/archive/${{e.date}}'">
      <div>
        <div class="archive-date">${{e.date}}</div>
        <div class="archive-count">기사 ${{e.total||0}}건</div>
      </div>
      <span style="color:#a0aec0;font-size:1.2rem">›</span>
    </div>`).join('');
}}
render();
</script>
</body>
</html>"""


# -------------------------------------------------------
# 라우트 - 아카이브 날짜별
# -------------------------------------------------------
@app.route("/archive/<date>")
def archive_date_page(date):
    topics_cfg_json = json.dumps(
        {k: {"icon": v["icon"], "color": v["color"]} for k, v in TOPICS.items()},
        ensure_ascii=False
    )
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{date} · 아카이브</title>
  <style>{COMMON_CSS}</style>
</head>
<body>
<header>
  <h1>저탄소에너지 브리핑</h1>
  <p>📅 {date} 아카이브</p>
</header>
{nav_html("/archive")}
<div class="toolbar">
  <button class="btn btn-secondary" onclick="history.back()">← 목록으로</button>
</div>
<main id="main-content">
  <p class="empty">데이터를 불러오는 중...</p>
</main>
<footer>저탄소에너지 브리핑 · RSS + NewsAPI</footer>
<script>
const CFG = {topics_cfg_json};
const DATE = '{date}';

function render() {{
  const stored = localStorage.getItem('briefing_archive_' + DATE);
  const el = document.getElementById('main-content');
  if (!stored) {{
    el.innerHTML = '<p class="empty">이 날짜의 아카이브가 없습니다.<br>해당 날짜에 브리핑 페이지를 방문해야 저장됩니다.</p>';
    return;
  }}
  const data = JSON.parse(stored);
  const news = data.news || {{}};
  let html = '';
  for (const [topic, articles] of Object.entries(news)) {{
    const cfg = CFG[topic]||{{}};
    html += `<section class="topic-section">
      <h2 class="topic-title" style="border-left-color:${{cfg.color||'#ccc'}}">${{cfg.icon||''}} ${{topic}}</h2>
      <div class="cards">`;
    if (!articles.length) {{
      html += '<p class="empty">수집된 기사 없음</p>';
    }} else {{
      articles.forEach(a => {{
        const flag = a.lang==='ko'?'🇰🇷':'🌐';
        const src  = (a.source||{{}}).name||'';
        const pub  = (a.publishedAt||'').slice(0,10);
        html += `<div class="card">
          <div class="card-header">
            <div style="flex:1"><div class="card-meta">${{flag}} ${{src}} · ${{pub}}</div></div>
          </div>
          <div class="card-title"><a href="${{a.url}}" target="_blank">${{a.title||''}}</a></div>
          <p class="card-desc">${{(a.description||'').slice(0,120)}}</p>
        </div>`;
      }});
    }}
    html += '</div></section>';
  }}
  el.innerHTML = html;
}}
render();
</script>
</body>
</html>"""


if __name__ == "__main__":
    app.run(debug=True, port=5001)
