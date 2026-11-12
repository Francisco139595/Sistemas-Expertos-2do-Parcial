# Para correr el programa: py -3.12 -m streamlit run app.py
import base64
import html
import re

import streamlit as st

import almacen
import voz
from motor import (analyze, run_tableau, model_of, frase_modelo, negar, resolver_rapido,
                   arbol_completo, arbol_en_texto, encadenar_adelante,
                   evaluar_hipotesis, consultar, consecuencias, parecidas, leer_hipotesis,
                   explicar, interpretar_pista, formula_de, dominio, y_lista, norm,
                   hipotesis_juego, es_de_produccion, preguntables, estado_juego, pregunta_adelante,
                   pregunta_atras, pregunta_texto, respuesta_si_no)

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

# personajes o conceptos: cada uno se guarda como una regla con sus características
@st.cache_data(show_spinner=False)
def caracteristicas(texto):
    if not texto.strip():
        return []
    a, r, letras = analyze(texto)
    hips, origen = hipotesis_juego(texto, a, r)
    return [a[i].meaning for i in preguntables(r, len(a), hips, True)]


def _insertar_regla(kb, regla):
    # las reglas nuevas van antes de los descubrimientos
    if ENCABEZADO_D in kb:
        antes, despues = kb.split(ENCABEZADO_D, 1)
        return antes.rstrip('\n') + '\n' + regla + '\n\n' + ENCABEZADO_D + despues
    return kb.rstrip('\n') + ('\n' if kb.strip() else '') + regla + '\n'


def al_guardar_personaje():
    s = st.session_state
    nombre = s.get('per_nombre', '').strip().rstrip('.')
    si = list(s.get('per_si', [])) + [x.strip() for x in s.get('per_si_nuevas', '').split(',') if x.strip()]
    no = list(s.get('per_no', [])) + [x.strip() for x in s.get('per_no_nuevas', '').split(',') if x.strip()]
    if not nombre or not (si or no):
        s.per_aviso = 'falta el nombre o al menos una característica'
        return
    a = analyze(s.kb)[0] if s.kb.strip() else []
    por_texto = {x.meaning: x for x in a}
    negadas = [negar(por_texto[x]) if x in por_texto else 'no ' + x for x in no]
    conclusion = nombre if re.match(r'^(es|son|era|fue)\b', norm(nombre)) else 'es ' + nombre
    regla = 'Si ' + ' y '.join(si + negadas) + ' entonces ' + conclusion
    s.kb = _insertar_regla(s.kb, regla)
    s.per_aviso = f'guardado: {regla}'
    s.per_nombre, s.per_si, s.per_no, s.per_si_nuevas, s.per_no_nuevas = '', [], [], '', ''


ENCABEZADO_D = '# Descubrimientos'

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
    with st.expander('agregar personaje o concepto (para las preguntas tipo Akinator)'):
        opciones_c = caracteristicas(texto)
        st.text_input('nombre del personaje o concepto', key='per_nombre', placeholder='se guarda como «es …»')
        p1, p2 = st.columns(2)
        p1.multiselect('características que SÍ tiene', opciones_c, key='per_si')
        p1.text_input('nuevas que sí tiene (separadas por coma)', key='per_si_nuevas')
        p2.multiselect('características que NO tiene', opciones_c, key='per_no')
        p2.text_input('nuevas que no tiene (separadas por coma)', key='per_no_nuevas')
        st.button('guardar en la base', on_click=al_guardar_personaje)
        if st.session_state.get('per_aviso'):
            linea(esc(st.session_state.per_aviso), 'linea dim')
        linea('se guarda como una regla «Si … y … entonces es …» · escribe cada característica igual en todos los '
              'personajes y sin «y», «o», «si» o «entonces» adentro', 'linea dim')

atoms, rules, L = analizar(texto)
valid = [r for r in rules if r.f]

if not rules:
    st.stop()

CAJA_SCROLL = 'max-height:340px;overflow:auto'

# dominio de conocimiento: de qué trata la base
with st.container(border=True):
    titulo_caja('dominio de conocimiento')
    tema = dominio(texto)
    linea(f'<span style="font-size:18px">{esc(tema) if tema else "(la base no tiene título: escribe un comentario # en el primer renglón)"}</span>')
    linea(f'{len(valid)} reglas y hechos · {len(atoms)} átomos · {len(leer_hipotesis(texto))} hipótesis', 'linea dim')

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


# descubrimientos e hipótesis: se agregan hechos nuevos y se reevalúan las hipótesis


