"""Motor isométrico (proyección 2:1) con voxels: modelos 3D pixel-art que giran, con sombreado dinámico.
Una capa {tipo:'iso'} lleva 'preset' (modelo listo) o 'partes' (formas que Claude compone)."""
import json, math, random
import numpy as np
from PIL import ImageDraw
from .escena import mezcla, claro, osc

def _col(c, pal):
    if isinstance(c, (tuple, list)) and len(c) >= 3: return tuple(int(v) for v in c[:3])
    if isinstance(c, str):
        if c in pal: return pal[c]
        h = c.lstrip("#")
        if len(h) == 6:
            try: return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            except ValueError: pass
    return pal["metal"]

def _map(eje, u, v, w):
    return {"z": (u, v, w), "x": (w, u, v), "y": (v, w, u)}.get(eje, (u, v, w))

# ----------------------------------------------------------------- voxelización
def v_caja(p, pal):
    x, y, z = p["pos"]; a, b, c = p["tam"]; col = _col(p.get("color", "metal"), pal); col2 = _col(p["color2"], pal) if p.get("color2") else None
    return {(int(x + i), int(y + j), int(z + k)): (col2 if col2 and (i + j) % 2 else col)
            for i in range(int(a)) for j in range(int(b)) for k in range(int(c))}

def v_cilindro(p, pal):
    cx, cy, cz = p["centro"]; r = float(p["radio"]); h = int(p["alto"]); ri = float(p.get("hueco", 0)); eje = p.get("eje", "z"); col = _col(p.get("color", "metal"), pal)
    R = int(math.ceil(r)); out = {}
    for u in range(-R, R + 1):
        for v in range(-R, R + 1):
            d2 = u * u + v * v
            if r * r + .25 >= d2 >= ri * ri and (ri == 0 or d2 > 0 or False):
                for w in range(h):
                    X, Y, Z = _map(eje, u, v, w)
                    if p.get("corte") and (Y > 0.5 if p["corte"] == "y+" else X > 0.5): continue
                    out[(int(round(cx + X)), int(round(cy + Y)), int(round(cz + Z)))] = col
    return out

def v_esfera(p, pal):
    cx, cy, cz = p["centro"]; r = float(p["radio"]); col = _col(p.get("color", "metal"), pal); R = int(math.ceil(r)); out = {}
    for i in range(-R, R + 1):
        for j in range(-R, R + 1):
            for k in range(-R, R + 1):
                if i * i + j * j + k * k <= r * r + .5: out[(int(round(cx + i)), int(round(cy + j)), int(round(cz + k)))] = col
    return out

def v_cono(p, pal):
    cx, cy, cz = p["centro"]; r = float(p["radio"]); h = int(p["alto"]); col = _col(p.get("color", "metal"), pal); eje = p.get("eje", "z"); out = {}
    R = int(math.ceil(r))
    for w in range(h):
        rr = r * (1 - w / h)
        for u in range(-R, R + 1):
            for v in range(-R, R + 1):
                if u * u + v * v <= rr * rr + .25:
                    X, Y, Z = _map(eje, u, v, w); out[(int(round(cx + X)), int(round(cy + Y)), int(round(cz + Z)))] = col
    return out

def v_engranaje(p, pal, ang):
    cx, cy, cz = p["centro"]; R = float(p["radio"]); z = int(p.get("dientes", 10)); g = int(p.get("grosor", 2)); eje = p.get("eje", "z"); col = _col(p.get("color", "metal"), pal)
    n = int(R) + 3; out = {}
    for u in range(-n, n + 1):
        for v in range(-n, n + 1):
            r = math.hypot(u, v); a = math.atan2(v, u)
            ok = (.68 * R <= r <= R - .5) or (R - .5 < r <= R + 1.5 and math.cos(z * (a - ang)) > .15) or r <= max(1.2, R * .22) \
                 or (R * .22 < r < .68 * R and math.cos(4 * (a - ang)) > .8)
            if ok:
                for w in range(g):
                    X, Y, Z = _map(eje, u, v, w); out[(int(round(cx + X)), int(round(cy + Y)), int(round(cz + Z)))] = col
    return out

def v_helice(p, pal, ang):
    cx, cy, cz = p["centro"]; R = float(p["radio"]); n = int(p.get("aspas", 3)); anc = float(p.get("ancho", 3)); g = int(p.get("grosor", 1)); eje = p.get("eje", "z"); col = _col(p.get("color", "metal"), pal)
    N = int(R) + 2; out = {}
    for u in range(-N, N + 1):
        for v in range(-N, N + 1):
            ok = math.hypot(u, v) <= 2
            for k in range(n):
                a = ang + 2 * math.pi * k / n; t_ = u * math.cos(a) + v * math.sin(a); s_ = -u * math.sin(a) + v * math.cos(a)
                if 1.5 <= t_ <= R and abs(s_) <= anc * (1 - .55 * t_ / R) / 2: ok = True
            if ok:
                for w in range(g):
                    X, Y, Z = _map(eje, u, v, w); out[(int(round(cx + X)), int(round(cy + Y)), int(round(cz + Z)))] = col
    return out

