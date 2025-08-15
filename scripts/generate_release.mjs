// scripts/generate_release.mjs
import fs from 'node:fs/promises';
import path from 'node:path';

const OPENAI_API_KEY = process.env.OPENAI_API_KEY || '';
const OPENAI_MODEL = process.env.OPENAI_MODEL || 'gpt-4o';

const today = new Date();
const y = today.getUTCFullYear();
const m = String(today.getUTCMonth()+1).padStart(2,'0');
const d = String(today.getUTCDate()).padStart(2,'0');
const DATE = `${y}${m}${d}`;

async function readOrEmpty(p){ try { return await fs.readFile(p,'utf8'); } catch { return ''; } }
const commits = await readOrEmpty('tmp/commits.txt');
const inspirations = await readOrEmpty('tmp/inspirations.txt');
const systemPrompt = await readOrEmpty('prompts/system.md');

const OUTDIR = 'dist';
await fs.mkdir(OUTDIR, { recursive: true });

function hasExternal(html){
  const bad = /(https?:\/\/|<link\b|<script\s+src=|<img\s+[^>]*src\s*=\s*["'](?!data:))/i;
  return bad.test(html);
}
function ensureCSP(html){
  if(!/<meta[^>]+Content-Security-Policy/i.test(html)){
    html = html.replace(/<head>|<html[^>]*>/i, (m)=>`${m}\n<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; font-src data:;">`);
  }
  return html;
}
function fallbackDemo(){
  const title = 'Chromatic Echo';
  const description = 'Fallback demo: colorful orbits with gentle motion (Canvas, no deps).';
  const to_next = 'Add subtle interactivity without breaking CSP.';
  const cover_prompt = 'Abstract neon orbits on black, soft glow, minimal poster';
  const html = `<!doctype html>
<html lang="en">
<meta charset="utf-8"/>
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; font-src data:'>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>${title}</title>
<style>html,body,#c{margin:0;padding:0;width:100%;height:100%}body{background:#000;color:#fff;font:16px/1.5 system-ui}</style>
<canvas id="c"></canvas>
<script>
const c=document.getElementById('c'),x=c.getContext('2d');function R(){c.width=innerWidth;c.height=innerHeight;}addEventListener('resize',R);R();
let t=0;function L(){t+=0.013;x.clearRect(0,0,c.width,c.height);const r=70+50*Math.sin(t*1.7);const cx=c.width/2+Math.cos(t*0.9)*160;const cy=c.height/2+Math.sin(t*1.1)*110;x.save();x.shadowBlur=30;x.shadowColor='hsl('+((t*60)%360)+' 100% 60%)';x.beginPath();x.arc(cx,cy,r,0,Math.PI*2);x.fillStyle='hsl('+((t*60)%360)+' 80% 55%)';x.fill();x.restore();requestAnimationFrame(L);}L();
</script>
</html>`;
  return {title, description, to_next, cover_prompt, html};
}
async function callOpenAI(){
  const prompt = [
    { role: 'system', content: systemPrompt || 'You write one-file Canvas demos under strict CSP. No external URLs. Return JSON.' },
    { role: 'user', content: `Recent commits:\n${commits || '(none)'}\n\nRecent inspirations:\n${inspirations || '(none)'}\n\nProduce JSON with keys: title, description, to_next, cover_prompt, html.` }
  ];
  const body = { model: OPENAI_MODEL, messages: prompt, response_format: { type: 'json_object' } };
  const res = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${OPENAI_API_KEY}`, 'Content-Type':'application/json' },
    body: JSON.stringify(body),
  });
  if(!res.ok) throw new Error('OpenAI API error: '+res.status+' '+await res.text());
  const data = await res.json();
  const txt = data.choices?.[0]?.message?.content || '{}';
  return JSON.parse(txt);
}

let result;
if(OPENAI_API_KEY){
  try { result = await callOpenAI(); }
  catch (e){ console.error('[warn] OpenAI failed, using fallback:', e.message); result = fallbackDemo(); }
} else { result = fallbackDemo(); }

if(!result || typeof result !== 'object') result = fallbackDemo();
let html = String(result.html||'');
if(!html || hasExternal(html)){ html = fallbackDemo().html; }
html = ensureCSP(html);

const title = String(result.title||'Untitled').slice(0,80).trim() || 'Untitled';
const description = String(result.description||'').trim();
const to_next = String(result.to_next||'').trim();
const cover_prompt = String(result.cover_prompt||'').trim();

await fs.writeFile(path.join(OUTDIR, `demo-${DATE}.html`), html, 'utf8');
const readme = `${title}\n\nDescription:\n${description}\n\nTO_NEXT: ${to_next}\nCOVER: ${cover_prompt}\n`;
await fs.writeFile(path.join(OUTDIR, `readme-${DATE}.txt`), readme, 'utf8');

console.log(JSON.stringify({ date: DATE, title }, null, 2));
