# Para correr el programa: py -3.12 -m streamlit run app.py
import re
from dataclasses import dataclass, field

# 1. Normalización de texto
#    Se quita acento y se pasa a minúsculas SIN cambiar la longitud,
#    para que las posiciones del texto normalizado sirvan en el original.
ACC = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ü': 'u',
       'Á': 'a', 'É': 'e', 'Í': 'i', 'Ó': 'o', 'Ú': 'u', 'Ü': 'u', 'Ñ': 'ñ'}


def norm(s: str) -> str:
    out = []
    for ch in s:
        c = ACC.get(ch)
        if c is None:
            c = ch.lower()
            if len(c) != 1:
                c = ch
        out.append(c)
    return ''.join(out)


class Seg:
    # Un pedazo de texto: original (o) y normalizado (n), misma longitud.
    def __init__(self, o, n=None):
        self.o = o
        self.n = norm(o) if n is None else n

    def sl(self, a, b=None):
        return Seg(self.o[a:b], self.n[a:b])


TRIM = " \t\r\n,.;:¡!¿?«»\"“”'‘’"


def match_close(n, a):
    d = 0
    for i in range(a, len(n)):
        if n[i] == '(':
            d += 1
        elif n[i] == ')':
            d -= 1
            if d == 0:
                return i
    return -1


def trim_seg(seg):
    a, b = 0, len(seg.n)
    while True:
        while a < b and seg.n[a] in TRIM:
            a += 1
        while b > a and seg.n[b - 1] in TRIM:
            b -= 1
        if a < b and seg.n[a] == '(' and seg.n[b - 1] == ')' and match_close(seg.n, a) == b - 1:
            a += 1
            b -= 1
            continue
        break
    return seg.sl(a, b)


def depth_at(n):
    d, k = [], 0
    for ch in n:
        if ch == ')':
            k = max(0, k - 1)
        d.append(k)
        if ch == '(':
            k += 1
    return d


WB, WE = r'(?<![a-zñ0-9])', r'(?![a-zñ0-9])'


def W(alts):
    # Expresión regular de palabras completas: W('y|e') busca 'y' o 'e' como palabra.
    return re.compile(WB + '(?:' + alts + ')' + WE)


def all_top(seg, rx):
    # Coincidencias que NO están dentro de paréntesis.
    d = depth_at(seg.n)
    return [(m.start(), m.end()) for m in rx.finditer(seg.n) if m.end() > m.start() and d[m.start()] == 0]


def first_top(seg, rx):
    r = all_top(seg, rx)
    return r[0] if r else None


def split_top(seg, rx):
    ms = all_top(seg, rx)
    parts, p = [], 0
    for a, b in ms:
        parts.append(seg.sl(p, a))
        p = b
    parts.append(seg.sl(p))
    parts = [x for x in (trim_seg(x) for x in parts) if x.n]
    return parts, len(ms)


# 2. Fórmulas
#    ('atom', id) | ('not', A) | ('and'|'or'|'imp'|'iff', A, B)
def At(i): return ('atom', i)
def N(a): return ('not', a)
def Bin(t, a, b): return (t, a, b)


OPS = {'and': '∧', 'or': '∨', 'imp': '→', 'iff': '↔'}


def fstr(f, L, top=True):
    # Fórmula a texto con paréntesis solo donde hacen falta.
    if f[0] == 'atom':
        return L[f[1]]
    if f[0] == 'not':
        return '¬' + fstr(f[1], L, False)
    s = fstr(f[1], L, False) + ' ' + OPS[f[0]] + ' ' + fstr(f[2], L, False)
    return s if top else '(' + s + ')'


def ops_used(f, acc=None):
    acc = set() if acc is None else acc
    acc.add(f[0])
    for x in f[1:]:
        if isinstance(x, tuple):
            ops_used(x, acc)
    return acc


# 3. Átomos (p, q, r, ...)
LETTERS = ['p', 'q', 'r', 's', 't', 'u', 'w', 'x', 'y', 'z']
SUB = '₀₁₂₃₄₅₆₇₈₉'


def letter_for(i):
    if i < len(LETTERS):
        return LETTERS[i]
    k = i // len(LETTERS)
    return LETTERS[i % len(LETTERS)] + ''.join(SUB[int(d)] for d in str(k))


@dataclass
class Atom:
    id: int
    letter: str
    meaning: str
    key: str
    neg: str = ''   # cómo se escribió la negación en el texto («el LED no está prendido»)


class Ctx:
    def __init__(self):
        self.map = {}
        self.list = []


def clean_text(o):
    o = re.sub(r'\s+', ' ', o).strip()
    o = re.sub(r'^[\s,.;:«»"“”\']+|[\s,.;:«»"“”\']+$', '', o).strip()
    if re.match(r'^[A-ZÁÉÍÓÚÑ][a-záéíóúüñ]', o):
        o = o[0].lower() + o[1:]
    return o


def remember_neg(ctx, f, text):
    # Si f es un átomo, guarda la forma negada tal como la escribió el usuario.
    if f[0] == 'atom' and not ctx.list[f[1]].neg:
        ctx.list[f[1]].neg = clean_text(text)


