const SALES_CATALOG='https://nobutakayamauchi.github.io/sales-catalog/';
const ITEMS=[
 {name:'INVOICE PAYMENT OPS',short:'¥',kind:'PRODUCT / PRODUCTION',cats:['production','product'],killer:'請求した後まで、終わらせます。',desc:'見積・納品・請求・入金確認・領収書までを、同じ取引IDでChatGPTから扱います。',definition:'請求業務を最後まで閉じるための請求・入金管理セットです。',url:`${SALES_CATALOG}products/invoice-payment-ops/`,salesUrl:`${SALES_CATALOG}products/invoice-payment-ops/sales.html`},
 {name:'WEB AI BRIDGE',short:'W',kind:'PRODUCT / PRODUCTION',cats:['production','product'],killer:'AIを、自分の場所で使えるようにします。',desc:'AI機能を、自分のサイトや仕組みへつなぎやすくするための橋を作ります。',definition:'AIとWebをつなぐための接続基盤です。',url:'products/webai-bridge.html',salesUrl:`${SALES_CATALOG}products/webai-bridge/`},
 {name:'BRIDGE PATCH',short:'B',kind:'SERVICE / PRODUCTION',cats:['production','product'],killer:'ここ直せば、大体直ります。',desc:'問題の中心になっている一部分を見つけて、そこだけ小さく直したり、つなぎ直したりします。',definition:'全部作り直さず、効く場所へ手を入れる一点改善サービスです。',url:'products/bridgepatch.html',salesUrl:`${SALES_CATALOG}products/bridgepatch/sales.html`},
 {name:'AXIS',short:'X',kind:'SERVICE / RESEARCH',cats:['research','product'],killer:'たくさんあっても、今やるのはこれだけです。',desc:'仕事や課題が増えても、優先順位を整理して「今やること」をひとつに絞ります。',definition:'困っている一点を実装可能な仕様書と見積書へ落とす設計サービスです。',url:'products/axis.html',salesUrl:`${SALES_CATALOG}products/axis/sales.html`},
 {name:'ULTIMATE LOOP',short:'∞',kind:'METHOD / RESEARCH',cats:['research'],killer:'一からの新造、やめてください。',desc:'今ある道具や過去の部品を先に探し、組み合わせても足りない部分だけを新しく作ります。',definition:'無駄な開発を減らすための開発手法です。',url:'products/ultimate-loop.html'},
 {name:'NAGI',short:'N',kind:'PRODUCTION',cats:['production'],killer:'中断した場所？ここからです。',desc:'どこまで進んだか、次に何をするかを残して、途中から再開しやすくします。',definition:'中断と再開を楽にするツールです。',url:'products/nagi.html'},
 {name:'TRACE',short:'T',kind:'RESEARCH / EVIDENCE',cats:['research'],killer:'「何が起きた？」慌てずこれ見てください。',desc:'変更・失敗・修正の流れを記録して、あとから何が起きたかを追えるようにします。',definition:'トラブル時に状況をたどるための記録ツールです。',url:'products/trace.html'}
];
let filter='all',visible=[...ITEMS.keys()],pos=0;const $=s=>document.querySelector(s);
const els={name:$('#name'),kind:$('#kind'),killer:$('#killer'),desc:$('#desc'),definition:$('#definition'),detail:$('#detail'),visualName:$('#visualName'),visualCode:$('#visualCode'),dots:$('#dots'),thumbs:$('#thumbs')};
function ensureSalesLinks(){
 const detail=els.detail;if(detail&&!$('#salesDetail')){const a=document.createElement('a');a.id='salesDetail';a.className='detail';a.hidden=true;a.style.marginLeft='14px';a.textContent='販売中の商品を見る →';detail.insertAdjacentElement('afterend',a)}
 const rail=document.querySelector('.rail');if(rail&&!$('#salesCatalog')){const a=document.createElement('a');a.id='salesCatalog';a.className='allindex';a.href=SALES_CATALOG;a.style.cssText='display:grid;place-items:center;text-align:center;text-decoration:none;padding:8px';a.innerHTML='SALES CATALOG<br><small>販売中の商品を見る →</small>';rail.appendChild(a)}
}
function rebuild(){visible=ITEMS.map((x,i)=>({x,i})).filter(o=>filter==='all'||o.x.cats.includes(filter)).map(o=>o.i);if(!visible.length)visible=[0];pos=0;render()}
function render(){const idx=visible[pos%visible.length],x=ITEMS[idx];els.name.textContent=x.name;els.kind.textContent=`${x.name} · ${x.kind}`;els.killer.textContent=x.killer;els.desc.textContent=x.desc;els.definition.textContent=x.definition;els.detail.href=x.url;const sales=$('#salesDetail');if(sales){sales.hidden=!x.salesUrl;if(x.salesUrl)sales.href=x.salesUrl}els.visualName.innerHTML=x.name.replaceAll(' ','<br>');els.visualCode.textContent=x.short;els.dots.innerHTML='';visible.forEach((v,i)=>{const b=document.createElement('button');b.className='dot'+(i===pos?' active':'');b.setAttribute('aria-label',`${i+1}番目へ`);b.onclick=()=>{pos=i;render()};els.dots.appendChild(b)});els.thumbs.innerHTML='';visible.forEach((v,i)=>{const x=ITEMS[v],b=document.createElement('button');b.className='thumb'+(i===pos?' active':'');b.innerHTML=`<span class="thumbmark">${x.short}</span><span>${x.name}</span>`;b.onclick=()=>{pos=i;render()};els.thumbs.appendChild(b)})}
function move(n){pos=(pos+n+visible.length)%visible.length;render()}
$('#prev').onclick=()=>move(-1);$('#next').onclick=()=>move(1);document.querySelectorAll('.filter').forEach(b=>b.onclick=()=>{document.querySelectorAll('.filter').forEach(x=>x.classList.remove('active'));b.classList.add('active');filter=b.dataset.filter;rebuild()});$('#allIndex').onclick=()=>{window.location.href='works/'};
let sx=0;$('#carousel').addEventListener('touchstart',e=>sx=e.changedTouches[0].clientX,{passive:true});$('#carousel').addEventListener('touchend',e=>{const dx=e.changedTouches[0].clientX-sx;if(Math.abs(dx)>45)move(dx<0?1:-1)},{passive:true});$('#carousel').addEventListener('keydown',e=>{if(e.key==='ArrowLeft')move(-1);if(e.key==='ArrowRight')move(1)});$('#carousel').tabIndex=0;
const menu=$('#menu'),mobile=$('#mobileNav');menu.onclick=()=>{const open=mobile.classList.toggle('open');menu.setAttribute('aria-expanded',String(open));menu.textContent=open?'×':'☰'};mobile.querySelectorAll('a').forEach(a=>a.onclick=()=>{mobile.classList.remove('open');menu.setAttribute('aria-expanded','false');menu.textContent='☰'});

