import json, os, time
from datetime import datetime
from zoneinfo import ZoneInfo
from . import motor2, voz, arte, demanda
from .analitica import resumen
from .horarios import elegir_hora, proxima_ocurrencia
from .publicadores import PUBLICADORES
from .llm import Presupuesto, PresupuestoAgotado

TOPE_USD_POR_VIDEO = 0.5  # ningún vídeo puede costar más de esto; nunca se aborta a medias, solo se dejan de pulir pasadas opcionales

CONTENIDO = {"titulo": "How a rotary engine works", "etiqueta": "Real speed", "cifra": "9,000 RPM: 300 explosions a second",
             "narracion": "This engine has no pistons. A triangular rotor spins inside a housing. Every turn completes four phases. At 9,000 RPM, that is 300 explosions every second. Follow for the next machine.",
             "plataformas": [{"plataforma": "tiktok", "titulo": "…", "caption": "…", "hashtags": ["#ejemplo"]}]}

MED = "MEDICINA: solo divulgación educativa y precisa; NUNCA diagnósticos, dosis ni consejos de tratamiento; añade al final de cada caption 'Educational content, not medical advice.'. "

# palabras que en la práctica han hecho que Calidad vete una idea por no poder verificar la cifra
# (récords, límites reglamentarios, superlativos): penalizan la puntuación antes de gastar un solo token en guion
_RIESGO = ("f1", "fórmula 1", "formula 1", "récord", "record", "fastest", "world's", "highest ever",
           "most powerful", "limit", "límite", "reglament")

def _viabilidad(idea, cands_por_tema):
    """Puntuación 0-1 SIN llamar a la API: demanda real ya calculada + riesgo de que Calidad la vete.
    Así se descartan las ideas más flojas/arriesgadas ANTES de pagar guion+crítico+arte, que es donde de verdad se va el gasto."""
    c = cands_por_tema.get(str(idea.get("tema", "")).lower())
    demanda = c["score"] if c else 0.3  # tema inventado (no viene de los candidatos puntuados): se trata con cautela
    texto = f"{idea.get('tema', '')} {idea.get('angulo', '')} {idea.get('por_que_funcionara', '')}".lower()
    riesgo = 0.15 * sum(1 for palabra in _RIESGO if palabra in texto)
    return round(max(0.0, min(1.0, demanda - riesgo)), 3)

def produccion_dia(cuenta, config, estado, of):
    """No repite intento cada 20 min si salta el freno de emergencia: se considera el día como 'intentado' igual,
    para no quedar en un bucle de gasto repetido sin producir nada."""
    try:
        _produccion_dia(cuenta, config, estado, of)
    except PresupuestoAgotado as e:
        print(f"[FRENO DE EMERGENCIA] {cuenta['id']}: {e} — se para la producción de hoy aquí, no se reintenta hasta mañana")

