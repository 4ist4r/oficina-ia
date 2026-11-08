"""Motor de animación pixel-art 8-bit. Lienzo 108x192 -> ffmpeg lo escala x10 a 1080x1920 (vídeo vertical)."""
import math, os, random, re, shutil, subprocess, unicodedata, wave
import numpy as np
from PIL import Image, ImageDraw

W, H, FPS = 108, 192, 30

PALETAS = {
    "azul":    dict(fondo=(11,18,48), panel=(20,30,75), texto=(240,240,230), a1=(255,214,64), a2=(90,200,255), metal=(150,160,180), oscuro=(55,65,100), caliente=(255,120,40), frio=(70,130,255)),
    "verde":   dict(fondo=(8,30,24), panel=(14,50,40), texto=(235,245,235), a1=(250,230,90), a2=(110,230,160), metal=(150,175,165), oscuro=(40,80,66), caliente=(255,130,50), frio=(70,170,255)),
    "naranja": dict(fondo=(40,16,12), panel=(70,28,18), texto=(250,240,225), a1=(255,215,80), a2=(255,150,70), metal=(170,150,140), oscuro=(95,50,38), caliente=(255,90,40), frio=(90,160,255)),
}

_G = {
 "A":"010 101 111 101 101","B":"110 101 110 101 110","C":"011 100 100 100 011","D":"110 101 101 101 110",
 "E":"111 100 110 100 111","F":"111 100 110 100 100","G":"011 100 101 101 011","H":"101 101 111 101 101",
 "I":"111 010 010 010 111","J":"001 001 001 101 010","K":"101 101 110 101 101","L":"100 100 100 100 111",
 "M":"101 111 111 101 101","N":"110 101 101 101 101","O":"010 101 101 101 010","P":"110 101 110 100 100",
 "Q":"010 101 101 110 011","R":"110 101 110 101 101","S":"011 100 010 001 110","T":"111 010 010 010 010",
 "U":"101 101 101 101 111","V":"101 101 101 101 010","W":"101 101 111 111 101","X":"101 101 010 101 101",
 "Y":"101 101 010 010 010","Z":"111 001 010 100 111","0":"111 101 101 101 111","1":"010 110 010 010 111",
 "2":"110 001 010 100 111","3":"110 001 010 001 110","4":"101 101 111 001 001","5":"111 100 110 001 110",
 "6":"011 100 111 101 111","7":"111 001 010 010 010","8":"111 101 111 101 111","9":"111 101 111 001 110",
 ".":"000 000 000 000 010",",":"000 000 000 010 100",":":"000 010 000 010 000","!":"010 010 010 000 010",
 "?":"110 001 010 000 010","-":"000 000 111 000 000","/":"001 001 010 100 100","%":"101 001 010 100 101",
 "+":"000 010 111 010 000"," ":"000 000 000 000 000",
}
FONT = {k: v.split() for k, v in _G.items()}

# ---------- texto ----------
def limpiar(s):
    s = unicodedata.normalize("NFD", str(s).replace("¿", "").replace("¡", "")).upper()
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", "".join(c for c in s if c in FONT)).strip()

def envolver(s, n):
    lineas, act = [], ""
    for p in s.split():
        if len(act) + len(p) + (1 if act else 0) <= n:
            act = f"{act} {p}".strip()
        else:
            if act: lineas.append(act)
            act = p[:n]
    return lineas + ([act] if act else [])

def texto(d, x, y, s, col, esc=1):
    for ch in s:
        for r, fila in enumerate(FONT.get(ch, FONT[" "])):
            for c, b in enumerate(fila):
                if b == "1":
                    d.rectangle([x + c*esc, y + r*esc, x + c*esc + esc - 1, y + r*esc + esc - 1], fill=col)
        x += 4 * esc

def texto_centrado(d, cx, y, s, col, esc=1):
    texto(d, int(cx - (len(s) * 4 * esc - esc) / 2), y, s, col, esc)