def descubrimientos(texto):
    # renglones escritos debajo de «# Descubrimientos»
    if ENCABEZADO_D not in texto:
        return []
    resto = texto.split(ENCABEZADO_D, 1)[1].splitlines()[1:]
    return [x.strip() for x in resto if x.strip() and not x.strip().startswith('#')]


def al_agregar_descubrimiento():
    frase = st.session_state.get('nuevo_desc', '').strip()
    if not frase:
        return
    kb = st.session_state.kb.rstrip('\n')
    if ENCABEZADO_D not in kb:
        kb += '\n\n' + ENCABEZADO_D
    st.session_state.kb = kb + '\n' + frase + '\n'
    st.session_state.nuevo_desc = ''


def al_quitar_descubrimiento():
    lineas = st.session_state.kb.rstrip('\n').split('\n')
    if ENCABEZADO_D not in st.session_state.kb:
        return
    pos = max(i for i, x in enumerate(lineas) if x.strip() == ENCABEZADO_D)
    for i in range(len(lineas) - 1, pos, -1):
        if lineas[i].strip() and not lineas[i].strip().startswith('#'):
            del lineas[i]
            break
    if not any(x.strip() for x in lineas[pos + 1:]):
        del lineas[pos:]
    st.session_state.kb = '\n'.join(lineas).rstrip('\n') + '\n'


@st.cache_data(show_spinner=False)
def hipotesis(texto):
    a, r, letras = analyze(texto)
    return evaluar_hipotesis(texto, a, r, letras)


@st.cache_data(show_spinner=False)
def revisar_descubrimientos(texto):
    # avisa si un descubrimiento usa una frase que no aparece en ninguna regla
    base = texto.split(ENCABEZADO_D, 1)[0]
    a, r, letras = analyze(base)
    avisos = []
    for d in descubrimientos(texto):
        c = consultar(a, r, letras, d)
        for nueva in c.get('nuevas', []):
            sug = parecidas(nueva, a)
            avisos.append(f'⚠ «{esc(nueva)}» no aparece en ninguna regla' +
                          (f' · ¿quisiste decir «{esc(sug[0])}»?' if sug else ' · revisa que esté escrita igual que en las reglas'))
    return avisos


@st.cache_data(show_spinner=False)
def consulta(texto, frase):
    a, r, letras = analyze(texto)
    c = consultar(a, r, letras, frase)
    c.pop('f', None)
    if c.get('nuevas'):
        c['sugerencias'] = {n: parecidas(n, a) for n in c['nuevas']}
    return c


@st.cache_data(show_spinner=False)
def certezas(texto):
    a, r, letras = analyze(texto)
    return consecuencias(r, len(a))


def al_agregar_hipotesis():
    frase = st.session_state.get('nueva_hip', '').strip()
    if not frase:
        return
    n = len(leer_hipotesis(st.session_state.kb)) + 1
    st.session_state.kb = st.session_state.kb.rstrip('\n') + f'\n# h{n}: {frase}\n'
    st.session_state.nueva_hip = ''


HIPS = hipotesis(texto)
ESTADO_COLOR = {'CONFIRMADA': OK, 'POSIBLE': FG, 'DESCARTADA': BAD, 'BASE INCONSISTENTE': DIM}


def chip(estado):
    c = ESTADO_COLOR.get(estado, DIM)
    return f'<span style="border:1px solid {c};color:{c};padding:0 6px;white-space:nowrap">{estado}</span>'


def tabla(filas, encabezado):
    # tabla sencilla con líneas, en el estilo de la consola
    th = ''.join(f'<th style="text-align:left;color:{DIM};font-weight:400;padding:4px 10px;'
                 f'border-bottom:1px solid {LINE}">{h}</th>' for h in encabezado)
    tr = ''.join('<tr>' + ''.join(f'<td style="padding:5px 10px;border-bottom:1px solid #222;vertical-align:top">{c}</td>'
                                  for c in f) + '</tr>' for f in filas)
    return f'<table style="width:100%;border-collapse:collapse;font-size:15px"><tr>{th}</tr>{tr}</table>'


# voz (VUI): se dicen las pistas y el programa contesta hablando
def _procesar_pista(texto_pista):
    # interpreta la pista y, si se pidió, la agrega a la base
    a, r, letras = analyze(st.session_state.kb)
    res = interpretar_pista(texto_pista, a)
    st.session_state.voz_oido = texto_pista
    st.session_state.voz_frases = res
    if st.session_state.get('voz_auto') and res and all(x['frase'] for x in res):
        _agregar_frases([x['frase'] for x in res])


