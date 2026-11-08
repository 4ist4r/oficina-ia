"""Responde comentarios automáticamente (Instagram y Facebook por API oficial)."""
import os, time, requests
from .analitica import G, _env

def _leer(cid, plat, post_id):
    tok = _env(cid, plat)
    r = requests.get(f"{G}/{post_id}/comments", params={"fields": "id,text,message,from", "limit": 25, "access_token": tok}, timeout=30)
    if not r.ok:
        return []
    return [{"id": c["id"], "texto": c.get("text") or c.get("message") or ""} for c in r.json().get("data", [])]

def _responder(cid, plat, comentario_id, texto):
    tok = _env(cid, plat)
    ruta = "replies" if plat == "instagram" else "comments"
    r = requests.post(f"{G}/{comentario_id}/{ruta}", data={"message": texto, "access_token": tok}, timeout=30)
    return r.ok

def _leer_yt(cid, video_id):
    key = _env(cid, "youtube", "API_KEY")
    r = requests.get("https://www.googleapis.com/youtube/v3/commentThreads", params={"part": "snippet", "videoId": video_id, "maxResults": 50, "key": key}, timeout=30)
    if not r.ok: return []
    return [{"id": i["id"], "texto": i["snippet"]["topLevelComment"]["snippet"].get("textOriginal", "")} for i in r.json().get("items", [])]

def responder_comentarios(estado, cuenta, oficina, max_por_ciclo=30):
    """Lee comentarios recientes (IG/FB/YouTube), responde en IG/FB y extrae PETICIONES de temas para el gestor de demanda."""
    hechos = 0
    for pid, cid, plat, post_id, ts, *_ in estado.publicaciones(cuenta["id"], time.time() - 5 * 86400):
        if str(post_id).startswith("sim_") or plat not in ("instagram", "facebook", "youtube"): continue
        if plat == "youtube" and not _env(cid, "youtube", "API_KEY"): continue
        if plat != "youtube" and not _env(cid, plat): continue
        try:
            coms = _leer_yt(cid, post_id) if plat == "youtube" else _leer(cid, plat, post_id)
        except Exception as e:
            print("[comentarios]", e); continue
        nuevos = [c for c in coms if not estado.q("select 1 from respondidos where comentario_id=?", (c["id"],)).fetchone()]
        if not nuevos: continue
        puede = plat != "youtube"
        dec = oficina["comunidad"].ejecutar(cuenta,
            f"{'Responde a estos comentarios en la voz de la marca (breve, amable, aporta un dato o pregunta que invite a seguir). No respondas a spam, odio ni provocaciones (responder=false). ' if puede else 'NO respondas (responder=false siempre). '}"
            f"Además EXTRAE las peticiones de temas ('haz un vídeo de X', 'how does Y work?') como peticiones con dominio (robotica, ingenieria, espacio, ciencia, medicina). Comentarios: {nuevos}",
            {"respuestas": [{"id": "…", "responder": True, "texto": "…"}], "peticiones": [{"tema": "how do jet engines work", "dominio": "ingenieria"}]})
        for pt in dec.get("peticiones", []) if isinstance(dec, dict) else []:
            if isinstance(pt, dict) and pt.get("tema"):
                estado.q("insert into peticiones(ts,tema,dominio) values(?,?,?)", (time.time(), str(pt["tema"]).lower()[:120], pt.get("dominio")))
        for r in (dec.get("respuestas", []) if isinstance(dec, dict) else []):
            if puede and r.get("responder") and r.get("texto") and hechos < max_por_ciclo and _responder(cid, plat, r["id"], r["texto"]):
                hechos += 1
        for c in nuevos:
            estado.q("insert or ignore into respondidos values(?)", (c["id"],))
