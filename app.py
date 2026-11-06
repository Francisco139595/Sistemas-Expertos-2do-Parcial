# Para correr el programa: py -3.12 -m streamlit run app.py
import base64
import html

import streamlit as st

import almacen
from motor import (analyze, run_tableau, model_of, frase_modelo, negar, resolver_rapido,
                   arbol_completo, arbol_en_texto)

st.set_page_config(page_title='Motor de Inferencia', layout='wide')

# colores de la consola
BG = '#111111'
FG = '#dddddd'
DIM = '#777777'
LINE = '#555555'
OK = '#55dd55'
BAD = '#ff5555'
MONO = "Consolas, 'Courier New', monospace"

st.markdown(f"""
<style>
html, body, [class*="css"], .stApp, .stMarkdown, p, li, div, span, label, textarea, button {{
    font-family: {MONO} !important;
}}
[data-testid="stIconMaterial"], .material-symbols-rounded {{ font-family: 'Material Symbols Rounded' !important; }}
.stApp {{ background: {BG}; }}
.block-container {{ max-width: 1100px; }}
header[data-testid="stHeader"] {{ background: {BG}; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ border: 1px solid {LINE} !important; border-radius: 0 !important; }}
.titulo {{ color: #ffffff; font-size: 20px; letter-spacing: .08em; margin-bottom: 6px; }}
.caja {{ color: {DIM}; font-size: 14px; margin-bottom: 2px; }}
.linea {{ color: {FG}; font-size: 15px; line-height: 1.7; }}
.dim {{ color: {DIM}; }}
.V {{ color: {OK}; }}
.F {{ color: {BAD}; }}
.err {{ color: {BAD}; }}
textarea {{ background: {BG} !important; color: {FG} !important; border: 1px solid {LINE} !important; border-radius: 0 !important; }}
.stButton button {{ background: {BG}; color: {FG}; border: 1px solid {LINE}; border-radius: 0; }}
.stButton button:hover {{ border-color: {FG}; color: #ffffff; }}
div[data-baseweb="select"] > div {{ background: {BG}; border-radius: 0; border-color: {LINE}; }}
[data-testid="stFileUploaderDropzone"] {{ background: {BG}; border: 1px dashed {LINE}; border-radius: 0; }}
.stTextInput input {{ background: {BG}; color: {FG}; border-radius: 0; }}
</style>
""", unsafe_allow_html=True)

esc = html.escape


def linea(texto, clase='linea'):
    st.markdown(f'<div class="{clase}">{texto}</div>', unsafe_allow_html=True)


def titulo_caja(texto):
    st.markdown(f'<div class="caja">{texto}</div>', unsafe_allow_html=True)


st.markdown('<div class="titulo">MOTOR DE INFERENCIA</div>', unsafe_allow_html=True)

# persistencia: bases de conocimiento guardadas en la carpeta "bases"
BORR = '(borrador)'

if 'sel' not in st.session_state:
    # al abrir el programa se recupera la última base que se tenía abierta
    ultima = almacen.leer_actual()
    st.session_state.sel = ultima if ultima in almacen.listar() else BORR
    st.session_state.kb = almacen.leer_borrador() if st.session_state.sel == BORR else almacen.leer(ultima)
if 'subida' not in st.session_state:
    st.session_state.subida = 0


def al_elegir():
    # al elegir una base se carga su texto en el cuadro de reglas
    sel = st.session_state.sel
    st.session_state.kb = almacen.leer_borrador() if sel == BORR else almacen.leer(sel)


def al_guardar_como():
    nombre = st.session_state.get('nuevo_nombre', '').strip()
    if nombre:
        st.session_state.sel = almacen.guardar(nombre, st.session_state.kb)
        st.session_state.nuevo_nombre = ''


def al_borrar():
    if st.session_state.sel != BORR:
        almacen.borrar(st.session_state.sel)
        st.session_state.sel = BORR
        st.session_state.kb = almacen.leer_borrador()


# límites para dibujar el árbol; arriba de esto se usa el método rápido sin dibujo
MAX_REGLAS_ARBOL = 40
MAX_NODOS = 800
MAX_MODELOS = 10


@st.cache_data(show_spinner=False)
def analizar(texto):
    return analyze(texto)


@st.cache_data(show_spinner=False)
def resolver(texto):
    a, r, letras = analyze(texto)
    v = [x for x in r if x.f]
    return resolver_rapido(v, len(a), max_modelos=MAX_MODELOS) if v else None


