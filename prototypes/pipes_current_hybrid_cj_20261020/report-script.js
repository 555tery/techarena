
const data=JSON.parse(document.getElementById('data').textContent);
const byId=id=>document.getElementById(id);
const fmt=(v,n)=>typeof v==='number'&&Number.isFinite(v)?v.toFixed(n):'—';
function show(){
 const q=byId('query').value.toLowerCase(),group=byId('cohort').value,order=byId('order').value;
 let rows=data.filter(r=>(!group||(group==='open'?r.open!==null:r.cohort===group))&&[r.name,r.family,r.id].join(' ').toLowerCase().includes(q));
 rows.sort((a,b)=>order==='gain'?b.delta-a.delta:order==='cpu'?b.cpu_h-a.cpu_h:order==='memory'?b.mem_h-a.mem_h:a.delta-b.delta);
 byId('count').textContent=`Найдено ${rows.length}; показано до 300. Полный набор — в analysis.json.`;
 const body=byId('cases');body.replaceChildren();
 for(const r of rows.slice(0,300)){
  const tr=document.createElement('tr'),title=document.createElement('td'),a=document.createElement('a');
  a.href=r.input;a.textContent=r.open!==null?`Open ${r.open}`:r.cohort==='fresh'?r.name:r.id.slice(0,16);
  title.append(a);const family=document.createElement('div');family.className='tiny muted';family.textContent=r.family;title.append(family);tr.append(title);
  const vals=[r.n,r.online.toFixed(6),r.hybrid.toFixed(6),(r.delta>=0?'+':'')+r.delta.toFixed(6),`${fmt(r.cpu_o,4)} / ${fmt(r.cpu_h,4)}`,`${fmt(r.mem_o,2)} / ${fmt(r.mem_h,2)}`,r.diagnostic];
  vals.forEach((v,i)=>{const td=document.createElement('td');td.textContent=v;if(i===3)td.className=r.delta<0?'down':'up';if(i===6)td.className='tiny';tr.append(td)});body.append(tr);
 }
}
for(const id of ['query','cohort','order'])byId(id).addEventListener('input',show);show();
