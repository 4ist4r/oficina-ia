"""Componentes animados pixel-art de alta definición (diseñados en un espacio ±100 y escalados a cualquier caja)."""
import math, random
from .escena import mezcla, claro, osc, limpiar, texto_centrado, FASES

class Lz:
    """Lienzo escalado: dibuja en coordenadas de diseño (centro 0,0) sobre un ImageDraw."""
    def __init__(s, d, cx, cy, k): s.d, s.cx, s.cy, s.k = d, cx, cy, k
    def P(s, x, y): return (s.cx + x * s.k, s.cy + y * s.k)
    def w(s, v): return max(1, int(round(v * s.k)))
    def rect(s, x0, y0, x1, y1, fill=None, outline=None): s.d.rectangle([*s.P(x0, y0), *s.P(x1, y1)], fill=fill, outline=outline)
    def poly(s, pts, fill=None, outline=None): s.d.polygon([s.P(*q) for q in pts], fill=fill, outline=outline)
    def line(s, pts, fill, w=1): s.d.line([s.P(*q) for q in pts], fill=fill, width=s.w(w))
    def circ(s, x, y, r, fill=None, outline=None):
        cx, cy = s.P(x, y); r *= s.k; s.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill, outline=outline)
    def arc(s, x, y, r, a0, a1, fill, w=1):
        cx, cy = s.P(x, y); r *= s.k; s.d.arc([cx - r, cy - r, cx + r, cy + r], a0, a1, fill=fill, width=s.w(w))
    def dot(s, x, y, fill, tam=1.5):
        px, py = s.P(x, y); t = max(1, int(round(tam * s.k))); s.d.rectangle([px - t / 2, py - t / 2, px + t / 2 - 1, py + t / 2 - 1], fill=fill)
    def txt(s, x, y, texto, col, esc=1):
        px, py = s.P(x, y); texto_centrado(s.d, px, py, limpiar(texto), col, max(1, int(round(esc * s.k))))
    def glow(s, x, y, r, col, fondo):
        for rad in range(int(r), 0, -2):
            s.circ(x, y, rad, fill=mezcla(fondo, col, 1 - rad / r))
    def textura(s, x0, y0, x1, y1, col, paso=6):
        """Puntos en rejilla tipo ladrillo sobre un rectángulo: da aspecto de metal/dithering en vez de color plano."""
        fila = 0; y = y0
        while y <= y1:
            x = x0 + (paso / 2 if fila % 2 else 0)
            while x <= x1:
                s.dot(x, y, col, 1.0)
                x += paso
            y += paso * 0.87; fila += 1
    def textura_circ(s, cx, cy, r, col, paso=6, r_int=0):
        """Igual que textura() pero recortada a un círculo (o anillo si r_int>0)."""
        fila = 0; y = cy - r
        while y <= cy + r:
            x = cx - r + (paso / 2 if fila % 2 else 0)
            while x <= cx + r:
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                if d2 <= r * r and d2 >= r_int * r_int:
                    s.dot(x, y, col, 1.0)
                x += paso
            y += paso * 0.87; fila += 1

def _clip(a, b, f): return a + (b - a) * f

# ---------------------------------------------------------------- engranajes
def engranaje(L, x, y, r, z, ang, col):
    h = r * .17; p = 2 * math.pi / z; rr, rt = r - h * .4, r + h * .6
    pts = []
    for i in range(z):
        a = ang + i * p
        for da, rad in ((-.5, rr), (-.27, rr), (-.16, rt), (.16, rt), (.27, rr)):
            pts.append((x + rad * math.cos(a + da * p), y + rad * math.sin(a + da * p)))
    L.poly([(px + 2.5, py + 2.5) for px, py in pts], fill=osc(col, .82))
    L.poly(pts, fill=col, outline=osc(col, .55))
    L.circ(x, y, r * .72, fill=osc(col, .42), outline=claro(col, .25))
    L.textura_circ(x, y, r * .72, claro(col, .18), paso=5, r_int=r * .15)
    for k in range(5):
        a = ang + k * 2 * math.pi / 5
        L.line([(x + r * .25 * math.cos(a), y + r * .25 * math.sin(a)), (x + r * .72 * math.cos(a), y + r * .72 * math.sin(a))], col, w=r * .13)
    L.circ(x, y, r * .3, fill=claro(col, .2), outline=osc(col, .6))
    for k in range(3):
        a = -ang * 2 + k * 2 * math.pi / 3
        L.circ(x + r * .17 * math.cos(a), y + r * .17 * math.sin(a), r * .035, fill=osc(col, .7))
    L.circ(x, y, r * .06, fill=osc(col, .85))
    L.arc(x, y, r + h * .15, 195, 265, claro(col, .75), w=2)

