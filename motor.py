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
        if not line or line.startswith('#') or line.startswith('//'):
            continue  # renglón vacío o comentario
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


# 9. Encadenamiento hacia adelante y hacia atrás
#    Las reglas se convierten a la forma de un sistema experto:  SI premisas ENTONCES conclusiones
#    Una letra se guarda como (átomo, True) y su negación como (átomo, False).

def literal(f):
    # (átomo, valor) si f es una letra o una letra negada; si no, None
    if f[0] == 'atom':
        return (f[1], True)
    if f[0] == 'not':
        g = f[1]
        if g[0] == 'atom':
            return (g[1], False)
        if g[0] == 'not':
            return literal(g[1])
    return None


def lista_y(f):
    # letras unidas con ∧ (también ¬(A ∨ B) = ¬A ∧ ¬B); si no se puede, None
    l = literal(f)
    if l:
        return [l]
    if f[0] == 'and':
        a, b = lista_y(f[1]), lista_y(f[2])
        return a + b if a is not None and b is not None else None
    if f[0] == 'not' and f[1][0] == 'or':
        return lista_y(('and', ('not', f[1][1]), ('not', f[1][2])))
    if f[0] == 'not' and f[1][0] == 'not':
        return lista_y(f[1][1])
    return None


def lista_o(f):
    # letras unidas con ∨; si no se puede, None
    l = literal(f)
    if l:
        return [l]
    if f[0] == 'or':
        a, b = lista_o(f[1]), lista_o(f[2])
        return a + b if a is not None and b is not None else None
    return None


def base_de_reglas(rules):
    # separa hechos y reglas SI-ENTONCES; lo que no tiene esa forma se reporta como ignorado
    hechos, reglas, ignoradas = [], [], []

    def agregar(et, prem, tipo, concl):
        reglas.append({'regla': et, 'premisas': prem, 'tipo': tipo, 'conclusiones': concl})

    for r in rules:
        f = r.f
        h = lista_y(f)
        if h is not None:
            for l in h:
                hechos.append((l, r.label))
            continue
        if f[0] == 'imp':
            concl = lista_y(f[2])
            prem_y, prem_o = lista_y(f[1]), lista_o(f[1])
            if concl is not None and prem_y is not None:
                agregar(r.label, prem_y, 'y', concl)
                continue
            if concl is not None and prem_o is not None:
                agregar(r.label, prem_o, 'o', concl)
                continue
        if f[0] == 'iff':
            a, b = lista_y(f[1]), lista_y(f[2])
            if a is not None and b is not None:
                agregar(r.label, a, 'y', b)
                agregar(r.label, b, 'y', a)
                continue
        ignoradas.append(r.label)
    return hechos, reglas, ignoradas


def texto_lit(l, L):
    return ('' if l[1] else '¬') + L[l[0]]


def encadenar_adelante(rules, L, meta=None):
    # parte de los hechos y dispara cada regla cuyas premisas ya se cumplen
    hechos, reglas, ignoradas = base_de_reglas(rules)
    conocido = {}            # átomo -> (valor, de dónde salió, ciclo)
    pasos, choques = [], []
    agenda = []
    for l, et in hechos:
        a, v = l
        if a in conocido and conocido[a][0] != v:
            choques.append(f'{et}: {texto_lit(l, L)} contradice a {conocido[a][1]}')
            continue
        if a not in conocido:
            conocido[a] = (v, et, 0)
            agenda.append(l)
    # índice: letra -> reglas donde aparece como premisa
    por_premisa = {}
    for i, rg in enumerate(reglas):
        for p in rg['premisas']:
            por_premisa.setdefault(p, []).append(i)
    faltan = [len(rg['premisas']) for rg in reglas]
    disparada = [False] * len(reglas)
    k = 0
    while k < len(agenda):
        l = agenda[k]
        k += 1
        for i in por_premisa.get(l, []):
            if disparada[i]:
                continue
            rg = reglas[i]
            faltan[i] -= 1
            if rg['tipo'] == 'y' and faltan[i] > 0:
                continue
            disparada[i] = True
            usadas = [p for p in rg['premisas'] if conocido.get(p[0], (None,))[0] == p[1]]
            ciclo = 1 + max(conocido[p[0]][2] for p in usadas)
            nuevas = []
            for c in rg['conclusiones']:
                a, v = c
                if a in conocido:
                    if conocido[a][0] != v:
                        choques.append(f'{rg["regla"]} concluye {texto_lit(c, L)} pero ya se sabía '
                                       f'{texto_lit((a, conocido[a][0]), L)} ({conocido[a][1]})')
                    continue
                conocido[a] = (v, rg['regla'], ciclo)
                agenda.append(c)
                nuevas.append(c)
            pasos.append({'regla': rg['regla'], 'premisas': usadas, 'tipo': rg['tipo'],
                          'conclusiones': rg['conclusiones'], 'nuevas': nuevas, 'ciclo': ciclo})
    alcanzada = None
    if meta is not None:
        alcanzada = meta[0] in conocido and conocido[meta[0]][0] == meta[1]
    return {'hechos': len(hechos), 'reglas': len(reglas), 'ignoradas': ignoradas, 'pasos': pasos,
            'conocido': conocido, 'choques': choques, 'meta': meta, 'alcanzada': alcanzada}