def _agregar_frases(frases):
    kb = st.session_state.kb.rstrip('\n')
    if ENCABEZADO_D not in kb:
        kb += '\n\n' + ENCABEZADO_D
    st.session_state.kb = kb + '\n' + '\n'.join(frases) + '\n'
    st.session_state.voz_frases = []
    st.session_state.decir = True
    st.session_state.confirmar = 'Entendí: ' + y_lista(frases) + '.'


def al_grabar():
    audio = st.session_state.get('mic')
    if audio is None:
        return
    texto_oido, motor_oido, error = voz.transcribir(audio.getvalue())
    st.session_state.voz_motor = motor_oido
    st.session_state.voz_error = error
    if texto_oido:
        _procesar_pista(texto_oido)


def al_interpretar_texto():
    t = st.session_state.get('pista_txt', '').strip()
    if t:
        st.session_state.voz_error = None
        st.session_state.voz_motor = 'texto'
        _procesar_pista(t)
        st.session_state.pista_txt = ''


def al_agregar_entendido():
    frases = [x['frase'] for x in st.session_state.get('voz_frases', []) if x['frase']]
    if frases:
        _agregar_frases(frases)


VOZ_NOMBRES = list(voz.VOCES)


def _voz_actual():
    for k, v in voz.VOCES.items():
        if v == voz.AJUSTES['voz_edge']:
            return VOZ_NOMBRES.index(k)
    return 0


def al_cambiar_voz():
    voz.guardar_ajustes(voz_edge=voz.VOCES[st.session_state.voz_sel], velocidad=f'{st.session_state.voz_vel:+d}%')


def decir(frase):
    # genera el audio y lo reproduce solo; dice con qué voz salió
    audio, tipo, motor_voz, error = voz.hablar(frase)
    if not audio:
        linea(f'no se pudo generar la voz: {esc(error)}', 'linea F')
        return
    st.audio(audio, format=tipo, autoplay=True)
    if motor_voz == 'voz de Windows':
        linea(f'voz de Windows (robótica) porque la voz neural no funcionó: {esc(error or "")} · '
              f'revisa el internet o actualiza con  py -3.12 -m pip install -U edge-tts', 'linea F')
    else:
        linea(f'voz: {esc(motor_voz)}', 'linea dim')


with st.container(border=True):
    titulo_caja('voz · dile la pista al motor')
    st.audio_input('graba la pista', key='mic', on_change=al_grabar, label_visibility='collapsed')
    t1, t2 = st.columns([4.2, 1.2])
    t1.text_input('pista', key='pista_txt', label_visibility='collapsed',
                  placeholder='o escribe la pista como viene, con tus palabras, y da clic en interpretar')
    t2.button('interpretar', use_container_width=True, on_click=al_interpretar_texto)
    st.checkbox('agregar automáticamente lo que entienda', key='voz_auto', value=True)
    v1, v2, v3 = st.columns([2.6, 1.6, 1.2])
    v1.selectbox('voz con la que habla el programa', VOZ_NOMBRES, index=_voz_actual(), key='voz_sel', on_change=al_cambiar_voz)
    vel_actual = int(re.sub(r'[^\d-]', '', voz.AJUSTES.get('velocidad', '0')) or 0)
    v2.slider('velocidad (%)', -30, 30, vel_actual, 5, key='voz_vel', on_change=al_cambiar_voz)
    v3.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    if v3.button('probar voz', use_container_width=True):
        decir('Hola. Así sueno cuando te doy la respuesta.')
    if st.session_state.get('voz_error'):
        linea(f'no se pudo transcribir: {esc(st.session_state.voz_error)}', 'linea F')
    if st.session_state.get('voz_oido'):
        de = st.session_state.get('voz_motor') or ''
        linea(f'escuché ({esc(de)}): «{esc(st.session_state.voz_oido)}»', 'linea dim')
    pendientes = st.session_state.get('voz_frases', [])
    if pendientes:
        filas_v = []
        for x in pendientes:
            if x['frase']:
                filas_v.append([esc(x['dicho']), f'<span class="V">{esc(x["frase"])}</span>', f'{int(x["confianza"] * 100)}%'])
            else:
                filas_v.append([esc(x['dicho']), '<span class="F">no se parece a ninguna frase de la base</span>',
                                f'{int(x["confianza"] * 100)}%'])
        linea(tabla(filas_v, ['dijiste', 'entendí', 'parecido']))
        st.button('agregar lo que entendí como descubrimiento', on_click=al_agregar_entendido,
                  disabled=not any(x['frase'] for x in pendientes))