function updateRow(u){
 const li=document.createElement('li'),time=document.createElement('time'),tag=document.createElement('span'),a=document.createElement('a'),arr=document.createElement('span');
 const day=typeof u.captured_at==='string'?u.captured_at.slice(0,10):'';
 time.textContent=day.replaceAll('-','.');tag.className='tag';tag.textContent=String(u.type||'UPDATE');a.textContent=String(u.title||'更新');a.href=`updates/#u-${encodeURIComponent(String(u.id||''))}`;arr.className='arr';arr.textContent='›';
 li.append(time,tag,a,arr);return li;
}
function journalRow(j){
 const li=document.createElement('li'),time=document.createElement('time'),a=document.createElement('a'),arr=document.createElement('span');
 const day=typeof j.date==='string'?j.date:'';time.textContent=day.length>=10?`${day.slice(5,7)}.${day.slice(8,10)}`:day;a.textContent=String(j.title||'開発日誌');a.href=`journal/${encodeURIComponent(day)}.html`;li.append(time,a,arr);arr.className='arr';arr.textContent='›';return li;
}
function wireJournalNavigation(){
 document.querySelectorAll('.nav a,.mobile-nav a').forEach(a=>{if(a.textContent.trim()==='JOURNAL')a.href='journal/'});
 const footerJournal=[...document.querySelectorAll('.footcol')].find(col=>col.querySelector('b')?.textContent.trim()==='JOURNAL');
 if(footerJournal){const links=footerJournal.querySelectorAll('a');if(links[0])links[0].href='journal/';if(links[1])links[1].href='journal/';if(links[2])links[2].href='journal/'}
 const index=$('#journalIndexLink');if(index)index.href='journal/';
 const feed=$('#journalFeed');if(feed){feed.querySelectorAll('li').forEach(li=>{const t=li.querySelector('time'),a=li.querySelector('a');if(!t||!a)return;const bits=t.textContent.trim().split('.');if(bits.length===2)a.href=`journal/2026-${bits[0]}-${bits[1]}.html`})}
}
async function loadJson(path){const r=await fetch(path,{cache:'no-store'});if(!r.ok)throw new Error(`${path}: ${r.status}`);return r.json()}
function showHourlyStatus(status){
 const small=document.querySelector('#journal .paneltitle small');if(!small)return;
 const raw=typeof status?.checked_at==='string'?status.checked_at:'';
 if(!raw){small.textContent='LIVE BOARD';return}
 const d=new Date(raw);const hh=Number.isNaN(d.getTime())?raw.slice(11,16):new Intl.DateTimeFormat('ja-JP',{hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Tokyo'}).format(d);
 small.textContent=`LIVE BOARD · 最終確認 ${hh} · 監視継続中`;
}
async function loadLiveBoards(){
 const updateFeed=$('#updateFeed'),journalFeed=$('#journalFeed');
 try{const updates=await loadJson('data/updates.json');if(Array.isArray(updates)&&updates.length&&updateFeed){updateFeed.replaceChildren(...updates.slice(0,5).map(updateRow));const all=$('#updateAllLink');if(all)all.href='updates/'}}catch(_){/* reviewed FGE bundle not published yet: keep static fallback */}
 try{const journals=await loadJson('data/journals.json');if(Array.isArray(journals)&&journals.length&&journalFeed){journalFeed.replaceChildren(...journals.slice(0,5).map(journalRow));const idx=$('#journalIndexLink');if(idx)idx.href='journal/'}}catch(_){/* keep static fallback */}
 try{showHourlyStatus(await loadJson('data/status.json'))}catch(_){showHourlyStatus(null)}
}
ensureSalesLinks();render();wireJournalNavigation();loadLiveBoards();