# ---------- color ----------
def mezcla(a, b, f):
    return tuple(int(a[i] * (1 - f) + b[i] * f) for i in range(3))
def claro(c, f=.4): return mezcla(c, (255, 255, 255), f)
def osc(c, f=.5): return mezcla(c, (0, 0, 0), f)

FASES = {"es": ["ADMISION", "COMPRESION", "EXPLOSION", "ESCAPE"], "en": ["INTAKE", "COMPRESSION", "POWER", "EXHAUST"]}

def brillo(d, cx, cy, r, col, fondo):
    for rad in range(int(r), 0, -2):
        d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=mezcla(fondo, col, 1 - rad / r))

# ---------- plantillas ----------
def _engranaje(d, cx, cy, r, dientes, ang, col, prof=3):
    n = dientes * 4; pts = []
    for i in range(n):
        a = ang + 2 * math.pi * i / n
        rr = r + prof if i % 4 in (0, 1) else r
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon([(x + 1.5, y + 1.5) for x, y in pts], fill=osc(col, .8))
    d.polygon(pts, fill=col, outline=osc(col, .55))
    d.arc([cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1], 195, 265, fill=claro(col, .65))
    d.ellipse([cx - r * .62, cy - r * .62, cx + r * .62, cy + r * .62], fill=osc(col, .45))
    for k in range(4):  # radios
        a = ang * .0 + ang + k * math.pi / 2
        d.line([cx + r * .25 * math.cos(a), cy + r * .25 * math.sin(a), cx + r * .62 * math.cos(a), cy + r * .62 * math.sin(a)], fill=col, width=2)
    d.ellipse([cx - r * .28, cy - r * .28, cx + r * .28, cy + r * .28], fill=claro(col, .25), outline=osc(col, .6))
    d.point((cx, cy), fill=osc(col, .8))

def t_engranajes(d, t, p, pal, z):
    x0, y0, x1, y1 = z
    v = p.get("velocidad", 1.0) * t * 1.2
    cx, cy = (x0 + x1) / 2 - 14, (y0 + y1) / 2 - 8
    r1, r2, r3, d1, d2, d3 = 18, 12, 8, 12, 8, 6
    _engranaje(d, cx, cy, r1, d1, v, pal["metal"])
    bx, by = cx + (r1 + r2 + 4) * math.cos(0.7), cy + (r1 + r2 + 4) * math.sin(0.7)
    _engranaje(d, bx, by, r2, d2, -v * d1 / d2 + math.pi / d2, pal["a2"])
    cx3, cy3 = bx + (r2 + r3 + 4) * math.cos(-0.6), by + (r2 + r3 + 4) * math.sin(-0.6)
    _engranaje(d, cx3, cy3, r3, d3, v * d1 / d3, pal["a1"])