# 1) descubrimientos: hechos nuevos que se van agregando
with st.container(border=True):
    titulo_caja('descubrimientos (hechos nuevos)')
    d1, d2, d3 = st.columns([3, 1.2, 1.2])
    d1.text_input('descubrimiento', key='nuevo_desc', label_visibility='collapsed',
                  placeholder='escribe el hecho nuevo con las mismas palabras que en las reglas')
    d2.button('agregar', use_container_width=True, on_click=al_agregar_descubrimiento)
    desc = descubrimientos(texto)
    d3.button('quitar último', use_container_width=True, on_click=al_quitar_descubrimiento, disabled=not desc)
    if desc:
        linea(tabla([[f'D{i + 1}', esc(x)] for i, x in enumerate(desc)], ['', 'hecho agregado']))
        for aviso in revisar_descubrimientos(texto):
            linea(aviso, 'linea F')
    else:
        linea('sin descubrimientos · cada uno se agrega como hecho al final de la base y todo se recalcula', 'linea dim')

@st.cache_data(show_spinner=False)
def explicaciones(texto):
    a, r, letras = analyze(texto)
    out = {}
    for h in evaluar_hipotesis(texto, a, r, letras):
        if 'error' in h or h['estado'] not in ('DESCARTADA', 'CONFIRMADA'):
            continue
        f, nuevas = formula_de(a, h['frase'])
        if nuevas:
            continue
        if h['estado'] == 'CONFIRMADA':
            f = ('not', f)
        e = explicar(a, r, letras, f, h['nombre'] if h['estado'] == 'DESCARTADA' else f'lo contrario de {h["nombre"]}')
        if e:
            out[h['nombre']] = e
    return out


def respuesta_en_voz(validas):
    # lo que el programa dice en voz alta
    siguen = [h for h in validas if h['estado'] in ('CONFIRMADA', 'POSIBLE')]
    fuera = [h for h in validas if h['estado'] == 'DESCARTADA']
    if validas and all(h['estado'] == 'BASE INCONSISTENTE' for h in validas):
        return 'La base de conocimiento se volvió contradictoria. No queda ninguna hipótesis posible.'
    if len(siguen) == 1 and siguen[0]['estado'] == 'CONFIRMADA':
        return f'La respuesta es: {siguen[0]["frase"]}. Es la única hipótesis que queda.'
    partes = []
    if siguen:
        partes.append(f'Siguen siendo posibles {len(siguen)}: ' + y_lista([h['frase'] for h in siguen]) + '.')
    else:
        partes.append('No queda ninguna hipótesis posible.')
    if fuera:
        partes.append('Se descartan: ' + y_lista([h['frase'] for h in fuera]) + '.')
    return ' '.join(partes)


