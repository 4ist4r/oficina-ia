"""Subida de vídeo por plataforma (APIs oficiales). pieza: {titulo, caption, hashtags, video_path}.
Devuelve {"ok": bool, "id": post_id, ...}. En simulación o sin credenciales -> outbox/."""
import json, os, shutil, time, requests

G = "https://graph.facebook.com/v21.0"

def _env(cid, plat, campo="TOKEN"):
    return os.getenv(f"{cid.upper()}_{plat.upper()}_{campo}")

def _texto(p):
    return f"{p.get('caption','')}\n\n{' '.join(p.get('hashtags', []))}".strip()

def _outbox(cid, plat, pieza, motivo):
    os.makedirs("outbox", exist_ok=True)
    base = f"outbox/{cid}_{plat}_{int(time.time())}"
    meta = {k: v for k, v in pieza.items()}
    if pieza.get("video_path") and os.path.exists(pieza["video_path"]):
        shutil.copy(pieza["video_path"], base + ".mp4")
    json.dump({"motivo": motivo, **meta}, open(base + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return {"ok": True, "simulado": True, "id": f"sim_{int(time.time())}", "ruta": base}

def facebook(cid, p, simular):
    tok, page = _env(cid, "facebook"), _env(cid, "facebook", "PAGE_ID")
    if simular or not (tok and page and p.get("video_path")):
        return _outbox(cid, "facebook", p, "simulación o sin credenciales")
    with open(p["video_path"], "rb") as f:
        r = requests.post(f"{G}/{page}/videos", data={"description": _texto(p), "title": p.get("titulo", ""), "access_token": tok},
                          files={"source": f}, timeout=900)
    return {"ok": r.ok, "id": r.json().get("id") if r.ok else None, "respuesta": r.text[:300]}

def instagram(cid, p, simular):
    tok, ig = _env(cid, "instagram"), _env(cid, "instagram", "USER_ID")
    if simular or not (tok and ig and p.get("video_path")):
        return _outbox(cid, "instagram", p, "simulación o sin credenciales")
    r = requests.post(f"{G}/{ig}/media", data={"media_type": "REELS", "upload_type": "resumable",
                      "caption": _texto(p), "access_token": tok}, timeout=60)
    if not r.ok:
        return {"ok": False, "respuesta": r.text[:300]}
    c = r.json(); cont = c["id"]
    uri = c.get("uri") or f"https://rupload.facebook.com/ig-api-upload/v21.0/{cont}"
    size = os.path.getsize(p["video_path"])
    with open(p["video_path"], "rb") as f:
        up = requests.post(uri, headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size)}, data=f, timeout=900)
    if not up.ok:
        return {"ok": False, "respuesta": up.text[:300]}
    for _ in range(40):  # esperar procesado
        st = requests.get(f"{G}/{cont}", params={"fields": "status_code", "access_token": tok}, timeout=30).json()
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") == "ERROR":
            return {"ok": False, "respuesta": str(st)}
        time.sleep(10)
    pub = requests.post(f"{G}/{ig}/media_publish", data={"creation_id": cont, "access_token": tok}, timeout=60)
    return {"ok": pub.ok, "id": pub.json().get("id") if pub.ok else None, "respuesta": pub.text[:300]}

def youtube(cid, p, simular):
    ruta_tok = f"credenciales/{cid}_youtube.json"
    if simular or not (os.path.exists(ruta_tok) and p.get("video_path")):
        return _outbox(cid, "youtube", p, "simulación o sin autorizar (ejecuta autorizar_youtube.py)")
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    yt = build("youtube", "v3", credentials=Credentials.from_authorized_user_file(ruta_tok))
    cuerpo = {"snippet": {"title": (p.get("titulo") or "Short")[:95] + " #Shorts", "description": _texto(p) + "\n#Shorts",
                          "tags": [h.lstrip("#") for h in p.get("hashtags", [])][:15], "categoryId": "27"},
              "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}}
    r = yt.videos().insert(part="snippet,status", body=cuerpo, media_body=MediaFileUpload(p["video_path"], resumable=True)).execute()
    return {"ok": True, "id": r["id"]}

def tiktok(cid, p, simular):
    tok = _env(cid, "tiktok")
    if simular or not (tok and p.get("video_path")):
        return _outbox(cid, "tiktok", p, "simulación o sin credenciales")
    size = os.path.getsize(p["video_path"])
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8"}
    ini = requests.post("https://open.tiktokapis.com/v2/post/publish/video/init/", headers=h, timeout=60, json={
        "post_info": {"title": _texto(p)[:2200], "privacy_level": "PUBLIC_TO_EVERYONE", "disable_duet": False,
                      "disable_comment": False, "disable_stitch": False},
        "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}})
    if not ini.ok or ini.json().get("error", {}).get("code", "ok") != "ok":
        return {"ok": False, "respuesta": ini.text[:300]}
    d = ini.json()["data"]
    with open(p["video_path"], "rb") as f:
        up = requests.put(d["upload_url"], data=f, timeout=900, headers={
            "Content-Type": "video/mp4", "Content-Length": str(size), "Content-Range": f"bytes 0-{size-1}/{size}"})
    return {"ok": up.ok, "id": d["publish_id"], "respuesta": up.text[:200]}

PUBLICADORES = {"facebook": facebook, "instagram": instagram, "youtube": youtube, "tiktok": tiktok}