def t_piston(d, t, p, pal, z):
    x0, y0, x1, y1 = z
    cx = (x0 + x1) // 2
    th = (t * p.get("velocidad", 1.0) * 2 * math.pi * 0.35) % (4 * math.pi)
    fases = p.get("fases") or FASES.get(p.get("idioma", "es"), FASES["es"])
    fase = int(th // math.pi)
    cols = [pal["frio"], pal["a2"], pal["caliente"], pal["metal"]]
    texto_centrado(d, cx, y0 + 3, limpiar(fases[fase]), cols[fase] if fase != 3 else pal["texto"], 1)
    top, bot, cyc, rr, L = y0 + 17, y0 + 65, y0 + 76, 10, 24
    px_, py_ = cx + rr * math.sin(th), cyc - rr * math.cos(th)
    pis = py_ - math.sqrt(L * L - (px_ - cx) ** 2)
    rnd = random.Random(int(t * 12))
    d.rectangle([cx - 12, top, cx + 12, bot], fill=osc(pal["fondo"], .4))                       # cilindro
    gas = mezcla(cols[fase], pal["fondo"], .55)
    d.rectangle([cx - 11, top + 1, cx + 11, int(pis) - 7], fill=gas)
    if fase == 2:
        brillo(d, cx, top + 6, 11, pal["caliente"], gas)
    for _ in range(10 if fase != 2 else 22):                                                      # partículas de gas
        yy = rnd.randint(top + 2, max(top + 3, int(pis) - 8)); xx = rnd.randint(cx - 10, cx + 10)
        d.point((xx, yy), fill=pal["a1"] if fase == 2 and rnd.random() < .6 else claro(cols[fase], .5))
    for sx in (cx - 17, cx + 13):                                                                 # bloque con rayado de sección
        d.rectangle([sx, top - 4, sx + 4, bot], fill=osc(pal["metal"], .35))
        for yy in range(top - 4, bot):
            if (yy + sx) % 4 == 0:
                d.line([sx, yy, sx + 4, yy - 4 if yy - 4 > top - 4 else yy], fill=osc(pal["metal"], .6))
    d.rectangle([cx - 17, top - 5, cx + 17, top], fill=pal["metal"], outline=osc(pal["metal"], .5))  # culata
    d.line([cx - 17, top - 5, cx + 17, top - 5], fill=claro(pal["metal"], .5))
    vi = 3 if fase == 0 else 0; ve = 3 if fase == 3 else 0                                       # válvulas
    for vx, vo, col in ((cx - 7, vi, pal["frio"]), (cx + 7, ve, pal["texto"])):
        d.line([vx, top - 11 + vo, vx, top + vo], fill=pal["texto"])
        d.rectangle([vx - 3, top + vo, vx + 3, top + vo + 1], fill=col)
    d.rectangle([cx - 1, top - 10, cx + 1, top - 5], fill=pal["a1"])                              # bujía
    if fase == 2 and th - 2 * math.pi < 0.5:
        d.rectangle([cx - 2, top + 1, cx + 2, top + 5], fill=(255, 255, 255))
    if fase == 0:                                                                                 # flecha aire entra
        d.polygon([(cx - 27, top - 10), (cx - 21, top - 7), (cx - 27, top - 4)], fill=pal["frio"])
    if fase == 3:
        d.polygon([(cx + 21, top - 10), (cx + 27, top - 7), (cx + 21, top - 4)], fill=pal["metal"])
    d.rectangle([cx - 11, int(pis) - 7, cx + 11, int(pis)], fill=claro(pal["metal"], .15), outline=osc(pal["metal"], .5))  # pistón
    d.line([cx - 11, int(pis) - 5, cx + 11, int(pis) - 5], fill=osc(pal["metal"], .6))
    d.line([cx - 11, int(pis) - 3, cx + 11, int(pis) - 3], fill=osc(pal["metal"], .6))
    d.line([cx - 10, int(pis) - 7, cx + 4, int(pis) - 7], fill=claro(pal["metal"], .7))
    d.line([cx, pis, px_, py_], fill=osc(pal["metal"], .7), width=4)                              # biela
    d.line([cx, pis, px_, py_], fill=claro(pal["metal"], .3), width=2)
    d.ellipse([cx - rr - 4, cyc - rr - 4, cx + rr + 4, cyc + rr + 4], fill=osc(pal["metal"], .5), outline=pal["metal"])  # cigüeñal
    d.ellipse([cx - 4 * math.sin(th) * -1 - 5 - rr * .6 * math.sin(th) * 0 - 0, cyc - 5, cx + 5, cyc + 5], fill=osc(pal["metal"], .5)) if False else None
    cwx, cwy = cx - rr * .7 * math.sin(th), cyc + rr * .7 * math.cos(th)
    d.ellipse([cwx - 5, cwy - 5, cwx + 5, cwy + 5], fill=pal["metal"], outline=osc(pal["metal"], .5))
    d.ellipse([px_ - 3, py_ - 3, px_ + 3, py_ + 3], fill=pal["a1"], outline=osc(pal["a1"], .5))
    d.ellipse([cx - 2, cyc - 2, cx + 2, cyc + 2], fill=pal["texto"])

def t_rotor(d, t, p, pal, z):
    x0, y0, x1, y1 = z
    cx, cy, R, e = (x0 + x1) / 2, (y0 + y1) / 2 + 4, 30, 7
    phi = t * p.get("velocidad", 1.0) * 2 * math.pi * 0.5
    H = lambda f: (cx + e * math.cos(f) + R * math.cos(f / 3), cy + e * math.sin(f) + R * math.sin(f / 3))
    cols = [pal["frio"], pal["a2"], pal["caliente"], pal["metal"]]
    rnd = random.Random(int(t * 12))
    for k in range(3):                                           # cámaras coloreadas por fase del ciclo
        fa = phi + 2 * math.pi * k
        pts = [H(fa + 2 * math.pi * j / 14) for j in range(15)]
        fase = int(((phi + 2 * math.pi * k) / (1.5 * math.pi)) % 4)
        d.polygon(pts, fill=mezcla(cols[fase], pal["fondo"], .45))
        if fase == 2:
            gx = sum(q[0] for q in pts) / len(pts); gy = sum(q[1] for q in pts) / len(pts)
            for _ in range(18):
                q = pts[rnd.randint(0, 14)]; f = rnd.uniform(.25, .8)
                d.point((q[0] + (gx - q[0]) * f, q[1] + (gy - q[1]) * f), fill=pal["a1"] if rnd.random() < .6 else pal["caliente"])
    prev = H(0)
    for i in range(1, 181):                                       # carcasa (epitrocoide)
        f = 6 * math.pi * i / 180; q = H(f)
        up = (q[0] - cx) + (q[1] - cy) < 0
        d.line([prev, q], fill=claro(pal["metal"], .5) if up else pal["metal"], width=2); prev = q
    yt = min(H(6 * math.pi * i / 180)[1] for i in range(181) if abs(H(6 * math.pi * i / 180)[0] - cx) < 9)
    for bx in (cx - 5, cx + 5):                                   # bujías en la cintura de la carcasa
        d.rectangle([bx - 1, yt - 7, bx + 1, yt - 1], fill=pal["a1"])
        d.point((bx, yt - 8), fill=(255, 255, 255))
    ccx, ccy = cx + e * math.cos(phi), cy + e * math.sin(phi)
    ap = [(ccx + R * math.cos(phi / 3 + 2 * math.pi * k / 3), ccy + R * math.sin(phi / 3 + 2 * math.pi * k / 3)) for k in range(3)]
    d.polygon([(x + 1, y + 1) for x, y in ap], fill=osc(pal["fondo"], .5))
    d.polygon(ap, fill=osc(pal["metal"], .35), outline=claro(pal["metal"], .4))
    d.ellipse([ccx - 8, ccy - 8, ccx + 8, ccy + 8], fill=osc(pal["metal"], .6), outline=pal["metal"])
    for k in range(3):
        d.rectangle([ap[k][0] - 1, ap[k][1] - 1, ap[k][0] + 1, ap[k][1] + 1], fill=pal["a1"])
    d.line([cx, cy, ccx, ccy], fill=pal["a1"], width=2)
    d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=pal["a1"], outline=osc(pal["a1"], .5))