def encadenar_atras(rules, L, meta, max_nodos=5000):
    # parte de la meta y busca reglas que la concluyan; luego intenta demostrar sus premisas
    hechos, reglas, ignoradas = base_de_reglas(rules)
    hecho = {}
    for l, et in hechos:
        hecho.setdefault(l, et)
    por_conclusion = {}
    for i, rg in enumerate(reglas):
        for c in rg['conclusiones']:
            por_conclusion.setdefault(c, []).append(i)
    resultado = {}           # letra -> True/False ya decidido
    nodos = []

    def nodo(padre, l, texto, estado):
        nodos.append({'padre': padre, 'lit': l, 'texto': texto, 'estado': estado})
        return len(nodos) - 1

    def probar(l, padre, en_camino):
        # regresa True si la letra l se puede demostrar
        n = nodo(padre, l, '', '')
        if len(nodos) > max_nodos:
            nodos[n].update(texto='límite de nodos alcanzado', estado='falla')
            return False
        if l in hecho:
            nodos[n].update(texto=f'es un hecho ({hecho[l]})', estado='ok')
            return True
        if (l[0], not l[1]) in hecho:
            nodos[n].update(texto=f'no: contradice el hecho {hecho[(l[0], not l[1])]}', estado='falla')
            return False
        if l in resultado:
            nodos[n].update(texto='ya demostrada arriba' if resultado[l] else 'ya se vio que no se puede demostrar',
                            estado='ok' if resultado[l] else 'falla')
            return resultado[l]
        if l in en_camino:
            nodos[n].update(texto='ciclo: se necesita a sí misma', estado='falla')
            return False
        candidatas = por_conclusion.get(l, [])
        if not candidatas:
            nodos[n].update(texto='no es un hecho y ninguna regla la concluye', estado='falla')
            resultado[l] = False
            return False
        for i in candidatas:
            rg = reglas[i]
            un = ' ∧ ' if rg['tipo'] == 'y' else ' ∨ '
            sub = nodo(n, None, f'por {rg["regla"]}: SI {un.join(texto_lit(p, L) for p in rg["premisas"])} '
                                f'ENTONCES {", ".join(texto_lit(c, L) for c in rg["conclusiones"])}', '')
            if rg['tipo'] == 'y':
                ok = all(probar(p, sub, en_camino | {l}) for p in rg['premisas'])
            else:
                ok = any(probar(p, sub, en_camino | {l}) for p in rg['premisas'])
            nodos[sub]['estado'] = 'ok' if ok else 'falla'
            if ok:
                nodos[n].update(texto=f'demostrada con {rg["regla"]}', estado='ok')
                resultado[l] = True
                return True
        nodos[n].update(texto='ninguna regla que la concluye se pudo cumplir', estado='falla')
        resultado[l] = False
        return False

    import sys
    sys.setrecursionlimit(max(20000, sys.getrecursionlimit()))
    ok = probar(meta, None, frozenset())
    return {'demostrada': ok, 'nodos': nodos, 'ignoradas': ignoradas, 'hechos': len(hechos), 'reglas': len(reglas)}


