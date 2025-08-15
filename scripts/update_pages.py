# scripts/update_pages.py
# Updates the gh-pages tree: copies today's artifacts, updates manifest.json
# (now WITH description), regenerates index.html (catalog with search),
# and refreshes latest/.

import json
import shutil
import sys
from pathlib import Path

if len(sys.argv) < 4:
    print("Usage: python3 scripts/update_pages.py YYYYMMDD SEQ TITLE")
    sys.exit(1)

DATE = sys.argv[1]          # e.g. 20250816
SEQ = str(sys.argv[2])      # e.g. 6 (no leading zeros)
TITLE = sys.argv[3]         # release title (string)

root = Path("gh-pages")
date_dir = root / "releases" / "date" / DATE
seq_dir = root / "releases" / "seq" / SEQ
latest_dir = root / "latest"

# Ensure directories
for p in (date_dir, seq_dir, latest_dir):
    p.mkdir(parents=True, exist_ok=True)

# ---- Copy today's artifacts into both aliases ----
src_html   = Path(f"dist/demo-{DATE}.html")
src_cover  = Path(f"dist/cover-{DATE}.png")
src_readme = Path(f"dist/readme-{DATE}.txt")

shutil.copyfile(src_html,  date_dir / "index.html")
shutil.copyfile(src_cover, date_dir / "cover.png")
shutil.copyfile(src_readme, date_dir / "readme.txt")

# seq aliases point to the same content
shutil.copyfile(date_dir / "index.html", seq_dir / "index.html")
shutil.copyfile(date_dir / "cover.png",   seq_dir / "cover.png")
shutil.copyfile(date_dir / "readme.txt",  seq_dir / "readme.txt")

# ---- Extract description from readme ----
def extract_description(readme_path: Path) -> str:
    try:
        text = readme_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    lines = [l.rstrip("\n") for l in text.splitlines()]
    desc_lines = []
    in_desc = False
    for line in lines:
        if not in_desc:
            if line.strip().lower().startswith("description:"):
                in_desc = True
            continue
        # stop on blank line or TO_NEXT / COVER markers
        if not line.strip() or line.strip().upper().startswith("TO_NEXT") or line.strip().upper().startswith("COVER"):
            break
        desc_lines.append(line)
    desc = " ".join(l.strip() for l in desc_lines).strip()
    # fall back: if no Description: block, take 1–2 lines after title
    if not desc:
        # remove first line (title) and join a couple next non-empty lines
        body = [l for l in lines[1:] if l.strip()]
        desc = " ".join(body[:2]).strip()
    # keep it compact
    if len(desc) > 400:
        desc = desc[:397].rstrip() + "..."
    return desc

DESC = extract_description(src_readme)

# ---- Update manifest.json ----
manifest_path = root / "releases" / "manifest.json"
manifest_path.parent.mkdir(parents=True, exist_ok=True)

if manifest_path.exists():
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        data = []
else:
    data = []

# remove duplicates by date or seq
data = [x for x in data if not (x.get("date") == DATE or str(x.get("seq")) == SEQ)]
data.append({"date": DATE, "seq": SEQ, "title": TITLE, "desc": DESC})
data.sort(key=lambda x: x["date"], reverse=True)

manifest_path.write_text(
    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
)