def t_turbina(d, t, p, pal, z):
    x0, y0, x1, y1 = z
    cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2, 31
    ang = t * p.get("velocidad", 1.0) * 5
    d.ellipse([cx - r - 3, cy - r - 3, cx + r + 3, cy + r + 3], fill=osc(pal["metal"], .4), outline=pal["metal"])
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=osc(pal["fondo"], .5))
    n = 11
    for k in range(n):
        a = ang + 2 * math.pi * k / n
        P = lambda rad, da: (cx + rad * math.cos(a + da), cy + rad * math.sin(a + da))
        col = mezcla(pal["metal"], pal["a2"], .5 if k % 2 else .1)
        d.polygon([P(6, 0), P(r - 1, .22), P(r - 1, .02), P(6, .5)], fill=col, outline=osc(col, .5))
        d.line([P(8, .1), P(r - 3, .1)], fill=claro(col, .5))
    d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=pal["a1"], outline=osc(pal["a1"], .5))
    d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=claro(pal["a1"], .6))
    d.arc([cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1], 200, 260, fill=claro(pal["metal"], .7))

def t_flujo(d, t, p, pal, z):
    x0, y0, x1, y1 = z
    ym, amp, grosor = (y0 + y1) // 2, 14, 8
    yc = lambda x: ym + amp * math.sin((x - x0) / (x1 - x0) * 4 * math.pi)
    xs = list(range(int(x0) + 2, int(x1) - 2, 2))
    d.polygon([(x, yc(x) - grosor - 2) for x in xs] + [(x, yc(x) + grosor + 2) for x in reversed(xs)], fill=osc(pal["metal"], .5))
    d.polygon([(x, yc(x) - grosor + 1) for x in xs] + [(x, yc(x) + grosor - 1) for x in reversed(xs)], fill=osc(pal["fondo"], .5))
    d.line([(x, yc(x) - grosor - 2) for x in xs], fill=claro(pal["metal"], .5)); d.line([(x, yc(x) + grosor + 2) for x in xs], fill=pal["metal"])
    n, v = 20, p.get("velocidad", 1.0) * 0.25
    for i in range(n):
        s0 = (i / n + t * v) % 1
        for tr in range(4):  # estela
            s = s0 - tr * .012
            if s < 0: continue
            x = x0 + 3 + s * (x1 - x0 - 6); y = yc(x) + 5 * math.sin(i * 7.3)
            col = mezcla(pal["frio"], pal["caliente"], s)
            d.rectangle([x, y, x + 1, y + 1], fill=claro(col, .5) if tr == 0 else mezcla(col, pal["fondo"], tr * .22))
    d.polygon([(x1 - 3, yc(x1 - 3) - 7), (x1 + 0, yc(x1 - 3)), (x1 - 3, yc(x1 - 3) + 7)], fill=pal["a1"])