@st.cache_data(show_spinner=False)
def pasos_arbol(texto):
    # número de pasos del árbol completo, o None si es demasiado grande para dibujarlo
    a, r, letras = analyze(texto)
    v = [x for x in r if x.f]
    if not v or len(v) > MAX_REGLAS_ARBOL:
        return None
    t = run_tableau(v, letras, max_nodos=MAX_NODOS)
    return None if t['excedido'] else t['step']


@st.cache_data(show_spinner=False)
def construir_completo(texto, cap):
    a, r, letras = analyze(texto)
    v = [x for x in r if x.f]
    arbol = arbol_completo(v, letras, max_nodos=cap)
    return arbol, arbol_en_texto(arbol['nodos'])


def resumen(texto):
    # lo necesario para la tabla de resumen de una base
    a, r, letras = analizar(texto)
    v = [x for x in r if x.f]
    if not v:
        return len(r), len(a), 'sin reglas válidas', 0, True
    res = resolver(texto)
    if res['modelos']:
        return len(v), len(a), 'SATISFACIBLE', len(res['modelos']), res['completo']
    return len(v), len(a), 'INSATISFACIBLE', 0, True


with st.container(border=True):
    titulo_caja('bases de conocimiento')
    archivos = st.file_uploader('cargar archivos .txt con reglas', type=['txt'], accept_multiple_files=True,
                                key=f'subida{st.session_state.subida}')
    if archivos:
        ultimo = None
        for arch in archivos:
            ultimo = almacen.guardar(arch.name, almacen.decodificar(arch.getvalue()))
        st.session_state.sel = ultimo
        st.session_state.kb = almacen.leer(ultimo)
        st.session_state.subida += 1  # limpia el cuadro de carga
        st.rerun()

    nombres = almacen.listar()
    if st.session_state.sel not in nombres:
        st.session_state.sel = BORR
    st.selectbox('base actual', [BORR] + nombres, key='sel', on_change=al_elegir)
    almacen.guardar_actual(st.session_state.sel)

    if nombres:
        def celda(t, n):
            # rellena con espacios para que las columnas queden alineadas
            return esc(t[:n - 2]) + '&nbsp;' * (n - len(t[:n - 2]))

        filas = [celda('nombre', 24) + celda('reglas', 8) + celda('átomos', 8) + 'resultado', '─' * 62]
        for n in nombres:
            nr, na, res, nm, completo = resumen(almacen.leer(n))
            color = 'V' if res == 'SATISFACIBLE' else ('F' if res == 'INSATISFACIBLE' else 'dim')
            extra = f' ({nm}{"" if completo else "+"} modelo{"s" if nm != 1 else ""})' if nm else ''
            filas.append(celda(n, 24) + celda(str(nr), 8) + celda(str(na), 8) + f'<span class="{color}">{res}</span>{extra}')
        linea('<br>'.join(filas))
        linea(f'{len(nombres)} base(s) guardada(s) en la carpeta «bases»', 'linea dim')
    else:
        linea('todavía no hay bases guardadas', 'linea dim')

# entrada de reglas
with st.container(border=True):
    titulo_caja('reglas' + ('' if st.session_state.sel == BORR else f' · {esc(st.session_state.sel)}'))
    texto = st.text_area('reglas', height=150, key='kb', label_visibility='collapsed',
                         placeholder='Escribe las reglas y hechos en español...')
    # guardado automático: el borrador o la base elegida
    if st.session_state.sel == BORR:
        almacen.guardar_borrador(texto)
    elif texto != almacen.leer(st.session_state.sel):
        almacen.guardar(st.session_state.sel, texto)
    b1, b2, b3, b4 = st.columns([1, 2, 1.2, 1.2])
    b1.button('analizar', use_container_width=True)
    b2.text_input('nombre', key='nuevo_nombre', label_visibility='collapsed', placeholder='nombre de la base')
    b3.button('guardar como', use_container_width=True, on_click=al_guardar_como)
    b4.button('borrar base', use_container_width=True, on_click=al_borrar, disabled=st.session_state.sel == BORR)
    linea('se guarda solo · si eliges una base, los cambios se guardan en su archivo', 'linea dim')

atoms, rules, L = analizar(texto)
valid = [r for r in rules if r.f]

if not rules:
    st.stop()

CAJA_SCROLL = 'max-height:340px;overflow:auto'

