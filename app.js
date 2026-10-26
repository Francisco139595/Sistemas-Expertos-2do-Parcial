// Interfaz: tablas, dibujo del árbol (SVG), pasos y modelos

// ================= Interfaz =================
const $=id=>document.getElementById(id);
const esc=s=>s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const KW=W('si y solo si|no es cierto que|no es verdad que|es falso que|solo si|siempre que|en caso de que|entonces|implica que|implica|cuando|si|pero|aunque|ademas|sin embargo|o bien|ni|no|tampoco|y|e|o|u');
function highlight(raw){
  const n=normChars(raw);let out='',p=0,m;KW.lastIndex=0;
  while((m=KW.exec(n))){out+=esc(raw.slice(p,m.index))+'<span class="kw">'+esc(raw.slice(m.index,m.index+m[0].length))+'</span>';p=m.index+m[0].length;}
  return out+esc(raw.slice(p));
}
let S={an:null,rules:[],step:0,total:0,zoom:1};

function analyzeAndRender(){
  const text=$('kb').value;
  const an=analyze(text);S.an=an;S.rules=an.rules.filter(r=>r.f);
  S.total=S.rules.length?totalSteps(S.rules,an.L):0;S.step=S.total;
  renderStatic();renderTree();
}
function renderStatic(){
  const an=S.an;
  // conectivos usados
  const used=new Set();S.rules.forEach(r=>opsUsed(r.f,used));
  let cu=0;document.querySelectorAll('.conn tr[data-op]').forEach(tr=>{const on=used.has(tr.dataset.op);tr.classList.toggle('used',on);if(on)cu++;});
  $('conncount').textContent=cu+' / 5 usados';
  // átomos
  $('atomcount').textContent=an.atoms.length+(an.atoms.length===1?' átomo':' átomos');
  $('atoms').innerHTML=an.atoms.length?'<table><thead><tr><th>Letra</th><th>Significado</th></tr></thead><tbody>'+
    an.atoms.map(a=>`<tr><td><span class="letter">${a.letter}</span></td><td>${esc(a.meaning)}</td></tr>`).join('')+'</tbody></table>'+
    '<p class="hint">La misma frase en varias reglas es el mismo átomo; «no …» se representa como ¬ de ese átomo.</p>'
    :'<p class="empty">Escribe al menos una regla o un hecho.</p>';
  // reglas
  $('rulecount').textContent=S.rules.length+(S.rules.length===1?' regla':' reglas');
  $('rules').innerHTML=an.rules.length?an.rules.map(r=>r.error
    ?`<div class="rule err"><span class="rl">!</span><span class="tx">${esc(r.raw)}</span><span class="fx">No se pudo traducir: ${esc(r.error)}</span></div>`
    :`<div class="rule"><span class="rl">${r.label}</span><span class="tx">${highlight(r.raw)}${r.inferred?' <span class="inf">«entonces» inferido</span>':''}</span><span class="fx">${esc(r.str)}</span></div>`).join('')
    :'<p class="empty">Aquí aparecerá cada regla junto a su fórmula (R1: p → q…).</p>';
  ['pp0','pp1','pp2'].forEach((id,i)=>$(id).classList.toggle('on',[an.rules.length,an.atoms.length,S.rules.length][i]>0));
}

// --- medición de texto
const cv=document.createElement('canvas').getContext('2d');
function tw(s,size,weight){cv.font=`${weight||500} ${size}px "JetBrains Mono", ui-monospace, Consolas, monospace`;return cv.measureText(s).width;}
const PADX=14,PADY=9,LH=22,GX=26,GY=52,MARK=46;