def atras_en_texto(nodos, L, atoms):
    # escribe la demostración como carpetas: ├─ └─ │
    hijos = {}
    for i, n in enumerate(nodos):
        if n['padre'] is not None:
            hijos.setdefault(n['padre'], []).append(i)
    lineas = []
    pila = [(0, '', '')]
    while pila:
        i, pref, rama = pila.pop()
        n = nodos[i]
        marca = '✓' if n['estado'] == 'ok' else '✕'
        if n['lit'] is not None:
            a, v = n['lit']
            frase = atoms[a].meaning if v else negar(atoms[a])
            txt = f'¿{texto_lit(n["lit"], L)}? «{frase}»  {marca} {n["texto"]}'
        else:
            txt = f'{n["texto"]}  {marca}'
        lineas.append((pref + rama + txt, n['estado']))
        hs = hijos.get(i, [])
        nuevo = pref + {'├─ ': '│  ', '└─ ': '   '}.get(rama, '')
        for j, h in reversed(list(enumerate(hs))):
            pila.append((h, nuevo, '└─ ' if j == len(hs) - 1 else '├─ '))
    return lineas


# 10. Hipótesis (diagnósticos a evaluar)
#     Se leen de los comentarios con la forma  # h1: frase  y se evalúan contra la base.

def leer_hipotesis(text):
    hips = []
    for line in text.splitlines():
        m = re.match(r'^\s*(?:#|//)\s*(h\d+)\s*[:=-]\s*(.+?)\s*$', line, flags=re.I)
        if m:
            hips.append((m.group(1).lower(), m.group(2)))
    return hips


def consultar(atoms, rules, L, frase):
    # evalúa cualquier frase contra la base: ¿se cumple siempre, a veces o nunca?
    valid = [r for r in rules if r.f]
    cx = Ctx()
    cx.map = {a.key: a for a in atoms}
    cx.list = list(atoms)
    try:
        f = parse(Seg(frase), cx)
    except ValueError as e:
        return {'frase': frase, 'error': str(e)}
    letras = L + [a.letter for a in cx.list[len(atoms):]]
    n = len(cx.list)

    class Extra:
        pass
    si, no = Extra(), Extra()
    si.f, si.label = f, 'consulta'
    no.f, no.label = ('not', f), '¬consulta'
    posible = bool(resolver_rapido(valid + [si], n, max_modelos=1)['modelos'])
    contraria = bool(resolver_rapido(valid + [no], n, max_modelos=1)['modelos'])
    if posible and not contraria:
        estado = 'CONFIRMADA'
    elif not posible and contraria:
        estado = 'DESCARTADA'
    elif posible and contraria:
        estado = 'POSIBLE'
    else:
        estado = 'BASE INCONSISTENTE'
    nuevas = [a.meaning for a in cx.list[len(atoms):]]
    return {'frase': frase, 'f': f, 'formula': fstr(f, letras), 'estado': estado, 'nuevas': nuevas}


def evaluar_hipotesis(text, atoms, rules, L):
    # para cada hipótesis del archivo (# h1: frase): ¿se cumple en todos los modelos, en algunos o en ninguno?
    valid = [r for r in rules if r.f]
    out = []
    for nombre, frase in leer_hipotesis(text):
        c = consultar(atoms, rules, L, frase)
        c['nombre'] = nombre
        if 'error' not in c:
            c['nueva'] = bool(c['nuevas'])
            meta = literal(c['f'])
            c['atras'] = None
            if meta is not None and meta[0] < len(atoms):
                c['atras'] = encadenar_atras(valid, L, meta)['demostrada']
            del c['f']
        out.append(c)
    return out


