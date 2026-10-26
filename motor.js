// Motor de inferencia: parser de español → fórmulas lógicas → árbol semántico (tableau)
// Sistemas Expertos 7E262 · CETI Colomos

// ================= Normalización de texto (misma longitud que el original) =================
const ACC={'á':'a','é':'e','í':'i','ó':'o','ú':'u','ü':'u','Á':'a','É':'e','Í':'i','Ó':'o','Ú':'u','Ü':'u','Ñ':'ñ'};
function normChars(s){let r='';for(let i=0;i<s.length;i++){const ch=s[i];let c=ACC[ch];if(c===undefined){c=ch.toLowerCase();if(c.length!==1)c=ch;}r+=c;}return r;}
function mk(o){return {o,n:normChars(o)}}
function sl(seg,a,b){return {o:seg.o.slice(a,b),n:seg.n.slice(a,b)}}
const TRIM=" \t\r\n,.;:¡!¿?«»\"“”'‘’";
function matchClose(n,a){let d=0;for(let i=a;i<n.length;i++){if(n[i]==='(')d++;else if(n[i]===')'){d--;if(d===0)return i;}}return -1;}
function trimSeg(seg){let a=0,b=seg.n.length;for(;;){while(a<b&&TRIM.includes(seg.n[a]))a++;while(b>a&&TRIM.includes(seg.n[b-1]))b--;if(a<b&&seg.n[a]==='('&&seg.n[b-1]===')'&&matchClose(seg.n,a)===b-1){a++;b--;continue;}break;}return sl(seg,a,b);}
function depthAt(n){const d=[];let k=0;for(let i=0;i<n.length;i++){if(n[i]===')')k=Math.max(0,k-1);d.push(k);if(n[i]==='(')k++;}return d;}
const WB='(?<![a-zñ0-9])',WE='(?![a-zñ0-9])';
const W=alts=>new RegExp(WB+'(?:'+alts+')'+WE,'g');
function allTop(seg,re){const d=depthAt(seg.n),out=[];re.lastIndex=0;let m;while((m=re.exec(seg.n))){if(!m[0].length){re.lastIndex++;continue;}if(d[m.index]===0)out.push({index:m.index,end:m.index+m[0].length});}return out;}
function firstTop(seg,re){return allTop(seg,re)[0]||null}
function splitTop(seg,re){const ms=allTop(seg,re),parts=[];let p=0;for(const m of ms){parts.push(sl(seg,p,m.index));p=m.end;}parts.push(sl(seg,p));return {parts:parts.map(trimSeg).filter(s=>s.n.length),count:ms.length};}

// ================= Fórmulas =================
const At=id=>({t:'atom',id}),N=a=>({t:'not',a}),Bin=(t,a,b)=>({t,a,b});
const OPS={and:'∧',or:'∨',imp:'→',iff:'↔'};
function fstr(f,L,top=true){if(f.t==='atom')return L[f.id];if(f.t==='not')return '¬'+fstr(f.a,L,false);const s=fstr(f.a,L,false)+' '+OPS[f.t]+' '+fstr(f.b,L,false);return top?s:'('+s+')';}
function opsUsed(f,set){set.add(f.t);if(f.a)opsUsed(f.a,set);if(f.b)opsUsed(f.b,set);return set;}

