"""Motor de vídeo v2(HTML): la misma 'escena' JSON que hoy consume motor2.py (capas, cámara, eventos,
narración) se traduce a una página HTML/CSS/GSAP y se renderiza con HyperFrames (Chrome headless),
en vez de dibujar a mano con PIL. Mismo contrato de salida que motor2.renderizar: un .mp4 con voz+música.

Cubre, de momento, solo los mecanismos más usados (piston+engranajes, rotor Wankel) como prueba real
de que el salto de calidad (tipografía, degradados, sombreado) funciona end-to-end con el pipeline de
agentes tal cual está hoy. El resto de componentes/presets de motor2 siguen con el motor PIL."""
import json, math, os, subprocess, time
from PIL import Image
from .escena import PALETAS, trocear_subs, ffmpeg, duracion_audio, chiptune

PROYECTO = os.path.join(os.path.dirname(os.path.dirname(__file__)), "hyperframes_proj")
W, H = 1080, 1920

GUIA_ESCENA_HTML = """Diseña una escena animada en HTML (vertical 1080x1920) para un mecanismo educativo.
Devuelve JSON con 'escena' y 'sprites_necesarios' (deja 'sprites_necesarios' como lista VACÍA: este motor no usa sprites).
La 'escena' debe tener EXACTAMENTE esta forma, más simple que en otros motores:
 - paleta: 'azul'|'verde'|'naranja'. titulo, etiqueta, cifra, narracion: igual que siempre (cifra corta, máx 48 car).
 - 'capas': una lista con:
   1) OBLIGATORIA, la primera: {"tipo":"componente", "nombre": uno de "piston"|"engranajes"|"rotor", "velocidad": 0.5-2, "t":[0,1]}.
      Esta pieza se ve FIJA durante TODO el vídeo (no se puede cambiar de pieza a mitad ni usar presets 3D/iso/sprites: elige la que mejor
      represente el mecanismo real, aunque sea una simplificación: piston=motores de pistón/combustión, engranajes=cualquier
      transmisión/reductora/reloj, rotor=motores rotativos tipo Wankel).
   2) OPCIONAL: UNA capa {"tipo":"contador", "valor":[desde,hasta], "formato":"{:,.0f} RPM", "t":[0,0.25]}:
      una cifra que sube como gancho en los primeros segundos. (No hace falta 'pos': el motor la coloca solo en su propia franja).
   3) OPCIONAL: hasta 2 capas {"tipo":"etiqueta"|"texto", "texto":"MÁX 20 CARACTERES", "t":[inicio,fin]}: datos cortos que
      aparecen y desaparecen en su ventana de tiempo (el motor las coloca solo en su propia franja; no hace falta 'pos').
      NO solapes sus ventanas de tiempo entre sí ni con la del contador.
 - NO uses 'camara', 'eventos', 'iso' ni 'sprite': este motor (HTML/HyperFrames) todavía no los soporta.
 - Sincroniza cada etiqueta/texto/contador con la frase de la narración que menciona ese dato."""

def _hex(rgb):
    return "#%02x%02x%02x" % tuple(int(max(0, min(255, c))) for c in rgb)

def _escapar(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def _ritmo_escena(e):
    vs = []
    for c in e.get("capas") or []:
        p = c.get("params") or {}
        v = p.get("velocidad", c.get("velocidad") if c.get("tipo") in ("componente", "iso") else None)
        if v is not None:
            try: vs.append(float(v))
            except Exception: pass
    return max(0.5, min(2.5, max(vs))) if vs else 1.0

def _mecanismo(e):
    """Elige qué pieza mecánica (de las portadas a HTML) dibujar, a partir de la 1ª capa de tipo
    'componente'/'iso' que haya propuesto el Director visual. Si no se reconoce, usa pistón+engranaje."""
    for c in e.get("capas") or []:
        if c.get("tipo") in ("componente", "iso"):
            nombre = str(c.get("nombre") or c.get("preset") or "").lower()
            if "rotor" in nombre or "wankel" in nombre:
                return "rotor"
            if "engranaje" in nombre or "gear" in nombre or "tren" in nombre:
                return "engranajes"
            return "piston"
    return "piston"

# ----------------------------------------------------------------- piezas (SVG/CSS)
_ROTOR_PATH = None

def _rotor_path(r=150):
    """Triángulo de Reuleaux (rotor de motor Wankel): 3 arcos, cada uno centrado en el vértice opuesto."""
    global _ROTOR_PATH
    if _ROTOR_PATH:
        return _ROTOR_PATH
    lado = r * math.sqrt(3)
    angs = [-90, 30, 150]
    pts = [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for a in angs]
    d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f} "
    for i in range(1, 4):
        x, y = pts[i % 3]
        d += f"A {lado:.1f} {lado:.1f} 0 0 1 {x:.1f} {y:.1f} "
    d += "Z"
    _ROTOR_PATH = d
    return d

