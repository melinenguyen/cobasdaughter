'use strict';
const el = id => document.getElementById(id);
const number = x => x === null || x === undefined ? 'Unavailable' : Number(x).toLocaleString();
const charts = {};
const today = new Date();
el('to').value = today.toISOString().slice(0,10);
el('from').value = new Date(today.getTime()-29*86400000).toISOString().slice(0,10);
function chart(id, labels, datasets) {
  if (!window.Chart) { el('message').textContent = 'Charts could not load; the data table remains available.'; return; }
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(el(id), {type:'line',data:{labels,datasets},options:{responsive:true,maintainAspectRatio:false,animation:false,spanGaps:false,plugins:{legend:{position:'bottom'}},scales:{y:{beginAtZero:true}}}});
}
function cell(tr, value) {const td=document.createElement('td');td.textContent=value;tr.append(td);}
function render(data) {
  const c=data.current,p=data.prior;
  const sum=(rows,key)=>rows.length?rows.reduce((n,r)=>n+r[key],0):null;
  el('impressions').textContent=number(sum(c.search,'impressions'));
  el('clicks').textContent=number(sum(c.search,'clicks'));
  el('videos').textContent=number(c.tiktok.length?c.tiktok[c.tiktok.length-1].posts:null);
  el('comparison').textContent=`Prior reported clicks: ${number(sum(p.search,'clicks'))} (${data.prior_from} – ${data.prior_to}). Totals cover reported days only.`;
  const days=[]; for(let d=new Date(data.from+'T00:00:00Z');d<=new Date(data.to+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+1))days.push(d.toISOString().slice(0,10));
  const series=(rows,key)=>{const m=new Map(rows.map(r=>[r.day,r[key]]));return days.map(d=>m.has(d)?m.get(d):null);};
  chart('search',days,[{label:'Reported impressions',data:series(c.search,'impressions'),borderColor:'#206d54',pointRadius:2}]);
  chart('social',days,[{label:'Instagram test sample',data:series(c.instagram,'posts'),borderColor:'#bf8144',pointRadius:4},{label:'TikTok owned videos',data:series(c.tiktok,'posts'),borderColor:'#206d54',pointRadius:4}]);
  el('sources').replaceChildren();
  for(const [key,label] of [['google_search_console','Google Search Console'],['tiktok','TikTok']]) {
    const r=c.runs.find(x=>x.source===key);const div=document.createElement('div');div.className='source';
    const b=document.createElement('b');b.textContent=label;const badge=document.createElement('span');badge.className='badge';badge.textContent=r?r.status:'Not collected';
    const text=document.createElement('p');text.textContent=r?`${r.detail} Updated ${r.updated}`:'No successful collection recorded. Connect in Private setup, then collect latest data.';
    div.append(b,badge,text);el('sources').append(div);
  }
  const info=document.createElement('p');info.textContent='Instagram: stored test sample only. Reddit, public web and other creators’ Instagram/TikTok mentions: unavailable. Total search volume and reach: unavailable.';el('sources').append(info);
  el('rows').replaceChildren();
  const rows=[...c.search.map(r=>({...r,source:'Google Search Console'})),...c.instagram.map(r=>({...r,source:'Instagram sample'})),...c.tiktok.map(r=>({...r,source:'TikTok owned'}))].sort((a,b)=>b.day.localeCompare(a.day));
  for(const r of rows) {const tr=document.createElement('tr');[r.day,r.source,...['posts','impressions','clicks','likes','comments'].map(k=>r[k]===undefined?'—':number(r[k]))].forEach(v=>cell(tr,v));el('rows').append(tr);}
  if(!rows.length){const tr=document.createElement('tr');cell(tr,'No collected data in this date range.');el('rows').append(tr);}
}
async function load() {
  el('message').textContent='Loading…';
  try {const params=new URLSearchParams({from:el('from').value,to:el('to').value,compare:el('compare').value});const res=await fetch('/api/pulse/data?'+params);if(res.status===401)throw Error('Sign in again by reloading this page.');const data=await res.json();if(!res.ok)throw Error(data.error);el('message').textContent='Stored data loaded. Use Collect latest data to update TikTok and Google.';render(data);}catch(e){el('message').textContent=e.message||'Unable to load data.';}
}
el('filters').addEventListener('submit',e=>{e.preventDefault();load();});
el('sync').addEventListener('click',async()=>{el('sync').disabled=true;try{const res=await fetch('/api/pulse/refresh',{method:'POST',headers:{'X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content}});const data=await res.json();el('message').textContent=data.message||data.error;}catch(e){el('message').textContent='Collection request could not be confirmed. Reload data before retrying.';}finally{el('sync').disabled=false;}});
load();