# átomos y fórmulas lado a lado
col_a, col_f = st.columns([1, 1.6])
with col_a:
    with st.container(border=True):
        titulo_caja(f'átomos ({len(atoms)})')
        linea(f'<div style="{CAJA_SCROLL}">' + '<br>'.join(f'{a.letter} = {esc(a.meaning)}' for a in atoms) + '</div>')
with col_f:
    with st.container(border=True):
        errores = sum(1 for r in rules if r.error)
        titulo_caja(f'fórmulas ({len(valid)})' + (f' · <span class="F">{errores} sin traducir</span>' if errores else ''))
        filas = []
        for r in rules:
            if r.error:
                filas.append(f'<span class="err">!&nbsp;&nbsp;&nbsp;{esc(r.raw)} → {esc(r.error)}</span>')
            else:
                extra = ' <span class="dim">(entonces inferido)</span>' if r.inferred else ''
                f = esc(r.str).ljust(12).replace(' ', '&nbsp;')
                filas.append(f'{r.label}&nbsp;&nbsp;{f}&nbsp;<span class="dim">{esc(r.raw)}</span>{extra}')
        linea(f'<div style="{CAJA_SCROLL}">' + '<br>'.join(filas) + '</div>')

if not valid:
    st.stop()


def mostrar_modelo(i, v, igual=''):
    # una asignación: letras, oración, lo que se cumple y lo que no
    asig = ' '.join(f'<span class="{x or "dim"}">{L[j]}={x or "V/F"}</span>' for j, x in enumerate(v))
    si = ', '.join(esc(atoms[j].meaning) for j, x in enumerate(v) if x == 'V') or '-'
    no = ', '.join(esc(atoms[j].meaning) for j, x in enumerate(v) if x == 'F') or '-'
    libres = ', '.join(esc(atoms[j].meaning) for j, x in enumerate(v) if x is None)
    sangria = '&nbsp;&nbsp;&nbsp;'
    texto_m = (f'M{i + 1}: {asig}{igual}'
               f'<br>{sangria}{esc(frase_modelo(v, atoms))}'
               f'<br>{sangria}<span class="V">✓ se cumple:</span> {si}'
               f'<br>{sangria}<span class="F">✕ no se cumple:</span> {no}')
    if libres:
        texto_m += f'<br>{sangria}<span class="dim">○ da igual:</span> {libres}'
    linea(texto_m)


def mostrar_svg(svg, W):
    # muestra el dibujo con botones de zoom (0 = ajustar al ancho de la pantalla)
    b64 = base64.b64encode(svg.encode('utf-8')).decode('ascii')
    zoom = st.session_state.get('zoom', 0)
    z1, z2, z3, z4, z5 = st.columns([1, 1, 1.4, 1, 1])
    if z1.button('− zoom', use_container_width=True):
        zoom = max(10, (zoom or 100) - 25)
    if z2.button('+ zoom', use_container_width=True):
        zoom = min(500, (zoom or 100) + 25)
    if z4.button('ajustar', use_container_width=True):
        zoom = 0
    if z5.button('100%', use_container_width=True):
        zoom = 100
    st.session_state.zoom = zoom
    z3.markdown(f'<div class="linea" style="text-align:center;padding-top:6px">'
                f'zoom: {"ajustado" if zoom == 0 else str(zoom) + "%"}</div>', unsafe_allow_html=True)
    # display:block + margin auto: centrado si cabe, y si es más grande se puede desplazar hasta la orilla
    if zoom == 0:
        estilo = f'display:block;margin:0 auto;width:100%;max-width:{W:.0f}px'
    else:
        estilo = f'display:block;margin:0 auto;width:{W * zoom / 100:.0f}px;max-width:none'
    st.markdown(f'<div style="overflow:auto;max-height:900px;border:1px solid #222">'
                f'<img src="data:image/svg+xml;base64,{b64}" style="{estilo}"></div>', unsafe_allow_html=True)


def letra_de(l):
    # número de letra del método rápido (1 = primer átomo, negativo = negado) -> texto
    return ('¬' if l < 0 else '') + L[abs(l) - 1]


def resumen_letras(lits, cuantas=5):
    txt = ', '.join(letra_de(x) for x in lits[:cuantas])
    if len(lits) > cuantas:
        txt += f', … (+{len(lits) - cuantas})'
    return txt