def consecuencias(rules, n_atoms, max_atomos=400):
    # letras que valen lo mismo en todos los modelos (lo que se sabe con certeza)
    valid = [r for r in rules if r.f]
    base = resolver_rapido(valid, n_atoms, max_modelos=1)
    if not base['modelos']:
        return None
    if n_atoms > max_atomos:
        return 'grande'
    modelo = base['modelos'][0]
    seguras = []

    class Extra:
        pass
    for i, v in enumerate(modelo):
        if v is None:
            continue
        e = Extra()
        e.label = 'prueba'
        e.f = ('not', ('atom', i)) if v == 'V' else ('atom', i)
        # si no hay ningún modelo con el valor contrario, ese valor es seguro
        if not resolver_rapido(valid + [e], n_atoms, max_modelos=1)['modelos']:
            seguras.append((i, v))
    return seguras


def parecidas(frase, atoms, n=3):
    # átomos con texto parecido, para avisar cuando algo está escrito distinto
    import difflib
    claves = {norm(a.meaning): a.meaning for a in atoms}
    hallados = difflib.get_close_matches(norm(frase), list(claves), n=n, cutoff=0.5)
    return [claves[h] for h in hallados]


# 11. Motor de explicación
#     Para decir por qué una hipótesis se descarta (o se confirma):
#     1) se busca el grupo más chico de reglas que ya choca con la hipótesis
#     2) se aplican sus consecuencias obligadas una por una, guardando qué regla las produjo
#     3) se cuenta solo el camino que lleva a la contradicción

def _frase_lit(l, atoms):
    a = abs(l) - 1
    return atoms[a].meaning if l > 0 else negar(atoms[a])


def _nucleo(reglas, extra, n_atoms, max_reglas=300):
    # quita reglas una por una mientras la contradicción se mantenga
    if len(reglas) > max_reglas:
        return reglas
    actuales = list(reglas)
    i = 0
    while i < len(actuales):
        prueba = actuales[:i] + actuales[i + 1:]
        if not resolver_rapido(prueba + [extra], n_atoms, max_modelos=1)['modelos']:
            actuales = prueba
        else:
            i += 1
    return actuales


def _cadena(reglas, extra, atoms, L):
    # propaga consecuencias obligadas guardando la razón de cada una
    clausulas = []
    for r in reglas + [extra]:
        for c in limpiar(a_clausulas(r.f)):
            clausulas.append((c, r))
    valor = {}
    razon = {}       # letra -> (regla, letras que la obligaron)
    orden = []
    while True:
        cambio = False
        for c, r in clausulas:
            libres = [x for x in c if abs(x) not in valor]
            ciertas = [x for x in c if abs(x) in valor and valor[abs(x)] == (x > 0)]
            if ciertas:
                continue
            if not libres:
                return orden, razon, (c, r)          # todas falsas: contradicción
            if len(libres) == 1:
                l = libres[0]
                valor[abs(l)] = l > 0
                razon[l] = (r, [-x for x in c if x != l])
                orden.append(l)
                cambio = True
        if not cambio:
            return orden, razon, None


def explicar(atoms, rules, L, f, nombre='la hipótesis'):
    # explica por qué la base junto con la fórmula f no tiene modelos
    valid = [r for r in rules if r.f]

    class Extra:
        pass
    extra = Extra()
    extra.f, extra.label, extra.raw = f, nombre, nombre
    n = len(atoms)
    if resolver_rapido(valid + [extra], n, max_modelos=1)['modelos']:
        return None
    nucleo = _nucleo(valid, extra, n)
    orden, razon, choque = _cadena(nucleo, extra, atoms, L)
    pasos = []
    if choque is None:
        # no basta con consecuencias directas: se explica con las reglas que chocan entre sí
        pasos.append('no hay una sola cadena directa; hay que revisar casos. estas reglas no se pueden cumplir juntas:')
        for r in nucleo:
            pasos.append(f'{r.label}: {r.raw}')
        return {'pasos': pasos, 'reglas': [r.label for r in nucleo]}
    # solo los pasos que llevan a la contradicción
    necesarios, pendientes = set(), [-x for x in choque[0]]
    while pendientes:
        l = pendientes.pop()
        if l in necesarios or l not in razon:
            continue
        necesarios.add(l)
        pendientes.extend(razon[l][1])
    for l in orden:
        if l not in necesarios:
            continue
        r, porque = razon[l]
        frase = _frase_lit(l, atoms)
        if r is extra:
            pasos.append(f'se supone {nombre}: {frase}')
        elif not porque:
            pasos.append(f'{r.label} es un hecho: {frase}')
        else:
            antes = ' y '.join(_frase_lit(x, atoms) for x in porque)
            pasos.append(f'como {antes}, por {r.label} → {frase}')
    c, r = choque
    if r is extra:
        pasos.append(f'✕ pero eso contradice {nombre}: contradicción')
    else:
        pasos.append(f'✕ pero {r.label} dice «{r.raw}», y con lo anterior ya no se puede cumplir: contradicción')
    return {'pasos': pasos, 'reglas': sorted({razon[l][0].label for l in necesarios} | {r.label})}


