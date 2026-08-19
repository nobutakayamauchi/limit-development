from __future__ import annotations
from html import escape
import json
from pathlib import Path
from ..core import search_documents, build_sns_drafts

CSS = '''
:root{--ink:#0b1835;--blue:#0b63f6;--muted:#68738a;--line:#dfe6f2;--wash:#f6f9ff;--good:#0e9f6e}*{box-sizing:border-box}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:linear-gradient(180deg,#eef4fb,#fff 260px);color:var(--ink)}a{color:inherit}.shell{max-width:1160px;margin:0 auto;padding:24px}.board{background:#fff;border:1px solid var(--line);border-radius:24px;box-shadow:0 22px 60px rgba(21,45,85,.12);overflow:hidden}.top{padding:26px 30px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:18px;align-items:flex-start}.brand{font-size:12px;letter-spacing:.14em;font-weight:800;color:var(--blue)}h1{margin:8px 0 4px;font-size:32px;letter-spacing:-.03em}.sub{color:var(--muted);font-size:14px}.online{white-space:nowrap;text-align:right;font-size:13px}.dot{color:var(--good)}.grid{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(260px,.8fr)}.panel{padding:28px 30px}.panel+.panel{border-left:1px solid var(--line)}h2{font-size:18px;margin:0 0 18px}.update{padding:18px 0;border-top:1px solid var(--line)}.update:first-of-type{border-top:0}.meta{font-size:12px;color:var(--muted);display:flex;gap:10px;flex-wrap:wrap}.badge{color:var(--blue);font-weight:800}.update h3{font-size:18px;margin:8px 0 6px}.update p{margin:0;color:#39465f;line-height:1.65}.journal{display:block;padding:14px 0;border-top:1px solid var(--line);text-decoration:none}.journal:first-of-type{border-top:0}.journal b{display:block;margin-top:4px}.cta{display:inline-flex;margin-top:16px;padding:10px 14px;border:1px solid var(--blue);border-radius:999px;text-decoration:none;color:var(--blue);font-weight:700;font-size:13px}.hero-note{padding:14px 30px;background:var(--wash);border-bottom:1px solid var(--line);font-size:14px}.article{max-width:820px;margin:0 auto;padding:34px 30px 60px}.article h1{font-size:34px}.article p{line-height:1.85;color:#34405a;white-space:pre-wrap}.search{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:10px;margin-bottom:18px}.search input,.search select{width:100%;padding:12px;border:1px solid var(--line);border-radius:12px;background:white;font:inherit}.result{padding:16px 0;border-top:1px solid var(--line)}.result small{color:var(--muted)}.result a{text-decoration:none}.result h3{margin:5px 0}.review{padding:16px;border:1px dashed #9db8ee;border-radius:16px;background:#f8fbff;margin-top:20px}.review strong{display:block;margin-bottom:6px}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.actions span{padding:9px 12px;border-radius:999px;border:1px solid var(--line);font-size:13px}@media(max-width:760px){.shell{padding:12px}.top{padding:22px 20px;display:block}.online{text-align:left;margin-top:14px}.grid{grid-template-columns:1fr}.panel{padding:22px 20px}.panel+.panel{border-left:0;border-top:1px solid var(--line)}h1{font-size:28px}.hero-note{padding:12px 20px}.search{grid-template-columns:1fr 1fr}.search input{grid-column:1/-1}.article{padding:26px 20px 50px}.article h1{font-size:30px}}@media(max-width:430px){.board{border-radius:20px}.panel{padding:20px 18px}}@media(max-width:390px){.search{grid-template-columns:1fr}.shell{padding:8px}.board{border-radius:18px}}@media(max-width:375px){h1{font-size:26px}.top{padding:20px 16px}.panel{padding:18px 16px}}
'''

def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text, encoding='utf-8')

def _page(title, body):
    return f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><style>{CSS}</style></head><body>{body}</body></html>'