TEMPLATES = {"engranajes": t_engranajes, "piston": t_piston, "rotor": t_rotor, "flujo": t_flujo, "turbina": t_turbina}
PLANTILLAS = list(TEMPLATES)

def medidor(d, t, m, pal, z):
    x1, y1 = z[2], z[3]
    cx, cy, r = x1 - 15, y1 - 15, 12
    d.ellipse([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2], fill=osc(pal["panel"], .3), outline=pal["metal"])
    for k in range(25):
        a = math.radians(210 - 240 * k / 24)
        d.point((cx + r * math.cos(a), cy - r * math.sin(a)), fill=mezcla(pal["a2"], pal["caliente"], k / 24))
    frac = min(1, m.get("valor", 5000) / max(1, m.get("max", 10000))) * (0.97 + 0.03 * math.sin(t * 40))
    a = math.radians(210 - 240 * frac)
    d.line([cx, cy, cx + (r - 2) * math.cos(a), cy - (r - 2) * math.sin(a)], fill=pal["caliente"])
    d.ellipse([cx - 1, cy - 1, cx + 1, cy + 1], fill=pal["texto"])
    texto_centrado(d, cx, cy + 4, limpiar(m.get("etiqueta", "RPM")), pal["texto"], 1)

# ---------- composición ----------
def validar(e):
    e = dict(e or {})
    e["plantilla"] = e.get("plantilla") if e.get("plantilla") in TEMPLATES else "engranajes"
    e["paleta"] = e.get("paleta") if e.get("paleta") in PALETAS else "azul"
    e.setdefault("titulo", "HOW IT WORKS"); e.setdefault("etiqueta", ""); e.setdefault("cifra", "")
    e.setdefault("narracion", e["titulo"]); e.setdefault("velocidad", 1.0); e.setdefault("idioma", "es")
    if not isinstance(e.get("parametros"), dict):
        e["parametros"] = {}
    return e