function renderTree(){
  const box=$('treebox');
  ['prev','first'].forEach(id=>$(id).disabled=S.step<=0);['next','last'].forEach(id=>$(id).disabled=S.step>=S.total);
  $('stepn').innerHTML=`Paso <b>${S.step}</b> / ${S.total}`;
  if(!S.rules.length){box.innerHTML='<p class="empty" style="padding:16px">El árbol aparecerá cuando haya reglas válidas.</p>';$('steplog').textContent='Sin reglas todavía.';$('result').innerHTML='<p class="empty">Sin resultado.</p>';['pp3','pp4'].forEach(id=>$(id).classList.remove('on'));return;}
  const an=S.an;const T=runTableau(S.rules,an.L,S.step);
  // numerar ramas abiertas
  const openIdx=new Map();if(T.done)T.open.forEach((l,i)=>openIdx.set(l.id,i+1));
  // medir
  const measure=n=>{
    let w=40;for(const e of n.entries){let x=tw(e.str,15);if(e.applied)x+=6+tw('✓'+e.applied,13,700);if(e.label)x+=12+tw(e.label,11,400);w=Math.max(w,x);}
    n.w=Math.ceil(w+PADX*2);n.h=n.entries.length*LH+PADY*2-4;
    const leaf=!n.children.length;
    if(leaf){let mw=0;if(n.closed)mw=tw(n.closeLits.join(' y '),11,400)+8;else if(T.done)mw=tw('○ ABIERTA · M'+openIdx.get(n.id),12,700)+8;else mw=tw('pendiente',11,400);n.w=Math.max(n.w,0);n.mw=mw;}
    n.children.forEach(measure);
    const cs=n.children.reduce((s,c)=>s+c.sw,0)+GX*Math.max(0,n.children.length-1);
    n.sw=Math.max(n.w,n.mw||0,cs);
  };
  measure(T.root);
  let maxY=0;
  const place=(n,cx,y)=>{n.cx=cx;n.x=cx-n.w/2;n.y=y;
    maxY=Math.max(maxY,y+n.h+(n.children.length?0:MARK));
    const cs=n.children.reduce((s,c)=>s+c.sw,0)+GX*Math.max(0,n.children.length-1);let x=cx-cs/2;
    for(const c of n.children){place(c,x+c.sw/2,y+n.h+GY);x+=c.sw+GX;}};
  const M=18;place(T.root,T.root.sw/2+M,M);
  const Wd=T.root.sw+M*2,Ht=maxY+M;
  let edges='',nodesSvg='';
  for(const n of T.nodes){
    // aristas hacia los hijos
    if(n.children.length){
      const by=n.y+n.h,sy=by+16;
      edges+=`<line class="edge" data-c="${n.children.map(c=>c.id).join(' ')}" x1="${n.cx}" y1="${by}" x2="${n.cx}" y2="${sy}"/>`;
      for(const c of n.children)edges+=`<line class="edge" data-c="${c.id}" x1="${n.cx}" y1="${sy}" x2="${c.cx}" y2="${c.y}"/>`;
      const v=n.children[0].via;
      edges+=`<text class="elbl" x="${n.cx+7}" y="${by+13}">${v.step}· ${esc(v.src.length>14?'':v.src)} ${esc(v.rule)}</text>`;
    }
    const leaf=!n.children.length;
    let cls='nd';if(n.closed)cls+=' closed';else if(leaf&&T.done)cls+=' open';if(n.step&&n.step===S.step)cls+=' new';
    let g=`<g class="${cls}" data-id="${n.id}"><rect x="${n.x}" y="${n.y}" width="${n.w}" height="${n.h}" rx="2"/>`;
    n.entries.forEach((e,i)=>{
      const ty=n.y+PADY+i*LH+15;const fw=tw(e.str,15);const lx=n.x+PADX;
      g+=`<text class="ft${e.applied?' done':''}" x="${lx}" y="${ty}">${esc(e.str)}</text>`;
      if(e.applied)g+=`<text class="ck" x="${lx+fw+6}" y="${ty}">✓${e.applied}</text>`;
      if(e.label)g+=`<text class="lbl" x="${n.x+n.w-PADX}" y="${ty}" text-anchor="end">${e.label}</text>`;
    });
    if(leaf){const b=n.y+n.h;
      if(n.closed)g+=`<text class="xm" x="${n.cx}" y="${b+22}" text-anchor="middle">✕</text><text class="xt" x="${n.cx}" y="${b+38}" text-anchor="middle">${esc(n.closeLits.join(' y '))}</text>`;
      else if(T.done)g+=`<text class="om" x="${n.cx}" y="${b+20}" text-anchor="middle">○ ABIERTA · M${openIdx.get(n.id)}</text>`;
      else g+=`<text class="pm" x="${n.cx}" y="${b+18}" text-anchor="middle">pendiente</text>`;}
    nodesSvg+=g+'</g>';
  }
  box.innerHTML=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${Wd} ${Ht}" width="${Wd*S.zoom}" height="${Ht*S.zoom}" role="img" aria-label="Árbol semántico">${edges}${nodesSvg}</svg>`;
  // bitácora del paso
  let msg;
  if(S.step===0)msg=`<b>Paso 0:</b> se parte suponiendo que todas las reglas son verdaderas (${S.rules.map(r=>r.label).join(', ')} en la raíz).`;
  else{const l=T.log[S.step-1];
    msg=`<b>Paso ${l.step}:</b> se desarrolla ${l.src?l.src+' = ':''}<span class="mono">${esc(l.str)}</span> con la regla <span class="mono">${esc(l.rule)}</span> — ${l.kind==='α'?'no bifurca: <span class="mono">'+esc(l.branches[0])+'</span>':'bifurca en <span class="mono">'+esc(l.branches[0])+'</span> | <span class="mono">'+esc(l.branches[1])+'</span>'} — en ${l.nLeaves} rama${l.nLeaves>1?'s':''} abierta${l.nLeaves>1?'s':''} de abajo.`;
    if(l.closed.length)msg+=` Se cierra${l.closed.length>1?'n':''} ${l.closed.length} rama${l.closed.length>1?'s':''} ✕ (${l.closed.map(c=>esc(c.join(' y '))).join('; ')}).`;}
  if(T.done)msg+=' <b>Fin:</b> no quedan fórmulas por desarrollar, solo letras o letras negadas.';
  $('steplog').innerHTML=msg;
  $('pp3').classList.add('on');$('pp4').classList.toggle('on',T.done);
  renderResult(T);
}
function renderResult(T){
  const an=S.an,L=an.L,nA=an.atoms.length;
  const leaves=T.nodes.filter(n=>!n.children.length);
  if(!T.done){$('result').innerHTML=`<div class="verdict"><span class="pill pend">En proceso</span><span class="hint">Avanza al último paso (⏭) para ver los modelos. Ramas cerradas hasta ahora: ${T.closedCount}.</span></div>`;return;}
  if(!T.open.length){
    $('result').innerHTML=`<div class="verdict"><span class="pill unsat">Insatisfacible</span><span>Las ${leaves.length} ramas se cierran ✕. La base de conocimiento es <b>inconsistente</b>: no existe ninguna asignación de valores en la que todas las reglas se cumplan.</span></div>`;return;}
  const models=T.open.map(l=>modelOf(l,nA));
  const anyX=models.some(m=>m.v.includes(null));
  let h=`<div class="verdict"><span class="pill sat">Satisfacible</span><span>${T.open.length} rama${T.open.length>1?'s':''} abierta${T.open.length>1?'s':''} y ${T.closedCount} cerrada${T.closedCount===1?'':'s'}. Cada rama abierta es una condición en la que <b>todas las reglas se cumplen</b>.</span></div>`;
  const firstSeen=new Map();
  h+='<div class="models">'+models.map((m,i)=>{
    const key=m.v.join(',');const dup=firstSeen.has(key)?` · igual a M${firstSeen.get(key)}`:'';if(!dup)firstSeen.set(key,i+1);
    const asg=m.v.map((x,j)=>`<span class="${x||'X'}">${L[j]} = ${x||'V/F'}</span>`).join(', ');
    const words=m.v.map((x,j)=>x==='V'?an.atoms[j].meaning:x==='F'?'no: '+an.atoms[j].meaning:null).filter(Boolean).join(' · ');
    return `<div class="model" tabindex="0" data-path="${m.path.join(' ')}"><h3>Modelo ${i+1} · rama abierta${dup}</h3><div class="assign">${asg}</div><div class="words">${esc(words)}</div></div>`;}).join('')+'</div>';
  h+='<div class="tscroll"><table><thead><tr><th>Modelo</th>'+an.atoms.map(a=>`<th title="${esc(a.meaning)}">${a.letter} · ${esc(a.meaning)}</th>`).join('')+'</tr></thead><tbody>'+
    models.map((m,i)=>`<tr><td class="mono">M${i+1}</td>${m.v.map(x=>`<td class="${x||'X'}">${x||'V/F'}</td>`).join('')}</tr>`).join('')+'</tbody></table></div>';
  if(anyX)h+='<p class="hint">V/F: esa letra no aparece en la rama, así que puede tomar cualquier valor sin romper las reglas.</p>';
  $('result').innerHTML=h;
  document.querySelectorAll('.model').forEach(el=>{
    const on=b=>{const ids=new Set(el.dataset.path.split(' '));
      document.querySelectorAll('#treebox .nd').forEach(g=>g.classList.toggle('hl',b&&ids.has(g.dataset.id)));
      document.querySelectorAll('#treebox .edge').forEach(e=>e.classList.toggle('hl',b&&e.dataset.c.split(' ').some(c=>ids.has(c))));};
    el.addEventListener('mouseenter',()=>on(true));el.addEventListener('mouseleave',()=>on(false));
    el.addEventListener('focus',()=>on(true));el.addEventListener('blur',()=>on(false));
  });
}
// --- eventos
let tmr;
$('kb').addEventListener('input',()=>{clearTimeout(tmr);tmr=setTimeout(analyzeAndRender,350);try{localStorage.setItem('mi-kb',$('kb').value)}catch(e){}});
$('run').addEventListener('click',analyzeAndRender);
$('first').onclick=()=>{S.step=0;renderTree();};
$('prev').onclick=()=>{S.step=Math.max(0,S.step-1);renderTree();};
$('next').onclick=()=>{S.step=Math.min(S.total,S.step+1);renderTree();};
$('last').onclick=()=>{S.step=S.total;renderTree();};
$('zin').onclick=()=>{S.zoom=Math.min(2.2,S.zoom*1.2);renderTree();};
$('zout').onclick=()=>{S.zoom=Math.max(0.4,S.zoom/1.2);renderTree();};
let saved=null;try{saved=localStorage.getItem('mi-kb')}catch(e){}
$('kb').value=saved&&saved.trim()?saved:'';
analyzeAndRender();
if(document.fonts&&document.fonts.ready)document.fonts.ready.then(()=>renderTree());