# 12. Interpretar pistas dichas con otras palabras
#     Convierte lo que se dijo («el saboteador no habla wookiee») a la frase exacta de la base
#     («no habla wookiee el saboteador»). No importa el orden de las palabras y tolera errores
#     pequeños de la transcripción («había» por «habla»).

VACIAS = {'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'del', 'al', 'a', 'en', 'que', 'se', 'lo',
          'le', 'su', 'sus', 'por', 'con', 'para', 'y', 'e', 'o', 'u'}
NEGACIONES = {'no', 'nunca', 'tampoco', 'jamas', 'ni'}


def _palabras(texto):
    return [w for w in re.findall(r'[a-zñ0-9]+', norm(texto)) if w not in VACIAS]


def _parecido(a, b):
    import difflib
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _puntaje(dichas, del_atomo):
    # cuántas palabras del átomo aparecen en lo dicho (con tolerancia a errores)
    if not del_atomo or not dichas:
        return 0.0
    usadas = set()
    aciertos = 0.0
    for w in del_atomo:
        mejor, cual = 0.0, None
        for j, d in enumerate(dichas):
            if j in usadas:
                continue
            p = _parecido(w, d)
            if p > mejor:
                mejor, cual = p, j
        if mejor >= 0.75:
            aciertos += mejor
            usadas.add(cual)
    sobran = len(dichas) - len(usadas)
    return aciertos / (len(del_atomo) + 0.5 * sobran)


def interpretar_pista(texto, atoms, minimo=0.6):
    # regresa una lista de hechos con la frase exacta de la base y qué tan seguro está
    texto = texto.strip()
    if ':' in texto:
        texto = texto.split(':', 1)[1]          # «La comandante informa: …» -> solo la pista
    piezas = [p for p in re.split(r'[.;]|,|\s+y\s+|\s+e\s+', texto) if p.strip()]
    resultados = []
    for pieza in piezas:
        todas = re.findall(r'[a-zñ0-9]+', norm(pieza))
        negada = sum(1 for w in todas if w in NEGACIONES) % 2 == 1
        dichas = [w for w in _palabras(pieza) if w not in NEGACIONES]
        mejor, cual = 0.0, None
        for a in atoms:
            p = _puntaje(dichas, [w for w in _palabras(a.meaning) if w not in NEGACIONES])
            if p > mejor:
                mejor, cual = p, a
        if cual is None or mejor < minimo:
            resultados.append({'dicho': pieza.strip(), 'frase': None, 'confianza': round(mejor, 2)})
            continue
        # el átomo mismo puede traer un «no» adentro
        neg_atomo = any(w in NEGACIONES for w in re.findall(r'[a-zñ0-9]+', norm(cual.meaning)))
        if negada != neg_atomo:
            frase = negar(cual)
        else:
            frase = cual.meaning
        frase = frase[0].upper() + frase[1:]
        resultados.append({'dicho': pieza.strip(), 'frase': frase, 'letra': cual.letter,
                           'negada': negada != neg_atomo, 'confianza': round(mejor, 2)})
    return resultados


def formula_de(atoms, frase):
    # traduce una frase usando los átomos que ya tiene la base
    cx = Ctx()
    cx.map = {a.key: a for a in atoms}
    cx.list = list(atoms)
    f = parse(Seg(frase), cx)
    return f, cx.list[len(atoms):]