def v_barra(p, pal):
    (x0, y0, z0), (x1, y1, z1) = p["de"], p["a"]; gr = max(1, int(round(float(p.get("grosor", 1.5))))); col = _col(p.get("color", "metal"), pal); out = {}
    n = int(max(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0)) * 2) + 1
    for i in range(n + 1):
        f = i / n; x, y, z = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, z0 + (z1 - z0) * f
        for a in range(gr):
            for b in range(gr):
                for c in range(gr): out[(int(round(x)) + a, int(round(y)) + b, int(round(z)) + c)] = col
    return out

def _rot(pt, ax, ay):
    x, y, z = pt
    y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
    x, z = x * math.cos(ay) + z * math.sin(ay), -x * math.sin(ay) + z * math.cos(ay)
    return x, y, z

def v_anillo(p, pal):
    cx, cy, cz = p["centro"]; r = float(p["radio"]); col = _col(p.get("color", "metal"), pal); ax, ay = (list(p.get("rot") or [0, 0]) + [0, 0])[:2]; out = {}
    for i in range(int(r * 8)):
        a = 2 * math.pi * i / int(r * 8); X, Y, Z = _rot((r * math.cos(a), r * math.sin(a), 0), ax, ay)
        out[(int(round(cx + X)), int(round(cy + Y)), int(round(cz + Z)))] = col
    return out

FORMAS = {"anillo": v_anillo, "caja": v_caja, "cilindro": v_cilindro, "esfera": v_esfera, "cono": v_cono}
_cache = {}

def _n(v, d, a, b):
    try: return max(a, min(b, float(v)))
    except (TypeError, ValueError): return d

def _limitar(p):
    """Recorta tamaños de las formas que genera Claude para evitar modelos gigantes."""
    p = dict(p); f = p.get("forma")
    for k in ("pos", "centro", "de", "a"):
        if k in p:
            try: p[k] = [_n(v, 0, -60, 60) for v in list(p[k])[:3]] + [0] * (3 - len(list(p[k])[:3]))
            except TypeError: p[k] = [0, 0, 0]
    if f == "caja":
        try: p["tam"] = [int(_n(v, 1, 1, 40)) for v in list(p.get("tam", [1, 1, 1]))[:3]]
        except TypeError: p["tam"] = [1, 1, 1]
        while len(p["tam"]) < 3: p["tam"].append(1)
    for k, (a, b) in {"radio": (.5, 20), "alto": (1, 60), "hueco": (0, 19), "grosor": (1, 12), "dientes": (3, 30), "aspas": (1, 8), "ancho": (1, 12)}.items():
        if k in p: p[k] = _n(p[k], a, a, b)
    return p

def voxeles_parte(p, pal, t):
    """Devuelve {(x,y,z): color} de la parte (con caché para las estáticas)."""
    p = _limitar(p); f = p.get("forma")
    ang = (p.get("ang", 0) + t * p.get("vel", 0)) if f in ("engranaje", "helice") else 0
    if f in ("engranaje", "helice"): ang = ang % (2 * math.pi)
    clave = json.dumps({k: v for k, v in p.items() if k not in ("off", "id", "anim")}, sort_keys=True, default=str) + (f"|{round(ang, 3)}" if f in ("engranaje", "helice") else "")
    if clave in _cache: return _cache[clave]
    if f in FORMAS: vox = FORMAS[f](p, pal)
    elif f == "engranaje": vox = v_engranaje(p, pal, ang)
    elif f == "helice": vox = v_helice(p, pal, ang)
    elif f == "barra": vox = v_barra(p, pal)
    else: vox = {}
    if len(_cache) > 400: _cache.clear()
    _cache[clave] = vox
    return vox

VEC = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1)]   # caras: +x, -x, +y, -y, +z

def expuestos(vox):
    out = []
    for (x, y, z), c in vox.items():
        m = 0
        for i, (dx, dy, dz) in enumerate(VEC):
            if (x + dx, y + dy, z + dz) not in vox: m |= 1 << i
        if m: out.append((x, y, z, c, m))
    return out

# ----------------------------------------------------------------- partículas
def particulas(p, t, pal):
    n = int(p.get("n", 30)); out = []; x, y, z = p["pos"]; tipo = p.get("tipo", "fuego"); vel = float(p.get("vel", 1.0)); alto = float(p.get("alto", 10)); dd = p.get("dir", [0, 0, 1])
    for i in range(n):
        r = random.Random(i * 7919 + 13)
        age = (t * vel * .6 + i / n) % 1
        sp = float(p.get("dispersion", 2.0)) * age
        px = x + dd[0] * alto * age + r.uniform(-1, 1) * sp; py = y + dd[1] * alto * age + r.uniform(-1, 1) * sp; pz = z + dd[2] * alto * age + r.uniform(-.5, .5)
        if tipo == "fuego": col = (255, 245, 170) if age < .2 else pal["a1"] if age < .45 else pal["caliente"] if age < .7 else (90, 80, 80)
        elif tipo == "humo": col = mezcla((200, 200, 205), (70, 70, 80), age)
        elif tipo == "chispas": col = pal["a1"] if r.random() < .6 else (255, 255, 255)
        else: col = pal["a2"]
        out.append((px, py, pz, col, max(.35, (1 - age) * float(p.get("tam", 1.6)))))
    return out

# ----------------------------------------------------------------- render
def _modelo(c, t, pal):
    if c.get("partes"): return c["partes"]
    return PRESETS.get(c.get("preset"), PRESETS["tren_engranajes"])(t, c.get("params") or {})