def dibujar_arbol_rapido(arbol, paso, hl):
    # dibuja el árbol que recorrió el método rápido, hasta el nodo número «paso»
    def ancho(s, size):
        return len(s) * size * 0.6

    PX, PY, LH, GX, GY, MARCA = 10, 8, 20, 30, 56, 34
    # nodos del recorrido hasta el paso pedido
    crudos = []
    for i, n in enumerate(arbol[:paso + 1]):
        crudos.append({'id': i, 'padre': n['padre'], 'hijos': [], 'dato': n})
    for n in crudos:
        if n['padre'] is not None:
            crudos[n['padre']]['hijos'].append(n)

    # una cadena de nodos con un solo hijo se junta en una caja, para que el árbol no sea una línea larguísima
    nodos = []

    def armar(n, padre_vis):
        cadena = [n]
        while n['padre'] is not None and len(cadena[-1]['hijos']) == 1:
            cadena.append(cadena[-1]['hijos'][0])
        ult = cadena[-1]
        if n['padre'] is None:
            lineas = [f'raíz: R1 … R{len(valid)} verdaderas']
            if n['dato']['lits']:
                lineas.append(f'obligadas ({len(n["dato"]["lits"])}): ' + resumen_letras(n['dato']['lits']))
        else:
            lineas = [letra_de(n['dato']['decision'])]
            if len(cadena) > 1:
                resto = [f'{letra_de(c["dato"]["decision"])}' for c in cadena[1:]]
                txt = ', '.join(resto[:4]) + (f', … (+{len(resto) - 4})' if len(resto) > 4 else '')
                lineas.append(f'luego 1ª rama en {len(resto)} bifurcacion{"es" if len(resto) > 1 else ""}: {txt}')
            obl = sum(len(c['dato']['lits']) - 1 for c in cadena)
            if obl:
                todas = [x for c in cadena for x in c['dato']['lits'][1:]]
                lineas.append(f'+ obligadas ({obl}): ' + resumen_letras(todas, 4))
        vis = {'id': ult['id'], 'ids': [c['id'] for c in cadena], 'padre': padre_vis, 'lineas': lineas,
               'hijos': [], 'dato': ult['dato'], 'primero': n}
        nodos.append(vis)
        for h in ult['hijos']:
            vis['hijos'].append(armar(h, vis))
        return vis

    import sys
    sys.setrecursionlimit(max(10000, sys.getrecursionlimit()))
    armar(crudos[0], None)
    hl = {nodos[k]['id'] for k in range(len(nodos)) if any(i in hl for i in nodos[k]['ids'])}

    def etiqueta_hoja(n):
        d = n['dato']
        if d['cerrada'] is not None:
            x = L[d['cerrada']]
            return f'✕ cerrada: {x} y ¬{x}'
        if d['modelo'] is not None:
            return f'○ abierta → M{d["modelo"] + 1}'
        return '...'

    def etiqueta_rama(n):
        h = n['hijos'][0]['primero']
        x = L[abs(h['dato']['decision']) - 1]
        return f'paso {h["id"]} · {h["dato"]["regla"]}: {x} | ¬{x}'

    # medidas sin recursión (el árbol puede ser profundo)
    orden = []
    pila = [nodos[0]]
    while pila:
        n = pila.pop()
        orden.append(n)
        pila.extend(n['hijos'])
    for n in reversed(orden):
        n['w'] = max(30, max(ancho(t, 14) for t in n['lineas'])) + 2 * PX
        n['h'] = len(n['lineas']) * LH + 2 * PY - 4
        hijos = sum(c['sw'] for c in n['hijos']) + GX * max(0, len(n['hijos']) - 1)
        extra = n['w'] + 2 * (ancho(etiqueta_rama(n), 11) + 10) if n['hijos'] else ancho(etiqueta_hoja(n), 12) + 10
        n['sw'] = max(n['w'], extra, hijos)
    fondo = 0
    nodos[0]['cx'], nodos[0]['y'] = nodos[0]['sw'] / 2 + 10, 10
    for n in orden:
        n['x'] = n['cx'] - n['w'] / 2
        fondo = max(fondo, n['y'] + n['h'] + (0 if n['hijos'] else MARCA))
        hijos = sum(c['sw'] for c in n['hijos']) + GX * max(0, len(n['hijos']) - 1)
        x = n['cx'] - hijos / 2
        for c in n['hijos']:
            c['cx'], c['y'] = x + c['sw'] / 2, n['y'] + n['h'] + GY + (16 if n['padre'] is None else 0)
            x += c['sw'] + GX
    W, H = nodos[0]['sw'] + 20, fondo + 10

    partes = []
    for n in orden:
        d = n['dato']
        if n['hijos']:
            y0 = n['y'] + n['h'] + (18 if n['padre'] is None else 0)
            for c in n['hijos']:
                color = FG if c['id'] in hl else LINE
                partes.append(f'<line x1="{n["cx"]}" y1="{y0}" x2="{c["cx"]}" y2="{c["y"]}" stroke="{color}" stroke-width="1.2"/>')
            partes.append(f'<text x="{n["x"] + n["w"] + 8}" y="{n["y"] + n["h"] - 6}" fill="{DIM}" font-size="11">'
                          f'{esc(etiqueta_rama(n))}</text>')
        hoja = not n['hijos']
        if d['cerrada'] is not None:
            borde = BAD
        elif d['modelo'] is not None:
            borde = OK
        else:
            borde = FG if n['padre'] is None else LINE
        grosor = 2.4 if n['id'] in hl else 1.4
        partes.append(f'<rect x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" height="{n["h"]}" fill="{BG}" '
                      f'stroke="{borde}" stroke-width="{grosor}"/>')
        for i, t in enumerate(n['lineas']):
            color = FG if i == 0 else DIM
            partes.append(f'<text x="{n["x"] + PX}" y="{n["y"] + PY + 14 + i * LH}" fill="{color}" font-size="14">{esc(t)}</text>')
        if hoja:
            color = BAD if d['cerrada'] is not None else (OK if d['modelo'] is not None else DIM)
            partes.append(f'<text x="{n["cx"]}" y="{n["y"] + n["h"] + 18}" fill="{color}" font-size="12" text-anchor="middle">'
                          f'{esc(etiqueta_hoja(n))}</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="Consolas, Courier New, monospace"><rect width="100%" height="100%" fill="{BG}"/>'
           f'{"".join(partes)}</svg>')
    return svg, W