def atom_of(ctx, o):
    clean = re.sub(r'\s+', ' ', o).strip()
    clean = re.sub(r'^[\s,.;:«»"“”\']+|[\s,.;:«»"“”\']+$', '', clean).strip()
    clean = re.sub(r'^que\s+', '', clean, flags=re.I)
    key = re.sub(r'\s+', ' ', re.sub(r'[^a-zñ0-9 ]', '', norm(clean))).strip()
    if not key:
        raise ValueError('Hay una proposición vacía cerca de un conectivo.')
    a = ctx.map.get(key)
    if a is None:
        m = clean
        if re.match(r'^[A-ZÁÉÍÓÚÑ][a-záéíóúüñ]', m):
            m = m[0].lower() + m[1:]
        a = Atom(len(ctx.list), letter_for(len(ctx.list)), m, key)
        ctx.map[key] = a
        ctx.list.append(a)
    return At(a.id)


# 4. Parser de español
#    Precedencia (de menor a mayor): ↔, →, ∨, ∧, ¬
NEG_PREFIX = re.compile(r'^(no es cierto que|no es verdad que|es falso que|no ocurre que|no sucede que|no se cumple que)(?![a-zñ0-9])')
COND_PREFIX = re.compile(r'^(si|cuando|siempre que|en caso de que)(?![a-zñ0-9])')


def parse(seg, ctx):
    seg = trim_seg(seg)
    if not seg.n:
        raise ValueError('Falta una proposición.')
    n = seg.n

    # «no es cierto que …» niega todo lo que sigue
    m = NEG_PREFIX.match(n)
    if m:
        return N(parse(seg.sl(m.end()), ctx))

    # ↔  «si y solo si»
    i = first_top(seg, W('si y solo si|sii'))
    if i:
        if i[0] == 0:  # «si y solo si P, Q»
            rest = seg.sl(i[1])
            c = first_top(rest, W('entonces')) or first_top(rest, re.compile(','))
            if not c:
                raise ValueError('Después de «si y solo si …» falta una coma.')
            return Bin('iff', parse(rest.sl(0, c[0]), ctx), parse(rest.sl(c[1]), ctx))
        return Bin('iff', parse(seg.sl(0, i[0]), ctx), parse(seg.sl(i[1]), ctx))

    # →  «si P, entonces Q» / «si P, Q» / «cuando P, Q»
    m = COND_PREFIX.match(n)
    if m:
        rest = seg.sl(m.end())
        e = first_top(rest, W('entonces')) or first_top(rest, re.compile(','))
        if not e:
            raise ValueError('Después de «si …» escribe «entonces» o una coma.')
        return Bin('imp', parse(rest.sl(0, e[0]), ctx), parse(rest.sl(e[1]), ctx))

    # →  «P entonces Q», «P implica Q», «P solo si Q», «Q si P»
    i = first_top(seg, W('entonces|implica que|implica'))
    if i:
        return Bin('imp', parse(seg.sl(0, i[0]), ctx), parse(seg.sl(i[1]), ctx))
    i = first_top(seg, W('solo si'))
    if i:
        return Bin('imp', parse(seg.sl(0, i[0]), ctx), parse(seg.sl(i[1]), ctx))
    i = first_top(seg, W('si'))
    if i and i[0] > 0:  # «Q si P» = P → Q
        return Bin('imp', parse(seg.sl(i[1]), ctx), parse(seg.sl(0, i[0]), ctx))

    # ∨  «o», «u», «o bien»
    s = seg
    if re.match(r'^(o|u)\s', n) and first_top(seg.sl(2), W('o|u')):
        s = seg.sl(2)  # «o P o Q»
    parts, cnt = split_top(s, W('o bien|o|u'))
    if cnt:
        if len(parts) < 2:
            raise ValueError('A la «o» le falta una de sus dos partes.')
        f = parse(parts[0], ctx)
        for p in parts[1:]:
            f = Bin('or', f, parse(p, ctx))
        return f

    # «ni P ni Q» / «no P ni Q»  ->  ¬P ∧ ¬Q
    if re.match(r'^(ni|no)\s', n) and first_top(seg.sl(3), W('ni')):
        parts, _ = split_top(seg.sl(2), W('ni'))
        subs = [parse(p, ctx) for p in parts]
        for sub, p in zip(subs, parts):
            remember_neg(ctx, sub, 'no ' + p.o)
        f = N(subs[0])
        for sub in subs[1:]:
            f = Bin('and', f, N(sub))
        return f

    # ∧  «y», «e», «pero», «aunque», «además», coma
    parts, cnt = split_top(seg, re.compile(',|' + WB + '(?:y|e|pero|aunque|ademas|sin embargo)' + WE))
    if cnt:
        if len(parts) < 2:
            raise ValueError('A la «y» le falta una de sus dos partes.')
        f = parse(parts[0], ctx)
        for p in parts[1:]:
            f = Bin('and', f, parse(p, ctx))
        return f

    # ¬  «no P»  y  «el LED no está prendido» -> ¬(el LED está prendido)
    m = re.match(r'^(no|tampoco)\s+', n)
    if m:
        sub = parse(seg.sl(m.end()), ctx)
        remember_neg(ctx, sub, seg.o)
        return N(sub)
    i = first_top(seg, W('no'))
    if i and i[0] > 0:
        sub = atom_of(ctx, seg.o[:i[0]] + ' ' + seg.o[i[1]:])
        remember_neg(ctx, sub, seg.o)
        return N(sub)
    return atom_of(ctx, seg.o)