def _produccion_dia(cuenta, config, estado, of):
    cid = cuenta["id"]
    tz = config.get("zona_audiencia", config.get("zona_horaria", "Europe/Madrid"))  # horas óptimas en la zona de la AUDIENCIA
    simular = config.get("modo_simulacion_publicacion", True)
    print(f"\n=== {cid}: producción del día ===")
    rend = resumen(estado, cid, cuenta["plataformas"])
    informe, _ = estado.ultima_nota(cid, "informe_analitica")

    # presupuesto de TODO el día (CEO + Estrategia + cada vídeo), no solo de cada vídeo por separado:
    # así el freno de emergencia también cubre lo que pasa ANTES de llegar al primer vídeo.
    n_videos = max(1, cuenta.get("publicaciones_por_dia", 1))
    presupuesto = Presupuesto(TOPE_USD_POR_VIDEO, limite_duro=TOPE_USD_POR_VIDEO * n_videos * 2)

    directrices = of["ceo"].hacer(cuenta,
        f"Fija las directrices de hoy. Rendimiento real (mejores/peores piezas y horas): {json.dumps(rend, ensure_ascii=False)}. "
        f"Informe analítico previo: {json.dumps(informe, ensure_ascii=False)}. Duplica lo que funciona y corta lo que no. Sé breve (máx. 80 palabras).",
        {"objetivo": "…", "pilares_contenido": ["…"], "que_evitar": ["…"]}, presupuesto=presupuesto)
    estado.nota(cid, "directrices", directrices)
    print("CEO:", directrices.get("objetivo"))

    doms = cuenta.get("dominios")
    cands = demanda.candidatos(estado, cid, doms, n=8)
    pets = demanda.peticiones(estado)[:10]
    print("  demanda:", [(x["tema"], x["score"]) for x in cands[:4]])
    ideas = of["estrategia"].hacer(cuenta,
        f"Elige {cuenta['publicaciones_por_dia']} ideas de vídeo para hoy como gestor de DEMANDA: lo que el público más pide y busca. "
        f"Candidatos ya puntuados por interés real, tendencia, rendimiento propio y peticiones: {json.dumps(cands, ensure_ascii=False)}. "
        f"Peticiones literales del público (comentarios): {pets}. Rendimiento por dominio: {json.dumps(demanda.resumen_dominios(estado, cid), ensure_ascii=False)}. "
        f"Elige de estos candidatos (no inventes temas nuevos, ya están puntuados por demanda real). "
        f"Mezcla dominios si hay varias ideas. Directrices: {json.dumps(directrices, ensure_ascii=False)}. Evita repetir: {[r['titulo'] for r in estado_titulos(estado, cid)]}. Sé breve.",
        {"ideas": [{"tema": "How a rotary engine works", "dominio": "ingenieria", "visual_sugerido": "iso:motor_abierto", "angulo": "…", "por_que_funcionara": "…"}]},
        presupuesto=presupuesto)

    lista_ideas = ideas.get("ideas") or []
    if not lista_ideas and cands:  # plan B: si Estrategia no decide nada, usa directamente los candidatos ya puntuados por demanda
        print("  (estrategia no devolvió ideas; se usan los candidatos de demanda)")
        lista_ideas = [{"tema": c["tema"], "dominio": c["dominio"], "visual_sugerido": c.get("visual")} for c in cands[:cuenta["publicaciones_por_dia"]]]

    # control de calidad MATEMÁTICO antes de gastar tokens: puntúa y ordena por viabilidad (demanda real - riesgo de veto)
    cands_por_tema = {c["tema"].lower(): c for c in cands}
    lista_ideas.sort(key=lambda i: -_viabilidad(i, cands_por_tema))
    for i in lista_ideas:
        print(f"  viabilidad {_viabilidad(i, cands_por_tema)}: {i.get('tema')}")
    UMBRAL_VIABILIDAD = 0.25
    viables = [i for i in lista_ideas if _viabilidad(i, cands_por_tema) >= UMBRAL_VIABILIDAD]
    if not viables and cands:  # todas las propuestas eran de riesgo alto: cae al candidato más seguro y demandado
        print("  (todas las ideas eran de riesgo alto; se usa el candidato más seguro)")
        viables = [{"tema": cands[0]["tema"], "dominio": cands[0]["dominio"], "visual_sugerido": cands[0].get("visual")}]

    for idea in viables[:cuenta["publicaciones_por_dia"]]:
        gastado_antes = presupuesto.gastado  # para informar del coste de ESTE vídeo (el presupuesto es del día entero)
        feedback, contenido = "", None
        for intento in range(2):
            contenido = of["contenido"].hacer(cuenta,
                f"Crea el guion del vídeo y los textos por plataforma ({', '.join(cuenta['plataformas'])}) para esta idea: "
                f"{json.dumps(idea, ensure_ascii=False)}. {MED if idea.get('dominio') == 'medicina' else ''}Título máx. 36 caracteres, cifra gancho máx. 48 (número impactante), "
                f"narración de 65-80 palabras MÁXIMO (frases cortas; "
                f"ESTRUCTURA tipo @8bitengineering: 1ª frase = CONTEXTO que plantea el problema o la pregunta ('How do you stop a missile with a missile?', "
                f"no empieces directo con la cifra), luego 2-4 pasos muy concretos del mecanismo en orden, cierre invitando a seguir; "
                f"al ritmo de locución el vídeo debe durar 25-32 s en total, así que no te pases de 80 palabras), "
                f"solo datos reales y verificables. {feedback}", CONTENIDO, max_tokens=8000, presupuesto=presupuesto)
            ver = of["calidad"].hacer(cuenta,
                f"Revisa y COMPRUEBA los datos con búsqueda web. Veta si hay datos falsos o dudosos, copyright o gancho flojo. Responde conciso (motivo y correcciones en 1-2 frases): "
                f"{json.dumps(contenido, ensure_ascii=False)}", {"aprobada": True, "motivo": "…", "correcciones": "…"}, max_tokens=6000, presupuesto=presupuesto)
            if ver.get("aprobada"):
                break
            if intento == 0 and presupuesto.agotado():
                print(f"  (idea ya gastó ${presupuesto.gastado:.2f} y Calidad la vetó; mejor probar otra idea que insistir)"); break
            feedback = f"Corrige lo que vetó Calidad: {ver.get('correcciones')}"
        else:
            print("Calidad vetó:", idea.get("tema")); continue
        if not ver.get("aprobada"):
            print("Calidad vetó:", idea.get("tema")); continue

        esc, sprites = arte.producir_escena(cuenta, contenido, of, pista=idea.get('visual_sugerido'), presupuesto=presupuesto)
        plats = of["publicacion"].hacer(cuenta,
            f"Adapta títulos, captions y hashtags al formato de cada plataforma: {json.dumps(contenido.get('plataformas'), ensure_ascii=False)}",
            CONTENIDO, max_tokens=4000, presupuesto=presupuesto).get("plataformas") or contenido["plataformas"]
        print(f"  [coste de este vídeo] ${presupuesto.gastado - gastado_antes:.3f} (acumulado del día: ${presupuesto.gastado:.3f})")

        # montaje del vídeo: voz + animación + música
        carpeta = f"videos/{cid}"; os.makedirs(carpeta, exist_ok=True)
        base = f"{carpeta}/{int(time.time()*1000)}_{os.getpid()}"
        mp3 = voz.sintetizar(esc.get("narracion") or contenido["narracion"], base + ".mp3", cuenta.get("voz_edge", "en-US-AndrewNeural"))
        ruta = motor2.renderizar(esc, base + ".mp4", mp3, sprites)
        print("Vídeo:", ruta)

        usadas = {}
        for p in plats:
            plat = p.get("plataforma")
            if plat not in cuenta["plataformas"] or plat not in PUBLICADORES:
                continue
            h = elegir_hora(estado, cid, plat, excluir=usadas.setdefault(plat, set()))
            usadas[plat].add(h)
            estado.encolar(cid, plat, proxima_ocurrencia(h, tz), {**p, "dominio": idea.get("dominio"), "tema": idea.get("tema"), "video_path": ruta, "titulo": p.get("titulo") or contenido.get("titulo"), "hora": h})
            print(f"  cola: {plat} a las {h}:00")

    # comunidad + analítica -> informe para el CEO de mañana
    plan, _ = estado.ultima_nota(cid, "plan_comunidad")
    informe = of["analitica"].hacer(cuenta,
        f"Con estos datos reales {json.dumps(rend, ensure_ascii=False)} interpreta qué está funcionando, qué hora/formato/tema rinde más "
        f"y propón 2 experimentos A/B para mañana. Sé breve.",
        {"hallazgos": ["…"], "experimentos": [{"hipotesis": "…", "variante_a": "…", "variante_b": "…"}]}, presupuesto=presupuesto)
    estado.nota(cid, "informe_analitica", informe)
    print(f"  [coste total del día] ${presupuesto.gastado:.3f} en {presupuesto.llamadas} llamadas (objetivo ${presupuesto.limite:.2f}/vídeo, freno de emergencia a ${presupuesto.limite_duro:.2f})")

