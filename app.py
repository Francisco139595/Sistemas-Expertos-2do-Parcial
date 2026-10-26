# Para correr el programa: py -3.12 -m streamlit run app.py
import base64
import html

import streamlit as st

from motor import analyze, run_tableau, model_of, ops_used, norm, W, frase_modelo, negar

st.set_page_config(page_title='Motor de Inferencia', layout='wide')

# colores
C = dict(bg='#081017', panel='#0d1a23', panel2='#11232f', line='#1f3747', fg='#d9e6ee', dim='#7f97a6',
         accent='#ff8f3a', cyan='#63cbe8', ok='#47d68a', bad='#ff5a52')

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
h1, h2, h3 {{ font-family: 'Chakra Petch', sans-serif !important; letter-spacing: .04em; }}
.eyebrow {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .14em; color: {C['dim']}; }}
.eyebrow b {{ color: {C['accent']}; font-weight: 500; }}
.n {{ color: {C['accent']}; margin-right: 8px; }}
.mono {{ font-family: 'JetBrains Mono', monospace; }}
table.t {{ width: 100%; border-collapse: collapse; }}
table.t th {{ text-align: left; font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .1em;
             text-transform: uppercase; color: {C['dim']}; font-weight: 500; border-bottom: 1px solid {C['line']}; padding: 6px 10px; }}
table.t td {{ border-bottom: 1px solid {C['line']}; padding: 7px 10px; vertical-align: top; }}
table.conn tr td {{ color: {C['dim']}; }}
table.conn tr.used td {{ color: {C['fg']}; background: rgba(255,143,58,.12); }}
table.conn tr.used td.sym {{ color: {C['accent']}; }}
.letter {{ display: inline-block; min-width: 28px; text-align: center; border: 1px solid {C['accent']}; color: {C['accent']};
          font-family: 'JetBrains Mono', monospace; font-weight: 700; padding: 1px 6px; }}
.rule {{ display: flex; gap: 14px; align-items: center; border: 1px solid {C['line']}; background: {C['panel2']};
        padding: 10px 12px; margin-bottom: 8px; flex-wrap: wrap; }}