def render_site(output_dir, updates, articles, journals, checked_at):
    out=Path(output_dir); data=out/'data'; data.mkdir(parents=True,exist_ok=True)
    _write(data/'updates.json',json.dumps([u.to_dict() for u in updates],ensure_ascii=False,indent=2))
    _write(data/'articles.json',json.dumps([a.to_dict() for a in articles],ensure_ascii=False,indent=2))
    _write(data/'journals.json',json.dumps([j.to_dict() for j in journals],ensure_ascii=False,indent=2))
    _write(data/'search-index.json',json.dumps(search_documents(updates,articles,journals),ensure_ascii=False,indent=2))
    _write(data/'status.json',json.dumps({'checked_at':checked_at,'window_updates':len(updates)},ensure_ascii=False,indent=2))

    rows=[]
    for u in updates[:12]:
        t=u.captured_at[11:16] if len(u.captured_at)>=16 else ''
        art=next((a for a in articles if a.update_id==u.id),None)
        link=f'<a class="cta" href="../articles/{escape(art.id)}.html">詳しく見る</a>' if art else ''
        rows.append(f'<article class="update" id="u-{escape(u.id)}"><div class="meta"><span>{escape(t)}</span><span class="badge">{escape(u.type)}</span><span>{escape(u.project)}</span></div><h3>{escape(u.title)}</h3><p>{escape(u.summary)}</p>{link}</article>')
    jrows=''.join(f'<a class="journal" href="../journal/{escape(j.date)}.html"><small>{escape(j.date)}</small><b>{escape(j.title)}</b></a>' for j in journals[:5])
    checked=checked_at.replace('T',' ')[:16]
    body=f'<main class="shell"><section class="board"><header class="top"><div><div class="brand">LIMIT OVER DEVELOPMENT / WEB OPEN FOUNDRY</div><h1>更新情報</h1><div class="sub">仕事から生まれた変更を、一般向けの言葉で。</div></div><div class="online"><div><span class="dot">●</span> FOUNDRY ONLINE</div><div class="sub">最終確認 {escape(checked)}</div></div></header><div class="hero-note"><strong>仕事してください。公開直前まで、こっちでやっときます。</strong></div><div class="grid"><section class="panel"><h2>LATEST UPDATES</h2>{"".join(rows) or "<p class=sub>意味のある変更はまだありません。監視を継続しています。</p>"}</section><aside class="panel"><h2>開発日誌</h2>{jrows or "<p class=sub>日誌はまだありません。</p>"}<a class="cta" href="../archive/">それ以前を検索</a></aside></div></section></main>'
    _write(out/'updates/index.html',_page('更新情報 | LIMIT OVER DEVELOPMENT',body))

    update_map={u.id:u for u in updates}
    review_rows=[]
    for a in articles:
        sns=build_sns_drafts(update_map[a.update_id])
        public_body=f'<main class="shell"><section class="board article"><div class="brand">LIMIT OVER DEVELOPMENT / ARTICLE</div><h1>{escape(a.title)}</h1><p><strong>{escape(a.dek)}</strong></p><p>{escape(a.body)}</p><a class="cta" href="../../updates/">更新情報へ戻る</a></section></main>'
        _write(out/f'articles/{a.id}.html',_page(a.title,public_body))
        review_rows.append(f'<article class="update"><div class="meta"><span class="badge">記事候補</span><span>{escape(a.project)}</span></div><h3><a href="../articles/{escape(a.id)}.html">{escape(a.title)}</a></h3><p>{escape(a.dek)}</p><div class="review"><strong>SNS draft</strong><div class="sub">{escape(sns["x"])}</div></div></article>')

    review_body=f'<main class="shell"><section class="board"><header class="top"><div><div class="brand">HUMAN REVIEW GATE</div><h1>レビューこれです。投稿しますか？</h1><div class="sub">生成は自動。公開だけは人間が決めます。</div></div></header><section class="panel">{"".join(review_rows) or "<p class=sub>今回、記事候補はありません。</p>"}<div class="review"><strong>最終判断</strong><div class="actions"><span>投稿</span><span>修正</span><span>記録だけ</span></div><div class="sub">GitHub v0: 投稿=reviewed publish / 修正=再生成 / 記録だけ=公開しない</div></div></section></section></main>'
    _write(out/'review/index.html',_page('FGE Review Gate',review_body))

    for j in journals:
        items=[update_map[i] for i in j.update_ids if i in update_map]
        jr=''.join(f'<article class="update"><div class="meta"><span class="badge">{escape(u.type)}</span><span>{escape(u.project)}</span></div><h3>{escape(u.title)}</h3><p>{escape(u.summary)}</p></article>' for u in items)
        body=f'<main class="shell"><section class="board article"><div class="brand">DEVELOPMENT JOURNAL / {escape(j.date)}</div><h1>{escape(j.title)}</h1><p>{escape(j.summary)}</p>{jr}<a class="cta" href="../../archive/">INDEXへ</a></section></main>'
        _write(out/f'journal/{j.date}.html',_page(j.title,body))

    archive='''<main class="shell"><section class="board"><header class="top"><div><div class="brand">DEVELOPMENT INDEX</div><h1>過去の記録を探す</h1><div class="sub">UPDATE / ARTICLE / JOURNAL を横断検索。</div></div></header><section class="panel"><div class="search"><input id="q" placeholder="キーワード"><select id="project"><option value="">PROJECT: ALL</option></select><select id="type"><option value="">TYPE: ALL</option></select><input id="date" type="month"></div><div id="results"></div></section></section></main><script>const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let docs=[];const q=document.querySelector('#q'),project=document.querySelector('#project'),type=document.querySelector('#type'),date=document.querySelector('#date'),results=document.querySelector('#results');function option(sel,values){[...new Set(values.filter(Boolean))].sort().forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;sel.appendChild(o)})}function render(){const n=q.value.trim().toLowerCase(),pm=project.value,tm=type.value,dm=date.value;const hit=docs.filter(d=>{const h=[d.title,d.summary,d.project,d.type,...(d.tags||[])].join(' ').toLowerCase();return(!n||h.includes(n))&&(!pm||d.project===pm)&&(!tm||d.type===tm)&&(!dm||d.date.startsWith(dm))});results.innerHTML=hit.map(d=>`<article class="result"><small>${esc(d.kind)} · ${esc(d.date)} · ${esc(d.project)} · ${esc(d.type)}</small><a href="${esc(d.href)}"><h3>${esc(d.title)}</h3></a><div class="sub">${esc(d.summary)}</div></article>`).join('')||'<p class="sub">該当する記録はありません。</p>'}fetch('../data/search-index.json').then(r=>r.json()).then(x=>{docs=x;option(project,docs.map(d=>d.project));option(type,docs.map(d=>d.type));render()}).catch(()=>{results.textContent='INDEXを読み込めませんでした。'});[q,project,type,date].forEach(el=>el.addEventListener('input',render));</script>'''
    _write(out/'archive/index.html',_page('開発INDEX | LIMIT OVER DEVELOPMENT',archive))