def split_rules(text):
    # Separa por renglones, puntos, punto y coma, o «comillas».
    out = []
    for line in re.split(r'\n+', text):
        line = line.strip()
        if not line:
            continue
        line = re.sub(r'^(?:[-*•]|\d+[.)]|R\d+\s*[:.)])\s*', '', line, flags=re.I)
        q = re.findall(r'[«“"]([^»”"]+)[»”"]', line)
        if q:
            out += [x.strip() for x in q]
            continue
        for s in re.split(r'(?<=[.;])\s+|;', line):
            s = s.strip()
            if re.sub(r'[.;\s]', '', s):
                out.append(s)
    return out


# 5. Texto corrido (sin puntos, comas ni comillas)
#    Usa «si»/«entonces» y las frases que se repiten para separar reglas.
CONNW = {'que', 'si', 'entonces', 'y', 'e', 'o', 'u', 'ni', 'pero', 'aunque', 'ademas', 'solo', 'implica', 'cuando', 'sii'}
STOPW = {'a', 'de', 'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'en', 'al', 'del', 'que', 'se',
         'me', 'te', 'lo', 'le', 'mi', 'su', 'es', 'con', 'por', 'para', 'ya'}


def toks(o):
    # Palabras con su posición en el texto: [(palabra, inicio, fin), ...]
    return [(m.group(), m.start(), m.end()) for m in re.finditer(r'[a-zñ0-9]+', norm(o))]


def split_by_si(o):
    # Corta antes de cada «si» que empieza una regla nueva.
    t = toks(o)
    if len(t) < 2:
        return [o]

    def is_cand(k):
        return (t[k][0] == 'si' and k > 0 and t[k - 1][0] not in ('solo', 'sii', 'que')
                and not (k + 2 < len(t) and t[k + 1][0] == 'y' and t[k + 2][0] == 'solo'))

    cands = [k for k in range(1, len(t)) if is_cand(k)]
    cuts, c = [], 0
    for ci, k in enumerate(cands):
        nxt = cands[ci + 1] if ci + 1 < len(cands) else len(t)
        starts_si = t[c][0] in ('si', 'cuando')
        entonces_ahead = any(x[0] == 'entonces' for x in t[k:nxt])
        if k - c >= 2 and (starts_si or entonces_ahead):
            cuts.append(t[k][1])
            c = k
    out, p = [], 0
    for x in cuts:
        out.append(o[p:x])
        p = x
    out.append(o[p:])
    return [x.strip() for x in out if re.search(r'[a-zñ0-9]', norm(x))]


def repeated_phrases(seqs):
    # Frases que aparecen 2 o más veces (candidatas a átomo). Se quedan las más largas.
    cnt = {}
    borde = set()  # palabras sueltas que alguna vez terminan una frase
    for ws in seqs:
        for i in range(len(ws)):
            if i + 1 == len(ws) or ws[i + 1] in CONNW:
                borde.add(ws[i])
            for n in range(1, 9):
                if i + n > len(ws):
                    break
                ph = ws[i:i + n]
                if ph[-1] in CONNW or ph[-1] == 'no':
                    break
                if ph[-1] in STOPW and ph[-1] != 'es':
                    continue
                k = ' '.join(ph)
                cnt[k] = cnt.get(k, 0) + 1
    rep = {k: c for k, c in cnt.items() if c >= 2}
    # se quita una frase si está dentro de otra más larga que se repite igual o más veces
    tapadas = set()
    for k, c in rep.items():
        ws = k.split()
        for i in range(len(ws)):
            for j in range(i + 1, len(ws) + 1):
                sub = ' '.join(ws[i:j])
                if sub != k and rep.get(sub, 0) <= c:
                    tapadas.add(sub)
    keep = set()
    for k in rep:
        if ' ' not in k and k not in borde:  # «hace» en «hace frío» / «hace calor» no es un átomo
            continue
        if k not in tapadas:
            keep.add(k)
    return keep


@dataclass
class Rule:
    raw: str
    f: tuple = None
    label: str = ''
    str: str = ''
    error: str = ''
    inferred: bool = False