total = pasos_arbol(texto)
T = None

# árbol semántico paso a paso
with st.container(border=True):
    titulo_caja('árbol semántico')
    RAPIDO, COMPLETO = 'rápido (con poda)', 'completo (método clásico)'
    modo = st.radio('tipo de árbol', [RAPIDO, COMPLETO], index=1 if total is not None else 0, horizontal=True,
                    key='modo_arbol')
    if modo == RAPIDO:
        # base grande: el árbol completo sería enorme, así que se dibuja el árbol que recorre el método rápido
        res = resolver(texto)
        arbol = res['arbol']
        linea(f'la base tiene {len(valid)} reglas: se dibuja el árbol con poda. en cada nodo se aplican primero todas las '
              f'letras obligadas (como las reglas que no bifurcan) y solo se bifurca cuando una regla todavía no se cumple: '
              f'una rama con la letra verdadera y otra con la letra falsa. cada rama se cierra en cuanto aparece una contradicción.',
              'linea dim')
        clave = 'rap:' + str(hash(texto))
        ultimo = len(arbol) - 1
        if st.session_state.get('last_text') != clave:
            st.session_state.last_text = clave
            st.session_state.step = ultimo
        step = min(st.session_state.get('step', ultimo), ultimo)
        c1, c2, c3, c4, c5 = st.columns([1, 1, 1.4, 1, 1])
        if c1.button('|<', use_container_width=True, disabled=step <= 0):
            step = 0
        if c2.button('<', use_container_width=True, disabled=step <= 0):
            step = max(0, step - 1)
        if c4.button('>', use_container_width=True, disabled=step >= ultimo):
            step = min(ultimo, step + 1)
        if c5.button('>|', use_container_width=True, disabled=step >= ultimo):
            step = ultimo
        st.session_state.step = step
        c3.markdown(f'<div class="linea" style="text-align:center;padding-top:6px">paso {step}/{ultimo}</div>',
                    unsafe_allow_html=True)
        if step == 0:
            msg = f'paso 0: se suponen verdaderas las {len(valid)} reglas y se aplican {len(arbol[0]["lits"])} letras obligadas'
        else:
            d = arbol[step]
            x = letra_de(d['decision'])
            msg = f'paso {step}: {d["regla"]} todavía no se cumple, se toma la rama {x} y se aplican {len(d["lits"]) - 1} letras obligadas'
            if d['cerrada'] is not None:
                msg += f' · se cierra: {L[d["cerrada"]]} y ¬{L[d["cerrada"]]}'
            if d['modelo'] is not None:
                msg += f' · rama abierta → M{d["modelo"] + 1}'
        linea(esc(msg), 'linea dim')
        linea(f'cláusulas: {res["clausulas"]} · nodos: {len(arbol)} · ramas cerradas: {res["cerradas"]} · '
              f'tiempo: {res["segundos"]} s' + (' · se dibujan los primeros nodos' if res['arbol_cortado'] else '') +
              ('' if res['completo'] else f' · se detuvo al encontrar {len(res["modelos"])} modelos'))
        hl = set()
        hojas_modelo = {d['modelo']: i for i, d in enumerate(arbol) if d['modelo'] is not None}
        if len(hojas_modelo) > 1:
            sel = st.selectbox('resaltar', ['resaltar rama: (ninguna)'] + [f'M{k + 1}' for k in sorted(hojas_modelo)],
                               label_visibility='collapsed')
            if sel.startswith('M'):
                i = hojas_modelo[int(sel[1:]) - 1]
                while i is not None:
                    hl.add(i)
                    i = arbol[i]['padre']
        svg, W = dibujar_arbol_rapido(arbol, step, hl)
        mostrar_svg(svg, W)
        linea(f'recuadro <span class="V">verde</span> = rama abierta (modelo) · <span class="F">rojo</span> = rama cerrada · '
              f'«obligadas» = letras que se deducen sin bifurcar · si el árbol no cabe, usa + zoom y desplázate', 'linea dim')
    elif total is None:
        # árbol completo de una base grande: método clásico construido rama por rama, escrito como carpetas
        linea('árbol completo con el método clásico: se desarrolla cada fórmula en todas las ramas, sin poda. '
              'con muchas reglas crece muchísimo, así que se construye hasta el número de nodos elegido.', 'linea dim')
        cap = st.select_slider('nodos a construir', options=[2000, 5000, 10000, 20000, 50000], value=10000)
        with st.spinner('construyendo el árbol completo...'):
            A, lineas_arbol = construir_completo(texto, cap)
        if A['completo']:
            estado = '<span class="V">árbol completo terminado</span>'
        else:
            estado = (f'<span class="F">se construyeron {len(A["nodos"])} nodos y quedaron {A["pendientes"]} ramas sin terminar</span>'
                      f' · el árbol completo de esta base es más grande que lo que cabe en la memoria de una computadora;'
                      f' el resultado de abajo se calcula con el método rápido')
        linea(f'{estado}<br>nodos: {len(A["nodos"])} · ramas abiertas: {A["abiertas"]} · ramas cerradas: {A["cerradas"]} · '
              f'tiempo: {A["segundos"]} s')
        cuerpo = []
        for t, fin in lineas_arbol:
            if fin.startswith('✕'):
                cuerpo.append(esc(t[:-len(fin)]) + f'<span class="F">{esc(fin)}</span>')
            elif fin.startswith('○'):
                cuerpo.append(esc(t[:-len(fin)]) + f'<span class="V">{esc(fin)}</span>')
            else:
                cuerpo.append(esc(t))
        st.markdown(f'<div style="max-height:700px;overflow:auto;white-space:pre;font-size:13px;line-height:1.5;'
                    f'border:1px solid #222;padding:8px">' + '\n'.join(cuerpo) + '</div>', unsafe_allow_html=True)
        st.download_button('descargar el árbol completo (.txt)', '\n'.join(t for t, _ in lineas_arbol),
                           file_name='arbol_completo.txt')
        linea('├─ └─ = bifurcación (β) · renglón sin rama = regla que no bifurca (α) · '
              '<span class="F">✕</span> rama cerrada · <span class="V">○</span> rama abierta', 'linea dim')
    else:
        if st.session_state.get('last_text') != texto:
            st.session_state.last_text = texto
            st.session_state.step = total
        step = min(st.session_state.get('step', total), total)

        c1, c2, c3, c4, c5 = st.columns([1, 1, 1.4, 1, 1])
        if c1.button('|<', use_container_width=True, disabled=step <= 0):
            step = 0
        if c2.button('<', use_container_width=True, disabled=step <= 0):
            step = max(0, step - 1)
        if c4.button('>', use_container_width=True, disabled=step >= total):
            step = min(total, step + 1)
        if c5.button('>|', use_container_width=True, disabled=step >= total):
            step = total
        st.session_state.step = step
        c3.markdown(f'<div class="linea" style="text-align:center;padding-top:6px">paso {step}/{total}</div>',
                    unsafe_allow_html=True)

        T = run_tableau(valid, L, step)
        open_idx = {leaf.id: i + 1 for i, leaf in enumerate(T['open'])} if T['done'] else {}
        models = [model_of(leaf, len(atoms)) for leaf in T['open']] if T['done'] else []

        # explicación del paso actual
        if step == 0:
            msg = 'paso 0: se suponen verdaderas todas las reglas (' + ', '.join(r.label for r in valid) + ')'
        else:
            lg = T['log'][step - 1]
            if lg['kind'] == 'α':
                como = 'no bifurca: ' + lg['branches'][0]
            else:
                como = 'bifurca en ' + lg['branches'][0] + ' | ' + lg['branches'][1]
            msg = f'paso {step}: se aplica {lg["src"] + " = " if lg["src"] else ""}{lg["str"]} ({lg["rule"]}), {como}'
            if lg['closed']:
                msg += ' · se cierra: ' + '; '.join(' y '.join(c) for c in lg['closed'])
        if T['done']:
            msg += ' · fin'
        linea(esc(msg), 'linea dim')

        # resaltar la rama de un modelo
        hl = set()
        if len(models) > 1:
            sel = st.selectbox('resaltar', ['resaltar rama: (ninguna)'] + [f'M{i + 1}' for i in range(len(models))],
                               label_visibility='collapsed')
            if sel.startswith('M'):
                hl = set(models[int(sel[1:]) - 1][1])

        # medidas del dibujo
        def ancho(s, size):
            return len(s) * size * 0.6

        PX, PY, LH, GX, GY, MARCA = 10, 8, 20, 30, 56, 34

        def etiqueta_rama(n):
            # texto que va en la rama que sale de este nodo
            v = n.children[0].via
            src = v['src'] if len(v['src']) <= 12 else ''
            return f'paso {v["step"]} · {src} ({v["rule"]})'.replace(' ·  (', ' · (')

        def etiqueta_hoja(n):
            if n.closed:
                return '✕ cerrada: ' + ' y '.join(n.close_lits)
            if T['done']:
                return '○ abierta → M%d' % open_idx[n.id]
            return '...'

        def medir(n):
            w = 30
            for e in n.entries:
                t = (e.label + ' ' if e.label else '') + e.str
                x = ancho(t, 14)
                if e.applied:
                    x += 6 + ancho('✓' + str(e.applied), 12)
                w = max(w, x)
            n.w = w + 2 * PX
            n.h = len(n.entries) * LH + 2 * PY - 4
            extra = ancho(etiqueta_hoja(n), 12) + 10 if not n.children else 0
            for c in n.children:
                medir(c)
            hijos = sum(c.sw for c in n.children) + GX * max(0, len(n.children) - 1)
            if n.children:
                extra = n.w + 2 * (ancho(etiqueta_rama(n), 11) + 10)
            n.sw = max(n.w, extra, hijos)

        fondo = [0]

        def ubicar(n, cx, y):
            n.cx, n.x, n.y = cx, cx - n.w / 2, y
            bajo = 16 if n.parent is None else 0
            fondo[0] = max(fondo[0], y + n.h + (0 if n.children else MARCA))
            hijos = sum(c.sw for c in n.children) + GX * max(0, len(n.children) - 1)
            x = cx - hijos / 2
            for c in n.children:
                ubicar(c, x + c.sw / 2, y + n.h + GY + bajo)
                x += c.sw + GX

        raiz = T['root']
        medir(raiz)
        ubicar(raiz, raiz.sw / 2 + 10, 10)
        W, H = raiz.sw + 20, fondo[0] + 10

        partes = []
        for n in T['nodes']:
            enc = n.id in hl
            # ramas hacia los hijos
            if n.children:
                y0 = n.y + n.h + (18 if n.parent is None else 0)
                for c in n.children:
                    color = FG if c.id in hl else LINE
                    partes.append(f'<line x1="{n.cx}" y1="{y0}" x2="{c.cx}" y2="{c.y}" stroke="{color}" stroke-width="1.2"/>')
                partes.append(f'<text x="{n.x + n.w + 8}" y="{n.y + n.h - 6}" fill="{DIM}" font-size="11">{esc(etiqueta_rama(n))}</text>')
            if n.parent is None:
                partes.append(f'<text x="{n.cx}" y="{n.y + n.h + 13}" fill="{DIM}" font-size="11" text-anchor="middle">'
                              f'raíz: todas las reglas verdaderas</text>')
            # caja del nodo
            hoja = not n.children
            borde = BAD if n.closed else (OK if hoja and T['done'] else (FG if n.parent is None else LINE))
            grosor = 2.4 if enc else 1.4
            partes.append(f'<rect x="{n.x}" y="{n.y}" width="{n.w}" height="{n.h}" fill="{BG}" stroke="{borde}" stroke-width="{grosor}"/>')
            for i, e in enumerate(n.entries):
                ty = n.y + PY + 14 + i * LH
                t = (e.label + ' ' if e.label else '') + e.str
                partes.append(f'<text x="{n.x + PX}" y="{ty}" fill="{FG}" font-size="14">{esc(t)}</text>')
                if e.applied:
                    partes.append(f'<text x="{n.x + PX + ancho(t, 14) + 6}" y="{ty}" fill="{OK}" font-size="12">✓{e.applied}</text>')
            if hoja:
                color = BAD if n.closed else (OK if T['done'] else DIM)
                partes.append(f'<text x="{n.cx}" y="{n.y + n.h + 18}" fill="{color}" font-size="12" text-anchor="middle">'
                              f'{esc(etiqueta_hoja(n))}</text>')

        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
               f'font-family="Consolas, Courier New, monospace"><rect width="100%" height="100%" fill="{BG}"/>'
               f'{"".join(partes)}</svg>')
        mostrar_svg(svg, W)
        linea(f'recuadro <span class="V">verde</span> = rama abierta (modelo) · <span class="F">rojo</span> = rama cerrada · '
              f'✓n = regla ya aplicada en el paso n · si el árbol no cabe, usa + zoom y desplázate', 'linea dim')