def dominio(text):
    # título de la base: primer comentario del archivo
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('#'):
            t = line.lstrip('#').strip()
            if t:
                t = re.sub(r'^base de conocimientos?\s*[·:\-]\s*', '', t, flags=re.I)
                return t
        elif line:
            break
    return ''


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
    if len(w) >= 3 and w[0].lower() in DETS:   # sin quitar acentos: «está» no es «esta»
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


# 13. Preguntas tipo Akinator
#     Hacia adelante: el programa pregunta características; cada respuesta se agrega como hecho
#       y se descartan las hipótesis que ya no pueden ser. Escoge la pregunta que mejor parte
#       a las hipótesis que quedan, hasta que queda una.
#     Hacia atrás: se escoge una hipótesis (la meta) y el programa busca las reglas que la concluyen;
#       de sus premisas pregunta solo lo que no puede deducir, hasta demostrarla o descartarla.
#     Mundo cerrado: algo que concluyen las reglas solo es cierto si alguna de esas reglas se cumple
#       (así funciona un sistema experto de personajes: si no tiene sus características, no es él).

class Hecho:
    # regla extra: respuestas, la hipótesis que se supone, reglas de mundo cerrado
    def __init__(self, f, label, raw=''):
        self.f, self.label, self.raw = f, label, raw or label


def _modelo(reglas, n, extra=()):
    res = resolver_rapido(list(reglas) + list(extra), n, max_modelos=1, max_segundos=5, max_nodos_arbol=0)
    return res['modelos'][0] if res['modelos'] else None


def _sat(reglas, n, extra=()):
    return _modelo(reglas, n, extra) is not None


def es_de_produccion(rules):
    # True si todas las reglas son  SI a y b y ... ENTONCES c  (o hechos sueltos)
    hay_reglas = False
    for r in rules:
        if not r.f:
            continue
        if lista_y(r.f) is not None:
            continue
        if r.f[0] == 'imp' and lista_y(r.f[1]) is not None and literal(r.f[2]) is not None:
            hay_reglas = True
            continue
        return False
    return hay_reglas


def mundo_cerrado(rules, atoms):
    # para cada letra que concluyen las reglas: «solo es cierta si se cumple alguna de esas reglas»
    hechos = set()
    cuerpos = {}
    for r in rules:
        if not r.f:
            continue
        h = lista_y(r.f)
        if h is not None:
            hechos.update(l for l in h if l[1])
            continue
        if r.f[0] == 'imp':
            c = literal(r.f[2])
            if c and c[1]:
                cuerpos.setdefault(c[0], []).append((r.f[1], r.label))
    extra = []
    for a, lista in cuerpos.items():
        if (a, True) in hechos:
            continue
        o = lista[0][0]
        for f, _ in lista[1:]:
            o = ('or', o, f)
        etiquetas = y_lista([et for _, et in lista])
        extra.append(Hecho(('imp', ('atom', a), o), f'{etiquetas} (mundo cerrado)',
                           f'«{atoms[a].meaning}» solo puede ser cierto si se cumple {etiquetas}'))
    return extra


def hipotesis_juego(text, atoms, rules):
    # las hipótesis del archivo (# h1: ...); si no hay, las conclusiones finales de las reglas
    hips = []
    for nombre, frase in leer_hipotesis(text):
        try:
            f, nuevas = formula_de(atoms, frase)
        except ValueError:
            continue
        if not nuevas:
            hips.append({'nombre': nombre, 'frase': frase, 'f': f})
    if hips:
        return hips, 'archivo'
    concluidas, premisas = [], set()
    for r in rules:
        if r.f and r.f[0] == 'imp':
            for l in lista_y(r.f[2]) or []:
                if l[1] and l[0] not in concluidas:
                    concluidas.append(l[0])
            for l in lista_y(r.f[1]) or lista_o(r.f[1]) or []:
                premisas.add(l[0])
    metas = [a for a in concluidas if a not in premisas]
    return [{'nombre': f'h{i + 1}', 'frase': atoms[a].meaning, 'f': ('atom', a)} for i, a in enumerate(metas)], 'reglas'


