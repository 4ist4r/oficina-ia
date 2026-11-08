"""Producción visual con solo la API de Claude: el Director diseña la escena, el Artista dibuja sprites,
el Crítico MIRA fotogramas renderizados y pide correcciones (bucle generar -> renderizar -> mirar -> mejorar)."""
import io, json, os, re
from PIL import Image
from . import motor2
from . import iso as isom
from .componentes import COMPONENTES

SPRITE_EJEMPLO = {"nombre": "barco", "filas": [
"..........................................",
"..................ffff....................",
"..................fggf....................",
"..........cccccc..fggf....................",
"..........crcrcc..fggf.hhhhhhh............",
"..........cccccc..ffff.hwhwhwh............",
"..aabbaaccbbaaccbbaaccbhhhhhhhh...........",
"..bbccbbaabbccbbaabbccbbaabbccb...........",
"..aabbaaccbbaaccbbaaccbbaaccbbaa..........",
"..bbccbbaabbccbbaabbccbbaabbccbb..........",
".nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn.......",
"nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn.....",
".nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn.......",
"..rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr........."],
"paleta": {"a": "#d8503a", "b": "#3a78c8", "c": "#e8c040", "n": "#2b3550", "r": "#a02828", "f": "#cfd6e4", "g": "#7d889c", "h": "#e8e8f0", "w": "#4a5878"}}

ESCENA_EJEMPLO = {
 "paleta": "azul", "fondo": "oceano", "titulo": "How a ship engine works", "etiqueta": "Real speed",
 "cifra": "1,470 TONS. 65,000 HP", "narracion": "(la narración final, 70-95 palabras)",
 "capas": [
  {"tipo": "sprite", "sprite": "barco", "pos": [0.5, 0.72], "escala": 4, "anim": "flotar", "t": [0, 0.45]},
  {"tipo": "contador", "valor": [0, 65000], "formato": "{:,.0f} HP", "pos": [0.5, 0.15], "escala": 3, "t": [0.05, 0.3]},
  {"tipo": "componente", "nombre": "piston", "caja": [0.5, 0.5, 0.95], "velocidad": 1.0, "params": {}, "t": [0.45, 1]},
  {"tipo": "etiqueta", "texto": "PISTON", "pos": [0.2, 0.8], "apunta": [0.5, 0.5], "t": [0.55, 1]}],
 "camara": [{"t": 0, "zoom": 1, "c": [0.5, 0.5]}, {"t": 0.5, "zoom": 1.4, "c": [0.5, 0.55]}],
 "eventos": [{"t": 0.45, "tipo": "flash"}, {"t": 0.46, "tipo": "sacudida"}]}

PLAN_EJEMPLO = {"escena": ESCENA_EJEMPLO, "sprites_necesarios": [{"nombre": "barco", "descripcion": "cargo container ship, side view", "ancho": 44, "alto": 16}]}
CRITICA_EJEMPLO = {"puntuacion": 9, "problemas": ["…"], "correcciones": ["…"]}