def analyze(text):
    # a) oraciones por puntuación y luego por «si»
    chunks, corrido = [], []
    oraciones = split_rules(text)
    for raw in oraciones:
        partes = split_by_si(raw)
        chunks += partes
        # «corrido» = el renglón traía varias reglas pegadas, o todo el texto es un solo renglón
        corrido += [len(partes) > 1 or len(oraciones) == 1] * len(partes)

    # b) vocabulario conocido: frases repetidas + átomos de las otras reglas
    seqs = [[w for w, _, _ in toks(c)] for c in chunks]
    REP = repeated_phrases([[w for w in ws if w != 'no'] for ws in seqs]) if any(corrido) else set()  # «no está prendido» cuenta como «está prendido»
    atoms_by = []
    for c in chunks:
        cx = Ctx()
        try:
            parse(Seg(c), cx)
        except ValueError:
            pass
        atoms_by.append({a.key for a in cx.list})
    # cuántas reglas usan cada átomo (para saber rápido si una frase aparece en otra regla)
    veces = {}
    for s_ in atoms_by:
        for k in s_:
            veces[k] = veces.get(k, 0) + 1

    def known(k, ci):
        # una frase es conocida si aparece como átomo en otra regla;
        # en texto corrido también cuentan las frases que se repiten
        if not k:
            return False
        if veces.get(k, 0) - (1 if k in atoms_by[ci] else 0) > 0:
            return True
        return corrido[ci] and k in REP

    def core(ws):
        return ' '.join(w for w in ws if w != 'no')

    def last_seg(ws):
        j = 0
        for i in range(len(ws) - 1, -1, -1):
            if ws[i] == 'no' or ws[i] in CONNW:
                j = i + 1
                break
        return ' '.join(ws[j:])

    def all_segs_known(ws, ci):
        segs, cur = [], []
        for w in ws:
            if w in CONNW:
                segs.append(cur)
                cur = []
            else:
                cur.append(w)
        segs.append(cur)
        return all(sg and known(core(sg), ci) for sg in segs)

    def segmentable(ws, ci):
        # Divide ws en piezas «[no] átomo conocido». Devuelve [(a,b), ...] o None.
        memo = {}

        def go(i):
            if i == len(ws):
                return []
            if i in memo:
                return memo[i]
            r = None
            for j in range(len(ws), i, -1):
                pc = ws[i:j]
                if any(w in CONNW for w in pc) or pc.count('no') > 1 or pc[-1] == 'no':
                    continue
                if known(core(pc), ci):
                    rest = go(j)
                    if rest is not None:
                        r = [(i, j)] + rest
                        break
            memo[i] = r
            return r
        return go(0)

    final = []
    for ci, raw in enumerate(chunks):
        T = toks(raw)
        Wd = [w for w, _, _ in T]
        cons_start, insert_at = 0, None
        if Wd and Wd[0] in ('si', 'cuando'):
            ei = Wd.index('entonces') if 'entonces' in Wd else -1
            comma = raw.find(',')
            if ei > 0:
                cons_start = ei + 1
            elif comma > 0 and any(x[1] > comma for x in T):
                cons_start = next((k for k, x in enumerate(T) if x[1] > comma), len(T))
            else:  # falta «entonces»: buscar dónde termina la condición
                best, bs = -1, 0
                for b in range(2, len(Wd)):
                    Lw, Rw = Wd[1:b], Wd[b:]
                    if Lw[-1] in CONNW or Lw[-1] == 'no' or Rw[0] in CONNW:
                        continue
                    sc = 2 if all_segs_known(Lw, ci) else 0
                    rc = Rw[1:] if Rw[0] == 'no' else Rw
                    for j in range(len(rc), 0, -1):
                        if known(' '.join(rc[:j]), ci):
                            sc += 1
                            break
                    if sc > bs:
                        bs, best = sc, b
                if bs < 3 and 'no' in Wd[2:]:
                    best, bs = Wd.index('no', 2), 2
                if best > 0 and bs >= 1:
                    insert_at, cons_start = T[best][1], best

        # c) hechos pegados al final («… no voy a trabajar es de día»)
        run_start = cons_start
        for i in range(len(Wd) - 1, cons_start - 1, -1):
            if Wd[i] in CONNW:
                run_start = i + 1
                break
        cut, pieces = -1, None
        run = Wd[run_start:]
        if len(run) > 1 and not known(core(run), ci):
            best_sc = -1
            for i in range(run_start + 1, len(Wd)):
                ls = last_seg(Wd[run_start:i])
                if not ls:
                    continue
                sg = segmentable(Wd[i:], ci)
                if not sg:
                    continue
                # si lo de la izquierda no es un átomo conocido, no se corta antes de un artículo:
                # «salen los duendes» es una sola frase, no «salen» + «los duendes»
                if not known(ls, ci) and any(Wd[i + a2] in STOPW and Wd[i + a2] != 'es' for a2, _ in sg):
                    continue
                min_len = min(len([w for w in Wd[i + a:i + b] if w != 'no']) for a, b in sg)
                sc = (100 if known(ls, ci) else 0) + 5 * len(ls.split()) + 10 * min_len - len(sg)
                if sc > best_sc:
                    best_sc, cut, pieces = sc, i, sg

        end_main = T[cut][1] if cut > 0 else len(raw)
        main_raw = raw[:end_main].strip()
        src = raw[:insert_at] + ' entonces ' + raw[insert_at:end_main] if insert_at is not None else main_raw
        final.append((main_raw, src, insert_at is not None))
        if pieces:
            for a, b in pieces:
                r = raw[T[cut + a][1]:T[cut + b - 1][2]].strip()
                final.append((r, r, False))

    # d) traducir cada regla a fórmula
    ctx, rules, k = Ctx(), [], 0
    for raw, src, inf in final:
        r = Rule(raw=raw, inferred=inf)
        try:
            r.f = parse(Seg(src), ctx)
            k += 1
            r.label = 'R%d' % k
        except ValueError as e:
            r.error = str(e)
        rules.append(r)
    L = [a.letter for a in ctx.list]
    for r in rules:
        if r.f:
            r.str = fstr(r.f, L)
    return ctx.list, rules, L