def atomos_de(f, acc=None):
    acc = set() if acc is None else acc
    if f[0] == 'atom':
        acc.add(f[1])
    else:
        for g in f[1:]:
            atomos_de(g, acc)
    return acc


def preguntables(rules, n, hips, cerrado):
    # letras que se le pueden preguntar al usuario
    en_hip = set()
    for h in hips:
        atomos_de(h['f'], en_hip)
    concluidas = set()
    if cerrado:
        for r in rules:
            if r.f and r.f[0] == 'imp':
                for l in lista_y(r.f[2]) or lista_o(r.f[2]) or []:
                    concluidas.add(l[0])
    return [a for a in range(n) if a not in en_hip and a not in concluidas]


def pregunta_texto(atom):
    t = atom.meaning
    return '¿' + t[0].upper() + t[1:] + '?'


def estado_juego(atoms, rules, hips, respuestas, cerrado):
    # respuestas: lista de (letra, True/False/None)
    n = len(atoms)
    base = [r for r in rules if r.f]
    extra = mundo_cerrado(base, atoms) if cerrado else []
    resp = []
    for i, (a, v) in enumerate(respuestas):
        if v is None:
            continue
        frase = atoms[a].meaning if v else negar(atoms[a])
        resp.append(Hecho(('atom', a) if v else ('not', ('atom', a)), f'P{i + 1}', f'contestaste: {frase}'))
    kb = base + extra + resp
    estados = []
    for h in hips:
        si = _sat(kb, n, [Hecho(h['f'], 'h')])
        no = _sat(kb, n, [Hecho(('not', h['f']), 'no h')])
        estados.append('CONFIRMADA' if si and not no else 'POSIBLE' if si else 'DESCARTADA' if no else 'BASE INCONSISTENTE')
    return {'kb': kb, 'n': n, 'estados': estados, 'extra': extra, 'resp': resp}


def pregunta_adelante(atoms, juego, hips, candidatos, ya, max_segundos=6):
    # escoge la pregunta que mejor parte a las hipótesis que siguen vivas
    import time
    inicio = time.time()
    kb, n = juego['kb'], juego['n']
    vivas = [h for h, e in zip(hips, juego['estados']) if e in ('POSIBLE', 'CONFIRMADA')]
    if len(vivas) <= 1:
        return None
    # con un modelo de cada hipótesis se ve qué letras las distinguen (para probar esas primero)
    modelos = [_modelo(kb, n, [Hecho(h['f'], 'h')]) for h in vivas]
    orden = []
    for a in candidatos:
        if a in ya:
            continue
        vals = [m[a] for m in modelos if m]
        v, f = vals.count('V'), vals.count('F')
        orden.append((-min(v, f), -(v + f), a))
    orden.sort()
    mejor = None
    for _, _, a in orden:
        if mejor and time.time() - inicio > max_segundos:
            break
        si = [h['nombre'] for h in vivas if _sat(kb, n, [Hecho(h['f'], 'h'), Hecho(('atom', a), 'p')])]
        no = [h['nombre'] for h in vivas if _sat(kb, n, [Hecho(h['f'], 'h'), Hecho(('not', ('atom', a)), 'p')])]
        if not si or not no:
            continue                    # la respuesta ya se sabe
        if len(si) == len(vivas) and len(no) == len(vivas):
            continue                    # no distingue nada
        puntos = max(len(si), len(no))
        if mejor is None or puntos < mejor['puntos']:
            mejor = {'letra': a, 'si': si, 'no': no, 'puntos': puntos}
            if puntos <= (len(vivas) + 1) // 2:
                break                   # ya parte a la mitad: no hay una mejor
    return mejor