GUIA_ESCENA = f"""Diseña una escena animada pixel-art (lienzo vertical 270x480). Devuelve JSON con 'escena' y 'sprites_necesarios'.
COMPONENTES animados listos (alta calidad; úsalos como piezas centrales, NO inventes otros): {list(COMPONENTES)}
 - corazon (latidos, sangre y ECG), neurona (impulso nervioso y sinapsis), pulmones (respiración), pendulo (energía cinética/potencial).
 - engranajes(params.n 2-4), piston (4 tiempos; NO pongas params.fases salvo que quieras sobrescribir las 4 etiquetas con una lista de 4 strings), rotor (motor Wankel), turbina (fan de turbina), flujo (tubería con partículas),
   resorte (masa-resorte con gráfica), ondas (ondas e interferencia), circuito (electrones y bombilla), orbitas (sol y planetas), levas (leva y seguidor con gráfica).
 - 'caja':[cx,cy,tam] en fracciones del visor (centro y tamaño relativo al lado menor; 0.9 casi llena el visor). 'velocidad' 0.3-3.
ISOMÉTRICO 3D (voxels, gira como una maqueta 3D; ÚSALO para máquinas con volumen: da el efecto 3D que más engancha): capa {{tipo:'iso', preset:<nombre>, caja:[cx,cy,tam], giro:grados/seg (def 12), ang0:35, balanceo:grados, params:{{velocidad}}, t}}.
 PRESETS listos: {list(isom.PRESETS)} 
   ROBÓTICA: brazo_robotico (articulado con pinza), dron (hélices), rover (ruedas dentadas, Marte). INGENIERÍA: motor_abierto (4 cilindros), tren_engranajes, aerogenerador, grua, noria, cinta (con escáner). 
   ESPACIO: cohete (despegue con fuego y humo), satelite (paneles y antena), estacion_espacial. CIENCIA: atomo (electrones en órbita), adn (doble hélice), volcan (lava y humo), molecula_agua. MEDICINA: virus (cápside y espigas), adn, (corazon/neurona/pulmones son 2D).
 O compón tu modelo con 'partes' (unidades = voxels; modelo de 10-40 unidades; suelo con isla automático): {{forma:'caja',pos:[x,y,z],tam:[a,b,c],color}} | {{forma:'cilindro',centro:[x,y,z],radio,alto,eje:'z|x|y',hueco}} | esfera{{centro,radio}} | cono{{centro,radio,alto}}
 | engranaje{{centro,radio,dientes,grosor,eje,vel,ang}} | helice{{centro,radio,aspas,ancho,grosor,eje,vel}} | barra{{de:[x,y,z],a:[x,y,z],grosor}} | emisor{{tipo:'fuego|humo|chispas|agua',pos,dir:[dx,dy,dz],alto,n,vel}}.
 Colores: 'metal','a1','a2','caliente','frio','oscuro','texto' o '#rrggbb'. Cualquier parte admite 'off':[dx,dy,dz] y 'id'. Un rótulo puede apuntar a una parte con {{tipo:'etiqueta', texto, pos, apunta_parte:id}}.
 (ids: tren_engranajes A,B,C; aerogenerador torre,gondola,aspas; cinta escaner,caja; cohete cuerpo; motor_abierto ciguenal,cilindro,piston; brazo_robotico base,brazo,pinza; dron cuerpo,helice; grua torre,pluma,carga; noria cabina; satelite cuerpo,panel,antena; estacion_espacial modulo,panel_solar; rover cuerpo,panel,camara; atomo nucleo,electron; adn hebra,base; virus capside,espiga; volcan cono,crater; molecula_agua oxigeno,hidrogeno). Mezcla 3D iso con contadores y rótulos 2D encima.
SPRITES propios (cualquier objeto: barco, avión, coche, cohete, persona...): pide en 'sprites_necesarios' {{nombre, descripcion, ancho, alto}} (ancho<=56, alto<=40);
 el Artista los dibujará. En capas: {{tipo:'sprite', sprite:nombre, pos:[x,y], escala:1-8, anim: {motor2.ANIMS}, mover:[[t,x,y],...] si anim='mover', espejo:true/false}}.
OTRAS capas: contador {{valor:[desde,hasta], formato:'{{:,.0f}} RPM', pos, escala, t}} (cifra que sube: gancho), texto {{texto,pos,escala}}, etiqueta {{texto,pos,apunta:[x,y]}} (rótulo con flecha, en pantalla, ignora la cámara).
FONDOS: {motor2.FONDOS}. PALETAS: azul, verde, naranja.
TIEMPOS: todos los 't' son fracciones 0-1 de la duración total. Cámara: lista de keyframes {{t, zoom 1-3, c:[x,y]}}. Eventos: {{t, tipo:'sacudida'|'flash'}} en momentos de impacto.
REGLAS DE RETENCIÓN: gancho en los primeros 2 s (contador o cifra que sube + algo moviéndose); cambia algo (capa, cámara, etiqueta) cada 3-4 s; sincroniza cada frase de la narración con lo que se ve;
máx. 4 capas a la vez; centra lo importante (el visor se tapa un poco a la derecha en TikTok); etiquetas cortas en mayúsculas; todo texto en el idioma de la cuenta; usa zoom para mostrar detalle.
Las capas pueden solaparse en el tiempo con fundido automático. Una escena = 1 explicación clara de 25-35 s."""