def _pieza_piston(pal):
    return f"""
      <div id="gear"></div>
      <div id="piston"></div>
      <style>
        #gear {{ position:absolute; left:50%; top:50%; width:420px; height:420px;
          margin-left:-210px; margin-top:-210px;
          background: repeating-conic-gradient({pal['metal']} 0deg 15deg, {pal['oscuro']} 15deg 30deg);
          border-radius:50%;
          clip-path: polygon(50% 0%,56% 0%,58% 8%,66% 6%,70% 13%,78% 10%,80% 18%,88% 18%,88% 26%,96% 28%,
            94% 36%,100% 40%,96% 48%,100% 56%,94% 60%,96% 68%,88% 70%,88% 78%,80% 78%,78% 86%,70% 83%,
            66% 90%,58% 88%,56% 96%,50% 96%,44% 96%,42% 88%,34% 90%,30% 83%,22% 86%,20% 78%,12% 78%,
            12% 70%,4% 68%,6% 60%,0% 56%,4% 48%,0% 40%,6% 36%,4% 28%,12% 26%,12% 18%,20% 18%,22% 10%,
            30% 13%,34% 6%,42% 8%);
          box-shadow: inset 10px 10px 0 rgba(255,255,255,.25), inset -10px -10px 0 rgba(0,0,0,.4); }}
        #gear::after {{ content:""; position:absolute; left:50%; top:50%; width:150px; height:150px;
          margin-left:-75px; margin-top:-75px;
          border-radius:50%; background:{pal['oscuro']};
          box-shadow: inset 8px 8px 0 rgba(0,0,0,.5), inset -8px -8px 0 rgba(255,255,255,.15); }}
        #piston {{ position:absolute; left:50%; top:50%; width:80px; height:380px;
          margin-left:-40px; margin-top:-430px;
          background: linear-gradient(90deg,{pal['oscuro']} 0%,{pal['metal']} 45%,{pal['a2']} 55%,{pal['oscuro']} 100%);
          box-shadow: inset 6px 0 0 rgba(255,255,255,.3), inset -6px 0 0 rgba(0,0,0,.4); }}
        #piston::before {{ content:""; position:absolute; left:-18px; top:-36px; width:116px; height:56px;
          background:{pal['metal']};
          box-shadow: inset 6px 6px 0 rgba(255,255,255,.3), inset -6px -6px 0 rgba(0,0,0,.45); }}
      </style>""", """
      tl.to("#gear", {{ rotation: 360 * {vueltas:.1f}, duration: {dur:.2f}, ease: "none" }}, 0);
      tl.fromTo("#piston", {{ y: 0 }}, {{ y: 160, duration: {paso:.3f},
        repeat: {reps}, yoyo: true, ease: "sine.inOut" }}, 0);"""

def _pieza_rotor(pal):
    path = _rotor_path()
    return f"""
      <svg id="housing" width="560" height="560" viewBox="-200 -200 400 400" style="position:absolute;left:50%;top:50%;margin-left:-280px;margin-top:-280px;overflow:visible">
        <ellipse cx="0" cy="0" rx="185" ry="155" fill="none" stroke="{pal['metal']}" stroke-width="13" />
        <ellipse cx="0" cy="0" rx="185" ry="155" fill="none" stroke="{pal['oscuro']}" stroke-width="4" />
      </svg>
      <svg id="rotor" width="560" height="560" viewBox="-200 -200 400 400" style="position:absolute;left:50%;top:50%;margin-left:-280px;margin-top:-280px;overflow:visible">
        <path d="{path}" fill="{pal['a2']}" stroke="{pal['oscuro']}" stroke-width="6" />
        <circle cx="0" cy="0" r="22" fill="{pal['oscuro']}" />
      </svg>""", """
      tl.to("#rotor", {{ rotation: 360 * {vueltas_rotor:.1f}, duration: {dur:.2f}, ease: "none",
        transformOrigin: "50% 50%" }}, 0);"""