# 2) hipótesis: cuáles siguen siendo posibles
with st.container(border=True):
    titulo_caja('hipótesis')
    if HIPS:
        validas = [h for h in HIPS if 'error' not in h]
        siguen = [h for h in validas if h['estado'] in ('CONFIRMADA', 'POSIBLE')]
        confirmadas = [h for h in validas if h['estado'] == 'CONFIRMADA']
        if validas and all(h['estado'] == 'BASE INCONSISTENTE' for h in validas):
            res_c = resolver(texto)
            choque = ''
            if res_c and res_c['choques']:
                k = res_c['choques'][0]
                choque = f'<br>choca «{esc(atoms[k].meaning)}» con «{esc(negar(atoms[k]))}»'
            linea(f'<span class="F" style="font-size:20px">SIGUEN SIENDO POSIBLES: 0</span><br>'
                  f'<span class="F">la base se volvió contradictoria: todas las ramas se cierran</span>{choque}')
        else:
            color_n = OK if siguen else BAD
            linea(f'<span style="font-size:20px">SIGUEN SIENDO POSIBLES: <b style="color:{color_n}">{len(siguen)}</b></span>')
            if confirmadas and len(siguen) == 1:
                linea(f'<span class="V">RESPUESTA: {confirmadas[0]["nombre"]} · {esc(confirmadas[0]["frase"])} '
                      f'(es la única y la base la confirma)</span>')
            elif siguen:
                linea('<br>'.join(f'<span class="V">✓</span> {h["nombre"]} · {esc(h["frase"])}' for h in siguen))
        filas = []
        for h in HIPS:
            if 'error' in h:
                filas.append([h['nombre'], esc(h['frase']), f'<span class="F">no se pudo traducir</span>'])
                continue
            nota = ' <span class="F">⚠ no aparece en las reglas</span>' if h['nueva'] else ''
            filas.append([h['nombre'], esc(h['frase']) + nota, chip(h['estado'])])
        linea('<br>' + tabla(filas, ['', 'hipótesis', 'estado']))
        linea('CONFIRMADA = verdadera en todos los modelos · POSIBLE = en algunos sí y en otros no · '
              'DESCARTADA = en ningún modelo', 'linea dim')

        # motor de explicación: por qué se descarta o se confirma cada una
        EXPL = explicaciones(texto)
        for h in validas:
            e = EXPL.get(h['nombre'])
            if not e:
                continue
            que = 'se descarta' if h['estado'] == 'DESCARTADA' else 'se confirma'
            with st.expander(f'¿por qué {que} {h["nombre"]}? · {h["frase"]}'):
                if h['estado'] == 'CONFIRMADA':
                    linea('si fuera falsa, pasaría esto:', 'linea dim')
                linea('<br>'.join(f'{i + 1}. {esc(p)}' for i, p in enumerate(e['pasos'])))
                linea('reglas usadas: ' + ', '.join(e['reglas']), 'linea dim')

        # respuesta hablada
        frase_resp = respuesta_en_voz(validas)
        r1, r2 = st.columns([1.4, 4])
        boton = r1.button('escuchar respuesta', use_container_width=True)
        por_pista = st.session_state.pop('decir', False)
        confirmacion = st.session_state.pop('confirmar', '')
        r2.markdown(f'<div class="linea dim" style="padding-top:6px">«{esc(frase_resp)}»</div>', unsafe_allow_html=True)
        if boton or por_pista:
            # un solo audio: primero lo que entendió de la pista y después las opciones que quedan
            decir((confirmacion + ' ' if por_pista and confirmacion else '') + frase_resp)
    else:
        linea('no hay hipótesis · agrégalas aquí abajo, o en el archivo con renglones que empiecen con  # h1:', 'linea dim')
    h1c, h2c = st.columns([4.2, 1.2])
    h1c.text_input('hipótesis', key='nueva_hip', label_visibility='collapsed',
                   placeholder='escribe una hipótesis a evaluar, con las mismas palabras que en las reglas')
    h2c.button('agregar hipótesis', use_container_width=True, on_click=al_agregar_hipotesis)

# encadenamiento con preguntas (tipo Akinator)
#   hacia adelante: el programa pregunta y con las respuestas llega a la hipótesis
#   hacia atrás: se escoge la hipótesis y el programa pregunta solo lo que necesita para demostrarla
@st.cache_data(show_spinner=False)
def juego_base(texto):
    a, r, letras = analyze(texto)
    hips, origen = hipotesis_juego(texto, a, r)
    return [{'nombre': h['nombre'], 'frase': h['frase']} for h in hips], origen, es_de_produccion(r) and origen == 'reglas'


def _frase_l(a, l):
    return a[l[0]].meaning if l[1] else negar(a[l[0]])


@st.cache_data(show_spinner=False)
def juego_paso(texto, modo, meta_i, cerrado, resp):
    a, r, letras = analyze(texto)
    hips, origen = hipotesis_juego(texto, a, r)
    idx = {x.meaning: i for i, x in enumerate(a)}
    respuestas = [(idx[m], v) for m, v in resp if m in idx]
    J = estado_juego(a, r, hips, respuestas, cerrado)
    cand = preguntables(r, len(a), hips, cerrado)
    ya = {x for x, _ in respuestas}
    q = None
    if modo == 'adelante':
        q = pregunta_adelante(a, J, hips, cand, ya)
    elif J['estados'][meta_i] == 'POSIBLE':
        q = pregunta_atras(a, r, letras, J, hips[meta_i], cand, respuestas)
    if q:
        q['texto'] = pregunta_texto(a[q['letra']])
        q['frase'] = a[q['letra']].meaning
    # lo que se deduce de las respuestas: encadenamiento hacia adelante con las respuestas como hechos
    A = encadenar_adelante([x for x in r if x.f] + J['resp'], letras)
    deducciones = []
    for p in A['pasos']:
        if p['nuevas']:
            un = ' y ' if p['tipo'] == 'y' else ' o '
            deducciones.append(f'{p["regla"]}: como {un.join(_frase_l(a, x) for x in p["premisas"])} → '
                               + ', '.join(_frase_l(a, x) for x in p['nuevas']))
    # explicaciones cuando ya no hay pregunta
    expl = {}
    if q is None:
        kb = [x for x in r if x.f] + J['extra'] + J['resp']
        quienes = range(len(hips)) if modo == 'adelante' else [meta_i]
        for i in quienes:
            e, h = J['estados'][i], hips[i]
            if e == 'DESCARTADA':
                expl[i] = explicar(a, kb, letras, h['f'], f'«{h["frase"]}»')
            elif e == 'CONFIRMADA':
                expl[i] = explicar(a, kb, letras, ('not', h['f']), f'que no fuera «{h["frase"]}»')
    return {'estados': J['estados'], 'pregunta': q, 'deducciones': deducciones, 'expl': expl,
            'quedan_preguntas': len([c for c in cand if c not in ya])}


