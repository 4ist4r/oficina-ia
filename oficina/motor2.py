"""Motor de vídeo pixel-art v2: lienzo 540x960 (x2 = 1080x1920), capas, sprites, cámara, eventos y montaje."""
import json, math, os, random, subprocess
import numpy as np
from PIL import Image, ImageDraw
from .escena import (PALETAS, mezcla, claro, osc, limpiar, envolver, texto, texto_centrado, trocear_subs,
                     ffmpeg, duracion_audio, chiptune)
from .componentes import COMPONENTES, Lz
from . import iso as isom

W, H, FPS = 540, 960, 30
ESC = H / 480.0  # factor de escala del "chrome" fijo (título, subtítulos, marca...) respecto al diseño original a 270x480
FONDOS = ["cuadricula", "estrellas", "cielo", "oceano"]
ANIMS = ["flotar", "vibrar", "girar", "pulso", "mover", "ninguna"]
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0

def suave(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

# ----------------------------------------------------------------- sprites
def sprite_a_imagen(sp, borde=True):
    """sprite = {filas:[str], paleta:{'a':'#rrggbb'}}; '.' transparente. Añade contorno automático."""
    filas = [str(f) for f in sp["filas"]]; w = max(len(f) for f in filas); h = len(filas)
    img = Image.new("RGBA", (w + 2, h + 2), (0, 0, 0, 0)); px = img.load()
    pal = sp.get("paleta", {})
    for y, f in enumerate(filas):
        for x, ch in enumerate(f):
            if ch in pal and ch != ".":
                c = pal[ch].lstrip("#")
                try:
                    px[x + 1, y + 1] = (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), 255)
                except ValueError:
                    pass
    if borde:
        src = img.copy().load(); lim = (12, 12, 28, 255)
        for y in range(h + 2):
            for x in range(w + 2):
                if src[x, y][3] == 0 and any(0 <= x + dx < w + 2 and 0 <= y + dy < h + 2 and src[x + dx, y + dy][3] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    px[x, y] = lim
    return img

def pegar(capa, img, cx, cy, esc=3, ang=0.0, sombra=True, flip=False):
    img = img.resize((img.width * esc, img.height * esc), Image.NEAREST)
    if flip: img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if ang:
        img = img.rotate(-ang, resample=Image.NEAREST, expand=True)
    if sombra:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0)); a = np.array(img)[..., 3]
        s = np.zeros((*a.shape, 4), dtype=np.uint8); s[..., 3] = (a > 0) * 90
        capa.alpha_composite(Image.fromarray(s), (int(cx - img.width / 2 + esc), int(cy - img.height / 2 + esc)))
    capa.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2))) if _dentro(capa, cx, cy, img) else None

def _dentro(capa, cx, cy, img):
    return -img.width < cx < capa.width + img.width and -img.height < cy < capa.height + img.height

# ----------------------------------------------------------------- validación
def _num(v, d, a=None, b=None):
    try: v = float(v)
    except (TypeError, ValueError): v = d
    if a is not None: v = max(a, v)
    if b is not None: v = min(b, v)
    return v

def validar(e):
    e = dict(e or {})
    e["paleta"] = e.get("paleta") if e.get("paleta") in PALETAS else "azul"
    e["fondo"] = e.get("fondo") if e.get("fondo") in FONDOS else "cuadricula"
    for k, d in (("titulo", "HOW IT WORKS"), ("etiqueta", ""), ("cifra", ""), ("narracion", ""), ("idioma", "en"), ("marca", "")):
        e[k] = str(e.get(k) or d)
    e["narracion"] = e["narracion"] or e["titulo"]
    capas = []
    for c in e.get("capas") or []:
        if not isinstance(c, dict): continue
        c = dict(c); tp = c.get("tipo")
        t = c.get("t") or [0, 1]
        try: c["t"] = [_num(t[0], 0, 0, 1), _num(t[1], 1, 0, 1)]
        except Exception: c["t"] = [0, 1]
        if tp == "componente" and c.get("nombre") in COMPONENTES: pass
        elif tp == "iso" and (c.get("preset") in isom.PRESETS or isinstance(c.get("partes"), list)): pass
        elif tp in ("sprite", "contador", "etiqueta", "texto", "flecha"): pass
        else: continue
        capas.append(c)
    e["capas"] = capas or [{"tipo": "componente", "nombre": "engranajes", "caja": [.5, .5, .8], "t": [0, 1]}]
    cam = []
    for k in e.get("camara") or []:
        try: cam.append({"t": _num(k["t"], 0, 0, 1), "zoom": _num(k.get("zoom", 1), 1, 1, 3), "c": [_num(k["c"][0], .5, 0, 1), _num(k["c"][1], .5, 0, 1)]})
        except Exception: pass
    e["camara"] = sorted(cam, key=lambda k: k["t"]) or [{"t": 0, "zoom": 1, "c": [.5, .5]}]
    e["eventos"] = [k for k in (e.get("eventos") or []) if isinstance(k, dict) and k.get("tipo") in ("sacudida", "flash")]
    e["sprites"] = e.get("sprites") if isinstance(e.get("sprites"), dict) else {}
    return e