def c_engranajes(L, t, p, pal):
    th = t * p.get("velocidad", 1.0) * 1.0
    cols = [pal["metal"], pal["a2"], pal["a1"], pal["caliente"]]
    zs = [16, 11, 8, 6]; rs = [46, 32, 23, 17]
    n = max(2, min(4, int(p.get("n", 3))))
    angs = [(-.45, 0), (.42, 0), (-.7, 0)]
    x, y = -42, -20
    posiciones = [(x, y)]; thetas = [th]
    for i in range(1, n):
        phi = [0.45, -0.65, 0.5][i - 1]
        d = rs[i - 1] + rs[i]
        nx, ny = posiciones[-1][0] + d * math.cos(phi), posiciones[-1][1] + d * math.sin(phi)
        t_prev = thetas[-1]
        t_new = phi + math.pi + math.pi / zs[i] - (t_prev - phi) * zs[i - 1] / zs[i]
        posiciones.append((nx, ny)); thetas.append(t_new)
    for i in range(n):
        engranaje(L, posiciones[i][0], posiciones[i][1], rs[i], zs[i], thetas[i], cols[i])

# ---------------------------------------------------------------- pistón
def c_piston(L, t, p, pal):
    th = (t * p.get("velocidad", 1.0) * 2 * math.pi * 0.35) % (4 * math.pi)
    fases = p.get("fases")
    if not (isinstance(fases, (list, tuple)) and len(fases) >= 4):
        fases = FASES.get(p.get("idioma", "es"), FASES["es"])
    fase = int(th // math.pi)
    cols = [pal["frio"], pal["a2"], pal["caliente"], pal["metal"]]
    rnd = random.Random(int(t * 12))
    top, bot, cyc, rr, Ln = -66, 34, 58, 20, 48
    px_, py_ = rr * math.sin(th), cyc - rr * math.cos(th)
    pis = py_ - math.sqrt(Ln * Ln - px_ * px_)
    L.txt(-66, 74, fases[fase], cols[fase] if fase != 3 else pal["texto"], 1.3)
    for sgn, col, on in ((-1, pal["frio"], fase == 0), (1, pal["metal"], fase == 3)):   # colectores
        L.rect(sgn * 12 if sgn > 0 else -100, -92, 100 if sgn > 0 else -12, -80, fill=osc(pal["metal"], .45), outline=pal["metal"])
        L.rect(sgn * 12 if sgn > 0 else -98, -90, 98 if sgn > 0 else -12, -82, fill=osc(pal["fondo"], .5))
        if on:
            for i in range(7):
                s = (i / 7 + t * 1.3) % 1
                x = (-98 + s * 86) if sgn < 0 else (12 + s * 86)
                L.dot(x, -86 + rnd.uniform(-2, 2), claro(col, .5), 3)
    gas = mezcla(cols[fase], pal["fondo"], .55)
    L.rect(-24, top, 24, bot, fill=osc(pal["fondo"], .4))
    L.rect(-23, top + 1, 23, pis - 14, fill=gas)
    if fase == 2:
        L.glow(0, top + 14, 22, pal["caliente"], gas)
    for _ in range(14 if fase != 2 else 40):
        yy = rnd.uniform(top + 3, max(top + 4, pis - 16)); xx = rnd.uniform(-21, 21)
        L.dot(xx, yy, pal["a1"] if fase == 2 and rnd.random() < .6 else claro(cols[fase], .5), 2)
    for sx in (-34, 24):                                                   # bloque, sección rayada
        L.rect(sx, -82, sx + 10, bot + 6, fill=osc(pal["metal"], .35), outline=osc(pal["metal"], .6))
        for yy in range(-80, bot, 7):
            L.line([(sx + 1, yy + 5), (sx + 9, yy)], osc(pal["metal"], .65), 1)
        L.textura(sx + 1, -80, sx + 9, bot + 5, claro(pal["metal"], .15), paso=4)
    L.rect(-36, -84, 36, -66, fill=pal["metal"], outline=osc(pal["metal"], .5))     # culata
    L.textura(-35, -83, 35, -67, claro(pal["metal"], .15), paso=4)
    L.line([(-35, -83), (35, -83)], claro(pal["metal"], .5), 1)
    vi = 6 if fase == 0 else 0; ve = 6 if fase == 3 else 0
    for vx, vo in ((-12, vi), (12, ve)):
        L.line([(vx, -94 + vo), (vx, -66 + vo)], pal["texto"], 2)
        L.rect(vx - 7, -66 + vo, vx + 7, -63 + vo, fill=pal["metal"], outline=osc(pal["metal"], .5))
    L.rect(-3, -100, 3, -84, fill=pal["a1"], outline=osc(pal["a1"], .5))
    if fase == 2 and th - 2 * math.pi < 0.55:
        L.rect(-5, top + 1, 5, top + 12, fill=(255, 255, 255))
    L.rect(-23, pis - 14, 23, pis, fill=claro(pal["metal"], .15), outline=osc(pal["metal"], .5))   # pistón
    for k in (3, 6, 9):
        L.line([(-23, pis - 14 + k), (23, pis - 14 + k)], osc(pal["metal"], .6), 1)
    L.line([(-21, pis - 13), (10, pis - 13)], claro(pal["metal"], .7), 1)
    L.line([(0, pis), (px_, py_)], osc(pal["metal"], .75), 9)                                     # biela
    L.line([(0, pis), (px_, py_)], claro(pal["metal"], .3), 5)
    L.circ(0, cyc, rr + 9, fill=osc(pal["metal"], .5), outline=pal["metal"])                      # cigüeñal
    L.circ(-rr * .7 * math.sin(th), cyc + rr * .7 * math.cos(th), 11, fill=pal["metal"], outline=osc(pal["metal"], .5))
    L.circ(px_, py_, 6, fill=pal["a1"], outline=osc(pal["a1"], .5))
    L.circ(0, cyc, 4, fill=pal["texto"])

# ---------------------------------------------------------------- rotor Wankel
def c_rotor(L, t, p, pal):
    R, e, cx, cy = 62, 14, 0, 8
    phi = t * p.get("velocidad", 1.0) * 2 * math.pi * 0.5
    H = lambda f: (cx + e * math.cos(f) + R * math.cos(f / 3), cy + e * math.sin(f) + R * math.sin(f / 3))
    cols = [pal["frio"], pal["a2"], pal["caliente"], pal["metal"]]
    rnd = random.Random(int(t * 12))
    for k in range(3):
        fa = phi + 2 * math.pi * k
        pts = [H(fa + 2 * math.pi * j / 16) for j in range(17)]
        fase = int(((phi + 2 * math.pi * k) / (1.5 * math.pi)) % 4)
        L.poly(pts, fill=mezcla(cols[fase], pal["fondo"], .45))
        if fase == 2:
            gx = sum(q[0] for q in pts) / len(pts); gy = sum(q[1] for q in pts) / len(pts)
            L.glow(gx, gy, 20, pal["caliente"], mezcla(cols[fase], pal["fondo"], .45))
            for _ in range(36):
                q = pts[rnd.randint(0, 16)]; f = rnd.uniform(.2, .85)
                L.dot(q[0] + (gx - q[0]) * f, q[1] + (gy - q[1]) * f, pal["a1"] if rnd.random() < .6 else pal["caliente"], 2)
    prev = H(0)
    for i in range(1, 241):
        f = 6 * math.pi * i / 240; q = H(f)
        up = (q[0] - cx) + (q[1] - cy) < 0
        L.line([prev, q], claro(pal["metal"], .5) if up else pal["metal"], 4); prev = q
    ys = [H(6 * math.pi * i / 240) for i in range(241)]
    yt = min(q[1] for q in ys if abs(q[0] - cx) < 14)
    for bx in (-9, 9):
        L.rect(bx - 2.5, yt - 16, bx + 2.5, yt - 2, fill=pal["a1"], outline=osc(pal["a1"], .5))
    if any(int(((phi + 2 * math.pi * k) / (1.5 * math.pi)) % 4) == 2 for k in range(3)):
        L.dot(0, yt - 18, (255, 255, 255), 4)
    ccx, ccy = cx + e * math.cos(phi), cy + e * math.sin(phi)
    ap = [(ccx + R * math.cos(phi / 3 + 2 * math.pi * k / 3), ccy + R * math.sin(phi / 3 + 2 * math.pi * k / 3)) for k in range(3)]
    L.poly([(x + 3, y + 3) for x, y in ap], fill=osc(pal["fondo"], .5))
    L.poly(ap, fill=osc(pal["metal"], .35), outline=claro(pal["metal"], .4))
    for k in range(3):
        a, b = ap[k], ap[(k + 1) % 3]
        L.line([a, b], [pal["frio"], pal["a2"], pal["caliente"]][k], 2)
    L.circ(ccx, ccy, 17, fill=osc(pal["metal"], .6), outline=pal["metal"])
    for k in range(18):
        a = k * 2 * math.pi / 18 - phi / 3 * 0
        L.dot(ccx + 17 * math.cos(a), ccy + 17 * math.sin(a), claro(pal["metal"], .4), 1.5)
    for k in range(3):
        L.circ(ap[k][0], ap[k][1], 3.2, fill=pal["a1"], outline=osc(pal["a1"], .5))
    L.line([(cx, cy), (ccx, ccy)], pal["a1"], 5)
    L.circ(cx, cy, 7, fill=pal["a1"], outline=osc(pal["a1"], .5)); L.circ(cx, cy, 2.5, fill=(255, 255, 255))

# ---------------------------------------------------------------- turbina
def c_turbina(L, t, p, pal):
    r = 82; ang = t * p.get("velocidad", 1.0) * 5
    L.circ(0, 0, r + 10, fill=osc(pal["metal"], .45), outline=pal["metal"])
    for k in range(10):
        a = k * 2 * math.pi / 10
        L.circ((r + 4) * math.cos(a), (r + 4) * math.sin(a), 2.5, fill=claro(pal["metal"], .5))
    L.circ(0, 0, r, fill=osc(pal["fondo"], .55))
    for k in range(18):  # álabes del estátor (fondo)
        a = k * 2 * math.pi / 18
        L.line([(12 * math.cos(a), 12 * math.sin(a)), ((r - 2) * math.cos(a), (r - 2) * math.sin(a))], osc(pal["metal"], .6), 2)
    n = 14
    for k in range(n):
        a = ang + 2 * math.pi * k / n
        Pt = lambda rad, da: (rad * math.cos(a + da), rad * math.sin(a + da))
        col = mezcla(pal["metal"], pal["a2"], .55 if k % 2 else .15)
        L.poly([Pt(14, 0), Pt(r - 2, .30), Pt(r - 2, .02), Pt(14, .62)], fill=col, outline=osc(col, .5))
        L.line([Pt(18, .15), Pt(r - 8, .13)], claro(col, .55), 2)
    for k in range(3):  # desenfoque de movimiento
        L.arc(0, 0, r - 12 - k * 14, (ang * 57 + k * 70) % 360, (ang * 57 + k * 70 + 50) % 360, mezcla(pal["a2"], pal["fondo"], .4), 3)
    L.circ(0, 0, 17, fill=pal["a1"], outline=osc(pal["a1"], .5))
    L.circ(0, 0, 9, fill=claro(pal["a1"], .55)); L.circ(-3, -3, 3, fill=(255, 255, 255))
    L.arc(0, 0, r + 8, 200, 262, claro(pal["metal"], .8), 3)

# ---------------------------------------------------------------- flujo en tubería
def c_flujo(L, t, p, pal):
    amp, g = 34, 17
    yc = lambda x: amp * math.sin((x + 100) / 200 * 4 * math.pi)
    xs = list(range(-96, 97, 3))
    L.poly([(x, yc(x) - g - 4) for x in xs] + [(x, yc(x) + g + 4) for x in reversed(xs)], fill=osc(pal["metal"], .5))
    L.poly([(x, yc(x) - g + 1) for x in xs] + [(x, yc(x) + g - 1) for x in reversed(xs)], fill=osc(pal["fondo"], .5))
    L.line([(x, yc(x) - g - 4) for x in xs], claro(pal["metal"], .5), 2); L.line([(x, yc(x) + g + 4) for x in xs], pal["metal"], 2)
    for bx in (-60, 0, 60):
        L.rect(bx - 3, yc(bx) - g - 8, bx + 3, yc(bx) + g + 8, fill=pal["metal"], outline=osc(pal["metal"], .5))
    n, v = 30, p.get("velocidad", 1.0) * 0.22
    for i in range(n):
        s0 = (i / n + t * v) % 1
        for tr in range(5):
            s = s0 - tr * .012
            if s < 0: continue
            x = -94 + s * 188; y = yc(x) + 9 * math.sin(i * 7.3)
            col = mezcla(pal["frio"], pal["caliente"], s)
            L.dot(x, y, claro(col, .5) if tr == 0 else mezcla(col, pal["fondo"], tr * .17), 3.2 - tr * .3)
    L.poly([(96, yc(96) - 14), (108, yc(96)), (96, yc(96) + 14)], fill=pal["a1"])

# ---------------------------------------------------------------- resorte-masa
def c_resorte(L, t, p, pal):
    w = t * p.get("velocidad", 1.0) * 2.4
    y = 12 + 38 * math.sin(w)
    L.rect(-70, -100, 10, -90, fill=osc(pal["metal"], .4), outline=pal["metal"])
    for x in range(-70, 10, 8):
        L.line([(x, -90), (x + 6, -100)], osc(pal["metal"], .7), 1)
    top, bot, n = -90, y - 20, 12
    pts = [(-30, top)]
    for i in range(n):
        yy = top + (bot - top) * (i + .5) / n
        pts.append((-30 + (14 if i % 2 else -14), yy))
    pts.append((-30, bot))
    L.line(pts, osc(pal["metal"], .6), 6); L.line(pts, claro(pal["metal"], .3), 3)
    L.rect(-60, y - 20, 0, y + 20, fill=pal["a2"], outline=osc(pal["a2"], .5))
    L.line([(-58, y - 18), (-2, y - 18)], claro(pal["a2"], .6), 2)
    L.txt(-30, y, "m", pal["fondo"], 1.6)
    L.rect(26, -90, 98, 90, fill=osc(pal["fondo"], .4), outline=pal["oscuro"])
    L.line([(26, 12), (98, 12)], pal["oscuro"], 1)
    pts = []
    for i in range(0, 72):
        tau = i / 72 * 1.8
        pts.append((98 - i, 12 + 38 * math.sin(w - tau * 2.4)))
    L.line(pts, pal["a1"], 2)
    L.circ(98, y, 4, fill=pal["caliente"])

# ---------------------------------------------------------------- ondas e interferencia
def c_ondas(L, t, p, pal):
    w = t * p.get("velocidad", 1.0) * 3
    pares = [(-62, 1.0, pal["a2"], "A"), (0, 1.4, pal["caliente"], "B")]
    sumas = []
    for yy, k, col, nom in pares:
        pts = [(x, yy + 20 * math.sin(k * x * .09 - w * k)) for x in range(-96, 97, 3)]
        L.line(pts, osc(col, .6), 6); L.line(pts, col, 3)
        L.txt(-90, yy - 28, nom, col, 1.6)
    for x in range(-96, 97, 3):
        a = 20 * math.sin(1.0 * x * .09 - w) + 20 * math.sin(1.4 * x * .09 - w * 1.4)
        sumas.append((x, 62 + a * .55))
    L.line(sumas, osc(pal["a1"], .6), 6); L.line(sumas, pal["a1"], 3)
    L.txt(-84, 62 - 34, "A+B", pal["a1"], 1.6)
    for yy in (-62, 0, 62):
        L.line([(-98, yy), (98, yy)], pal["oscuro"], 1)

# ---------------------------------------------------------------- circuito
def c_circuito(L, t, p, pal):
    X, Y = 82, 52
    cam = [(-X, -Y), (X, -Y), (X, Y), (-X, Y)]
    L.line(cam + [cam[0]], osc(pal["metal"], .5), 9); L.line(cam + [cam[0]], pal["metal"], 5)
    L.rect(-96, -22, -66, 22, fill=pal["fondo"])                                 # batería
    L.rect(-92, -20, -70, 20, fill=osc(pal["a1"], .35), outline=pal["a1"])
    L.rect(-82, -26, -78, -20, fill=pal["a1"])
    L.txt(-81, 0, "+", pal["texto"], 2); L.txt(-81, 12, "-", pal["texto"], 2)
    brillo = .6 + .4 * math.sin(t * 7)
    L.rect(66, -26, 96, 26, fill=pal["fondo"])
    L.glow(82, 0, 34, pal["a1"], pal["fondo"])
    L.circ(82, 0, 16, fill=mezcla(pal["a1"], (255, 255, 255), .3 + .3 * brillo), outline=pal["a1"])
    L.line([(76, 8), (82, -6), (88, 8)], osc(pal["a1"], .6), 2)
    per = 2 * (2 * X + 2 * Y); n, v = 32, p.get("velocidad", 1.0) * .12
    for i in range(n):
        s = ((i / n) + t * v) % 1 * per
        if s < 2 * X: q = (-X + s, -Y)
        elif s < 2 * X + 2 * Y: q = (X, -Y + (s - 2 * X))
        elif s < 4 * X + 2 * Y: q = (X - (s - 2 * X - 2 * Y), Y)
        else: q = (-X, Y - (s - 4 * X - 2 * Y))
        L.circ(q[0], q[1], 3.2, fill=pal["frio"], outline=claro(pal["frio"], .5))
        L.dot(q[0], q[1], (255, 255, 255), 1.2)
    L.txt(0, 0, "I", pal["a2"], 2)

# ---------------------------------------------------------------- órbitas
def c_orbitas(L, t, p, pal):
    v = p.get("velocidad", 1.0) * t
    L.glow(0, 0, 36, pal["a1"], pal["fondo"])
    L.circ(0, 0, 15, fill=pal["a1"], outline=claro(pal["a1"], .5)); L.circ(-4, -4, 5, fill=(255, 255, 230))
    datos = [(40, .6, pal["frio"], 6, 1.6), (68, .6, pal["caliente"], 8, .8), (94, .6, pal["a2"], 7, .5)]
    for i, (rx, f, col, rp, sp) in enumerate(datos):
        for k in range(0, 120):
            a = k * 2 * math.pi / 120
            L.dot(rx * math.cos(a), rx * f * math.sin(a), osc(pal["metal"], .4), 1)
        a = v * sp + i
        px, py = rx * math.cos(a), rx * f * math.sin(a)
        L.circ(px + 1.5, py + 1.5, rp, fill=osc(col, .7)); L.circ(px, py, rp, fill=col, outline=osc(col, .5))
        L.circ(px - rp * .3, py - rp * .3, rp * .3, fill=claro(col, .6))
        if i == 1:
            m = v * 4
            L.circ(px + 15 * math.cos(m), py + 10 * math.sin(m), 2.4, fill=pal["texto"])

# ---------------------------------------------------------------- leva y seguidor
def c_levas(L, t, p, pal):
    th = t * p.get("velocidad", 1.0) * 2.2
    cx, cy = -34, 40
    rad = lambda a: 28 + 16 * max(0, math.cos(a)) ** 1.5
    pts = [(cx + rad(a - th) * math.cos(a), cy + rad(a - th) * math.sin(a)) for a in [k * 2 * math.pi / 72 for k in range(72)]]
    ytop = cy - rad(-math.pi / 2 - th + 0) * 1  # radio en el ángulo hacia arriba
    L.poly([(x + 3, y + 3) for x, y in pts], fill=osc(pal["fondo"], .6))
    L.poly(pts, fill=pal["metal"], outline=osc(pal["metal"], .5))
    L.circ(cx, cy, 8, fill=pal["a1"], outline=osc(pal["a1"], .5)); L.circ(cx, cy, 2.5, fill=osc(pal["a1"], .8))
    L.line([(cx - 24, cy - 24), (cx - 10, cy - 36)], claro(pal["metal"], .7), 2)
    L.circ(cx, ytop - 7, 7, fill=pal["a2"], outline=osc(pal["a2"], .5))
    L.rect(cx - 4, -88, cx + 4, ytop - 14, fill=claro(pal["metal"], .2), outline=osc(pal["metal"], .5))
    n = 9; top, bot = -70, ytop - 14
    zz = [(cx - 18, top)]
    for i in range(n):
        zz.append((cx - 18 + (14 if i % 2 else -2), top + (bot - top) * (i + .5) / n))
    L.line(zz, pal["caliente"], 3)
    L.rect(cx - 22, -92, cx + 22, -86, fill=pal["metal"], outline=osc(pal["metal"], .5))
    L.rect(26, -90, 98, 90, fill=osc(pal["fondo"], .4), outline=pal["oscuro"])
    gp = []
    for i in range(72):
        tau = i / 72 * 2.8
        gp.append((98 - i, 62 - (rad(-math.pi / 2 - (th - tau * 2.2)) - 28) * 2.4))
    L.line(gp, pal["a1"], 2)
    L.txt(62, -78, "LIFT", pal["texto"], 1.2)

# ---------------------------------------------------------------- corazón (medicina)
def c_corazon(L, t, p, pal):
    f = 1.2 * p.get("velocidad", 1.0); ph = (t * f) % 1
    beat = (max(0.0, math.sin(ph * math.pi * 2 * 1.0)) ** 6) * .12
    k = 1 + beat
    rojo, azul = (225, 60, 70), (70, 120, 230)
    def H(x, y): return (x * k, y * k - 6)
    L.poly([H(-46, -26), H(-34, -46), H(-10, -44), H(0, -22), H(0, 58), H(-26, 34), H(-48, 6)], fill=rojo, outline=osc(rojo, .5))   # lado izquierdo (oxigenado)
    L.poly([H(46, -26), H(34, -46), H(10, -44), H(0, -22), H(0, 58), H(26, 34), H(48, 6)], fill=azul, outline=osc(azul, .5))
    L.line([H(-44, -4), H(-4, -4)], osc(rojo, .5), 2); L.line([H(4, -4), H(44, -4)], osc(azul, .5), 2)
    L.line([H(0, -22), H(0, 58)], (255, 255, 255), 2)
    L.circ(*H(-26, -22), 4 * k, fill=claro(rojo, .5)); L.circ(*H(26, -22), 4 * k, fill=claro(azul, .5))
    L.poly([H(-14, -44), H(-8, -76), H(14, -80), H(26, -64), H(18, -62), H(8, -68), H(-2, -64), H(-4, -44)], fill=rojo, outline=osc(rojo, .5))   # aorta
    L.poly([H(26, -44), H(34, -70), H(46, -70), H(40, -44)], fill=azul, outline=osc(azul, .5))
    for i in range(10):
        s = (i / 10 + t * f * .5) % 1
        L.dot(*H(-8 + s * 30, -44 - s * 34 + 8 * math.sin(s * 6)), (255, 220, 220), 3)
        L.dot(*H(40 - s * 6, -70 + s * 24), (200, 220, 255), 3)
    pts = []
    for i in range(0, 200, 2):
        x = i - 100; q = (((x / 100 + t * f * .5) % 1) + 1) % 1
        y = 0
        if .10 < q < .18: y = -5 * math.sin((q - .10) / .08 * math.pi)
        elif .28 < q < .30: y = 4
        elif .30 < q < .34: y = -26 * math.sin((q - .30) / .04 * math.pi)
        elif .34 < q < .37: y = 7
        elif .50 < q < .62: y = -8 * math.sin((q - .50) / .12 * math.pi)
        pts.append((x, 88 + y))
    L.line(pts, pal["a1"], 2)
    L.txt(0, 98, "ECG", pal["a1"], 1)

# ---------------------------------------------------------------- neurona (medicina / ciencia)
def c_neurona(L, t, p, pal):
    v = p.get("velocidad", 1.0); s = (t * .22 * v) % 1
    col = mezcla(pal["a2"], (255, 255, 255), .1)
    L.circ(-64, 0, 17, fill=osc(col, .4), outline=col); L.circ(-64, 0, 7, fill=pal["a1"], outline=osc(pal["a1"], .5))
    for i in range(7):
        a = -1.2 + i * .4 + math.pi * .55
        e1 = (-64 - 17 * math.cos(a), 17 * math.sin(a)); e2 = (e1[0] - 22 * math.cos(a + .25 * math.sin(i)), e1[1] + 22 * math.sin(a) * 1.0)
        L.line([e1, e2], col, 3); L.line([e2, (e2[0] - 10, e2[1] + (8 if i % 2 else -8))], col, 2)
    L.line([(-47, 0), (60, 0)], osc(col, .5), 6)
    for i in range(4):
        x0 = -40 + i * 26; L.rect(x0, -7, x0 + 18, 7, fill=pal["texto"], outline=osc(pal["texto"], .5))
    px = -47 + s * 107
    L.glow(px, 0, 20, pal["a1"], osc(pal["fondo"], .3)); L.circ(px, 0, 5, fill=(255, 255, 255))
    L.circ(70, 0, 8, fill=osc(col, .4), outline=col)
    for i in range(8):
        q = (i / 8 + t * .9) % 1 if s > .85 or s < .1 else 0
        if q: L.dot(70 + q * 22, -6 + q * 12 + 3 * math.sin(i), pal["caliente"], 2.6)
    L.rect(92, -6, 98, 26, fill=osc(col, .5), outline=col); L.line([(92, 10), (92, 10)], col, 1)
    L.txt(-64, 30, "SOMA", pal["texto"], 1); L.txt(6, 22, "AXON", pal["texto"], 1); L.txt(78, -22, "SYNAPSE" if p.get("idioma") == "en" else "SINAPSIS", pal["texto"], 1)

# ---------------------------------------------------------------- pulmones (medicina)
def c_pulmones(L, t, p, pal):
    f = .35 * p.get("velocidad", 1.0); b = (math.sin(t * f * 2 * math.pi) + 1) / 2; k = .86 + .2 * b
    rosa = (235, 130, 150)
    L.rect(-4, -90, 4, -30, fill=pal["metal"], outline=osc(pal["metal"], .5))
    for sg in (-1, 1):
        L.poly([(sg * 6 * k, -30), (sg * 20, -28), (sg * 58 * k, -8), (sg * 62 * k, 40 * k), (sg * 50 * k, 70 * k), (sg * 8, 66 * k), (sg * 4, -8)], fill=mezcla(rosa, pal["fondo"], .25), outline=osc(rosa, .5))
        L.line([(sg * 4, -30), (sg * 24 * k, 0), (sg * 40 * k, 24 * k)], pal["metal"], 3)
        L.line([(sg * 24 * k, 0), (sg * 34 * k, -16 * k)], pal["metal"], 2)
        L.line([(sg * 24 * k, 0), (sg * 24 * k, 28 * k)], pal["metal"], 2)
        for q, (ax, ay) in enumerate(((40, 24), (34, -16), (24, 28), (46, 6), (30, 44), (50, 42))):
            L.circ(sg * ax * k, ay * k, 6 * k, fill=claro(rosa, .3), outline=osc(rosa, .4))
    for i in range(14):
        s = (i / 14 + t * f) % 1; ent = math.cos(t * f * 2 * math.pi) < 0 if False else (math.sin(t * f * 2 * math.pi) > 0)
        yy = -88 + s * 80 if ent else -8 - s * 80
        L.dot(((i % 3) - 1) * 2, yy, pal["a2"] if ent else pal["caliente"], 2.6)
    L.rect(-64, 72 * k + 4 - 10 * b, 64, 78 * k + 4 - 10 * b, fill=pal["metal"], outline=osc(pal["metal"], .5))
    L.txt(0, -96, "O2 IN" if math.sin(t * f * 2 * math.pi) > 0 else "CO2 OUT", pal["a2"] if math.sin(t * f * 2 * math.pi) > 0 else pal["caliente"], 1.2)

# ---------------------------------------------------------------- péndulo (física)
def c_pendulo(L, t, p, pal):
    w = 2.1 * p.get("velocidad", 1.0); a0 = .85; a = a0 * math.cos(w * t)
    px, py, Ln = 0, -86, 120
    bx, by = px + Ln * math.sin(a), py + Ln * math.cos(a)
    L.rect(-40, -96, 40, -88, fill=osc(pal["metal"], .4), outline=pal["metal"])
    L.arc(px, py, 40, 90 - math.degrees(a0), 90 + math.degrees(a0), pal["oscuro"], 1)
    L.line([(px, py), (bx, by)], pal["texto"], 2)
    L.circ(bx + 2, by + 2, 14, fill=osc(pal["fondo"], .5)); L.circ(bx, by, 14, fill=pal["a1"], outline=osc(pal["a1"], .5)); L.circ(bx - 4, by - 4, 4, fill=(255, 255, 230))
    L.circ(px, py, 3, fill=pal["texto"])
    h = (1 - math.cos(a)) / (1 - math.cos(a0)); ec = 1 - h
    L.rect(-98, 20, -80, 98, fill=osc(pal["fondo"], .4), outline=pal["oscuro"])
    L.rect(-97, 98 - 78 * h, -81, 98, fill=pal["caliente"]); L.txt(-89, 108, "PE", pal["caliente"], 1)
    L.rect(-72, 20, -54, 98, fill=osc(pal["fondo"], .4), outline=pal["oscuro"])
    L.rect(-71, 98 - 78 * ec, -55, 98, fill=pal["a2"]); L.txt(-63, 108, "KE", pal["a2"], 1)

COMPONENTES = {"engranajes": c_engranajes, "piston": c_piston, "rotor": c_rotor, "turbina": c_turbina, "flujo": c_flujo,
               "resorte": c_resorte, "ondas": c_ondas, "circuito": c_circuito, "orbitas": c_orbitas, "levas": c_levas, "corazon": c_corazon, "neurona": c_neurona, "pulmones": c_pulmones, "pendulo": c_pendulo}