def _jg_hablar():
    # el juego solo habla en la vuelta que provocó el propio juego (así no se encima con otras voces)
    st.session_state.jg_hablar_ahora = True


def _jg_empezar():
    st.session_state.jg_activo = True
    st.session_state.jg_resp = []
    _jg_hablar()


def _jg_terminar():
    st.session_state.jg_activo = False


def _jg_responder(valor):
    q = st.session_state.get('jg_preg')
    if q:
        st.session_state.jg_resp = st.session_state.jg_resp + [(q, valor)]
        st.session_state.jg_aviso = ''
        _jg_hablar()


def _jg_deshacer():
    st.session_state.jg_resp = st.session_state.jg_resp[:-1]
    _jg_hablar()


def _jg_reiniciar():
    st.session_state.jg_resp = []
    _jg_hablar()


def _jg_voz(clave):
    audio = st.session_state.get(clave)
    if audio is None:
        return
    oido, _, error = voz.transcribir(audio.getvalue())
    if not oido:
        st.session_state.jg_aviso = f'no se pudo transcribir: {error}'
        return
    r = respuesta_si_no(oido)
    if r is None:
        st.session_state.jg_aviso = f'escuché «{oido}» pero no entendí si es sí, no o no sé'
        return
    _jg_responder({'si': True, 'no': False, 'nose': None}[r])
    dicho = {'si': 'sí', 'no': 'no', 'nose': 'no sé'}[r]
    st.session_state.jg_aviso = f'escuché «{oido}» → {dicho}'
    st.session_state.jg_confirmar = f'Dijiste: {dicho}.'


def _jg_comprobar(i):
    # pasa a hacia atrás con esa hipótesis como meta, conservando lo ya contestado
    st.session_state.jg_modo = ATRAS_J
    st.session_state.jg_meta = i
    st.session_state.jg_mantener = True
    _jg_hablar()


ADELANTE_J, ATRAS_J = 'hacia adelante · el programa adivina', 'hacia atrás · comprueba una hipótesis'
NOMBRE_RESP = {True: '<span class="V">sí</span>', False: '<span class="F">no</span>', None: '<span class="dim">no sé</span>'}