def pregunta_atras(atoms, rules, L, juego, meta, candidatos, respuestas, max_segundos=6):
    # encadenamiento hacia atrás: de la meta a las reglas que la concluyen y de ahí a sus premisas
    import time
    inicio = time.time()
    sabido = {a: v for a, v in respuestas if v is not None}
    ya = {a for a, _ in respuestas}
    preg = set(candidatos)
    hechos, reglas, _ = base_de_reglas([r for r in rules if r.f])
    hecho = {l for l, _ in hechos}
    por_conclusion = {}
    for i, rg in enumerate(reglas):
        for c in rg['conclusiones']:
            por_conclusion.setdefault(c, []).append(i)

    def falla(l):
        a, v = l
        return (a in sabido and sabido[a] != v) or (a, not v) in hecho

    def buscar(l, camino, en_camino):
        # regresa ('si'|'no'|'?', (letra, camino) si hay que preguntar)
        a, v = l
        if a in sabido:
            return ('si' if sabido[a] == v else 'no'), None
        if l in hecho:
            return 'si', None
        if (a, not v) in hecho or l in en_camino:
            return 'no', None
        for i in por_conclusion.get(l, []):
            rg = reglas[i]
            paso = camino + [(l, rg['regla'])]
            if rg['tipo'] == 'y':
                if any(falla(p) for p in rg['premisas']):
                    continue
                res = 'si'
                for p in rg['premisas']:
                    r, q = buscar(p, paso, en_camino | {l})
                    if r == 'no':
                        res = 'no'
                        break
                    if r == '?':
                        return '?', q
                if res == 'si':
                    return 'si', None
            else:
                for p in rg['premisas']:
                    r, q = buscar(p, paso, en_camino | {l})
                    if r == 'si':
                        return 'si', None
                    if r == '?':
                        return '?', q
        if a in preg and a not in ya:
            return '?', (a, camino)
        return 'no', None

    meta_l = literal(meta['f'])
    if meta_l is not None:
        r, q = buscar(meta_l, [], frozenset())
        if r == '?':
            a, camino = q
            pasos = [f'meta: «{atoms[x[0]].meaning if x[1] else negar(atoms[x[0]])}» → la concluye {et}'
                     if k == 0 else
                     f'submeta: «{atoms[x[0]].meaning if x[1] else negar(atoms[x[0]])}» → la concluye {et}'
                     for k, (x, et) in enumerate(camino)]
            pasos.append(f'falta un dato que ninguna regla da: «{atoms[a].meaning}»')
            return {'letra': a, 'porque': pasos, 'como': 'reglas'}
    # si las reglas ya no dicen qué preguntar: lo que la meta obliga (si no se cumple, se descarta)
    kb, n = juego['kb'], juego['n']
    h = Hecho(meta['f'], 'meta')
    no_h = Hecho(('not', meta['f']), 'no meta')
    for a in candidatos:
        if a in ya or time.time() - inicio > max_segundos:
            continue
        con_si = _sat(kb, n, [h, Hecho(('atom', a), 'p')])
        con_no = _sat(kb, n, [h, Hecho(('not', ('atom', a)), 'p')])
        if con_si != con_no:
            esperado = atoms[a].meaning if con_si else negar(atoms[a])
            return {'letra': a, 'porque': [f'si fuera «{meta["frase"]}», tendría que cumplirse «{esperado}»'],
                    'como': 'prediccion'}
    # o algo que, contestado, la deja confirmada
    for a in candidatos:
        if a in ya or time.time() - inicio > max_segundos:
            continue
        for v in (True, False):
            lit = Hecho(('atom', a) if v else ('not', ('atom', a)), 'p')
            if _sat(kb, n, [lit]) and not _sat(kb, n, [no_h, lit]):
                frase = atoms[a].meaning if v else negar(atoms[a])
                return {'letra': a, 'porque': [f'si «{frase}», ya quedaría demostrado «{meta["frase"]}»'],
                        'como': 'confirmar'}
    return None


def respuesta_si_no(texto):
    # 'si', 'no', 'nose' o None, a partir de lo que se dijo
    t = ' ' + ' '.join(re.findall(r'[a-zñ0-9]+', norm(texto))) + ' '
    if re.search(r' (no se|no lo se|no estoy segur[oa]|quiza|quizas|tal vez|a lo mejor|ni idea) ', t):
        return 'nose'
    if re.search(r' (no|nop|nel|negativo|falso|nunca|para nada|tampoco) ', t):
        return 'no'
    if re.search(r' (si|sip|simon|claro|correcto|afirmativo|cierto|verdad|exacto|obvio|asi es|efectivamente) ', t):
        return 'si'
    return None


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