SPRITE_PROMPT = """Dibuja un sprite pixel-art. Devuelve JSON {nombre, filas:[strings de IGUAL longitud], paleta:{caracter:'#rrggbb'}}.
'.' = transparente. Un carácter = un píxel. NO dibujes contorno (se añade solo). Vista lateral, luz desde arriba-izquierda, 3-4 tonos por material
(base, sombra, luz), 6-10 colores en total, siluetas claras y reconocibles, detalles pequeños (ventanas, remaches, reflejos). Máx. {ancho}x{alto}."""

def png_bytes(img):
    b = io.BytesIO(); img.save(b, "PNG"); return b.getvalue()

def hoja(frames, escala=1.5):
    w, h = frames[0].size; w2, h2 = int(w * escala), int(h * escala)
    s = Image.new("RGB", (w2 * len(frames) + 6 * (len(frames) - 1), h2), (255, 255, 255))
    for i, f in enumerate(frames):
        s.paste(f.resize((w2, h2), Image.NEAREST), (i * (w2 + 6), 0))
    return s

def _sprite_valido(sp):
    try:
        filas = [str(f) for f in sp["filas"]]
        return bool(filas) and len(filas) <= 48 and max(len(f) for f in filas) <= 64 and isinstance(sp.get("paleta"), dict)
    except Exception:
        return False

def crear_sprites(cuenta, necesarios, of, carpeta="sprites", presupuesto=None):
    os.makedirs(carpeta, exist_ok=True); defs = {}
    for s in necesarios or []:
        nombre = re.sub(r"[^a-z0-9_]", "", str(s.get("nombre", "x")).lower()) or "x"
        ruta = f"{carpeta}/{nombre}.json"
        if os.path.exists(ruta):                          # reutiliza: coste cero y coherencia de marca
            defs[nombre] = json.load(open(ruta, encoding="utf-8")); continue
        if presupuesto is not None and presupuesto.agotado():
            # Opus (el artista) es lo más caro de toda la pieza: si ya no queda margen, nos quedamos sin
            # este sprite decorativo (la escena se renderiza sin él) en vez de forzar el gasto.
            print(f"  (sin presupuesto para el sprite '{nombre}', se omite)"); continue
        ancho, alto = int(s.get("ancho", 40)), int(s.get("alto", 24))
        feedback = ""
        for intento in range(2):
            sp = of["artista"].hacer(cuenta, SPRITE_PROMPT.replace("{ancho}", str(ancho)).replace("{alto}", str(alto)) + f"\nSujeto: {s.get('descripcion', nombre)}. {feedback}",
                                     SPRITE_EJEMPLO, max_tokens=8000, presupuesto=presupuesto)
            if not _sprite_valido(sp):
                feedback = "El JSON no era válido: filas de igual longitud y paleta completa."; continue
            img = motor2.sprite_a_imagen(sp)
            fondo = Image.new("RGB", (img.width * 8, img.height * 8), (40, 50, 80))
            big = img.resize((img.width * 8, img.height * 8), Image.NEAREST); fondo.paste(big, (0, 0), big)
            rev = of["critico"].hacer(cuenta, f"Mira este sprite de '{s.get('descripcion', nombre)}'. ¿Se reconoce a primera vista? ¿Buen sombreado y colores? Puntúa 1-10 y da correcciones concretas (máx. 3, 1 frase cada una).",
                                      CRITICA_EJEMPLO, imagenes=[png_bytes(fondo)], max_tokens=8000, presupuesto=presupuesto)
            if float(rev.get("puntuacion", 0)) >= 7: break
            if presupuesto is not None and presupuesto.agotado(): break  # nos quedamos con este intento, no pedimos otro
            feedback = f"Un crítico vio problemas, corrígelos: {rev.get('problemas')} {rev.get('correcciones')}"
        if _sprite_valido(sp):
            json.dump(sp, open(ruta, "w", encoding="utf-8"), ensure_ascii=False); defs[nombre] = sp
    return defs