with st.container(border=True):
    titulo_caja('encadenamiento con preguntas (tipo Akinator)')
    hips_j, origen_j, cerrado_def = juego_base(texto)
    if not hips_j:
        linea('no hay a qué llegar: escribe reglas «Si … entonces es …» (o agrega un personaje en el recuadro de reglas), '
              'o hipótesis con renglones  # h1: …', 'linea dim')
    else:
        g1, g2 = st.columns([2.4, 1])
        modo_j = g1.radio('modo', [ADELANTE_J, ATRAS_J], horizontal=True, key='jg_modo', label_visibility='collapsed',
                          on_change=_jg_hablar)
        cerrado = g2.checkbox('mundo cerrado', value=cerrado_def, key=f'jg_cerrado|{st.session_state.sel}|{origen_j}',
                              help='lo que concluyen las reglas solo es cierto si se cumple alguna de esas reglas; '
                                   'sirve para bases de personajes «Si … entonces es …»')
        meta_i = 0
        if modo_j == ATRAS_J:
            meta_i = st.selectbox('hipótesis a comprobar (la meta)', range(len(hips_j)), key='jg_meta', on_change=_jg_hablar,
                                  format_func=lambda i: f'{hips_j[i]["nombre"]} · {hips_j[i]["frase"]}')
            meta_i = min(meta_i or 0, len(hips_j) - 1)
        modo = 'adelante' if modo_j == ADELANTE_J else 'atras'
        clave = (st.session_state.sel, modo, meta_i, cerrado, origen_j)
        if st.session_state.get('jg_clave') != clave:
            st.session_state.jg_clave = clave
            if not st.session_state.pop('jg_mantener', False):
                st.session_state.jg_resp = []
        resp = st.session_state.jg_resp
        P = juego_paso(texto, modo, meta_i, cerrado, tuple(resp))
        est = P['estados']
        vivas = [i for i, e in enumerate(est) if e in ('POSIBLE', 'CONFIRMADA')]
        q = P['pregunta']
        st.session_state.jg_preg = q['frase'] if q else None

        # resultado o pregunta (solo después de presionar «empezar»)
        decir_j = None
        activo = st.session_state.get('jg_activo', False)
        if not activo:
            linea('piensa en una de las hipótesis de abajo y presiona «empezar»' if modo == 'adelante' else
                  'escoge la hipótesis que quieres comprobar y presiona «empezar»', 'linea dim')
            st.button('empezar', on_click=_jg_empezar)
        elif modo == 'adelante':
            if all(e == 'BASE INCONSISTENTE' for e in est):
                linea('<span class="F" style="font-size:20px">LA BASE ES CONTRADICTORIA</span>')
                decir_j = 'La base de conocimiento es contradictoria.'
            elif not vivas:
                linea('<span class="F" style="font-size:20px">NINGUNA HIPÓTESIS CONCUERDA CON TUS RESPUESTAS</span>')
                decir_j = 'Ninguna hipótesis concuerda con tus respuestas.'
            elif len(vivas) == 1:
                h = hips_j[vivas[0]]
                if est[vivas[0]] == 'CONFIRMADA':
                    linea(f'<span class="V" style="font-size:24px">{esc(h["frase"].upper())}</span><br>'
                          f'<span class="dim">tus respuestas lo demuestran ({len(resp)} preguntas)</span>')
                    decir_j = f'Ya sé. {h["frase"]}.'
                else:
                    linea(f'<span style="font-size:24px">CREO QUE {esc(h["frase"].upper())}</span><br>'
                          f'<span class="dim">es la única que queda, pero falta confirmarla</span>')
                    st.button('comprobarla hacia atrás', on_click=_jg_comprobar, args=(vivas[0],))
                    decir_j = f'Creo que {h["frase"]}.'
            elif not q:
                linea(f'<span style="font-size:20px">QUEDAN {len(vivas)} Y YA NO HAY PREGUNTAS QUE LAS DISTINGAN</span>')
                decir_j = f'Quedan {len(vivas)}: ' + y_lista([hips_j[i]['frase'] for i in vivas]) + '.'
        else:
            h = hips_j[meta_i]
            if est[meta_i] == 'CONFIRMADA':
                linea(f'<span class="V" style="font-size:24px">SÍ: {esc(h["frase"].upper())}</span><br>'
                      f'<span class="dim">queda demostrado con tus respuestas ({len(resp)} preguntas)</span>')
                decir_j = f'Sí. Queda demostrado: {h["frase"]}.'
            elif est[meta_i] == 'DESCARTADA':
                otras = [hips_j[i]['frase'] for i in vivas]
                linea(f'<span class="F" style="font-size:24px">NO: {esc(h["frase"].upper())}</span>'
                      + (f'<br><span class="dim">siguen posibles: {esc(y_lista(otras))}</span>' if otras else ''))
                decir_j = f'No. Se descarta: {h["frase"]}.'
            elif est[meta_i] == 'BASE INCONSISTENTE':
                linea('<span class="F" style="font-size:20px">LA BASE ES CONTRADICTORIA</span>')
            elif not q:
                linea('<span style="font-size:20px">NO SE PUEDE DEMOSTRAR NI DESCARTAR CON PREGUNTAS</span>')
                decir_j = 'Con lo que puedo preguntar no se puede demostrar ni descartar.'

        if activo and q:
            linea(f'<span class="dim">PREGUNTA {len(resp) + 1}</span><br><span style="font-size:24px;color:#fff">{esc(q["texto"])}</span>')
            if modo == 'adelante':
                linea(f'si contestas sí quedan {len(q["si"])} · si contestas no quedan {len(q["no"])}', 'linea dim')
            else:
                linea('<br>'.join(esc(p) for p in q['porque']), 'linea dim')
            k1, k2, k3, k4, k5, k6 = st.columns(6)
            k1.button('sí', use_container_width=True, on_click=_jg_responder, args=(True,))
            k2.button('no', use_container_width=True, on_click=_jg_responder, args=(False,))
            k3.button('no sé', use_container_width=True, on_click=_jg_responder, args=(None,))
            k4.button('deshacer', use_container_width=True, on_click=_jg_deshacer, disabled=not resp)
            k5.button('empezar de nuevo', use_container_width=True, on_click=_jg_reiniciar, disabled=not resp)
            k6.button('terminar', use_container_width=True, on_click=_jg_terminar)
            clave_mic = f'mic_jg{len(resp)}'
            st.audio_input('contesta con la voz: sí, no o no sé', key=clave_mic, on_change=_jg_voz, args=(clave_mic,))
            decir_j = q['texto']
        elif activo:
            k4, k5, k6, _ = st.columns([1, 1, 1, 2])
            k4.button('deshacer', use_container_width=True, on_click=_jg_deshacer, disabled=not resp, key='jg_d2')
            k5.button('empezar de nuevo', use_container_width=True, on_click=_jg_reiniciar, key='jg_r2')
            k6.button('terminar', use_container_width=True, on_click=_jg_terminar, key='jg_t2')
        if st.session_state.get('jg_aviso'):
            linea(esc(st.session_state.jg_aviso), 'linea dim')

        hablar_j = st.session_state.pop('jg_hablar_ahora', False)
        confirmar_j = st.session_state.pop('jg_confirmar', '')
        if st.checkbox('leer en voz alta', key='jg_leer', value=True) and activo and hablar_j and decir_j:
            decir((confirmar_j + ' ' if confirmar_j else '') + decir_j)

        # cómo van las hipótesis
        linea(tabla([[hips_j[i]['nombre'], esc(hips_j[i]['frase']), chip(e)] for i, e in enumerate(est)],
                    ['', 'hipótesis', 'estado']))
        if resp:
            linea('<br>' + tabla([[f'P{k + 1}', esc('¿' + m[:1].upper() + m[1:] + '?'), NOMBRE_RESP[v]]
                                  for k, (m, v) in enumerate(resp)], ['', 'pregunta', 'respuesta']))
        if P['deducciones']:
            with st.expander('lo que el motor deduce de tus respuestas (encadenamiento hacia adelante)', expanded=not q):
                linea('<br>'.join(esc(d) for d in P['deducciones']))
        for i, e in P['expl'].items():
            if e:
                que = 'por qué sí' if est[i] == 'CONFIRMADA' else 'por qué no'
                with st.expander(f'{que}: {hips_j[i]["frase"]}'):
                    linea('<br>'.join(f'{k + 1}. {esc(p)}' for k, p in enumerate(e['pasos'])))
                    linea('reglas usadas: ' + ', '.join(e['reglas']), 'linea dim')
        linea('P1, P2… = tus respuestas, que se agregan como hechos · con «no sé» la pregunta se salta', 'linea dim')