# ----------------------------------------------------------------- layout
def disponer(e):
    E = ESC
    tit = envolver(limpiar(e["titulo"]), 20); esc, paso = round(3 * E), round(15 * E)
    if len(tit) > 2:
        tit, esc, paso = envolver(limpiar(e["titulo"]), 30)[:3], round(2 * E), round(10 * E)
    ht = len(tit) * (paso + round(4 * E)) + round(6 * E); yt = round(24 * E)
    cif = envolver(limpiar(e["cifra"]), 30)[:2] if e["cifra"] else []
    yc = yt + ht + round(4 * E); hc = len(cif) * round(12 * E) + round(8 * E) if cif else 0
    vy0 = yc + hc + round(8 * E)
    return dict(tit=tit, esc=esc, paso=paso, ht=ht, yt=yt, cif=cif, yc=yc, hc=hc, vx0=round(6 * E), vy0=vy0, vx1=W - round(6 * E), vy1=round(372 * E))

def fondo_estatico(pal):
    img = Image.new("RGB", (W, H)); px = img.load()
    a, b = pal["fondo"], mezcla(pal["fondo"], pal["panel"], .85)
    for y in range(H):
        f = y / H * 6; n0 = int(f); fr = f - n0
        for x in range(W):
            px[x, y] = mezcla(a, b, (n0 + (1 if fr > .5 and (x + y) % 2 == 0 else 0)) / 6)
    return img