def estado_titulos(estado, cid):
    return [{"titulo": t} for _, _, _, _, _, _, t, _ in estado.publicaciones(cid)[:30]]

def publicar_pendientes(config, estado):
    simular = config.get("modo_simulacion_publicacion", True)
    for id_, cid, plat, datos in estado.pendientes(time.time()):
        try:
            res = PUBLICADORES[plat](cid, datos, simular)
        except Exception as e:
            res = {"ok": False, "respuesta": str(e)}
        if res.get("ok"):
            estado.registrar_publicacion(cid, plat, res.get("id"), datos.get("hora", 0), datos.get("titulo"), datos.get("caption"), datos.get("dominio"), datos.get("tema"))
            estado.marcar(id_, "publicada")
            print(f"[publicado] {cid}/{plat}: {datos.get('titulo')} ({res.get('ruta') or res.get('id')})")
        else:
            estado.marcar(id_, "error")
            print(f"[ERROR publicando] {cid}/{plat}: {res.get('respuesta')}")
        _limpiar_video_si_ya_no_hace_falta(estado, cid, datos.get("video_path"))

def _limpiar_video_si_ya_no_hace_falta(estado, cid, video_path):
    """Un mismo vídeo se encola para varias plataformas; solo se borra del disco (y así del próximo commit)
    cuando YA NINGUNA fila pendiente lo necesita, para no acumular vídeos para siempre en el repo."""
    if not video_path or not os.path.exists(video_path):
        return
    for _, c, _, d in estado.pendientes(float("inf")):
        if c == cid and d.get("video_path") == video_path:
            return  # todavía lo necesita otra plataforma
    try:
        os.remove(video_path)
    except OSError:
        pass