// ================= Átomos =================
const LETTERS=['p','q','r','s','t','u','w','x','y','z'];
const SUB='₀₁₂₃₄₅₆₇₈₉';
function letterFor(i){if(i<LETTERS.length)return LETTERS[i];const k=Math.floor(i/LETTERS.length);return LETTERS[i%LETTERS.length]+String(k).split('').map(d=>SUB[d]).join('');}
function makeCtx(){return {map:new Map(),list:[]}}
function atomOf(ctx,o){
  let clean=o.replace(/\s+/g,' ').trim().replace(/^[\s,.;:«»"“”']+|[\s,.;:«»"“”']+$/g,'').trim();
  clean=clean.replace(/^que\s+/i,'');
  const key=normChars(clean).replace(/[^a-zñ0-9 ]/g,'').replace(/\s+/g,' ').trim();
  if(!key)throw new Error('Hay una proposición vacía cerca de un conectivo.');
  let a=ctx.map.get(key);
  if(!a){let m=clean;if(/^[A-ZÁÉÍÓÚÑ][a-záéíóúüñ]/.test(m))m=m[0].toLowerCase()+m.slice(1);
    a={id:ctx.list.length,letter:letterFor(ctx.list.length),meaning:m,key};ctx.map.set(key,a);ctx.list.push(a);}
  return At(a.id);
}

// ================= Parser de español =================
// Precedencia (de menor a mayor): ↔, →, ∨, ∧, ¬
function parse(seg,ctx){
  seg=trimSeg(seg);
  if(!seg.n)throw new Error('Falta una proposición.');
  const n=seg.n;let m,i;
  // «no es cierto que …»: niega todo lo que sigue
  m=n.match(/^(no es cierto que|no es verdad que|es falso que|no ocurre que|no sucede que|no se cumple que)(?![a-zñ0-9])/);
  if(m)return N(parse(sl(seg,m[0].length),ctx));
  // ↔
  i=firstTop(seg,W('si y solo si|sii'));
  if(i){
    if(i.index===0){const rest=sl(seg,i.end);const c=firstTop(rest,W('entonces'))||firstTop(rest,/,/g);
      if(!c)throw new Error('Después de «si y solo si …» falta una coma.');
      return Bin('iff',parse(sl(rest,0,c.index),ctx),parse(sl(rest,c.end),ctx));}
    return Bin('iff',parse(sl(seg,0,i.index),ctx),parse(sl(seg,i.end),ctx));
  }
  // → con «si» al inicio
  m=n.match(/^(si|cuando|siempre que|en caso de que)(?![a-zñ0-9])/);
  if(m){const rest=sl(seg,m[0].length);
    const e=firstTop(rest,W('entonces'))||firstTop(rest,/,/g);
    if(!e)throw new Error('Después de «si …» escribe «entonces» o una coma.');
    return Bin('imp',parse(sl(rest,0,e.index),ctx),parse(sl(rest,e.end),ctx));}
  // → en medio
  i=firstTop(seg,W('entonces|implica que|implica'));
  if(i)return Bin('imp',parse(sl(seg,0,i.index),ctx),parse(sl(seg,i.end),ctx));
  i=firstTop(seg,W('solo si'));
  if(i)return Bin('imp',parse(sl(seg,0,i.index),ctx),parse(sl(seg,i.end),ctx));
  i=firstTop(seg,W('si'));
  if(i&&i.index>0)return Bin('imp',parse(sl(seg,i.end),ctx),parse(sl(seg,0,i.index),ctx)); // «Q si P» = P → Q
  // ∨
  let s=seg;if(/^(o|u)\s/.test(n)&&firstTop(sl(seg,2),W('o|u')))s=sl(seg,2); // «o P o Q»
  let sp=splitTop(s,W('o bien|o|u'));
  if(sp.count){if(sp.parts.length<2)throw new Error('A la «o» le falta una de sus dos partes.');
    return sp.parts.map(p=>parse(p,ctx)).reduce((a,b)=>Bin('or',a,b));}
  // ni … ni
  if(/^(ni|no)\s/.test(n)&&firstTop(sl(seg,3),W('ni'))){
    const st=sl(seg,n.startsWith('ni')?2:2);const sp2=splitTop(st,W('ni'));
    return sp2.parts.map(p=>N(parse(p,ctx))).reduce((a,b)=>Bin('and',a,b));}
  // ∧
  sp=splitTop(seg,new RegExp(',|'+WB+'(?:y|e|pero|aunque|ademas|sin embargo)'+WE,'g'));
  if(sp.count){if(sp.parts.length<2)throw new Error('A la «y» le falta una de sus dos partes.');
    return sp.parts.map(p=>parse(p,ctx)).reduce((a,b)=>Bin('and',a,b));}
  // ¬
  m=n.match(/^(no|tampoco)\s+/);
  if(m)return N(parse(sl(seg,m[0].length),ctx));
  i=firstTop(seg,W('no'));
  if(i&&i.index>0)return N(atomOf(ctx,seg.o.slice(0,i.index)+' '+seg.o.slice(i.end)));
  return atomOf(ctx,seg.o);
}
function splitRules(text){
  const out=[];
  for(let line of text.split(/\n+/)){
    line=line.trim();if(!line)continue;
    line=line.replace(/^(?:[-*•]|\d+[.)]|R\d+\s*[:.)])\s*/i,'');
    const q=[...line.matchAll(/[«“"]([^»”"]+)[»”"]/g)];
    if(q.length){q.forEach(x=>out.push(x[1].trim()));continue;}
    line.split(/(?<=[.;])\s+|;/).forEach(s=>{s=s.trim();if(s.replace(/[.;\s]/g,''))out.push(s);});
  }
  return out;
}
// ================= Texto corrido (sin puntos, comas ni comillas) =================
// Separa reglas pegadas usando «si»/«entonces» y las frases que se repiten en el texto.
const CONNW=new Set(['que','si','entonces','y','e','o','u','ni','pero','aunque','ademas','solo','implica','cuando','sii']);
const STOPW=new Set(['a','de','el','la','los','las','un','una','unos','unas','en','al','del','que','se','me','te','lo','le','mi','su','es','con','por','para','ya']);
function toks(o){const n=normChars(o);const re=/[a-zñ0-9]+/g;const t=[];let m;while((m=re.exec(n)))t.push({w:m[0],s:m.index,e:m.index+m[0].length});return t;}
// 1) Cortar antes de cada «si» que empieza una regla nueva
function splitBySi(o){
  const t=toks(o);if(t.length<2)return [o];
  const isCand=k=>t[k].w==='si'&&k>0&&t[k-1].w!=='solo'&&t[k-1].w!=='sii'&&t[k-1].w!=='que'&&!(t[k+1]&&t[k+1].w==='y'&&t[k+2]&&t[k+2].w==='solo');
  const cands=[];for(let k=1;k<t.length;k++)if(isCand(k))cands.push(k);
  const cuts=[];let c=0;
  cands.forEach((k,ci)=>{
    const nxt=ci+1<cands.length?cands[ci+1]:t.length;
    const startsSi=t[c].w==='si'||t[c].w==='cuando';
    const entoncesAhead=t.slice(k,nxt).some(x=>x.w==='entonces');
    const curHasBody=k-c>=2;
    if(curHasBody&&(startsSi||entoncesAhead)){cuts.push(t[k].s);c=k;}
  });
  const out=[];let p=0;for(const x of cuts){out.push(o.slice(p,x));p=x;}out.push(o.slice(p));
  return out.map(x=>x.trim()).filter(x=>/[a-zñ0-9]/i.test(normChars(x)));
}
// Frases que aparecen 2+ veces (candidatas a átomo)
function repeatedPhrases(seqs){
  const cnt=new Map();
  for(const ws of seqs)for(let i=0;i<ws.length;i++)for(let n=1;n<=8&&i+n<=ws.length;n++){
    const ph=ws.slice(i,i+n);if(CONNW.has(ph[n-1])||ph[n-1]==='no')break;
    if(STOPW.has(ph[n-1])&&ph[n-1]!=='es')continue;const k=ph.join(' ');cnt.set(k,(cnt.get(k)||0)+1);}
  const rep=[...cnt].filter(([k,c])=>c>=2);
  const keep=new Set();
  for(const [k,c] of rep){if(!rep.some(([k2,c2])=>k2!==k&&c2>=c&&(' '+k2+' ').includes(' '+k+' ')))keep.add(k);}
  return keep;
}
function analyze(text){
  // a) oraciones por puntuación, luego por «si»
  let chunks=[];for(const raw of splitRules(text))chunks.push(...splitBySi(raw));
  // b) vocabulario conocido: frases repetidas + átomos de las otras reglas
  const seqs=chunks.map(c=>toks(c).map(x=>x.w));
  const REP=repeatedPhrases(seqs.map(w=>w.filter(x=>x!=='no'))); // «el LED no está prendido» cuenta como «el LED está prendido»
  const atomsBy=chunks.map(c=>{const cx=makeCtx();try{parse(mk(c),cx);}catch(e){}return new Set(cx.list.map(a=>a.key));});
  const known=(k,ci)=>!!k&&(REP.has(k)||atomsBy.some((s,j)=>j!==ci&&s.has(k)));
  const core=ws=>ws.filter(w=>w!=='no').join(' ');
  const lastSeg=ws=>{let j=0;for(let i=ws.length-1;i>=0;i--)if(ws[i]==='no'||CONNW.has(ws[i])){j=i+1;break;}return ws.slice(j).join(' ');};
  const allSegsKnown=(ws,ci)=>{const segs=[];let cur=[];for(const w of ws){if(CONNW.has(w)){segs.push(cur);cur=[];}else cur.push(w);}segs.push(cur);return segs.every(sg=>sg.length&&known(core(sg),ci));};
  const segmentable=(ws,ci)=>{ // divide en piezas «[no] átomo conocido»
    const memo=new Map();const go=i=>{if(i===ws.length)return [];if(memo.has(i))return memo.get(i);let r=null;
      for(let j=ws.length;j>i;j--){const pc=ws.slice(i,j);if(pc.some(w=>CONNW.has(w))||pc.filter(w=>w==='no').length>1||pc[pc.length-1]==='no')continue;if(known(core(pc),ci)){const rest=go(j);if(rest){r=[[i,j],...rest];break;}}}
      memo.set(i,r);return r;};return go(0);};
  const final=[];
  chunks.forEach((raw,ci)=>{
    const T=toks(raw),W=T.map(x=>x.w);
    let consStart=0,insertAt=null;
    if(W[0]==='si'||W[0]==='cuando'){
      const ei=W.indexOf('entonces');const comma=raw.indexOf(',');
      if(ei>0)consStart=ei+1;
      else if(comma>0){consStart=T.findIndex(x=>x.s>comma);if(consStart<0)consStart=T.length;}
      else if(!W.includes('si',1)||W.indexOf('si',1)<0){ // falta «entonces»: buscar dónde termina la condición
        let best=-1,bs=0;
        for(let b=2;b<W.length;b++){const L=W.slice(1,b),R=W.slice(b);
          let sc=(allSegsKnown(L,ci)?2:0);const rc=R[0]==='no'?R.slice(1):R;
          for(let j=rc.length;j>0;j--)if(known(rc.slice(0,j).join(' '),ci)){sc+=1;break;}
          if(sc>bs){bs=sc;best=b;}}
        if(bs<2){const ni=W.indexOf('no',2);if(ni>0){best=ni;bs=2;}}
        if(best>0&&bs>=1){insertAt=T[best].s;consStart=best;}
      }
    }
    // c) hechos pegados al final («… no voy a trabajar es de día»)
    let runStart=consStart;for(let i=W.length-1;i>=consStart;i--)if(CONNW.has(W[i])){runStart=i+1;break;}
    let cut=-1,pieces=null;
    const run=W.slice(runStart);
    if(run.length>1&&!known(core(run),ci)){
      let bestSc=-1;
      for(let i=runStart+1;i<W.length;i++){const ls=lastSeg(W.slice(runStart,i));if(!ls)continue;
        const sg=segmentable(W.slice(i),ci);if(!sg)continue;
        const minLen=Math.min(...sg.map(([a,b])=>W.slice(i+a,i+b).filter(w=>w!=='no').length));
        const sc=(known(ls,ci)?100:0)+5*ls.split(' ').length+10*minLen-sg.length;
        if(sc>bestSc){bestSc=sc;cut=i;pieces=sg;}}
    }
    const endMain=cut>0?T[cut].s:raw.length;
    const mainRaw=raw.slice(0,endMain).trim();
    const src=insertAt!==null?raw.slice(0,insertAt)+' entonces '+raw.slice(insertAt,endMain):mainRaw;
    final.push({raw:mainRaw,src,inferred:insertAt!==null});
    if(pieces)for(const [a,b] of pieces){const r=raw.slice(T[cut+a].s,T[cut+b-1].e).trim();final.push({raw:r,src:r,split:true});}
  });
  // d) traducir
  const ctx=makeCtx(),rules=[];let k=0;
  for(const c of final){
    const r={raw:c.raw,inferred:c.inferred};
    try{r.f=parse(mk(c.src),ctx);r.label='R'+(++k);}catch(e){r.error=e.message;}
    rules.push(r);
  }
  const L=ctx.list.map(a=>a.letter);
  rules.forEach(r=>{if(r.f)r.str=fstr(r.f,L);});
  return {atoms:ctx.list,rules,L};
}

// ================= Árbol semántico (tableau) =================
function classify(f){
  switch(f.t){
    case 'atom':return null;
    case 'and':return {k:'α',name:'∧',br:[[f.a,f.b]]};
    case 'or':return {k:'β',name:'∨',br:[[f.a],[f.b]]};
    case 'imp':return {k:'β',name:'→',br:[[N(f.a)],[f.b]]};
    case 'iff':return {k:'β',name:'↔',br:[[f.a,f.b],[N(f.a),N(f.b)]]};
    case 'not':{const g=f.a;switch(g.t){
      case 'atom':return null;
      case 'not':return {k:'α',name:'¬¬',br:[[g.a]]};
      case 'and':return {k:'β',name:'¬∧',br:[[N(g.a)],[N(g.b)]]};
      case 'or':return {k:'α',name:'¬∨',br:[[N(g.a),N(g.b)]]};
      case 'imp':return {k:'α',name:'¬→',br:[[g.a,N(g.b)]]};
      case 'iff':return {k:'β',name:'¬↔',br:[[g.a,N(g.b)],[N(g.a),g.b]]};
    }}
  }
}
const isLit=f=>f.t==='atom'||(f.t==='not'&&f.a.t==='atom');
const litKey=f=>f.t==='atom'?String(f.id):'~'+f.a.id;
function runTableau(rules,L,maxSteps=Infinity){
  let nid=0;const nodes=[];
  const entry=(f,label)=>({f,str:fstr(f,L),label:label||'',applied:0});
  const newNode=(parent,entries,via,step)=>{const n={id:nid++,parent,entries,children:[],closed:false,closeLits:null,via,step};nodes.push(n);return n;};
  const closeCheck=node=>{
    const seen=new Map();
    for(let a=node.parent;a;a=a.parent)for(const e of a.entries)if(isLit(e.f))seen.set(litKey(e.f),e.str);
    for(const e of node.entries)if(isLit(e.f)){const k=litKey(e.f),c=k[0]==='~'?k.slice(1):'~'+k;
      if(seen.has(c)){node.closed=true;const pair=[seen.get(c),e.str];pair.sort((x,y)=>x.length-y.length);node.closeLits=pair;return true;}seen.set(k,e.str);}
    return false;
  };
  const openLeaves=n=>n.closed?[]:(n.children.length?n.children.flatMap(openLeaves):[n]);
  const pre=n=>[n,...n.children.flatMap(pre)];
  const findCand=root=>{
    for(const kind of ['α','β'])for(const node of pre(root))for(const e of node.entries){
      if(e.applied)continue;const c=classify(e.f);if(!c||c.k!==kind)continue;
      if(openLeaves(node).length)return {node,e,c};}
    return null;
  };
  const root=newNode(null,rules.map(r=>entry(r.f,r.label)),null,0);
  closeCheck(root);
  const log=[];let step=0;
  while(step<maxSteps){
    const cand=findCand(root);if(!cand)break;
    step++;const {node,e,c}=cand;e.applied=step;
    const leaves=openLeaves(node),closed=[];
    for(const leaf of leaves)for(const comps of c.br){
      const ch=newNode(leaf,comps.map(f=>entry(f)),{step,src:e.label||e.str,rule:c.name},step);
      leaf.children.push(ch);if(closeCheck(ch))closed.push(ch.closeLits);
    }
    log.push({step,src:e.label,str:e.str,rule:c.name,kind:c.k,branches:c.br.map(b=>b.map(f=>fstr(f,L)).join(', ')),nLeaves:leaves.length,closed});
  }
  const done=!findCand(root);
  const open=openLeaves(root);
  const leavesAll=nodes.filter(n=>!n.children.length);
  return {root,nodes,log,step,done,open,closedCount:leavesAll.filter(n=>n.closed).length};
}
function totalSteps(rules,L){return runTableau(rules,L).step;}
function modelOf(leaf,nAtoms){
  const v=new Array(nAtoms).fill(null);const path=[];
  for(let a=leaf;a;a=a.parent){path.push(a.id);for(const e of a.entries)if(isLit(e.f)){if(e.f.t==='atom')v[e.f.id]='V';else v[e.f.a.id]='F';}}
  return {v,path};
}