def fondo_vp(tipo, pal, vw, vh, t, rnd):
    img = Image.new("RGBA", (vw, vh), osc(pal["fondo"], .3) + (255,)); d = ImageDraw.Draw(img)
    if tipo == "cuadricula":
        off = int(t * 6) % 16
        for gx in range(-16 + off, vw, 16):
            d.line([gx, 0, gx, vh], fill=mezcla(pal["fondo"], pal["oscuro"], .55))
        for gy in range(-16 + off, vh, 16):
            d.line([0, gy, vw, gy], fill=mezcla(pal["fondo"], pal["oscuro"], .55))
    elif tipo == "estrellas":
        r = random.Random(3)
        for i in range(70):
            x, y = r.randint(0, vw - 1), r.randint(0, vh - 1)
            if (int(t * 2) + i) % 6: d.point((x, y), fill=claro(pal["a2"], .3) if i % 7 == 0 else mezcla(pal["fondo"], pal["a2"], .5))
    elif tipo == "cielo":
        for y in range(vh):
            d.line([0, y, vw, y], fill=mezcla(pal["frio"], (200, 230, 255), y / vh * .8 + .1))
        r = random.Random(5)
        for i in range(6):
            cx = (r.randint(0, vw) + t * (4 + i * 2)) % (vw + 80) - 40; cy = r.randint(10, vh // 2)
            for dx, dy, rr in ((0, 0, 12), (14, 4, 9), (-14, 5, 8), (6, -5, 8)):
                d.ellipse([cx + dx - rr, cy + dy - rr * .6, cx + dx + rr, cy + dy + rr * .6], fill=(240, 248, 255))
    elif tipo == "oceano":
        for y in range(vh):
            d.line([0, y, vw, y], fill=mezcla(osc(pal["frio"], .2), osc(pal["frio"], .7), y / vh))
        for fila in range(6):
            yy = vh * .55 + fila * 14
            for x in range(0, vw, 2):
                d.point((x, yy + 2 * math.sin(x * .09 + t * 2 + fila)), fill=claro(pal["frio"], .35 - fila * .04))
    return img

# ----------------------------------------------------------------- capas
def _caja(c, vw, vh):
    cx, cy, tam = (list(c.get("caja") or [.5, .5, .8]) + [.5, .5, .8])[:3]
    return _num(cx, .5, 0, 1) * vw, _num(cy, .5, 0, 1) * vh, _num(tam, .8, .1, 1.4) * min(vw, vh)

def dibujar_capa(c, capa, t, tl, e, pal, sprites_img, vw, vh, total, anclas=None):
    d = ImageDraw.Draw(capa)
    a, b = c["t"]; loc = (tl - a) / max(1e-6, b - a)
    if c["tipo"] == "componente":
        cx, cy, tam = _caja(c, vw, vh)
        p = {**(c.get("params") or {}), "velocidad": _num(c.get("velocidad", (c.get("params") or {}).get("velocidad", 1.0)), 1.0, .1, 4), "idioma": e["idioma"]}
        COMPONENTES[c["nombre"]](Lz(d, cx, cy, tam / 200.0), t, p, pal)
    elif c["tipo"] == "iso":
        an = isom.render_iso(capa, c, max(0.0, t - c["t"][0] * total), pal, vw, vh)
        if anclas is not None: anclas.update({k: v for k, v in an.items()})
    elif c["tipo"] == "sprite":
        img = sprites_img.get(c.get("sprite"))
        if img is None: return
        px, py = _num((c.get("pos") or [.5, .5])[0], .5) * vw, _num((c.get("pos") or [.5, .5])[1], .5) * vh
        esc = max(1, int(round(_num(c.get("escala", 3), 3, 1, 12) * ESC))); an = c.get("anim", "ninguna"); ang = 0.0
        if an == "flotar": py += 4 * math.sin(t * 2.2); ang = 2 * math.sin(t * 1.6)
        elif an == "vibrar": px += random.Random(int(t * 30)).randint(-1, 1); py += random.Random(int(t * 30) + 9).randint(-1, 1)
        elif an == "girar": ang = (t * 90 * _num(c.get("velocidad", 1), 1)) % 360
        elif an == "pulso": esc = max(1, int(round(esc * (1 + .08 * math.sin(t * 5)))))
        elif an == "mover":
            ks = sorted([k for k in (c.get("mover") or []) if isinstance(k, (list, tuple)) and len(k) >= 3], key=lambda k: k[0])
            if ks:
                if tl <= ks[0][0]: px, py = ks[0][1] * vw, ks[0][2] * vh
                elif tl >= ks[-1][0]: px, py = ks[-1][1] * vw, ks[-1][2] * vh
                else:
                    for k0, k1 in zip(ks, ks[1:]):
                        if k0[0] <= tl <= k1[0]:
                            f = suave((tl - k0[0]) / max(1e-6, k1[0] - k0[0]))
                            px, py = (k0[1] + (k1[1] - k0[1]) * f) * vw, (k0[2] + (k1[2] - k0[2]) * f) * vh
        pegar(capa, img, px, py, esc, ang, flip=bool(c.get("espejo")))
    elif c["tipo"] == "contador":
        v0, v1 = (list(c.get("valor") or [0, 100]) + [100])[:2]
        f = suave(loc); v = _num(v0, 0) + (_num(v1, 100) - _num(v0, 0)) * f
        try: s = str(c.get("formato", "{:,.0f}")).format(v)
        except Exception: s = f"{v:,.0f}"
        px, py = (c.get("pos") or [.5, .9])[0] * vw, (c.get("pos") or [.5, .9])[1] * vh
        esc = max(1, int(round(_num(c.get("escala", 3), 3, 1, 6) * ESC))); s = limpiar(s)
        wd = len(s) * 4 * esc
        d.rectangle([px - wd / 2 - 5 * ESC, py - 4 * esc, px + wd / 2 + 5 * ESC, py + 4 * esc], fill=osc(pal["panel"], .2) + (230,), outline=pal["a1"])
        texto_centrado(d, px + 1, py - 2.5 * esc + 1, s, (0, 0, 0), esc); texto_centrado(d, px, py - 2.5 * esc, s, pal["a1"], esc)
    elif c["tipo"] == "texto":
        px, py = (c.get("pos") or [.5, .1])[0] * vw, (c.get("pos") or [.5, .1])[1] * vh
        esc = max(1, int(round(_num(c.get("escala", 2), 2, 1, 5) * ESC))); s = limpiar(c.get("texto", ""))
        n = max(0, int(len(s) * min(1, loc * 3)))
        texto_centrado(d, px + 1, py + 1, s[:n], (0, 0, 0), esc); texto_centrado(d, px, py, s[:n], pal["texto"], esc)

def dibujar_pantalla(c, d, tl, pal, vw, vh, anclas=None, cam=None):
    """Capas en espacio de pantalla (no les afecta la cámara): etiquetas con flecha."""
    a, b = c["t"]; loc = (tl - a) / max(1e-6, b - a)
    if c["tipo"] == "etiqueta":
        px, py = (c.get("pos") or [.3, .3])[0] * vw, (c.get("pos") or [.3, .3])[1] * vh
        s = limpiar(c.get("texto", "")); n = max(0, int(len(s) * min(1, loc * 4)))
        if not n: return
        wd = len(s) * round(8 * ESC) + round(8 * ESC)
        ap = c.get("apunta")
        if c.get("apunta_parte") and anclas and c["apunta_parte"] in anclas:
            ax, ay = anclas[c["apunta_parte"]]
            if cam: ax, ay = (ax - cam[0]) * vw / cam[2], (ay - cam[1]) * vh / cam[3]
            ap = [ax / vw, ay / vh]
        if ap:
            ax, ay = ap[0] * vw, ap[1] * vh
            d.line([px, py, ax, ay], fill=pal["a1"], width=max(1, round(2 * ESC))); d.ellipse([ax - 3 * ESC, ay - 3 * ESC, ax + 3 * ESC, ay + 3 * ESC], fill=pal["a1"], outline=(0, 0, 0))
        d.rectangle([px - wd / 2, py - 9 * ESC, px + wd / 2, py + 9 * ESC], fill=osc(pal["panel"], .2), outline=pal["a1"])
        texto_centrado(d, px, py - 5 * ESC, s[:n], pal["texto"], round(2 * ESC))

def camara_en(e, tl):
    ks = e["camara"]
    if tl <= ks[0]["t"]: k = ks[0]; return k["zoom"], k["c"][0], k["c"][1]
    if tl >= ks[-1]["t"]: k = ks[-1]; return k["zoom"], k["c"][0], k["c"][1]
    for k0, k1 in zip(ks, ks[1:]):
        if k0["t"] <= tl <= k1["t"]:
            f = suave((tl - k0["t"]) / max(1e-6, k1["t"] - k0["t"]))
            return (k0["zoom"] + (k1["zoom"] - k0["zoom"]) * f, k0["c"][0] + (k1["c"][0] - k0["c"][0]) * f, k0["c"][1] + (k1["c"][1] - k0["c"][1]) * f)

def disolver(capa, a):
    if a >= 1: return capa
    arr = np.array(capa); h, w = arr.shape[:2]
    umbral = np.tile(BAYER, (h // 4 + 1, w // 4 + 1))[:h, :w]
    arr[..., 3] = np.where(umbral < a, arr[..., 3], 0)
    return Image.fromarray(arr)

def frame(e, pal, lay, t, total, subs, bg, sprites_img):
    E = ESC
    tl = t / total
    img = bg.copy().convert("RGBA"); d = ImageDraw.Draw(img)
    # intro del título (entra deslizando)
    dy = -int((1 - suave(t / 0.5)) * 70 * E)
    m6 = round(6 * E); m8 = round(8 * E); m22 = round(22 * E)
    if e["etiqueta"]:
        et = limpiar(e["etiqueta"])[:30]
        d.rectangle([m6, m6 + dy, m6 + len(et) * round(8 * E) + m8, m22 + dy], fill=pal["panel"], outline=pal["a1"])
        texto(d, round(10 * E), round(10 * E) + dy, et, pal["a1"], round(2 * E))
    d.rectangle([m6, lay["yt"] + dy, W - m6 - 1, lay["yt"] + lay["ht"] + dy], fill=pal["panel"], outline=pal["a2"])
    d.line([m8, lay["yt"] + round(2 * E) + dy, W - m8 - 1, lay["yt"] + round(2 * E) + dy], fill=claro(pal["panel"], .25))
    for i, l in enumerate(lay["tit"]):
        y = lay["yt"] + round(6 * E) + i * (lay["paso"] + round(4 * E)) + dy
        texto_centrado(d, W / 2 + 2, y + 2, l, (0, 0, 0), lay["esc"]); texto_centrado(d, W / 2, y, l, pal["texto"], lay["esc"])
    if lay["cif"]:
        pulso = 1 if (t < 1.2 and int(t * 8) % 2 == 0) else 0
        d.rectangle([m6, lay["yc"], W - m6 - 1, lay["yc"] + lay["hc"]], fill=pal["panel"], outline=claro(pal["a1"], .5) if pulso else pal["a1"])
        for i, l in enumerate(lay["cif"]):
            texto_centrado(d, W / 2, lay["yc"] + round(5 * E) + i * round(12 * E), l, claro(pal["a1"], .6) if pulso else pal["a1"], round(2 * E))
    vx0, vy0, vx1, vy1 = lay["vx0"], lay["vy0"], lay["vx1"], lay["vy1"]; vw, vh = vx1 - vx0, vy1 - vy0
    rnd = random.Random(1)
    vp = fondo_vp(e["fondo"], pal, vw, vh, t, rnd); anclas = {}
    for c in e["capas"]:
        if c["tipo"] == "etiqueta": continue
        a, b = c["t"]
        if not (a - 0.001 <= tl <= b + 0.001): continue
        capa = Image.new("RGBA", (vw, vh), (0, 0, 0, 0))
        try: dibujar_capa(c, capa, t, tl, e, pal, sprites_img, vw, vh, total, anclas)
        except Exception as ex: print("[capa]", c.get("tipo"), ex)
        alfa = min(suave((tl - a) / 0.03), 1.0 if b >= .999 else suave((b - tl) / 0.03))
        vp.alpha_composite(disolver(capa, alfa))
    z, cx, cy = camara_en(e, tl); camp = (0, 0, vw, vh)
    if z > 1.001:
        cw, ch = vw / z, vh / z; x0 = max(0, min(vw - cw, cx * vw - cw / 2)); y0 = max(0, min(vh - ch, cy * vh - ch / 2))
        camp = (int(x0), int(y0), int(cw), int(ch)); vp = vp.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((vw, vh), Image.NEAREST)
    sx = sy = 0
    for ev in e["eventos"]:
        te = ev["t"] * total; dt = t - te
        if 0 <= dt < .6 and ev["tipo"] == "sacudida":
            r = random.Random(int(t * 40)); am = 7 * ESC * math.exp(-dt * 7); sx, sy = int(r.uniform(-am, am)), int(r.uniform(-am, am))
        if 0 <= dt < .35 and ev["tipo"] == "flash":
            fl = Image.new("RGBA", (vw, vh), (255, 255, 255, int(200 * (1 - dt / .35)))); vp.alpha_composite(fl)
    dv = ImageDraw.Draw(vp)
    for c in e["capas"]:
        a, b = c["t"]
        if c["tipo"] == "etiqueta" and a <= tl <= b:
            try: dibujar_pantalla(c, dv, tl, pal, vw, vh, anclas, camp)
            except Exception as ex: print("[etiqueta]", ex)
    img.alpha_composite(vp, (vx0 + sx, vy0 + sy))
    d.rectangle([vx0 - 1, vy0 - 1, vx1, vy1], outline=pal["a2"])
    for cx_, cy_ in ((vx0 - 1, vy0 - 1), (vx1, vy0 - 1), (vx0 - 1, vy1), (vx1, vy1)):
        d.rectangle([cx_ - 2, cy_ - 2, cx_ + 2, cy_ + 2], fill=pal["a2"])
    for a, b, lin in subs:
        if a <= t < b:
            y0 = round(378 * E)
            d.rectangle([m6, y0, W - m6 - 1, y0 + len(lin) * round(12 * E) + round(6 * E)], fill=(0, 0, 0, 215))
            for i, l in enumerate(lin): texto_centrado(d, W / 2, y0 + round(4 * E) + i * round(12 * E), l, (255, 255, 255), round(2 * E))
            break
    if e["marca"]:
        texto_centrado(d, W / 2, round(440 * E), limpiar(e["marca"])[:30], mezcla(pal["texto"], pal["fondo"], .45), round(2 * E))
    if tl > .93:  # cierre: llamada a seguir
        s = "FOLLOW FOR MORE" if e["idioma"] == "en" else "SIGUEME PARA MAS"
        if int(t * 3) % 2 == 0: texto_centrado(d, W / 2, round(420 * E), s, pal["a1"], round(2 * E))
    pb0, pb1 = round(472 * E), round(475 * E)
    d.rectangle([m6, pb0, W - m6 - 1, pb1], fill=pal["oscuro"]); d.rectangle([m6, pb0, m6 + int((W - 2 * m6 - 1) * tl), pb1], fill=pal["a1"])
    return img.convert("RGB")

# ----------------------------------------------------------------- render
def preparar(e, sprites_defs):
    e = validar(e)
    defs = {**(e["sprites"] or {}), **(sprites_defs or {})}
    imgs = {}
    for nombre, sp in defs.items():
        try: imgs[nombre] = sprite_a_imagen(sp)
        except Exception as ex: print("[sprite]", nombre, ex)
    return e, imgs

def fotogramas_previa(e, sprites_defs, tiempos=(.08, .3, .5, .72, .92), dur=25.0):
    e, imgs = preparar(e, sprites_defs); pal = PALETAS[e["paleta"]]; lay = disponer(e); bg = fondo_estatico(pal)
    subs = trocear_subs(e["narracion"], dur)
    return [frame(e, pal, lay, f * dur, dur, subs, bg, imgs) for f in tiempos]

def _ritmo_escena(e):
    """Velocidad relativa del mecanismo principal de la escena, para que la música vaya al compás de la imagen."""
    vs = []
    for c in e.get("capas") or []:
        p = c.get("params") or {}
        v = p.get("velocidad", c.get("velocidad") if c.get("tipo") in ("componente", "iso") else None)
        if v is not None:
            try: vs.append(float(v))
            except Exception: pass
    return max(0.5, min(2.5, max(vs))) if vs else 1.0

def renderizar(escena, salida, voz=None, sprites_defs=None, dur_defecto=28.0):
    e, imgs = preparar(escena, sprites_defs); pal = PALETAS[e["paleta"]]; lay = disponer(e); bg = fondo_estatico(pal)
    dur = duracion_audio(voz) if voz else dur_defecto
    total = dur + 1.5
    subs = trocear_subs(e["narracion"], dur)
    os.makedirs(os.path.dirname(salida) or ".", exist_ok=True)
    musica = chiptune(salida + ".musica.wav", total, ritmo=_ritmo_escena(e))
    cmd = [ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    vf = "[0:v]scale=1080:1920:flags=neighbor,format=yuv420p[v]"
    if voz:
        cmd += ["-i", voz, "-i", musica, "-filter_complex", vf + ";[1:a]apad,volume=1.0[a1];[2:a]volume=0.12[a2];[a1][a2]amix=inputs=2:duration=longest:normalize=0[a]"]
    else:
        cmd += ["-i", musica, "-filter_complex", vf + ";[1:a]volume=0.5[a]"]
    cmd += ["-map", "[v]", "-map", "[a]", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", salida]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(total * FPS)):
        p.stdin.write(frame(e, pal, lay, i / FPS, total, subs, bg, imgs).tobytes())
    p.stdin.close(); p.wait(); os.remove(musica)
    if p.returncode != 0: raise RuntimeError("ffmpeg falló")
    return salida