# 3) consulta libre: cualquier frase, simple o compuesta
with st.container(border=True):
    titulo_caja('consulta libre')
    pregunta = st.text_input('consulta', key='consulta_libre', label_visibility='collapsed',
                             placeholder='escribe cualquier frase (puede llevar y, o, no, si… entonces) y presiona Enter')
    if pregunta.strip():
        c = consulta(texto, pregunta.strip())
        if 'error' in c:
            linea(f'no se pudo traducir: {esc(c["error"])}', 'linea F')
        else:
            significado = {'CONFIRMADA': 'es verdadera en todos los casos: se deduce de la base',
                           'POSIBLE': 'puede ser verdadera o falsa: la base no lo decide',
                           'DESCARTADA': 'es falsa en todos los casos: contradice la base',
                           'BASE INCONSISTENTE': 'la base no tiene modelos'}
            linea(tabla([[esc(c['formula']), chip(c['estado']), significado[c['estado']]]],
                        ['fórmula', 'estado', 'significa']))
            for n_, sug in c.get('sugerencias', {}).items():
                linea(f'⚠ «{esc(n_)}» no aparece en ninguna regla' +
                      (f' · ¿quisiste decir «{esc(sug[0])}»?' if sug else ''), 'linea F')
    else:
        linea('dice si la frase es verdadera siempre, a veces o nunca', 'linea dim')

# 4) lo que vale lo mismo en todos los modelos
with st.container(border=True):
    titulo_caja('lo que se sabe con certeza')
    seguras = certezas(texto)
    if seguras is None:
        linea('la base es contradictoria: no hay nada que se cumpla con certeza', 'linea F')
    elif seguras == 'grande':
        linea('la base es muy grande para revisarlo frase por frase · usa la consulta libre', 'linea dim')
    else:
        verdaderas = [atoms[i].meaning for i, v in seguras if v == 'V']
        falsas = [negar(atoms[i]) for i, v in seguras if v == 'F']
        cv, cf = st.columns(2)
        with cv:
            linea('<span class="V">✓ siempre verdadero</span><br>' +
                  ('<br>'.join(esc(x) for x in verdaderas) or '<span class="dim">-</span>'))
        with cf:
            linea('<span class="F">✕ siempre falso, o sea:</span><br>' +
                  ('<br>'.join(esc(x) for x in falsas) or '<span class="dim">-</span>'))


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
        cap = st.select_slider('nodos a construir', options=[2000, 5000, 10000, 20000, 50000], value=20000)
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