def _pieza_engranajes(pal):
    gear_css = f"""
        background: repeating-conic-gradient({pal['metal']} 0deg 15deg, {pal['oscuro']} 15deg 30deg);
        border-radius:50%;
        clip-path: polygon(50% 0%,56% 0%,58% 8%,66% 6%,70% 13%,78% 10%,80% 18%,88% 18%,88% 26%,96% 28%,
          94% 36%,100% 40%,96% 48%,100% 56%,94% 60%,96% 68%,88% 70%,88% 78%,80% 78%,78% 86%,70% 83%,
          66% 90%,58% 88%,56% 96%,50% 96%,44% 96%,42% 88%,34% 90%,30% 83%,22% 86%,20% 78%,12% 78%,
          12% 70%,4% 68%,6% 60%,0% 56%,4% 48%,0% 40%,6% 36%,4% 28%,12% 26%,12% 18%,20% 18%,22% 10%,
          30% 13%,34% 6%,42% 8%);
        box-shadow: inset 8px 8px 0 rgba(255,255,255,.25), inset -8px -8px 0 rgba(0,0,0,.4);"""
    return f"""
      <div id="gearA"></div>
      <div id="gearB"></div>
      <style>
        #gearA {{ position:absolute; left:50%; top:50%; width:360px; height:360px;
          margin-left:-350px; margin-top:-180px; {gear_css} }}
        #gearA::after {{ content:""; position:absolute; left:50%; top:50%; width:120px; height:120px;
          margin-left:-60px; margin-top:-60px; border-radius:50%; background:{pal['oscuro']}; }}
        #gearB {{ position:absolute; left:50%; top:50%; width:230px; height:230px;
          margin-left:30px; margin-top:-115px; {gear_css} }}
        #gearB::after {{ content:""; position:absolute; left:50%; top:50%; width:72px; height:72px;
          margin-left:-36px; margin-top:-36px; border-radius:50%; background:{pal['oscuro']}; }}
      </style>""", """
      tl.to("#gearA", {{ rotation: 360 * {vueltas:.1f}, duration: {dur:.2f}, ease: "none" }}, 0);
      tl.to("#gearB", {{ rotation: -360 * {vueltas_b:.1f}, duration: {dur:.2f}, ease: "none" }}, 0);"""

_PIEZAS = {"piston": _pieza_piston, "rotor": _pieza_rotor, "engranajes": _pieza_engranajes}

def _parse_formato(formato):
    """'{:,.0f} RPM' -> (prefijo, sufijo) alrededor del marcador numérico, para recomponer en JS."""
    import re
    m = re.search(r"\{[^}]*\}", str(formato or "{:,.0f}"))
    if not m:
        return "", str(formato or "")
    return formato[:m.start()], formato[m.end():]