# 6. Árbol semántico (tableau)
#    α = no bifurca: ∧, ¬∨, ¬→, ¬¬
#    β = bifurca:    ∨, →, ↔, ¬∧, ¬↔
def classify(f):
    t = f[0]
    if t == 'atom':
        return None
    if t == 'and':
        return ('α', '∧', [[f[1], f[2]]])
    if t == 'or':
        return ('β', '∨', [[f[1]], [f[2]]])
    if t == 'imp':
        return ('β', '→', [[N(f[1])], [f[2]]])
    if t == 'iff':
        return ('β', '↔', [[f[1], f[2]], [N(f[1]), N(f[2])]])
    g = f[1]  # t == 'not'
    if g[0] == 'atom':
        return None
    if g[0] == 'not':
        return ('α', '¬¬', [[g[1]]])
    if g[0] == 'and':
        return ('β', '¬∧', [[N(g[1])], [N(g[2])]])
    if g[0] == 'or':
        return ('α', '¬∨', [[N(g[1]), N(g[2])]])
    if g[0] == 'imp':
        return ('α', '¬→', [[g[1], N(g[2])]])
    if g[0] == 'iff':
        return ('β', '¬↔', [[g[1], N(g[2])], [N(g[1]), g[2]]])


def is_lit(f):
    return f[0] == 'atom' or (f[0] == 'not' and f[1][0] == 'atom')


def lit_key(f):
    return str(f[1]) if f[0] == 'atom' else '~' + str(f[1][1])


@dataclass
class Entry:
    f: tuple
    str: str
    label: str = ''
    applied: int = 0   # paso en el que se aplicó (0 = todavía no)


@dataclass
class Node:
    id: int
    parent: 'Node'
    entries: list
    via: dict = None
    step: int = 0
    children: list = field(default_factory=list)
    closed: bool = False
    close_lits: list = None


def run_tableau(rules, L, max_steps=float('inf'), max_nodos=None):
    nodes = []

    def entry(f, label=''):
        return Entry(f, fstr(f, L), label)

    def new_node(parent, entries, via, step):
        n = Node(len(nodes), parent, entries, via, step)
        nodes.append(n)
        return n

    def close_check(node):
        # Cierra la rama si tiene un átomo y su negación.
        seen = {}
        a = node.parent
        while a:
            for e in a.entries:
                if is_lit(e.f):
                    seen[lit_key(e.f)] = e.str
            a = a.parent
        for e in node.entries:
            if is_lit(e.f):
                k = lit_key(e.f)
                c = k[1:] if k[0] == '~' else '~' + k
                if c in seen:
                    node.closed = True
                    node.close_lits = sorted([seen[c], e.str], key=len)
                    return True
                seen[k] = e.str
        return False

    def open_leaves(n):
        if n.closed:
            return []
        if not n.children:
            return [n]
        return [l for c in n.children for l in open_leaves(c)]

    def pre(n):
        out = [n]
        for c in n.children:
            out += pre(c)
        return out

    def find_cand(root):
        for kind in ('α', 'β'):  # primero las que no bifurcan
            for node in pre(root):
                for e in node.entries:
                    if e.applied:
                        continue
                    c = classify(e.f)
                    if c and c[0] == kind and open_leaves(node):
                        return node, e, c
        return None

    root = new_node(None, [entry(r.f, r.label) for r in rules], None, 0)
    close_check(root)
    log, step = [], 0
    while step < max_steps:
        cand = find_cand(root)
        if not cand:
            break
        step += 1
        node, e, (kind, name, br) = cand
        e.applied = step
        leaves = open_leaves(node)
        closed = []
        for leaf in leaves:            # se desarrolla en TODAS las ramas abiertas de abajo
            for comps in br:
                ch = new_node(leaf, [entry(f) for f in comps], {'step': step, 'src': e.label or e.str, 'rule': name}, step)
                leaf.children.append(ch)
                if close_check(ch):
                    closed.append(ch.close_lits)
        log.append({'step': step, 'src': e.label, 'str': e.str, 'rule': name, 'kind': kind,
                    'branches': [', '.join(fstr(f, L) for f in b) for b in br],
                    'n_leaves': len(leaves), 'closed': closed})
        if max_nodos and len(nodes) > max_nodos:   # el árbol ya es demasiado grande para dibujarlo
            break
    excedido = bool(max_nodos) and len(nodes) > max_nodos
    done = not excedido and find_cand(root) is None
    leaves_all = [n for n in nodes if not n.children]
    return {'root': root, 'nodes': nodes, 'log': log, 'step': step, 'done': done, 'excedido': excedido,
            'open': open_leaves(root), 'closed_count': sum(1 for n in leaves_all if n.closed)}