# resultado
with st.container(border=True):
    titulo_caja('resultado')
    if T is not None:
        # resultado del árbol dibujado
        if not T['done']:
            linea('en proceso... avanza hasta el último paso (>|)', 'linea dim')
        elif not T['open']:
            linea('<span class="F">INSATISFACIBLE</span> · todas las ramas se cierran, la base de conocimiento es inconsistente')
            por_letra = {a.letter: a for a in atoms}
            choques = []
            for n in T['nodes']:
                if n.closed:
                    letra = n.close_lits[0].lstrip('¬')
                    a = por_letra[letra]
                    txt = f'✕ «{esc(a.meaning)}» y «{esc(negar(a))}» no pueden ser ciertas a la vez ({letra}, ¬{letra})'
                    if txt not in choques:
                        choques.append(txt)
            linea('<br>'.join(choques), 'linea F')
        else:
            linea(f'SATISFACIBLE · {len(T["open"])} abierta(s), {T["closed_count"]} cerrada(s)')
            vistos = {}
            for i, (v, _) in enumerate(models):
                clave = tuple(v)
                igual = f'&nbsp;&nbsp;<span class="dim">(igual a M{vistos[clave]})</span>' if clave in vistos else ''
                vistos.setdefault(clave, i + 1)
                linea('')
                mostrar_modelo(i, v, igual)
    else:
        # resultado del método rápido
        res = resolver(texto)
        if not res['modelos']:
            linea('<span class="F">INSATISFACIBLE</span> · todas las ramas se cierran, la base de conocimiento es inconsistente')
            choques = [f'✕ «{esc(atoms[k].meaning)}» y «{esc(negar(atoms[k]))}» no pueden ser ciertas a la vez '
                       f'({L[k]}, ¬{L[k]})' for k in res['choques']]
            linea('<br>'.join(choques), 'linea F')
        else:
            n = len(res['modelos'])
            if res['completo']:
                cuantos = f'{n} rama(s) abierta(s) (modelos)'
            else:
                cuantos = f'se muestran las primeras {n} ramas abiertas (hay más)'
            linea(f'SATISFACIBLE · {cuantos} · {res["cerradas"]} cerrada(s)')
            linea('cada modelo está en su desplegable; ábrelo para ver lo que se cumple y lo que no', 'linea dim')
            for i, v in enumerate(res['modelos']):
                nv, nf, nx = v.count('V'), v.count('F'), v.count(None)
                with st.expander(f'M{i + 1} · {nv} verdaderas · {nf} falsas · {nx} da igual', expanded=(i == 0 and len(atoms) <= 30)):
                    mostrar_modelo(i, v)