def _overlays(e, total, offset=0):
    """Capas 'contador' (cifra que sube) y 'etiqueta'/'texto' (texto corto que aparece y desaparece),
    igual que hoy en motor2 pero como overlays HTML que se funden en su ventana de tiempo. 'offset' evita
    colisionar los id con los de los subtítulos."""
    html, js = [], []
    for i, c in enumerate(e.get("capas") or []):
        tipo = c.get("tipo")
        if tipo not in ("contador", "etiqueta", "texto"):
            continue
        t = c.get("t") or [0, 1]
        t0, t1 = max(0.0, float(t[0])) * total, min(1.0, float(t[1] if len(t) > 1 else 1)) * total
        if t1 <= t0:
            continue
        # posición FIJA en una franja segura (entre la cifra y el mecanismo, o entre el mecanismo y los
        # subtítulos); se ignora el 'pos' que proponga el Director para no arriesgarse a que choque con
        # otro bloque de texto (cifra, subtítulos) que ya ocupan sus propias franjas.
        x = W / 2
        y = 510 if tipo == "contador" else 640
        escala = float(c.get("escala", 2) or 2)
        cid = f"ov{offset + i}"
        if tipo == "contador":
            desde, hasta = (c.get("valor") or [0, 100])[:2]
            pre, suf = _parse_formato(c.get("formato"))
            html.append(f'<div id="{cid}" class="clip ov" data-start="{t0:.2f}" data-duration="{(t1 - t0):.2f}" '
                        f'style="left:{x:.0f}px;top:{y:.0f}px;font-size:{round(52 * escala / 2)}px"><span id="{cid}i">0</span></div>')
            js.append(f'''
      {{ const o = {{ v: {float(desde)} }};
        tl.fromTo("#{cid}i", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2 }}, {t0:.2f});
        tl.to(o, {{ v: {float(hasta)}, duration: {max(0.3, (t1 - t0) * 0.85):.2f}, ease: "power1.out",
          onUpdate: () => {{ const el = document.getElementById("{cid}i");
            if (el) el.textContent = {json.dumps(pre)} + Math.round(o.v).toLocaleString("en-US") + {json.dumps(suf)}; }} }}, {t0:.2f}); }}''')
        else:
            txt = _escapar(c.get("texto", ""))
            html.append(f'<div id="{cid}" class="clip ov" data-start="{t0:.2f}" data-duration="{(t1 - t0):.2f}" '
                        f'style="left:{x:.0f}px;top:{y:.0f}px;font-size:{round(36 * escala / 2)}px"><span id="{cid}i">{txt}</span></div>')
            js.append(f'''
      tl.fromTo("#{cid}i", {{ opacity: 0, y: 8 }}, {{ opacity: 1, y: 0, duration: 0.2 }}, {t0:.2f});
      tl.to("#{cid}i", {{ opacity: 0, duration: 0.15, ease: "power2.in" }}, {max(t0, t1 - 0.15):.2f});''')
    return "".join(html), "".join(js)