.rule .rl {{ font-family: 'Chakra Petch', sans-serif; font-weight: 700; color: {C['accent']}; font-size: 17px; }}
.rule .tx {{ flex: 1; min-width: 200px; }}
.rule .kw {{ color: {C['accent']}; border: 1px solid {C['accent']}; padding: 0 3px; }}
.rule .fx {{ font-family: 'JetBrains Mono', monospace; font-size: 16px; color: {C['cyan']}; }}
.rule .inf {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; color: {C['dim']}; border: 1px dashed {C['line']}; padding: 0 5px; margin-left: 6px; }}
.rule.err {{ border-color: {C['bad']}; }}
.rule.err .fx {{ color: {C['bad']}; font-family: inherit; font-size: 13px; }}
.steplog {{ border-left: 3px solid {C['accent']}; background: {C['panel2']}; padding: 9px 12px; }}
.steplog .mono {{ color: {C['cyan']}; }}
.pill {{ font-family: 'Chakra Petch', sans-serif; font-weight: 700; letter-spacing: .12em; padding: 4px 12px; border: 1.5px solid; margin-right: 10px; }}
.sat {{ color: {C['ok']}; border-color: {C['ok']}; }}
.unsat {{ color: {C['bad']}; border-color: {C['bad']}; }}
.pend {{ color: {C['dim']}; border-color: {C['line']}; }}
.model {{ border: 1px solid {C['line']}; background: {C['panel2']}; padding: 12px; margin-bottom: 10px; }}
.model h4 {{ margin: 0 0 6px 0; font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: .12em; color: {C['dim']}; font-weight: 500; }}
.assign {{ font-family: 'JetBrains Mono', monospace; font-size: 17px; }}
.V {{ color: {C['ok']}; }} .F {{ color: {C['bad']}; }} .X {{ color: {C['dim']}; }}
.words {{ font-size: 15px; color: {C['fg']}; margin-top: 4px; }}
.lst {{ margin-top: 8px; font-size: 14px; }}
.lst ul {{ margin: 2px 0 0 0; padding-left: 20px; }}
.lst li {{ margin: 0; }}
.hint {{ font-size: 13px; color: {C['dim']}; }}
</style>
""", unsafe_allow_html=True)

esc = html.escape
KW = W('si y solo si|no es cierto que|no es verdad que|es falso que|solo si|siempre que|en caso de que|entonces|'
       'implica que|implica|cuando|si|pero|aunque|ademas|sin embargo|o bien|ni|no|tampoco|y|e|o|u')


def highlight(raw):
    # Encierra los conectores del texto en un recuadro.
    n, out, p = norm(raw), '', 0
    for m in KW.finditer(n):
        out += esc(raw[p:m.start()]) + '<span class="kw">' + esc(raw[m.start():m.end()]) + '</span>'
        p = m.end()
    return out + esc(raw[p:])


# encabezado
st.markdown('<div class="eyebrow"><b>SYS EXP</b> // MOTOR DE INFERENCIA · LÓGICA PROPOSICIONAL</div>', unsafe_allow_html=True)
st.markdown(f'<h1 style="margin-top:0">Motor de <span style="color:{C["accent"]}">Inferencia</span></h1>', unsafe_allow_html=True)
st.caption('Del lenguaje natural al árbol semántico: escribe reglas en español y el motor encuentra las condiciones en las que todas se cumplen.')

# 01 entrada
col_in, col_conn = st.columns([1.6, 1])
with col_in:
    st.markdown('### <span class="n">01</span>Base de conocimiento', unsafe_allow_html=True)
    texto = st.text_area('Escribe las reglas y hechos. Pueden ir uno por línea, con puntos o todo corrido sin puntuación.',
                         height=170, key='kb')
    st.button('Construir árbol', type='primary')

atoms, rules, L = analyze(texto)
valid = [r for r in rules if r.f]

with col_conn:
    used = set()
    for r in valid:
        ops_used(r.f, used)
    filas = [('and', '«y»', '∧', 'Conjunción'), ('or', '«o»', '∨', 'Disyunción'), ('not', '«no»', '¬', 'Negación'),
             ('imp', '«si… entonces»', '→', 'Condicional'), ('iff', '«si y solo si»', '↔', 'Bicondicional')]
    cu = sum(1 for f in filas if f[0] in used)
    st.markdown(f'### Conectivos <span class="hint">({cu} / 5 usados)</span>', unsafe_allow_html=True)
    st.markdown('<table class="t conn"><tr><th>Texto</th><th>Símbolo</th><th>Nombre</th></tr>' +
                ''.join(f'<tr class="{"used" if op in used else ""}"><td>{t}</td><td class="sym mono">{s}</td><td>{nm}</td></tr>'
                        for op, t, s, nm in filas) + '</table>', unsafe_allow_html=True)
    st.markdown('<p class="hint">También entiende: «e», «pero», «aunque», «u», «ni… ni», «… solo si …», «Q si P», '
                '«cuando P, Q», «no es cierto que…».</p>', unsafe_allow_html=True)

# 02 átomos / 03 reglas
col_a, col_r = st.columns([1, 1.7])
with col_a:
    st.markdown('### <span class="n">02</span>Tabla de átomos', unsafe_allow_html=True)
    if atoms:
        st.markdown('<table class="t"><tr><th>Letra</th><th>Significado</th></tr>' +
                    ''.join(f'<tr><td><span class="letter">{a.letter}</span></td><td>{esc(a.meaning)}</td></tr>' for a in atoms) +
                    '</table>', unsafe_allow_html=True)
        st.markdown('<p class="hint">La misma frase en varias reglas es el mismo átomo; «no …» se representa como ¬ de ese átomo.</p>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<p class="hint">Escribe al menos una regla o un hecho.</p>', unsafe_allow_html=True)

with col_r:
    st.markdown('### <span class="n">03</span>Reglas → fórmulas', unsafe_allow_html=True)
    if not rules:
        st.markdown('<p class="hint">Aquí aparecerá cada regla junto a su fórmula (R1: p → q…).</p>', unsafe_allow_html=True)
    for r in rules:
        if r.error:
            st.markdown(f'<div class="rule err"><span class="rl">!</span><span class="tx">{esc(r.raw)}</span>'
                        f'<span class="fx">No se pudo traducir: {esc(r.error)}</span></div>', unsafe_allow_html=True)
        else:
            inf = ' <span class="inf">«entonces» inferido</span>' if r.inferred else ''
            st.markdown(f'<div class="rule"><span class="rl">{r.label}</span><span class="tx">{highlight(r.raw)}{inf}</span>'
                        f'<span class="fx">{esc(r.str)}</span></div>', unsafe_allow_html=True)

# 04 árbol
st.markdown('### <span class="n">04</span>Árbol semántico', unsafe_allow_html=True)
if not valid:
    st.markdown('<p class="hint">El árbol aparecerá cuando haya reglas válidas.</p>', unsafe_allow_html=True)
    st.stop()

total = run_tableau(valid, L)['step']
# al cambiar el texto se muestra el árbol completo
if st.session_state.get('last_text') != texto:
    st.session_state.last_text = texto
    st.session_state.step = total
step = min(st.session_state.get('step', total), total)

b1, b2, b3, b4, b5 = st.columns([1, 1, 2, 1, 1])
if b1.button('⏮ Inicio', use_container_width=True, disabled=step <= 0):
    step = 0
if b2.button('◀ Anterior', use_container_width=True, disabled=step <= 0):
    step = max(0, step - 1)
if b4.button('Siguiente ▶', use_container_width=True, disabled=step >= total):
    step = min(total, step + 1)
if b5.button('Completo ⏭', use_container_width=True, disabled=step >= total):
    step = total
st.session_state.step = step
b3.markdown(f'<div style="text-align:center;padding-top:8px" class="mono">Paso <b>{step}</b> / {total}</div>', unsafe_allow_html=True)

T = run_tableau(valid, L, step)
open_idx = {leaf.id: i + 1 for i, leaf in enumerate(T['open'])} if T['done'] else {}
models = [model_of(leaf, len(atoms)) for leaf in T['open']] if T['done'] else []

# bitácora del paso
if step == 0:
    msg = f'<b>Paso 0:</b> se parte suponiendo que todas las reglas son verdaderas ({", ".join(r.label for r in valid)} en la raíz).'
else:
    lg = T['log'][step - 1]
    nl = lg['n_leaves']
    pl = 's' if nl > 1 else ''
    if lg['kind'] == 'α':
        how = f'no bifurca: <span class="mono">{esc(lg["branches"][0])}</span>'
    else:
        how = f'bifurca en <span class="mono">{esc(lg["branches"][0])}</span> | <span class="mono">{esc(lg["branches"][1])}</span>'
    msg = (f'<b>Paso {lg["step"]}:</b> se desarrolla {lg["src"] + " = " if lg["src"] else ""}'
           f'<span class="mono">{esc(lg["str"])}</span> con la regla <span class="mono">{esc(lg["rule"])}</span> — {how} — '
           f'en {nl} rama{pl} abierta{pl} de abajo.')
    if lg['closed']:
        k = len(lg['closed'])
        msg += f' Se cierra{"n" if k > 1 else ""} {k} rama{"s" if k > 1 else ""} ✕ ({"; ".join(esc(" y ".join(c)) for c in lg["closed"])}).'
if T['done']:
    msg += ' <b>Fin:</b> no quedan fórmulas por desarrollar, solo letras o letras negadas.'
st.markdown(f'<div class="steplog">{msg}</div>', unsafe_allow_html=True)

# resaltar un modelo en el árbol
hl = set()
if models:
    opciones = ['(ninguno)'] + [f'Modelo {i + 1}' for i in range(len(models))]
    sel = st.selectbox('Resaltar la rama de un modelo', opciones, index=0)
    if sel != '(ninguno)':
        hl = set(models[int(sel.split()[1]) - 1][1])


# dibujo del árbol en SVG
def tw(s, size):  # ancho aproximado de texto monoespaciado
    return len(s) * size * 0.6


PADX, PADY, LH, GX, GY, MARK = 14, 9, 22, 26, 52, 46


def measure(n):
    w = 40
    for e in n.entries:
        x = tw(e.str, 15)
        if e.applied:
            x += 6 + tw('✓' + str(e.applied), 13)
        if e.label:
            x += 12 + tw(e.label, 11)
        w = max(w, x)
    n.w = w + 2 * PADX
    n.h = len(n.entries) * LH + 2 * PADY - 4
    mw = 0
    if not n.children:
        if n.closed:
            mw = tw(' y '.join(n.close_lits), 11) + 8
        elif T['done']:
            mw = tw('○ ABIERTA · M%d' % open_idx[n.id], 12) + 8
        else:
            mw = tw('pendiente', 11)
    for c in n.children:
        measure(c)
    cs = sum(c.sw for c in n.children) + GX * max(0, len(n.children) - 1)
    n.sw = max(n.w, mw, cs)


maxy = [0]


def place(n, cx, y):
    n.cx, n.x, n.y = cx, cx - n.w / 2, y
    maxy[0] = max(maxy[0], y + n.h + (0 if n.children else MARK))
    cs = sum(c.sw for c in n.children) + GX * max(0, len(n.children) - 1)
    x = cx - cs / 2
    for c in n.children:
        place(c, x + c.sw / 2, y + n.h + GY)
        x += c.sw + GX


root = T['root']
measure(root)
M = 18
place(root, root.sw / 2 + M, M)
Wd, Ht = root.sw + 2 * M, maxy[0] + M

edges, gnodes = [], []
for n in T['nodes']:
    if n.children:
        by, sy = n.y + n.h, n.y + n.h + 16
        on = any(c.id in hl for c in n.children)
        edges.append(f'<line class="edge{" hl" if on else ""}" x1="{n.cx}" y1="{by}" x2="{n.cx}" y2="{sy}"/>')
        for c in n.children:
            edges.append(f'<line class="edge{" hl" if c.id in hl else ""}" x1="{n.cx}" y1="{sy}" x2="{c.cx}" y2="{c.y}"/>')
        v = n.children[0].via
        src = v['src'] if len(v['src']) <= 14 else ''
        edges.append(f'<text class="elbl" x="{n.cx + 7}" y="{by + 13}">{v["step"]}· {esc(src)} {esc(v["rule"])}</text>')
    leaf = not n.children
    cls = 'nd'
    if n.closed:
        cls += ' closed'
    elif leaf and T['done']:
        cls += ' open'
    if n.step and n.step == step:
        cls += ' new'
    if n.id in hl:
        cls += ' hl'
    g = [f'<g class="{cls}"><rect x="{n.x}" y="{n.y}" width="{n.w}" height="{n.h}" rx="2"/>']
    for i, e in enumerate(n.entries):
        ty, lx = n.y + PADY + i * LH + 15, n.x + PADX
        g.append(f'<text class="ft{" done" if e.applied else ""}" x="{lx}" y="{ty}">{esc(e.str)}</text>')
        if e.applied:
            g.append(f'<text class="ck" x="{lx + tw(e.str, 15) + 6}" y="{ty}">✓{e.applied}</text>')
        if e.label:
            g.append(f'<text class="lbl" x="{n.x + n.w - PADX}" y="{ty}" text-anchor="end">{e.label}</text>')
    if leaf:
        b = n.y + n.h
        if n.closed:
            g.append(f'<text class="xm" x="{n.cx}" y="{b + 22}" text-anchor="middle">✕</text>'
                     f'<text class="xt" x="{n.cx}" y="{b + 38}" text-anchor="middle">{esc(" y ".join(n.close_lits))}</text>')
        elif T['done']:
            g.append(f'<text class="om" x="{n.cx}" y="{b + 20}" text-anchor="middle">○ ABIERTA · M{open_idx[n.id]}</text>')
        else:
            g.append(f'<text class="pm" x="{n.cx}" y="{b + 18}" text-anchor="middle">pendiente</text>')
    g.append('</g>')
    gnodes.append(''.join(g))

svg_css = f"""
.nd rect {{ fill: {C['panel']}; stroke: {C['line']}; stroke-width: 1.4; }}
.nd.new rect {{ stroke: {C['accent']}; stroke-width: 2; }}
.nd.closed rect {{ stroke: {C['bad']}; fill: rgba(255,90,82,.12); }}
.nd.open rect {{ stroke: {C['ok']}; fill: rgba(71,214,138,.12); }}
.nd.hl rect {{ stroke: {C['accent']}; stroke-width: 2.8; }}
.edge {{ stroke: {C['dim']}; stroke-width: 1.3; opacity: .8; }}
.edge.hl {{ stroke: {C['accent']}; stroke-width: 2.6; opacity: 1; }}
text {{ font-family: 'JetBrains Mono', Consolas, monospace; }}
.ft {{ font-size: 15px; font-weight: 500; fill: {C['fg']}; }}
.ft.done {{ fill: {C['dim']}; }}
.ck {{ fill: {C['ok']}; font-size: 13px; font-weight: 700; }}
.lbl {{ fill: {C['dim']}; font-size: 11px; }}
.elbl {{ fill: {C['accent']}; font-size: 11px; }}
.xm {{ fill: {C['bad']}; font-size: 20px; font-weight: 700; }}
.xt {{ fill: {C['bad']}; font-size: 11px; }}
.om {{ fill: {C['ok']}; font-size: 12px; font-weight: 700; }}
.pm {{ fill: {C['dim']}; font-size: 11px; }}
"""
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wd}" height="{Ht}" viewBox="0 0 {Wd} {Ht}">'
       f'<rect width="100%" height="100%" fill="{C["panel2"]}"/><style>{svg_css}</style>{"".join(edges)}{"".join(gnodes)}</svg>')
zoom = st.slider('Zoom del árbol (%)', 40, 200, 100, 10)
b64 = base64.b64encode(svg.encode('utf-8')).decode('ascii')
st.markdown(f'<div style="overflow:auto;max-height:900px;border:1px solid {C["line"]};background:{C["panel2"]};text-align:center">'
            f'<img src="data:image/svg+xml;base64,{b64}" width="{Wd * zoom / 100:.0f}" style="max-width:none" alt="Árbol semántico"></div>',
            unsafe_allow_html=True)

st.markdown(f"""
<p class="hint">
<span style="color:{C['ok']}">■</span> Rama abierta (modelo) &nbsp;
<span style="color:{C['bad']}">■</span> Rama cerrada ✕ (átomo y su negación) &nbsp;
<span style="color:{C['accent']}">■</span> Agregado en este paso &nbsp;
<b style="color:{C['ok']}">✓n</b> fórmula ya aplicada en el paso n
</p>
<ol class="hint">
<li>Se parte suponiendo que todas las reglas son verdaderas (raíz).</li>
<li>Se aplica primero la regla que no bifurca (∧, ¬∨, ¬→, ¬¬) y después las que bifurcan (∨, →, ↔, ¬∧, ¬↔), desarrollando en todas las ramas abiertas de abajo.</li>
<li>Una rama con un átomo y su negación se cierra (✕).</li>
<li>Al final solo quedan letras o letras negadas: las ramas abiertas son los modelos.</li>
</ol>
""", unsafe_allow_html=True)

# 05 resultado
st.markdown('### <span class="n">05</span>Resultado · modelos', unsafe_allow_html=True)
if not T['done']:
    st.markdown(f'<span class="pill pend">EN PROCESO</span><span class="hint">Avanza al último paso (Completo ⏭) para ver los modelos. '
                f'Ramas cerradas hasta ahora: {T["closed_count"]}.</span>', unsafe_allow_html=True)
elif not T['open']:
    hojas = sum(1 for n in T['nodes'] if not n.children)
    st.markdown(f'<span class="pill unsat">INSATISFACIBLE</span> Las {hojas} ramas se cierran ✕. La base de conocimiento es '
                f'<b>inconsistente</b>: no existe ninguna asignación de valores en la que todas las reglas se cumplan.',
                unsafe_allow_html=True)
    # qué frases chocan en cada rama cerrada
    por_letra = {a.letter: a for a in atoms}
    choques = []
    for n in T['nodes']:
        if n.closed:
            letra = n.close_lits[0].lstrip('¬')
            at = por_letra[letra]
            txt = f'«{at.meaning}» y «{negar(at)}» ({letra} y ¬{letra})'
            if txt not in choques:
                choques.append(txt)
    st.markdown('<div class="model"><h4>LO QUE NO SE PUEDE CUMPLIR</h4><div class="lst"><b class="F">✘ Contradicciones encontradas</b><ul>' +
                ''.join(f'<li>{esc(c)} no pueden ser ciertas al mismo tiempo.</li>' for c in choques) + '</ul></div></div>',
                unsafe_allow_html=True)
else:
    no, nc = len(T['open']), T['closed_count']
    st.markdown(f'<span class="pill sat">SATISFACIBLE</span> {no} rama{"s" if no > 1 else ""} abierta{"s" if no > 1 else ""} y '
                f'{nc} cerrada{"" if nc == 1 else "s"}. Cada rama abierta es una condición en la que <b>todas las reglas se cumplen</b>.',
                unsafe_allow_html=True)
    st.write('')
    vistos = {}
    cols = st.columns(min(3, len(models)))
    for i, (v, _) in enumerate(models):
        key = tuple(v)
        dup = f' · igual a M{vistos[key]}' if key in vistos else ''
        vistos.setdefault(key, i + 1)
        asg = ', '.join(f'<span class="{x or "X"}">{L[j]} = {x or "V/F"}</span>' for j, x in enumerate(v))
        words = frase_modelo(v, atoms)
        si = [atoms[j].meaning for j, x in enumerate(v) if x == 'V']
        no = [atoms[j].meaning for j, x in enumerate(v) if x == 'F']
        da = [atoms[j].meaning for j, x in enumerate(v) if x is None]
        lst = lambda xs: ''.join(f'<li>{esc(x)}</li>' for x in xs) or '<li class="X">(ninguna)</li>'
        partes = (f'<div class="lst"><b class="V">✔ Se cumple</b><ul>{lst(si)}</ul></div>'
                  f'<div class="lst"><b class="F">✘ No se cumple</b><ul>{lst(no)}</ul></div>')
        if da:
            partes += f'<div class="lst"><b class="X">○ Da igual</b><ul>{lst(da)}</ul></div>'
        cols[i % len(cols)].markdown(f'<div class="model"><h4>MODELO {i + 1} · RAMA ABIERTA{dup}</h4>'
                                     f'<div class="assign">{asg}</div><div class="words">{esc(words)}</div>{partes}</div>',
                                     unsafe_allow_html=True)
    tabla = ('<table class="t"><tr><th>Modelo</th>' + ''.join(f'<th>{a.letter} · {esc(a.meaning)}</th>' for a in atoms) + '</tr>' +
             ''.join(f'<tr><td class="mono">M{i + 1}</td>' + ''.join(f'<td class="mono {x or "X"}"><b>{x or "V/F"}</b></td>' for x in v) + '</tr>'
                     for i, (v, _) in enumerate(models)) + '</table>')
    st.markdown(tabla, unsafe_allow_html=True)
    if any(x is None for v, _ in models for x in v):
        st.markdown('<p class="hint">V/F: esa letra no aparece en la rama, así que puede tomar cualquier valor sin romper las reglas.</p>',
                    unsafe_allow_html=True)

st.divider()
st.markdown('<p class="hint mono">Sistemas Expertos 7E262 · CETI Colomos · Francisco Ramiro Gómez Arce</p>', unsafe_allow_html=True)