"""Lectura de métricas reales por API. Cada función devuelve {vistas,likes,comentarios,compartidos,seguidores} o None."""
import os, time, requests
from .horarios import puntuacion, tabla_horas

G = "https://graph.facebook.com/v21.0"

def _env(cid, plat, campo="TOKEN"):
    return os.getenv(f"{cid.upper()}_{plat.upper()}_{campo}")

def _ig(cid, post_id):
    tok, ig = _env(cid, "instagram"), _env(cid, "instagram", "USER_ID")
    if not tok:
        return None
    m = {"vistas": 0, "likes": 0, "comentarios": 0, "compartidos": 0}
    mapa = {"views": "vistas", "plays": "vistas", "likes": "likes", "comments": "comentarios", "shares": "compartidos"}
    for met, clave in mapa.items():  # una a una: Meta cambia métricas soportadas con frecuencia
        r = requests.get(f"{G}/{post_id}/insights", params={"metric": met, "access_token": tok}, timeout=30)
        if r.ok and r.json().get("data"):
            m[clave] = max(m[clave], r.json()["data"][0]["values"][0]["value"])
    s = requests.get(f"{G}/{ig}", params={"fields": "followers_count", "access_token": tok}, timeout=30)
    m["seguidores"] = s.json().get("followers_count", 0) if s.ok else 0
    return m

def _fb(cid, post_id):
    tok, page = _env(cid, "facebook"), _env(cid, "facebook", "PAGE_ID")
    if not tok:
        return None
    m = {"vistas": 0, "likes": 0, "comentarios": 0, "compartidos": 0, "seguidores": 0}
    r = requests.get(f"{G}/{post_id}", params={"fields": "views,likes.summary(true),comments.summary(true)", "access_token": tok}, timeout=30)
    if r.ok:
        j = r.json()
        m["vistas"] = j.get("views", 0)
        m["likes"] = j.get("likes", {}).get("summary", {}).get("total_count", 0)
        m["comentarios"] = j.get("comments", {}).get("summary", {}).get("total_count", 0)
    s = requests.get(f"{G}/{page}", params={"fields": "followers_count", "access_token": tok}, timeout=30)
    m["seguidores"] = s.json().get("followers_count", 0) if s.ok else 0
    return m

def _yt(cid, post_id):
    key, canal = _env(cid, "youtube", "API_KEY"), _env(cid, "youtube", "CHANNEL_ID")
    if not key:
        return None
    r = requests.get("https://www.googleapis.com/youtube/v3/videos", params={"part": "statistics", "id": post_id, "key": key}, timeout=30)
    if not r.ok or not r.json().get("items"):
        return None
    st = r.json()["items"][0]["statistics"]
    c = requests.get("https://www.googleapis.com/youtube/v3/channels", params={"part": "statistics", "id": canal, "key": key}, timeout=30)
    subs = int(c.json()["items"][0]["statistics"].get("subscriberCount", 0)) if c.ok and c.json().get("items") else 0
    return {"vistas": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
            "comentarios": int(st.get("commentCount", 0)), "compartidos": 0, "seguidores": subs}

def _tt(cid, post_id):
    tok = _env(cid, "tiktok")
    if not tok:
        return None
    r = requests.post("https://open.tiktokapis.com/v2/video/list/?fields=id,view_count,like_count,comment_count,share_count",
                      headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}, json={"max_count": 20}, timeout=30)
    if not r.ok:
        return None
    vids = r.json().get("data", {}).get("videos", [])
    v = next((x for x in vids if str(x.get("id")) == str(post_id)), None) or (vids[0] if vids else None)  # publish_id != video id: aproximación
    if not v:
        return None
    return {"vistas": v.get("view_count", 0), "likes": v.get("like_count", 0), "comentarios": v.get("comment_count", 0),
            "compartidos": v.get("share_count", 0), "seguidores": 0}

LECTORES = {"instagram": _ig, "facebook": _fb, "youtube": _yt, "tiktok": _tt}

def medir(estado, cuentas):
    """Mide todas las publicaciones de los últimos 14 días."""
    for c in cuentas:
        for pid, cid, plat, post_id, ts, *_ in estado.publicaciones(c["id"], time.time() - 14 * 86400):
            if str(post_id).startswith("sim_"):
                continue
            try:
                m = LECTORES[plat](cid, post_id)
            except Exception as e:
                print(f"[medir {cid}/{plat}] {e}"); m = None
            if m:
                estado.guardar_metricas(pid, m)

def online_ig(estado, cuentas):
    """Horas en que tus seguidores están conectados (si la API lo permite) -> prior del optimizador de horas."""
    for c in cuentas:
        tok, ig = _env(c["id"], "instagram"), _env(c["id"], "instagram", "USER_ID")
        if not tok:
            continue
        try:
            r = requests.get(f"{G}/{ig}/insights", params={"metric": "online_followers", "period": "lifetime", "access_token": tok}, timeout=30)
            if r.ok and r.json().get("data"):
                v = r.json()["data"][0]["values"][-1]["value"]
                estado.nota(c["id"], "online_instagram", {str(h): n for h, n in v.items()})
        except Exception as e:
            print("[online_ig]", e)

def resumen(estado, cuenta, plataformas):
    """Resumen legible para los agentes: mejores/peores publicaciones y rendimiento por hora."""
    filas = []
    for pid, _, plat, _, ts, hora, titulo, _ in estado.publicaciones(cuenta, time.time() - 30 * 86400):
        m = estado.ultima_metrica(pid)
        if m:
            filas.append({"plataforma": plat, "hora": hora, "titulo": titulo, "vistas": m[0], "likes": m[1],
                          "comentarios": m[2], "compartidos": m[3], "seguidores": m[4], "puntuacion": round(puntuacion(m), 2)})
    filas.sort(key=lambda f: f["puntuacion"], reverse=True)
    return {"mejores": filas[:3], "peores": filas[-3:] if len(filas) > 3 else [],
            "rendimiento_por_hora": {p: tabla_horas(estado, cuenta, p) for p in plataformas},
            "seguidores_actuales": {f["plataforma"]: f["seguidores"] for f in filas[::-1] if f["seguidores"]}}