# ----------------------------------------------------------------- HTML completo
def _html(e, total, subs):
    pal_rgb = PALETAS.get(e.get("paleta", "azul"), PALETAS["azul"])
    pal = {k: _hex(v) for k, v in pal_rgb.items()}
    ritmo = _ritmo_escena(e)
    mec = _mecanismo(e)
    markup, anim_tpl = _PIEZAS[mec](pal)
    vueltas = total * ritmo * 0.5
    anim = anim_tpl.format(dur=total, vueltas=vueltas, vueltas_rotor=vueltas / 3, vueltas_b=vueltas * 360 / 230,
                           paso=max(0.18, 0.5 / ritmo), reps=max(1, int(total / max(0.18, 0.5 / ritmo))))

    titulo = _escapar(e.get("titulo", ""))
    etiqueta = _escapar(e.get("etiqueta", ""))
    cifra = _escapar(e.get("cifra", ""))
    marca = _escapar(e.get("marca", ""))

    ov_html, ov_js = _overlays(e, total, offset=1000)

    caps_html, caps_js = [], []
    for i, (t0, t1, lineas) in enumerate(subs):
        if t1 <= t0:
            continue
        txt = _escapar(" ".join(lineas))
        cid = f"sub{i}"
        dura = max(0.1, (t1 - t0) - 0.08)  # hueco pequeño entre subtítulos consecutivos (evita solape en el borde)
        fin = t0 + dura
        caps_html.append(f'<div id="{cid}" class="clip sub" data-start="{t0:.2f}" data-duration="{dura:.2f}"><span id="{cid}i">{txt}</span></div>')
        caps_js.append(f'''
      tl.fromTo("#{cid}i", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.15 }}, {t0:.2f});
      tl.to("#{cid}i", {{ opacity: 0, duration: 0.1, ease: "power2.in" }}, {max(t0, fin - 0.1):.2f});''')

    return f"""<!doctype html>
<html lang="{'es' if e.get('idioma') == 'es' else 'en'}">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
  :root {{
    --ground: {pal['fondo']}; --ink: {pal['texto']}; --accent: {pal['a1']};
    --metal-light: {pal['metal']}; --metal-dark: {pal['oscuro']}; --hot: {pal['caliente']}; --cold: {pal['frio']};
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html, body {{ width:{W}px; height:{H}px; overflow:hidden; background:var(--ground);
    font-family:"Archivo Black","Arial Black",sans-serif; }}
  #bg {{ position:absolute; inset:0;
    background:
      radial-gradient(circle at 50% 28%, color-mix(in srgb, var(--cold) 22%, var(--ground)) 0%, var(--ground) 62%),
      conic-gradient(from 0deg at 50% 85%, color-mix(in srgb, var(--hot) 10%, transparent), transparent 40%); }}
  #root {{ width:100%; height:100%; position:relative; }}
  #tag {{ position:absolute; top:190px; left:0; right:0; text-align:center; color:var(--accent);
    font-size:36px; letter-spacing:9px; text-shadow:3px 3px 0 #000; }}
  #cifra {{ position:absolute; top:272px; left:0; right:0; text-align:center; color:var(--ink);
    font-size:80px; line-height:1.08; text-shadow:6px 6px 0 #000; padding:0 70px; }}
  #stage {{ position:absolute; left:50%; top:630px; width:700px; height:700px; margin-left:-350px; }}
  #marca {{ position:absolute; bottom:120px; left:0; right:0; text-align:center; color:var(--metal-light);
    font-size:30px; letter-spacing:5px; }}
  .sub {{ position:absolute; bottom:420px; left:60px; right:60px; text-align:center; color:var(--ink);
    font-size:48px; line-height:1.15; text-shadow:4px 4px 0 #000; overflow:visible; }}
  .sub span {{ display:block; }}
  .ov {{ position:absolute; transform:translate(-50%,-50%); color:var(--ink); text-align:center;
    text-shadow:4px 4px 0 #000; white-space:nowrap; letter-spacing:1px; }}
  .ov span {{ display:block; }}
  #flash {{ position:absolute; inset:0; background:#fff; opacity:0; pointer-events:none; }}
</style>
</head>
<body>
  <div id="root" data-composition-id="main" data-start="0" data-duration="{total:.2f}" data-width="{W}" data-height="{H}">
    <div id="bg" class="clip" data-start="0" data-duration="{total:.2f}" data-track-index="0"></div>
    <div id="tag" class="clip" data-start="0" data-duration="{total:.2f}" data-track-index="1" data-layout-allow-overlap>{etiqueta}</div>
    <div id="cifra" class="clip" data-start="0" data-duration="{total:.2f}" data-track-index="1" data-layout-allow-overlap>{cifra}</div>
    <div id="stage" class="clip" data-start="0" data-duration="{total:.2f}" data-track-index="1" data-layout-allow-overlap>
      {markup}
    </div>
    {''.join(caps_html)}
    {ov_html}
    <div id="marca" class="clip" data-start="0" data-duration="{total:.2f}" data-track-index="1">{marca}</div>
    <div id="flash" class="clip" data-start="0" data-duration="{total:.2f}" data-track-index="2"></div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
    tl.fromTo("#tag", {{ opacity: 0, y: -20 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: "power2.out" }}, 0);
    tl.fromTo("#cifra", {{ opacity: 0, scale: 0.92 }}, {{ opacity: 1, scale: 1, duration: 0.4, ease: "power2.out" }}, 0.15);
    tl.fromTo("#marca", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, 0.6);
    {anim}
    {''.join(caps_js)}
    {ov_js}
    window.__timelines = window.__timelines || {{}};
    window.__timelines["main"] = tl;
    tl.seek(0);
  </script>
</body>
</html>"""

# ----------------------------------------------------------------- check / snapshot / render
def _npx(*args, timeout=180):
    cmd = ["npx", "--yes", "hyperframes@0.9.26", *args]
    r = subprocess.run(cmd, cwd=PROYECTO, capture_output=True, text=True, timeout=timeout, shell=True)
    return r

def comprobar(e, total, subs):
    with open(os.path.join(PROYECTO, "index.html"), "w", encoding="utf-8") as f:
        f.write(_html(e, total, subs))
    r = _npx("check", "--json")
    try:
        datos = json.loads(r.stdout or "{}")
    except Exception:
        datos = {"raw": r.stdout, "err": r.stderr}
    return datos