# ---- Build index.html (catalog with search + favicon) ----
index_html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>jsdemo — All Releases</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="./latest/cover.png" type="image/png">
<style>
  body{{font:16px/1.5 system-ui,Segoe UI,Roboto,Arial;margin:2rem;max-width:920px}}
  header{{display:flex;gap:1rem;align-items:center;flex-wrap:wrap}}
  input{{font:inherit;padding:.5rem .75rem;border:1px solid #ddd;border-radius:.5rem;min-width:280px}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem;margin-top:1rem}}
  .card{{border:1px solid #e5e5e5;border-radius:.75rem;padding:1rem}}
  .card h3{{margin:.25rem 0 .25rem;font-size:1.1rem}}
  .meta{{color:#666;font-size:.9rem;margin-top:.15rem}}
  .meta a{{color:inherit;text-decoration:underline dotted}}
  .cover{{width:100%;aspect-ratio:1/1;object-fit:cover;border-radius:.5rem;border:1px solid #eee;margin:.5rem 0;display:block}}
  .desc{{color:#555;font-size:.92rem;margin-top:.35rem}}
  .muted{{color:#888;font-size:.95rem}}
</style>
</head>
<body>
<header>
  <h1 style="margin:0">jsdemo</h1>
  <a href="./latest/" style="margin-left:auto">Latest</a>
  <input id="q" placeholder="Search by date (YYYYMMDD), year/month, #seq or text">
</header>
<p class="muted">Click the cover to open the demo. In the meta line, <b>Date</b> and <b>Seq</b> are links.</p>
<div id="list" class="grid"></div>
<script>
async function load(){{
  let base = [];
  try {{
    const res = await fetch('./releases/manifest.json', {{cache:'no-store'}});
    if(!res.ok) throw new Error('manifest not found');
    base = await res.json();
  }} catch (e) {{
    console.error('Failed to load manifest:', e);
    base = [];
  }}

  const list = document.getElementById('list');
  const q = document.getElementById('q');

  function esc(s){{
    const map = {{ "&":"&amp;", "<":"&lt;", ">":"&gt;", "\\"":"&quot;", "'":"&#39;" }};
    return String(s||"").replace(/[&<>\"']/g, m => map[m]);
  }}

  function render(items){{
    list.innerHTML = '';
    for (const it of items) {{
      const el = document.createElement('div'); el.className='card';
      el.innerHTML = `
        <a href="./releases/date/${{it.date}}/" target="_blank">
          <img class="cover" src="./releases/date/${{it.date}}/cover.png" alt="open ${{esc(it.title||'demo')}}">
        </a>
        <h3>${{esc(it.seq)}}: ${{esc(it.title||'Untitled')}}</h3>
        <div class="meta">
          Date: <a href="./releases/date/${{it.date}}/" target="_blank"><code>${{it.date}}</code></a>
          ·
          Seq: <a href="./releases/seq/${{it.seq}}/" target="_blank"><code>${{it.seq}}</code></a>
        </div>
        <p class="desc">${{esc((it.desc||'').trim())}}</p>`;
      list.appendChild(el);
    }}
  }}

  // Simple 3-bucket ranking: exact seq, starts-with, contains
  function searchRanked(qs){{
    qs = (qs||'').trim().toLowerCase();
    if(!qs) return base;

    const exact=[], starts=[], contains=[];
    for(const it of base){{
      const seqStr = String(it.seq).toLowerCase();
      const date   = String(it.date).toLowerCase();
      const title  = String(it.title||'').toLowerCase();
      const desc   = String(it.desc||'').toLowerCase();

      const startsAny   = date.startsWith(qs) || seqStr.startsWith(qs) || title.startsWith(qs) || desc.startsWith(qs);
      const containsAny = date.includes(qs)   || seqStr.includes(qs)   || title.includes(qs)   || desc.includes(qs);

      if(qs === seqStr) {{ exact.push(it); continue; }}
      if(startsAny)     {{ starts.push(it); continue; }}
      if(containsAny)   {{ contains.push(it); continue; }}
    }}

    const order = new Map(base.map((x,i)=>[x.date+':'+x.seq, i]));
    const byBase = arr => arr.sort((a,b)=> order.get(a.date+':'+a.seq) - order.get(b.date+':'+b.seq));
    return [...byBase(exact), ...byBase(starts), ...byBase(contains)];
  }}

  q.addEventListener('input', () => render(searchRanked(q.value)));
  render(base);
}}
load();
</script>
</body>
</html>
"""

(root / "index.html").write_text(index_html, encoding="utf-8")

# ---- Update latest/ with today's release ----
shutil.copyfile(date_dir / "index.html", latest_dir / "index.html")
shutil.copyfile(date_dir / "cover.png",   latest_dir / "cover.png")
shutil.copyfile(date_dir / "readme.txt",  latest_dir / "readme.txt")

print("Pages updated for", DATE, "seq", SEQ)