def disponer(e):
    tit = envolver(limpiar(e["titulo"]), 12)
    esc, paso = 2, 12
    if len(tit) > 2:
        tit, esc, paso = envolver(limpiar(e["titulo"]), 24)[:3], 1, 8
    cif = envolver(limpiar(e["cifra"]), 24)[:2] if e["cifra"] else []
    y = 13; ht = len(tit) * paso + 4
    y2 = y + ht + 2; hc = len(cif) * 8 + 4 if cif else 0
    return dict(tit=tit, esc=esc, paso=paso, cif=cif, yt=y, ht=ht, yc=y2, hc=hc, z=(4, y2 + hc + 5, W - 4, 165))

def trocear_subs(narr, dur):
    frases = [f.strip() for f in re.split(r"(?<=[.!?;:])\s+", narr) if f.strip()]
    trozos = []
    for f in frases:
        lin = envolver(limpiar(f), 24)
        for i in range(0, len(lin), 2):
            trozos.append(lin[i:i + 2])
    tot = sum(len(" ".join(t)) for t in trozos) or 1
    res, t = [], 0.0
    for tr in trozos:
        dd = dur * len(" ".join(tr)) / tot
        res.append((t, t + dd, tr)); t += dd
    return res

def fondo_base(pal):
    img = Image.new("RGB", (W, H)); px = img.load()
    a, b = pal["fondo"], mezcla(pal["fondo"], pal["panel"], .8)
    for y in range(H):
        f = y / H * 5; nivel = int(f); frac = f - nivel
        for x in range(W):
            n = nivel + (1 if frac > .5 and (x + y) % 2 == 0 else 0)
            px[x, y] = mezcla(a, b, n / 5)
    return img

def frame(e, pal, lay, t, subs, estrellas, bg=None, prog=0.0):
    img = bg.copy() if bg is not None else Image.new("RGB", (W, H), pal["fondo"]); d = ImageDraw.Draw(img)
    for i, (sx, sy) in enumerate(estrellas):
        if (int(t * 2) + i) % 5:
            d.point((sx, sy), fill=mezcla(pal["fondo"], pal["a2"], .35))
    if e["etiqueta"]:
        et = limpiar(e["etiqueta"])[:20]
        d.rectangle([2, 2, 2 + len(et) * 4 + 3, 10], fill=pal["panel"], outline=pal["a1"])
        texto(d, 4, 4, et, pal["a1"])
    d.rectangle([3, lay["yt"], W - 4, lay["yt"] + lay["ht"]], fill=pal["panel"], outline=pal["a2"])
    d.line([4, lay["yt"] + 1, W - 5, lay["yt"] + 1], fill=claro(pal["panel"], .25))
    for i, l in enumerate(lay["tit"]):
        y = lay["yt"] + 3 + i * lay["paso"]
        texto_centrado(d, W / 2 + 1, y + 1, l, (0, 0, 0), lay["esc"])
        texto_centrado(d, W / 2, y, l, pal["texto"], lay["esc"])
    if lay["cif"]:
        d.rectangle([3, lay["yc"], W - 4, lay["yc"] + lay["hc"]], fill=pal["panel"], outline=pal["a1"])
        for i, l in enumerate(lay["cif"]):
            texto_centrado(d, W / 2, lay["yc"] + 3 + i * 8, l, pal["a1"], 1)
    zx0, zy0, zx1, zy1 = lay["z"]                                  # visor tipo monitor retro
    d.rectangle([zx0, zy0, zx1, zy1], fill=osc(pal["fondo"], .35), outline=pal["oscuro"])
    for gx in range(zx0 + 8, zx1, 8):
        for gy in range(zy0 + 8, zy1, 8):
            d.point((gx, gy), fill=pal["oscuro"])
    for cx_, cy_ in ((zx0, zy0), (zx1, zy0), (zx0, zy1), (zx1, zy1)):
        d.rectangle([cx_ - 1, cy_ - 1, cx_ + 1, cy_ + 1], fill=pal["a2"])
    TEMPLATES[e["plantilla"]](d, t, {**e["parametros"], "velocidad": e["velocidad"], "idioma": e["idioma"]}, pal, lay["z"])
    if e.get("medidor"):
        medidor(d, t, e["medidor"], pal, lay["z"])
    if e.get("marca"):
        texto(d, zx0 + 3, zy1 - 8, limpiar(e["marca"])[:18], mezcla(pal["texto"], pal["fondo"], .55))
    d.rectangle([3, 167, W - 4, 168], fill=pal["oscuro"])
    d.rectangle([3, 167, 3 + int((W - 7) * min(1, prog)), 168], fill=pal["a1"])
    for a, b, lin in subs:
        if a <= t < b:
            d.rectangle([2, 170, W - 3, 170 + len(lin) * 8 + 2], fill=(0, 0, 0))
            for i, l in enumerate(lin):
                texto_centrado(d, W / 2, 172 + i * 8, l, (255, 255, 255), 1)
            break
    return img