def fotogramas_previa(e, sprites_defs=None, tiempos=(.06, .3, .55, .8), dur=25.0):
    """Igual que motor2.fotogramas_previa (mismo contrato: devuelve PIL.Image) pero vía 'hyperframes
    snapshot' (sin codificar vídeo) en vez de dibujar a mano: para el bucle del Crítico visual."""
    total = dur + 1.5
    subs = trocear_subs(e.get("narracion", ""), dur)
    with open(os.path.join(PROYECTO, "index.html"), "w", encoding="utf-8") as f:
        f.write(_html(e, total, subs))
    ats = ",".join(f"{t * total:.2f}" for t in tiempos)
    r = _npx("snapshot", "--at", ats, "--json", timeout=120)
    try:
        datos = json.loads(r.stdout or "{}")
    except Exception:
        print("[motor_html] snapshot no devolvió JSON:", r.stdout[:800], r.stderr[:800])
        return []
    rutas = [f.get("path") for f in (datos.get("frames") or []) if f.get("path")]
    return [Image.open(p).convert("RGB") for p in rutas if os.path.exists(p)]

def contact_sheet(e, sprites_defs=None, tiempos=(.06, .3, .55, .8), dur=25.0):
    """Como fotogramas_previa pero devuelve la ruta al contact-sheet.jpg (cuadrícula ya montada por
    HyperFrames) para pasárselo tal cual al Crítico visual, sin tener que componer un hoja() en PIL."""
    total = dur + 1.5
    subs = trocear_subs(e.get("narracion", ""), dur)
    with open(os.path.join(PROYECTO, "index.html"), "w", encoding="utf-8") as f:
        f.write(_html(e, total, subs))
    ats = ",".join(f"{t * total:.2f}" for t in tiempos)
    r = _npx("snapshot", "--at", ats, "--json", timeout=120)
    try:
        datos = json.loads(r.stdout or "{}")
    except Exception:
        print("[motor_html] snapshot no devolvió JSON:", r.stdout[:800], r.stderr[:800])
        return None
    hojas = datos.get("contactSheets") or []
    return hojas[0] if hojas and os.path.exists(hojas[0]) else None

def renderizar(escena, salida, voz=None, sprites_defs=None, dur_defecto=28.0):
    dur = duracion_audio(voz) if voz else dur_defecto
    total = dur + 1.5
    subs = trocear_subs(escena.get("narracion", ""), dur)
    with open(os.path.join(PROYECTO, "index.html"), "w", encoding="utf-8") as f:
        f.write(_html(escena, total, subs))

    chk = _npx("check", "--json", timeout=120)
    try:
        datos = json.loads(chk.stdout or "{}")
    except Exception:
        datos = {}
    if not datos.get("ok", True):
        errores = []
        for seccion in ("lint", "runtime", "layout", "motion", "contrast"):
            errores += [x for x in (datos.get(seccion, {}).get("findings") or []) if x.get("severity") == "error"]
        raise RuntimeError(f"hyperframes check encontró errores: {errores[:3] or datos}")

    os.makedirs(os.path.dirname(salida) or ".", exist_ok=True)
    muda = salida + ".muda.mp4"
    r = _npx("render", "--quality", "delivery", "-o", os.path.abspath(muda), timeout=300)
    if r.returncode != 0 or not os.path.exists(muda):
        raise RuntimeError(f"hyperframes render falló: {r.stdout[-1500:]} {r.stderr[-1500:]}")

    musica = chiptune(salida + ".musica.wav", total, ritmo=_ritmo_escena(escena))
    cmd = [ffmpeg(), "-y", "-loglevel", "error", "-i", muda]
    if voz:
        cmd += ["-i", voz, "-i", musica, "-filter_complex",
                "[1:a]apad,volume=1.0[a1];[2:a]volume=0.12[a2];[a1][a2]amix=inputs=2:duration=longest:normalize=0[a]"]
    else:
        cmd += ["-i", musica, "-filter_complex", "[1:a]volume=0.5[a]"]
    cmd += ["-map", "0:v", "-map", "[a]", "-t", f"{total:.2f}", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", salida]
    p = subprocess.run(cmd)
    os.remove(musica)
    try: os.remove(muda)
    except OSError: pass
    if p.returncode != 0:
        raise RuntimeError("ffmpeg (mux final) falló")
    return salida