def model_of(leaf, n_atoms):
    # Asignación de una rama abierta: 'V', 'F' o None (cualquier valor).
    v, path = [None] * n_atoms, []
    a = leaf
    while a:
        path.append(a.id)
        for e in a.entries:
            if is_lit(e.f):
                if e.f[0] == 'atom':
                    v[e.f[1]] = 'V'
                else:
                    v[e.f[1][1]] = 'F'
        a = a.parent
    return v, path


# 7. Método rápido para bases grandes
#    Es el mismo árbol semántico, pero sin dibujarlo: se recorre rama por rama (primero en profundidad)
#    y cada rama se cierra en cuanto aparece una contradicción. Así aguanta miles de reglas.
#    Primero cada regla se pasa a cláusulas: listas de letras o letras negadas unidas con ∨.

def a_clausulas(f, positivo=True):
    # regresa una lista de cláusulas (conjunción de disyunciones) equivalente a f (o a ¬f)
    t = f[0]
    if t == 'atom':
        return [[f[1] + 1 if positivo else -(f[1] + 1)]]
    if t == 'not':
        return a_clausulas(f[1], not positivo)
    a, b = f[1], f[2]
    if t == 'imp':
        return a_clausulas(('or', ('not', a), b), positivo)
    if t == 'iff':
        if positivo:
            return a_clausulas(('and', ('imp', a, b), ('imp', b, a)))
        return a_clausulas(('or', ('and', a, ('not', b)), ('and', ('not', a), b)))
    es_y = (t == 'and') == positivo  # De Morgan: ¬(A ∧ B) = ¬A ∨ ¬B
    ca, cb = a_clausulas(a, positivo), a_clausulas(b, positivo)
    if es_y:
        return ca + cb
    return [x + y for x in ca for y in cb]


def limpiar(clausulas):
    # quita letras repetidas y cláusulas que siempre son verdaderas (p ∨ ¬p)
    out = []
    for c in clausulas:
        s = set(c)
        if any(-x in s for x in s):
            continue
        out.append(list(dict.fromkeys(c)))
    return out