# ---------- audio y vídeo ----------
def ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg") or "ffmpeg"

def duracion_audio(ruta):
    r = subprocess.run([ffmpeg(), "-i", ruta], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 30.0

def chiptune(ruta, seg, sr=22050, ritmo=1.0):
    """ritmo: velocidad relativa del mecanismo de la escena (1.0=normal); más alto = pulso más rápido y marcado, para que la música vaya con la imagen."""
    ritmo = max(0.5, min(2.5, ritmo))
    n = int(seg * sr); t = np.arange(n) / sr; audio = np.zeros(n)
    acordes = [[220, 261.63, 329.63], [174.61, 220, 261.63], [261.63, 329.63, 392], [196, 246.94, 293.66]]
    paso = 0.125 / ritmo
    kick = 0.4 + 0.25 * (ritmo - 1.0)  # motor más rápido = golpe de bajo más presente
    for i in range(int(seg / paso) + 1):
        ac = acordes[(i // 16) % 4]; f = ac[i % 3]
        a, b = int(i * paso * sr), min(n, int((i + 1) * paso * sr))
        if a >= n: break
        tt = t[a:b]
        audio[a:b] += 0.5 * np.sign(np.sin(2 * np.pi * f * tt)) * np.linspace(1, 0.3, b - a)
        if i % 2 == 0:
            audio[a:b] += kick * np.sign(np.sin(2 * np.pi * (ac[0] / 2) * tt))
    audio = audio / (np.max(np.abs(audio)) + 1e-9) * 0.6
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((audio * 32767).astype("<i2").tobytes())
    return ruta

def renderizar(escena, salida, voz=None, dur_defecto=25.0, seed=7):
    """Devuelve la ruta del mp4 (1080x1920, 30fps, voz + música chiptune)."""
    e = validar(escena); pal = PALETAS[e["paleta"]]; lay = disponer(e)
    dur = duracion_audio(voz) if voz else dur_defecto
    total = dur + 1.2
    subs = trocear_subs(e["narracion"], dur)
    bg = fondo_base(pal)
    rnd = random.Random(seed); estrellas = [(rnd.randint(0, W - 1), rnd.randint(0, H - 1)) for _ in range(30)]
    os.makedirs(os.path.dirname(salida) or ".", exist_ok=True)
    musica = chiptune(salida + ".musica.wav", total)
    cmd = [ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    if voz:
        cmd += ["-i", voz, "-i", musica, "-filter_complex",
                "[0:v]scale=1080:1920:flags=neighbor,format=yuv420p[v];[1:a]apad,volume=1.0[a1];[2:a]volume=0.12[a2];[a1][a2]amix=inputs=2:duration=longest:normalize=0[a]"]
    else:
        cmd += ["-i", musica, "-filter_complex", "[0:v]scale=1080:1920:flags=neighbor,format=yuv420p[v];[1:a]volume=0.5[a]"]
    cmd += ["-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", salida]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(total * FPS)):
        p.stdin.write(frame(e, pal, lay, i / FPS, subs, estrellas, bg, i / FPS / total).tobytes())
    p.stdin.close(); p.wait()
    os.remove(musica)
    if p.returncode != 0:
        raise RuntimeError("ffmpeg falló al montar el vídeo")
    return salida
