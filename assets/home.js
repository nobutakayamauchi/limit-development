const ITEMS=[
 {name:'FOUNDRY GROWTH ENGINE',short:'FGE',kind:'PRODUCT',cats:['production','product'],killer:'仕事してください。',desc:'仕事の簡単な報告から、更新情報・記事・SNS投稿用の文章まで整えます。',definition:'発信作業を、もう一仕事にしないための投稿支援ツールです。',url:'products/foundry-growth-engine.html'},
 {name:'ULTIMATE LOOP',short:'∞',kind:'METHOD / RESEARCH',cats:['research'],killer:'一からの新造、やめてください。',desc:'今ある道具や過去の部品を先に探し、組み合わせても足りない部分だけを新しく作ります。',definition:'無駄な開発を減らすための開発手法です。',url:'products/ultimate-loop.html'},
 {name:'WEB AI BRIDGE',short:'W',kind:'PRODUCTION',cats:['production','product'],killer:'AIを、自分の場所で使えるようにします。',desc:'AI機能を、自分のサイトや仕組みへつなぎやすくするための橋を作ります。',definition:'AIとWebをつなぐための接続基盤です。',url:'products/webai-bridge.html'},
 {name:'BRIDGE PATCH',short:'B',kind:'PRODUCTION',cats:['production','product'],killer:'ここ直せば、大体直ります。',desc:'問題の中心になっている一部分を見つけて、そこだけ小さく直したり、つなぎ直したりします。',definition:'全部作り直さず、効く場所へ手を入れる改善ツールです。',url:'products/bridgepatch.html'},
 {name:'AXIS',short:'X',kind:'RESEARCH',cats:['research'],killer:'たくさんあっても、今やるのはこれだけです。',desc:'仕事や課題が増えても、優先順位を整理して「今やること」をひとつに絞ります。',definition:'迷わず次の一手を決めるための整理ツールです。',url:'products/axis.html'},
 {name:'NAGI',short:'N',kind:'PRODUCTION',cats:['production'],killer:'中断した場所？ここからです。',desc:'どこまで進んだか、次に何をするかを残して、途中から再開しやすくします。',definition:'中断と再開を楽にするツールです。',url:'products/nagi.html'},
 {name:'TRACE',short:'T',kind:'RESEARCH / EVIDENCE',cats:['research'],killer:'「何が起きた？」慌てずこれ見てください。',desc:'変更・失敗・修正の流れを記録して、あとから何が起きたかを追えるようにします。',definition:'トラブル時に状況をたどるための記録ツールです。',url:'products/trace.html'}
];
let filter='all',visible=[...ITEMS.keys()],pos=0;const $=s=>document.querySelector(s);
const els={name:$('#name'),kind:$('#kind'),killer:$('#killer'),desc:$('#desc'),definition:$('#definition'),detail:$('#detail'),visualName:$('#visualName'),visualCode:$('#visualCode'),dots:$('#dots'),thumbs:$('#thumbs')};
function rebuild(){visible=ITEMS.map((x,i)=>({x,i})).filter(o=>filter==='all'||o.x.cats.includes(filter)).map(o=>o.i);if(!visible.length)visible=[0];pos=0;render()}
function render(){const idx=visible[pos%visible.length],x=ITEMS[idx];els.name.textContent=x.name;els.kind.textContent=`${x.name} · ${x.kind}`;els.killer.textContent=x.killer;els.desc.textContent=x.desc;els.definition.textContent=x.definition;els.detail.href=x.url;els.visualName.innerHTML=x.name.replaceAll(' ','<br>');els.visualCode.textContent=x.short;els.dots.innerHTML='';visible.forEach((v,i)=>{const b=document.createElement('button');b.className='dot'+(i===pos?' active':'');b.setAttribute('aria-label',`${i+1}番目へ`);b.onclick=()=>{pos=i;render()};els.dots.appendChild(b)});els.thumbs.innerHTML='';visible.forEach((v,i)=>{const x=ITEMS[v],b=document.createElement('button');b.className='thumb'+(i===pos?' active':'');b.innerHTML=`<span class="thumbmark">${x.short}</span><span>${x.name}</span>`;b.onclick=()=>{pos=i;render()};els.thumbs.appendChild(b)})}
function move(n){pos=(pos+n+visible.length)%visible.length;render()}
$('#prev').onclick=()=>move(-1);$('#next').onclick=()=>move(1);document.querySelectorAll('.filter').forEach(b=>b.onclick=()=>{document.querySelectorAll('.filter').forEach(x=>x.classList.remove('active'));b.classList.add('active');filter=b.dataset.filter;rebuild()});$('#allIndex').onclick=()=>{filter='all';document.querySelectorAll('.filter').forEach(x=>x.classList.toggle('active',x.dataset.filter==='all'));rebuild();$('#carousel').scrollIntoView({behavior:'smooth',block:'center'})};
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
 const day=typeof j.date==='string'?j.date:'';time.textContent=day.length>=10?`${day.slice(5,7)}.${day.slice(8,10)}`:day;a.textContent=String(j.title||'開発日誌');a.href=`journal/${encodeURIComponent(day)}.html`;arr.className='arr';arr.textContent='›';li.append(time,a,arr);return li;
}
async function loadJson(path){const r=await fetch(path,{cache:'no-store'});if(!r.ok)throw new Error(`${path}: ${r.status}`);return r.json()}
async function loadLiveBoards(){
 const updateFeed=$('#updateFeed'),journalFeed=$('#journalFeed');
 try{const updates=await loadJson('data/updates.json');if(Array.isArray(updates)&&updates.length&&updateFeed){updateFeed.replaceChildren(...updates.slice(0,5).map(updateRow));const all=$('#updateAllLink');if(all)all.href='updates/'}}catch(_){/* reviewed FGE bundle not published yet: keep static fallback */}
 try{const journals=await loadJson('data/journals.json');if(Array.isArray(journals)&&journals.length&&journalFeed){journalFeed.replaceChildren(...journals.slice(0,5).map(journalRow));const idx=$('#journalIndexLink');if(idx)idx.href='archive/'}}catch(_){/* keep static fallback */}
}
render();loadLiveBoards();