def resolver_rapido(rules, n_atoms, max_modelos=50, max_segundos=30, max_nodos_arbol=3000):
    import time
    inicio = time.time()
    clausulas, origen = [], []         # origen: de qué regla salió cada cláusula
    for r in rules:
        for c in limpiar(a_clausulas(r.f)):
            clausulas.append(c)
            origen.append(r.label)
    val = [0] * (n_atoms + 1)          # 1 = V, -1 = F, 0 = sin valor
    pila = []                          # letras asignadas, en orden
    vigilantes = {}                    # letra -> cláusulas que la vigilan
    unitarias = []
    for i, c in enumerate(clausulas):
        if len(c) == 1:
            unitarias.append(c[0])
        else:
            vigilantes.setdefault(c[0], []).append(i)
            vigilantes.setdefault(c[1], []).append(i)

    def valor(l):
        v = val[abs(l)]
        return v if l > 0 else -v

    def asignar(l):
        val[abs(l)] = 1 if l > 0 else -1
        pila.append(l)

    choques = []                       # átomos donde se cerró una rama

    def propagar(desde):
        # aplica todas las consecuencias obligadas; regresa False si la rama se cierra
        i = desde
        while i < len(pila):
            l = pila[i]
            i += 1
            falsa = -l
            lista = vigilantes.get(falsa, [])
            j = 0
            while j < len(lista):
                ci = lista[j]
                c = clausulas[ci]
                if c[0] == falsa:
                    c[0], c[1] = c[1], c[0]
                if valor(c[0]) == 1:
                    j += 1
                    continue
                for k in range(2, len(c)):
                    if valor(c[k]) != -1:
                        c[1], c[k] = c[k], c[1]
                        vigilantes.setdefault(c[1], []).append(ci)
                        lista[j] = lista[-1]
                        lista.pop()
                        break
                else:
                    if valor(c[0]) == -1:
                        choques.append(abs(l) - 1)
                        return False
                    if valor(c[0]) == 0:
                        asignar(c[0])
                    j += 1
        return True

    def sin_cumplir():
        # primera cláusula que todavía no se cumple
        for i, c in enumerate(clausulas):
            if not any(valor(x) == 1 for x in c):
                return i
        return None

    # árbol que se va recorriendo: cada nodo guarda las letras que se agregaron en ese tramo de la rama
    arbol = []
    cortado = [False]

    def nuevo_nodo(padre, decision, regla):
        if padre is None and arbol:
            return None
        if len(arbol) >= max_nodos_arbol or (padre is not None and padre < 0):
            cortado[0] = True
            return -1
        arbol.append({'padre': padre, 'decision': decision, 'regla': regla, 'lits': [],
                      'cerrada': None, 'modelo': None})
        return len(arbol) - 1

    def anotar(nodo, desde, ok):
        if nodo is not None and nodo >= 0:
            arbol[nodo]['lits'] = pila[desde:]
            if not ok:
                arbol[nodo]['cerrada'] = choques[-1] if choques else None

    modelos, cerradas, decisiones = [], 0, []
    completo = True
    ok = True
    actual = nuevo_nodo(None, None, '')
    for u in unitarias:
        if valor(u) == -1:
            choques.append(abs(u) - 1)
            ok = False
            break
        if valor(u) == 0:
            asignar(u)
    ok = ok and propagar(0)
    anotar(actual, 0, ok)

    while True:
        if time.time() - inicio > max_segundos:
            completo = False
            break
        if ok:
            ci = sin_cumplir()
            if ci is None:
                if actual is not None and actual >= 0:
                    arbol[actual]['modelo'] = len(modelos)
                modelos.append([None if v == 0 else ('V' if v == 1 else 'F') for v in val[1:]])
                if len(modelos) >= max_modelos:
                    completo = False
                    break
                ok = False          # se busca la siguiente rama
            else:
                # bifurcación: la primera letra libre de esa regla, primero verdadera y luego falsa
                l = next(x for x in clausulas[ci] if valor(x) == 0)
                pos = len(pila)
                decisiones.append((pos, l, actual, origen[ci]))
                actual = nuevo_nodo(actual, l, origen[ci])
                asignar(l)
                ok = propagar(pos)
                anotar(actual, pos, ok)
                if not ok:
                    cerradas += 1
                continue
        # regresar a la última bifurcación y tomar la otra rama
        while decisiones:
            pos, l, padre, regla = decisiones.pop()
            while len(pila) > pos:
                val[abs(pila.pop())] = 0
            if l is not None:
                decisiones.append((pos, None, padre, regla))   # la otra rama ya no tiene alternativa
                actual = nuevo_nodo(padre, -l, regla)
                asignar(-l)
                ok = propagar(pos)
                anotar(actual, pos, ok)
                if not ok:
                    cerradas += 1
                break
        else:
            break
    if not modelos and cerradas == 0 and not ok:
        cerradas = 1
    return {'modelos': modelos, 'cerradas': cerradas, 'completo': completo,
            'clausulas': len(clausulas), 'choques': list(dict.fromkeys(choques))[:10],
            'segundos': round(time.time() - inicio, 2), 'arbol': arbol, 'arbol_cortado': cortado[0]}


# 8. Árbol completo (método clásico) para bases grandes
#    Mismas reglas α/β que run_tableau, pero recorriendo rama por rama para aguantar muchos nodos.
#    Orden: primero α, luego las β que cierran una rama de inmediato, y al final las demás β.

def arbol_completo(rules, L, max_nodos=20000, max_segundos=25):
    import time
    inicio = time.time()

    def lit(f):
        return (f[1], True) if f[0] == 'atom' else (f[1][1], False)

    def choca(f, asig):
        if not is_lit(f):
            return False
        a, v = lit(f)
        return a in asig and asig[a] != v

    nodos = [{'padre': None, 'texto': f'raíz: R1 … R{len(rules)} verdaderas', 'fin': None}]
    completo = True
    abiertas = cerradas = 0
    # cada rama pendiente: (nodo donde cuelga, asignación, fórmulas pendientes, β guardadas)
    pila = [(0, {}, [(r.f, r.label) for r in rules], [])]
    while pila:
        if len(nodos) >= max_nodos or time.time() - inicio > max_segundos:
            completo = False
            break
        nodo, asig, pend, betas = pila.pop()
        asig, pend, betas = dict(asig), list(pend), list(betas)
        fin = None
        while fin is None:
            # letras y fórmulas α (no bifurcan)
            while pend and fin is None:
                f, et = pend.pop()
                if is_lit(f):
                    a, v = lit(f)
                    if a in asig and asig[a] != v:
                        fin = 'cerrada'
                        nodos[nodo]['fin'] = f'✕ cerrada: {L[a]} y ¬{L[a]}'
                    asig[a] = v
                else:
                    c = classify(f)
                    if c[0] == 'α':
                        comps = c[2][0]
                        nodos.append({'padre': nodo, 'texto': f'{et or fstr(f, L)} ({c[1]}): ' +
                                      ', '.join(fstr(g, L) for g in comps), 'fin': None})
                        nodo = len(nodos) - 1
                        pend.extend((g, '') for g in comps)
                    else:
                        betas.append((f, et))
            if fin is not None:
                break
            if not betas:
                fin = 'abierta'
                break
            # β: primero una que cierre una rama enseguida
            elegido = None
            for i in range(len(betas) - 1, max(-1, len(betas) - 301), -1):   # se revisan las últimas 300
                f, et = betas[i]
                br = classify(f)[2]
                for k, comp in enumerate(br):
                    if any(choca(g, asig) for g in comp):
                        elegido = (i, k)
                        break
                if elegido:
                    break
            i, k = elegido if elegido else (len(betas) - 1, None)
            f, et = betas.pop(i)
            nombre, br = classify(f)[1], classify(f)[2]
            ramas = []
            for comp in br:
                nodos.append({'padre': nodo, 'texto': f'{et or fstr(f, L)} ({nombre}): ' +
                              ', '.join(fstr(g, L) for g in comp), 'fin': None})
                ramas.append(len(nodos) - 1)
            if k is not None:
                # esa rama se cierra de inmediato
                g = next(g for g in br[k] if choca(g, asig))
                a = lit(g)[0]
                nodos[ramas[k]]['fin'] = f'✕ cerrada: {L[a]} y ¬{L[a]}'
                cerradas += 1
                otra = 1 - k
                nodo = ramas[otra]
                pend.extend((g, '') for g in br[otra])
            else:
                pila.append((ramas[1], dict(asig), list(pend) + [(g, '') for g in br[1]], list(betas)))
                nodo = ramas[0]
                pend.extend((g, '') for g in br[0])
            if len(nodos) >= max_nodos:
                break
        if fin == 'cerrada':
            cerradas += 1
        elif fin == 'abierta':
            abiertas += 1
            nodos[nodo]['fin'] = f'○ abierta (modelo {abiertas})'
    if pila:
        completo = False
    return {'nodos': nodos, 'completo': completo, 'abiertas': abiertas, 'cerradas': cerradas,
            'pendientes': len(pila), 'segundos': round(time.time() - inicio, 2)}