def producir_escena(cuenta, contenido, of, max_iter=2, pista=None, presupuesto=None):
    """Devuelve (escena, sprites_defs) listos para motor2.renderizar. El director visual y el crítico (paso 1 de cada uno)
    son obligatorios para tener un vídeo; las pasadas de corrección SOLO se hacen si queda presupuesto."""
    base = (f"Contenido del vídeo: título='{contenido.get('titulo')}', etiqueta='{contenido.get('etiqueta')}', cifra='{contenido.get('cifra')}', "
            f"narración='{contenido.get('narracion')}'. Mantén la narración (puedes pulirla para 25-35 s). "
            + (f"Pista de visual sugerida por el gestor de demanda: {pista} (iso:X = preset 3D, 2d:X = componente 2D); úsala si encaja o elige algo mejor. " if pista else ""))
    plan = of["director_visual"].hacer(cuenta, GUIA_ESCENA + "\n" + base, PLAN_EJEMPLO, max_tokens=12000, presupuesto=presupuesto)
    sprites = crear_sprites(cuenta, plan.get("sprites_necesarios"), of, presupuesto=presupuesto)
    mejor_plan, mejor_punt = plan, -1
    for it in range(max_iter):
        esc = plan.get("escena") or {}
        esc["idioma"] = cuenta.get("idioma", "en"); esc["marca"] = cuenta.get("marca", "")
        previa = hoja(motor2.fotogramas_previa(esc, sprites, tiempos=(.06, .3, .55, .8)))
        rev = of["critico"].hacer(cuenta,
            "Eres un crítico visual muy exigente de vídeos virales pixel-art (formato vertical). Estos 4 fotogramas son momentos del vídeo (de izquierda a derecha). "
            "Evalúa: ¿se entiende el mecanismo?, ¿hay solapes o textos cortados?, ¿composición y uso del espacio?, ¿gancho visual?, ¿variedad de ritmo? "
            f"Narración: '{esc.get('narracion')}'. Puntúa 1-10 y da correcciones concretas sobre las capas (posición, tamaño, tiempos, cámara, componentes). "
            "Máximo 4 problemas y 4 correcciones, cada uno en 1 frase breve.",
            CRITICA_EJEMPLO, imagenes=[png_bytes(previa)], max_tokens=10000, presupuesto=presupuesto)
        punt = float(rev.get("puntuacion", 0) or 0)
        print(f"  crítico visual (iter {it + 1}): {punt}/10")
        if punt > mejor_punt:
            mejor_plan, mejor_punt = plan, punt
        if punt >= 8:
            break
        if presupuesto is not None and presupuesto.agotado():
            print(f"  (sin presupuesto para pulir más la escena; nos quedamos con la mejor hasta ahora: {mejor_punt}/10)")
            break
        plan = of["director_visual"].hacer(cuenta, GUIA_ESCENA + f"\nESCENA ACTUAL: {json.dumps(esc, ensure_ascii=False)}\n"
            f"Corrígela según el crítico: {json.dumps(rev, ensure_ascii=False)}. Sprites ya disponibles: {list(sprites)}.", PLAN_EJEMPLO, max_tokens=12000, presupuesto=presupuesto)
        sprites.update(crear_sprites(cuenta, plan.get("sprites_necesarios"), of, presupuesto=presupuesto))
    plan = mejor_plan
    esc = plan.get("escena") or {}
    esc["idioma"] = cuenta.get("idioma", "en"); esc["marca"] = cuenta.get("marca", "")
    return esc, sprites