_enc = {}

def _voxeles_modelo(c, t, pal):
    vox, anclas = [], {}
    for q in [q for q in _modelo(c, t, pal) if isinstance(q, dict)]:
        if q.get("forma") == "emisor": continue
        try:
            v = voxeles_parte(q, pal, t)
            ox, oy, oz = (list(q.get("off") or [0, 0, 0]) + [0, 0, 0])[:3]
            k = ("exp", len(v), q.get("forma"), json.dumps(sorted(v.items())[:2], default=str), str(q.get("centro") or q.get("pos") or q.get("de")))
            lst = _cache.get(k)
            if lst is None:
                lst = expuestos(v); _cache[k] = lst
            vox += [(x + ox, y + oy, z + oz, col, m) for x, y, z, col, m in lst]
            if q.get("id") and v:
                xs = [k_[0] for k_ in v]; ys = [k_[1] for k_ in v]; zs = [k_[2] for k_ in v]
                anclas[q["id"]] = ((min(xs) + max(xs)) / 2 + ox, (min(ys) + max(ys)) / 2 + oy, (min(zs) + max(zs)) / 2 + oz + 1)
        except Exception as ex:
            print("[iso parte]", q.get("forma"), ex)
    return vox, anclas

def _encuadre(c, pal, vw, vh):
    """Escala y centro fijos del modelo (muestreando varios instantes) para que no 'respire' al girar o moverse."""
    clave = json.dumps(c, sort_keys=True, default=str) + f"|{vw}x{vh}"
    if clave in _enc: return _enc[clave]
    pts = []
    for ts in [i * 1.3 for i in range(17)]:
        v, _ = _voxeles_modelo(c, ts, pal)
        pts += [(x, y, z) for x, y, z, _, _ in v]
    if not pts: _enc[clave] = None; return None
    A = np.array(pts, dtype=float)
    cx, cy = (A[:, 0].min() + A[:, 0].max()) / 2, (A[:, 1].min() + A[:, 1].max()) / 2
    zmin, zmax = A[:, 2].min(), A[:, 2].max()
    R = float(np.max(np.hypot(A[:, 0] - cx, A[:, 1] - cy))) + 1
    Zr = zmax - zmin + 1
    tam = (list(c.get("caja") or [.5, .5, .8]) + [.5, .5, .8])[2]
    s = 1.25 * min(tam * vw / (4 * 1.414 * R + 6), tam * vh / (2 * 1.414 * R + 2 * Zr + 6))
    s = float(c["escala_vox"]) if isinstance(c.get("escala_vox"), (int, float)) else max(1.0, s)
    _enc[clave] = (cx, cy, (zmin + zmax) / 2, R, s)
    if len(_enc) > 50: _enc.pop(next(iter(_enc)))
    return _enc[clave]