def arbol_en_texto(nodos):
    # escribe el árbol como carpetas: ├─ └─ │
    hijos = {}
    for i, n in enumerate(nodos):
        if n['padre'] is not None:
            hijos.setdefault(n['padre'], []).append(i)
    lineas = []
    pila = [(0, '', '', True)]
    while pila:
        i, pref, rama, ultimo = pila.pop()
        n = nodos[i]
        fin = f'   {n["fin"]}' if n['fin'] else ''
        lineas.append((pref + rama + n['texto'] + fin, n['fin'] or ''))
        hs = hijos.get(i, [])
        # los hijos se escriben debajo del texto de este nodo
        nuevo = pref + {'├─ ': '│  ', '└─ ': '   '}.get(rama, '')
        if len(hs) == 1:
            # una sola continuación: va en el mismo nivel, sin rama nueva
            pila.append((hs[0], nuevo, '', True))
        else:
            for j, h in reversed(list(enumerate(hs))):
                pila.append((h, nuevo, '└─ ' if j == len(hs) - 1 else '├─ ', j == len(hs) - 1))
    return lineas


def y_lista(items):
    # ['a','b','c'] -> 'a, b y c'
    if not items:
        return ''
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' y ' + items[-1]


DETS = {'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'mi', 'tu', 'su', 'mis', 'tus', 'sus', 'este', 'esta', 'ese', 'esa'}


def negar(atom):
    # Forma negada de un átomo, en español natural.
    # Usa la que escribió el usuario; si no hay, mete «no» antes del verbo:
    # «el motor está encendido» -> «el motor no está encendido».
    if atom.neg:
        return atom.neg
    w = atom.meaning.split()
    if len(w) >= 3 and norm(w[0]) in DETS:
        k = 2
        while k + 1 < len(w) and norm(w[k]) in ('de', 'del'):  # «la luz del cuarto está…»
            k += 2
        if k < len(w):
            return ' '.join(w[:k] + ['no'] + w[k:])
    return 'no ' + atom.meaning


def frase_modelo(v, atoms):
    # Convierte una asignación en una oración: «Se cumple cuando es de día, voy a trabajar y no llueve.»
    partes = []
    for j, x in enumerate(v):
        if x == 'V':
            partes.append(atoms[j].meaning)
        elif x == 'F':
            partes.append(negar(atoms[j]))
    libres = [atoms[j].meaning for j, x in enumerate(v) if x is None]
    txt = 'Se cumple cuando ' + y_lista(partes) + '.' if partes else 'Se cumple sin importar los valores.'
    if libres:
        txt += ' Da igual si ' + y_lista(libres) + ' o no.'
    return txt


if __name__ == '__main__':
    texto = 'Si es de día, entonces voy a trabajar.\nSi llueve, entonces no voy a trabajar.\nEs de día.'
    atoms, rules, L = analyze(texto)
    for a in atoms:
        print(a.letter, '=', a.meaning)
    for r in rules:
        print(r.label, r.raw, '=>', r.str or r.error)
    T = run_tableau([r for r in rules if r.f], L)
    print('Ramas abiertas:', len(T['open']), ' cerradas:', T['closed_count'])
    for leaf in T['open']:
        v, _ = model_of(leaf, len(atoms))
        print('Modelo:', ', '.join('%s = %s' % (L[j], x or 'V/F') for j, x in enumerate(v)))
        print('       ', frase_modelo(v, atoms))