def render_iso(capa, c, t, pal, vw, vh):
    """t = tiempo local de la capa. Devuelve {id_parte: (x,y)} en coordenadas del visor (para rótulos)."""
    d = ImageDraw.Draw(capa)
    enc = _encuadre(c, pal, vw, vh)
    if not enc: return {}
    cx, cy, zmid, R, s = enc
    vox, anclas3d = _voxeles_modelo(c, t, pal)
    free = []
    for q in [q for q in _modelo(c, t, pal) if isinstance(q, dict) and q.get("forma") == "emisor"]:
        free += particulas(q, t, pal)
    if c.get("suelo", SUELO_DEF.get(c.get("preset"), True)):
        n = int(min(46, R * 1.5 + 6))
        g = v_caja({"pos": [int(cx) - n // 2, int(cy) - n // 2, int(zmid - 0) - 0 - 0], "tam": [1, 1, 1]}, pal) if False else None
        zb = int(min(v[2] for v in vox)) if vox else 0
        g = v_caja({"pos": [int(cx) - n // 2, int(cy) - n // 2, zb - 2], "tam": [n, n, 2], "color": mezcla(pal["panel"], _col(c.get("suelo_color", SUELO_COLOR.get(c.get("preset"), "oscuro")), pal), .6), "color2": mezcla(pal["panel"], _col(c.get("suelo_color", SUELO_COLOR.get(c.get("preset"), "oscuro")), pal), .35)}, pal)
        vox = vox + [(x, y, z, col, m) for x, y, z, col, m in expuestos(g)]
    ang = math.radians(float(c.get("ang0", 35)) + float(c.get("giro", 12)) * t + float(c.get("balanceo", 0)) * math.sin(t * .8))
    co, si = math.cos(ang), math.sin(ang)
    cxp, cyp = (list(c.get("caja") or [.5, .5, .8]) + [.5, .5, .8])[:2]
    # el punto (cx,cy,zmid) del modelo cae en el centro de la caja
    ox, oy = cxp * vw, cyp * vh + zmid * 2 * s

    def P(x, y, z):
        a = (x - cx) * co - (y - cy) * si; b = (x - cx) * si + (y - cy) * co
        return ((a - b) * 2 * s + ox, (a + b) * s - z * 2 * s + oy)
    vis = [(co + si) > 0, -(co + si) > 0, (co - si) > 0, (si - co) > 0]
    Lz = np.array([-.35, .85]); Lz = Lz / np.linalg.norm(Lz)
    normales = [(co, si), (-co, -si), (-si, co), (si, -co)]
    sombra = [0.5 + 0.55 * max(0.0, nx * Lz[0] + ny * Lz[1]) for nx, ny in normales] + [1.12]
    orden = sorted(range(len(vox)), key=lambda i: ((vox[i][0] - cx) * co - (vox[i][1] - cy) * si) + ((vox[i][0] - cx) * si + (vox[i][1] - cy) * co) + vox[i][2])
    cc = {}
    def tono(col, k):
        kk = (col, k)
        if kk not in cc:
            f = sombra[k]; cc[kk] = tuple(max(0, min(255, int(ch * f))) for ch in col) if f <= 1 else claro(col, (f - 1) * 1.6)
        return cc[kk]
    for i in orden:
        x, y, z, col, m = vox[i]
        if m & 16:
            q = [P(x, y, z + 1), P(x + 1, y, z + 1), P(x + 1, y + 1, z + 1), P(x, y + 1, z + 1)]; cl = tono(col, 4); d.polygon(q, fill=cl, outline=cl)
        for k in range(4):
            if vis[k] and m & (1 << k):
                if k == 0: q = [P(x + 1, y, z), P(x + 1, y + 1, z), P(x + 1, y + 1, z + 1), P(x + 1, y, z + 1)]
                elif k == 1: q = [P(x, y, z), P(x, y + 1, z), P(x, y + 1, z + 1), P(x, y, z + 1)]
                elif k == 2: q = [P(x, y + 1, z), P(x + 1, y + 1, z), P(x + 1, y + 1, z + 1), P(x, y + 1, z + 1)]
                else: q = [P(x, y, z), P(x + 1, y, z), P(x + 1, y, z + 1), P(x, y, z + 1)]
                cl = tono(col, k); d.polygon(q, fill=cl, outline=cl)
    for px, py, pz, col, sz in sorted(free, key=lambda f: f[0] + f[1] + f[2]):
        h = sz / 2
        d.polygon([P(px - h, py - h, pz + h), P(px + h, py - h, pz + h), P(px + h, py + h, pz + h), P(px - h, py + h, pz + h)], fill=col, outline=col)
        d.polygon([P(px - h, py + h, pz + h), P(px + h, py + h, pz + h), P(px + h, py + h, pz - h), P(px - h, py + h, pz - h)], fill=osc(col, .3), outline=osc(col, .3))
    return {k: P(*v) for k, v in anclas3d.items()}

# ----------------------------------------------------------------- presets
def _mesh(R1, z1, th1, R2, z2, phi):
    return phi + math.pi + math.pi / z2 - (th1 - phi) * z1 / z2

def p_tren_engranajes(t, p):
    w = t * float(p.get("velocidad", 1.0)) * .9
    A, B = (-9, 0), (5, 0); C = (5 + 10 * math.cos(-.9), 10 * math.sin(-.9))
    thA = w; thB = _mesh(8, 12, thA, 5, 8, 0.0); thC = _mesh(5, 8, thB, 4, 6, -.9)
    return [{"forma": "caja", "pos": [-20, -12, 0], "tam": [38, 26, 2], "color": "oscuro"},
        {"forma": "cilindro", "centro": [*A, 2], "radio": 1, "alto": 8, "color": "texto"},
        {"forma": "cilindro", "centro": [*B, 2], "radio": 1, "alto": 8, "color": "texto"},
        {"forma": "cilindro", "centro": [round(C[0]), round(C[1]), 2], "radio": 1, "alto": 8, "color": "texto"},
        {"forma": "engranaje", "id": "A", "centro": [*A, 3], "radio": 8, "dientes": 12, "grosor": 3, "color": "metal", "ang": thA},
        {"forma": "engranaje", "id": "B", "centro": [*B, 3], "radio": 5, "dientes": 8, "grosor": 3, "color": "a2", "ang": thB},
        {"forma": "engranaje", "id": "C", "centro": [round(C[0]), round(C[1]), 3], "radio": 4, "dientes": 6, "grosor": 3, "color": "a1", "ang": thC}]

def p_aerogenerador(t, p):
    w = t * float(p.get("velocidad", 1.0)) * 1.6
    return [{"forma": "cilindro", "centro": [0, 0, 0], "radio": 3, "alto": 8, "color": "texto"},
        {"forma": "cilindro", "centro": [0, 0, 8], "radio": 2, "alto": 14, "color": "texto", "id": "torre"},
        {"forma": "caja", "pos": [-3, -2, 22], "tam": [8, 4, 4], "color": "metal", "id": "gondola"},
        {"forma": "esfera", "centro": [5, 0, 24], "radio": 2, "color": "a1"},
        {"forma": "helice", "centro": [6, 0, 24], "radio": 16, "aspas": 3, "ancho": 5, "grosor": 2, "eje": "x", "color": "texto", "vel": w, "id": "aspas"}]

def p_cinta(t, p):
    v = float(p.get("velocidad", 1.0)) * .12
    partes = [{"forma": "caja", "pos": [-16, -3, 4], "tam": [32, 7, 2], "color": "oscuro", "color2": "metal"},
              {"forma": "caja", "pos": [-16, -3, 0], "tam": [2, 7, 4], "color": "metal"}, {"forma": "caja", "pos": [14, -3, 0], "tam": [2, 7, 4], "color": "metal"},
              {"forma": "cilindro", "centro": [-16, -4, 5], "radio": 2, "alto": 9, "eje": "y", "color": "texto"}, {"forma": "cilindro", "centro": [15, -4, 5], "radio": 2, "alto": 9, "eje": "y", "color": "texto"},
              {"forma": "caja", "pos": [-1, -6, 6], "tam": [2, 2, 11], "color": "frio"}, {"forma": "caja", "pos": [-1, 5, 6], "tam": [2, 2, 11], "color": "frio"},
              {"forma": "caja", "pos": [-1, -6, 15], "tam": [2, 13, 2], "color": "frio", "id": "escaner"}]
    cols = ["a1", "a2", "caliente", "texto", "a1"]
    for i in range(5):
        x = -14 + ((i / 5 + t * v) % 1) * 28
        partes.append({"forma": "caja", "pos": [0, -2, 6], "tam": [4, 4, 4], "color": cols[i], "off": [x, 0, 0], "id": "caja" if i == 0 else None})
    return partes

def p_cohete(t, p):
    lift = min(26.0, max(0.0, t - 1.5) ** 2 * 2.2)
    out = [{"forma": "caja", "pos": [-6, -6, 0], "tam": [12, 12, 2], "color": "oscuro"}, {"forma": "caja", "pos": [-1, -8, 2], "tam": [2, 3, 14], "color": "metal"}]
    off = [0, 0, lift]
    out += [{"forma": "cilindro", "centro": [0, 0, 5], "radio": 3, "alto": 18, "color": "texto", "off": off, "id": "cuerpo"},
            {"forma": "cilindro", "centro": [0, 0, 14], "radio": 3.2, "alto": 3, "color": "caliente", "off": off},
            {"forma": "cono", "centro": [0, 0, 23], "radio": 3, "alto": 7, "color": "caliente", "off": off},
            {"forma": "esfera", "centro": [3, 0, 18], "radio": 1.2, "color": "frio", "off": off}]
    for dx, dy in ((4, 0), (-4, 0), (0, 4), (0, -4)):
        out.append({"forma": "caja", "pos": [dx - 1, dy - 1, 5], "tam": [2, 2, 5], "color": "caliente", "off": off})
    if t > 1.0:
        out.append({"forma": "emisor", "tipo": "fuego", "pos": [0, 0, 5 + lift], "dir": [0, 0, -1], "alto": 12, "n": 50, "vel": 2.2, "dispersion": 3, "tam": 2.2})
        out.append({"forma": "emisor", "tipo": "humo", "pos": [0, 0, 2], "dir": [0, 0, 1], "alto": 7, "n": 36, "vel": .9, "dispersion": 9, "tam": 3.4})
    return out

def p_motor_abierto(t, p):
    w = t * float(p.get("velocidad", 1.0)) * 2.2
    xs = [-15, -5, 5, 15]; offs = [0, math.pi, 3 * math.pi, 2 * math.pi]; zc, r, Lr = 5, 3, 7.5
    out = [{"forma": "caja", "pos": [-21, -6, 0], "tam": [42, 12, 2], "color": "oscuro"},
           {"forma": "cilindro", "centro": [-20, 0, zc], "radio": 1.3, "alto": 40, "eje": "x", "color": "metal", "id": "ciguenal"}]
    for j, x in enumerate(xs):
        phi = (w + offs[j]) % (4 * math.pi); th = phi % (2 * math.pi); fase = int(phi // math.pi)
        py_, pz_ = r * math.sin(th), zc - r * math.cos(th); zp = pz_ + math.sqrt(Lr ** 2 - py_ ** 2)
        out += [{"forma": "cilindro", "centro": [x, 0, 3], "radio": 3.9, "hueco": 3.3, "alto": 15, "corte": "y+", "color": "metal", "id": "cilindro" if j == 0 else None},
                {"forma": "barra", "de": [x, 0, zc], "a": [x, round(py_, 1), round(pz_, 1)], "grosor": 2, "color": "a1"},
                {"forma": "barra", "de": [x, round(py_, 1), round(pz_, 1)], "a": [x, 0, round(zp, 1)], "grosor": 1.4, "color": "texto"},
                {"forma": "cilindro", "centro": [x, 0, 0], "radio": 3.2, "alto": 3, "color": ["texto", "metal", "texto", "metal"][j], "off": [0, 0, round(zp, 1)], "id": "piston" if j == 0 else None}]
        gas = ["frio", "a2", "caliente", "metal"][fase]
        out.append({"forma": "cilindro", "centro": [x, 0, 0], "radio": 2.8, "alto": max(1, int(17 - zp - 3)), "color": gas, "off": [0, 0, round(zp + 3, 1)], "corte": "y+"})
        if fase == 2:
            out.append({"forma": "emisor", "tipo": "fuego", "pos": [x, 0, zp + 4], "dir": [0, 0, 1], "alto": 4, "n": 14, "vel": 3, "dispersion": 2, "tam": 1.6})
    return out

PRESETS = {"tren_engranajes": p_tren_engranajes, "aerogenerador": p_aerogenerador, "cinta": p_cinta, "cohete": p_cohete, "motor_abierto": p_motor_abierto}

def _d(psi, al): return (math.cos(al) * math.cos(psi), math.cos(al) * math.sin(psi), math.sin(al))
def _pt(p0, d, L): return [round(p0[i] + d[i] * L, 1) for i in range(3)]

def p_brazo_robotico(t, p):
    v = float(p.get("velocidad", 1.0)); psi = .9 * math.sin(t * .6 * v); a1 = .9 + .35 * math.sin(t * 1.1 * v); a2 = a1 - 1.2 + .45 * math.sin(t * 1.7 * v)
    S = [0, 0, 10]; E = _pt(S, _d(psi, a1), 13); W = _pt(E, _d(psi, a2), 11)
    abre = 1.2 + 1.0 * (math.sin(t * 2.4 * v) > 0); pe = (-math.sin(psi), math.cos(psi), 0); dg = _d(psi, a2 - .2)
    out = [{"forma": "cilindro", "centro": [0, 0, 0], "radio": 7, "alto": 3, "color": "oscuro"}, {"forma": "cilindro", "centro": [0, 0, 3], "radio": 3.5, "alto": 7, "color": "metal", "id": "base"},
           {"forma": "barra", "de": S, "a": E, "grosor": 3, "color": "a2", "id": "brazo"}, {"forma": "barra", "de": E, "a": W, "grosor": 2.4, "color": "metal"},
           {"forma": "esfera", "centro": S, "radio": 2.6, "color": "a1"}, {"forma": "esfera", "centro": E, "radio": 2.2, "color": "a1"}, {"forma": "esfera", "centro": W, "radio": 1.8, "color": "a1"}]
    for sg in (-1, 1):
        q0 = [W[i] + pe[i] * abre * sg for i in range(3)]; out.append({"forma": "barra", "de": [round(c, 1) for c in q0], "a": _pt(q0, dg, 4), "grosor": 1.2, "color": "texto", "id": "pinza" if sg == 1 else None})
    out.append({"forma": "caja", "pos": [9, 6, 2], "tam": [3, 3, 3], "color": "caliente"}); out.append({"forma": "caja", "pos": [12, 9, 2], "tam": [3, 3, 3], "color": "a1"})
    return out

def p_dron(t, p):
    v = float(p.get("velocidad", 1.0)); z = 6 + 2 * math.sin(t * 1.3); off = [3 * math.sin(t * .7), 3 * math.cos(t * .9), z]
    out = [{"forma": "caja", "pos": [-3, -3, 0], "tam": [6, 6, 2], "color": "oscuro", "off": off, "id": "cuerpo"}, {"forma": "esfera", "centro": [0, 0, 0], "radio": 1.6, "color": "frio", "off": [off[0], off[1], off[2] - 1.5]}]
    for i, (dx, dy) in enumerate(((8, 8), (-8, 8), (8, -8), (-8, -8))):
        out += [{"forma": "barra", "de": [0, 0, 1], "a": [dx * .8, dy * .8, 1], "grosor": 1.2, "color": "metal", "off": off},
                {"forma": "cilindro", "centro": [dx * .8, dy * .8, 1], "radio": 1, "alto": 2, "color": "texto", "off": off},
                {"forma": "helice", "centro": [round(dx * .8), round(dy * .8), 3], "radio": 5, "aspas": 2, "ancho": 2, "grosor": 1, "color": "a1", "vel": 18 * v * (1 if i % 2 else -1), "off": off, "id": "helice" if i == 0 else None}]
    return out

def p_grua(t, p):
    v = float(p.get("velocidad", 1.0)); psi = .5 + .9 * math.sin(t * .35 * v); tr = 11 + 6 * math.sin(t * .6 * v); cab = 8 + 5 * (1 + math.sin(t * .6 * v + 1)) / 2
    top = [0, 0, 28]; tip = [round(math.cos(psi) * 24, 1), round(math.sin(psi) * 24, 1), 28]; cw = [round(-math.cos(psi) * 8, 1), round(-math.sin(psi) * 8, 1), 28]
    tx, ty = round(math.cos(psi) * tr, 1), round(math.sin(psi) * tr, 1)
    return [{"forma": "caja", "pos": [-4, -4, 0], "tam": [8, 8, 2], "color": "oscuro"}, {"forma": "caja", "pos": [-1, -1, 2], "tam": [3, 3, 26], "color": "a1", "id": "torre"},
            {"forma": "caja", "pos": [-2, -2, 28], "tam": [5, 5, 3], "color": "metal"},
            {"forma": "barra", "de": top, "a": tip, "grosor": 2, "color": "a1", "id": "pluma"}, {"forma": "barra", "de": top, "a": cw, "grosor": 2, "color": "a1"},
            {"forma": "caja", "pos": [round(cw[0]) - 2, round(cw[1]) - 2, 25], "tam": [4, 4, 3], "color": "oscuro"},
            {"forma": "caja", "pos": [-1, -1, 0], "tam": [2, 2, 2], "color": "metal", "off": [tx, ty, 26]},
            {"forma": "barra", "de": [tx, ty, 27], "a": [tx, ty, round(27 - cab, 1)], "grosor": 1, "color": "texto"},
            {"forma": "caja", "pos": [-2, -2, 0], "tam": [4, 4, 3], "color": "caliente", "off": [tx, ty, 22 - cab], "id": "carga"}]

def p_noria(t, p):
    w = t * float(p.get("velocidad", 1.0)) * .35; cols = ["caliente", "a1", "a2", "frio", "texto", "caliente", "a1", "a2"]
    out = [{"forma": "barra", "de": [0, 0, 16], "a": [-9, 0, 0], "grosor": 2, "color": "metal"}, {"forma": "barra", "de": [0, 0, 16], "a": [9, 0, 0], "grosor": 2, "color": "metal"}]
    for y in (-2, 2):
        out += [{"forma": "cilindro", "centro": [0, y, 16], "radio": 14.5, "hueco": 13.4, "alto": 1, "eje": "y", "color": "a2"},
                {"forma": "helice", "centro": [0, y, 16], "radio": 14, "aspas": 8, "ancho": 1, "grosor": 1, "eje": "y", "color": "texto", "vel": w}]
    for i in range(8):
        a = w + i * math.pi / 4; cx, cz = 14 * math.cos(a), 16 + 14 * math.sin(a)
        out.append({"forma": "caja", "pos": [-1, -3, 0], "tam": [3, 6, 3], "color": cols[i], "off": [round(cx - 1, 1), 0, round(cz - 4, 1)], "id": "cabina" if i == 0 else None})
    return out

def p_satelite(t, p):
    return [{"forma": "caja", "pos": [-3, -3, 0], "tam": [6, 6, 8], "color": "a1", "id": "cuerpo"}, {"forma": "caja", "pos": [-3, -3, 8], "tam": [6, 6, 1], "color": "metal"},
            {"forma": "barra", "de": [-3, 0, 4], "a": [-9, 0, 4], "grosor": 1, "color": "metal"}, {"forma": "barra", "de": [3, 0, 4], "a": [9, 0, 4], "grosor": 1, "color": "metal"},
            {"forma": "caja", "pos": [-24, -4, 3], "tam": [15, 8, 1], "color": "frio", "color2": "oscuro", "id": "panel"}, {"forma": "caja", "pos": [9, -4, 3], "tam": [15, 8, 1], "color": "frio", "color2": "oscuro"},
            {"forma": "cono", "centro": [0, 0, 9], "radio": 4.5, "alto": 3, "color": "texto", "id": "antena"}, {"forma": "barra", "de": [0, 0, 9], "a": [0, 0, 14], "grosor": 1, "color": "metal"},
            {"forma": "esfera", "centro": [0, 0, 14], "radio": 1.3, "color": "caliente"}] + ([{"forma": "emisor", "tipo": "chispas", "pos": [0, -4, 2], "dir": [0, -1, 0], "alto": 6, "n": 10, "vel": 2}] if int(t * 2) % 4 == 0 else [])

def p_estacion_espacial(t, p):
    out = [{"forma": "cilindro", "centro": [-12, 0, 6], "radio": 3, "alto": 24, "eje": "x", "color": "texto", "id": "modulo"}, {"forma": "cilindro", "centro": [0, -8, 6], "radio": 2.4, "alto": 16, "eje": "y", "color": "metal"},
           {"forma": "esfera", "centro": [0, 0, 6], "radio": 4, "color": "texto"}, {"forma": "cilindro", "centro": [-18, 0, 6], "radio": 1.6, "alto": 4, "eje": "x", "color": "a1"},
           {"forma": "barra", "de": [-9, 0, 6], "a": [9, 0, 6], "grosor": 1, "color": "oscuro"}]
    for xx in (-10, 8):
        for sg in (-1, 1):
            out.append({"forma": "caja", "pos": [xx, 8 * sg - (0 if sg > 0 else 8), 3], "tam": [4, 8, 1], "color": "frio", "color2": "oscuro", "id": "panel_solar" if (xx == -10 and sg == 1) else None})
    out.append({"forma": "caja", "pos": [-1, -9, 5], "tam": [2, 2, 2], "color": "caliente"})
    return out

def p_rover(t, p):
    v = float(p.get("velocidad", 1.0)); x = 10 * math.sin(t * .35 * v); w = t * v * 3.2
    off = [x, 0, 0]; out = [{"forma": "caja", "pos": [-6, -4, 4], "tam": [12, 8, 3], "color": "metal", "off": off, "id": "cuerpo"}, {"forma": "caja", "pos": [-6, -4, 7], "tam": [8, 8, 1], "color": "frio", "off": off, "id": "panel"},
           {"forma": "barra", "de": [4, 0, 7], "a": [4, 0, 12], "grosor": 1, "color": "texto", "off": off}, {"forma": "caja", "pos": [3, -2, 12], "tam": [3, 4, 2], "color": "a1", "off": off, "id": "camara"},
           {"forma": "barra", "de": [6, 3, 5], "a": [10, 5, 4], "grosor": 1, "color": "caliente", "off": off}]
    for xx in (-5, 0, 5):
        for yy in (-5, 4):
            out.append({"forma": "engranaje", "centro": [xx, yy, 3], "radio": 2.6, "dientes": 7, "grosor": 2, "eje": "y", "color": "oscuro", "vel": -w, "off": off})
    return out

def p_atomo(t, p):
    v = float(p.get("velocidad", 1.0)); out = []
    for k, (dx, dy, dz, c) in enumerate(((0, 0, 0, "caliente"), (2, 1, 0, "frio"), (-2, 1, 1, "caliente"), (0, -2, 1, "frio"), (1, 0, -2, "caliente"), (-1, 0, -2, "frio"))):
        out.append({"forma": "esfera", "centro": [dx, dy, 12 + dz], "radio": 1.8, "color": c, "id": "nucleo" if k == 0 else None})
    for k, (r, ax, ay, c, sp) in enumerate(((9, 0, 0, "a2", 1.0), (13, 1.0, .5, "a1", .7), (17, -.9, 1.0, "texto", .5))):
        out.append({"forma": "anillo", "centro": [0, 0, 12], "radio": r, "rot": [ax, ay], "color": "oscuro"})
        for j in range(1 + k):
            a = t * v * sp * 1.6 + j * 2 * math.pi / (1 + k); X, Y, Z = _rot((r * math.cos(a), r * math.sin(a), 0), ax, ay)
            out.append({"forma": "esfera", "centro": [round(X), round(Y), round(12 + Z)], "radio": 1.5, "color": c, "id": "electron" if (k == 0 and j == 0) else None})
    return out

def p_adn(t, p):
    out = []
    for i in range(44):
        a = i * .55
        for sg, c in ((0, "a2"), (math.pi, "caliente")):
            out.append({"forma": "esfera", "centro": [round(5 * math.cos(a + sg)), round(5 * math.sin(a + sg)), i], "radio": 1.3, "color": c, "id": "hebra" if i == 20 and sg == 0 else None})
        if i % 2 == 0:
            out.append({"forma": "barra", "de": [round(5 * math.cos(a)), round(5 * math.sin(a)), i], "a": [round(5 * math.cos(a + math.pi)), round(5 * math.sin(a + math.pi)), i], "grosor": 1, "color": ["a1", "texto", "frio", "verde" if False else "a1"][(i // 2) % 3], "id": "base" if i == 20 else None})
    return out

def p_virus(t, p):
    out = [{"forma": "esfera", "centro": [0, 0, 12], "radio": 7, "color": "caliente", "id": "capside"}, {"forma": "esfera", "centro": [0, 0, 12], "radio": 3, "color": "oscuro"}]
    n = 32
    for i in range(n):
        y = 1 - 2 * (i + .5) / n; r = math.sqrt(1 - y * y); th = i * 2.399963
        d = (r * math.cos(th), r * math.sin(th), y)
        out += [{"forma": "barra", "de": [round(d[0] * 6, 1), round(d[1] * 6, 1), round(12 + d[2] * 6, 1)], "a": [round(d[0] * 10, 1), round(d[1] * 10, 1), round(12 + d[2] * 10, 1)], "grosor": 1, "color": "texto"},
                {"forma": "esfera", "centro": [round(d[0] * 11), round(d[1] * 11), round(12 + d[2] * 11)], "radio": 1.4, "color": "a1", "id": "espiga" if i == 0 else None}]
    return out

def p_volcan(t, p):
    out = [{"forma": "cono", "centro": [0, 0, 0], "radio": 17, "alto": 16, "color": "oscuro", "id": "cono"}, {"forma": "cilindro", "centro": [0, 0, 14], "radio": 3.6, "alto": 2, "color": "caliente", "id": "crater"}]
    for i in range(3):
        a = i * 2.1 + .4; out.append({"forma": "barra", "de": [round(3 * math.cos(a), 1), round(3 * math.sin(a), 1), 14], "a": [round(13 * math.cos(a), 1), round(13 * math.sin(a), 1), 1], "grosor": 1.6, "color": "caliente"})
    out += [{"forma": "emisor", "tipo": "fuego", "pos": [0, 0, 16], "dir": [0, 0, 1], "alto": 16, "n": 60, "vel": 1.6, "dispersion": 7, "tam": 2.2},
            {"forma": "emisor", "tipo": "humo", "pos": [0, 0, 20], "dir": [.3, 0, 1], "alto": 20, "n": 40, "vel": .6, "dispersion": 8, "tam": 3.6}]
    return out

def p_molecula_agua(t, p):
    v = float(p.get("velocidad", 1.0)); vib = .5 * math.sin(t * 4 * v); a = math.radians(52 + 4 * math.sin(t * 3 * v)); b = 7 + vib
    H1 = [round(b * math.sin(a), 1), 0, round(12 - b * math.cos(a), 1)]; H2 = [round(-b * math.sin(a), 1), 0, round(12 - b * math.cos(a), 1)]
    return [{"forma": "barra", "de": [0, 0, 12], "a": H1, "grosor": 1.4, "color": "metal"}, {"forma": "barra", "de": [0, 0, 12], "a": H2, "grosor": 1.4, "color": "metal"},
            {"forma": "esfera", "centro": [0, 0, 12], "radio": 4.2, "color": "caliente", "id": "oxigeno"}, {"forma": "esfera", "centro": H1, "radio": 2.6, "color": "texto", "id": "hidrogeno"}, {"forma": "esfera", "centro": H2, "radio": 2.6, "color": "texto"}]

PRESETS.update({"brazo_robotico": p_brazo_robotico, "dron": p_dron, "grua": p_grua, "noria": p_noria, "satelite": p_satelite, "estacion_espacial": p_estacion_espacial,
                "rover": p_rover, "atomo": p_atomo, "adn": p_adn, "virus": p_virus, "volcan": p_volcan, "molecula_agua": p_molecula_agua})
SUELO_DEF = {"satelite": False, "estacion_espacial": False, "atomo": False, "adn": False, "virus": False, "molecula_agua": False}
SUELO_COLOR = {"rover": "caliente", "volcan": "oscuro"}
