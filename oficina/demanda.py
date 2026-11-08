"""Gestor de demanda: decide QUÉ publicar según lo que el público realmente busca y pide.
Señales: (1) interés real en Wikipedia (API pública gratis, sin clave), (2) rendimiento propio por dominio/tema,
(3) peticiones en comentarios, (4) tendencia (7 días vs 30 días). Incluye exploración para probar dominios poco medidos."""
import json, math, time
from datetime import datetime, timedelta
import requests
from .temas import catalogo, DOMINIOS
from .horarios import puntuacion

UA = {"User-Agent": "oficina-ia/1.0 (analisis de demanda de temas)"}
COOLDOWN_DIAS = 45

def _views(estado, wiki):
    clave = f"wiki:{wiki}"
    datos, ts = estado.ultima_nota("_global", clave)
    if datos and time.time() - ts < 20 * 3600:
        return datos
    fin = datetime.utcnow() - timedelta(days=1); ini = fin - timedelta(days=29)
    url = (f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{wiki}/daily/"
           f"{ini:%Y%m%d}/{fin:%Y%m%d}")
    try:
        r = requests.get(url, headers=UA, timeout=15)
        v = [i["views"] for i in r.json()["items"]]
        res = {"m30": sum(v) / max(1, len(v)), "m7": sum(v[-7:]) / max(1, len(v[-7:]))}
        estado.nota("_global", clave, res)
        return res
    except Exception:
        return None

def _rend_dominio(estado, cuenta):
    """Recompensa media normalizada por dominio (a partir de las métricas propias) y nº de muestras."""
    filas = []
    for pid, _, plat, _, ts, _, titulo, _ in estado.publicaciones(cuenta):
        m = estado.ultima_metrica(pid)
        d = estado.q("select dominio, tema from publicaciones where id=?", (pid,)).fetchone()
        if m and d and d[0]:
            filas.append((d[0], d[1], puntuacion(m)))
    mx = max([f[2] for f in filas] or [1]) or 1
    dom, tem = {}, {}
    for d, t, s in filas:
        dom.setdefault(d, []).append(s / mx); tem.setdefault(t, []).append(s / mx)
    return dom, tem

def peticiones(estado, dias=30):
    desde = time.time() - dias * 86400
    cuenta = {}
    for tema, dom in estado.q("select lower(tema), dominio from peticiones where ts>=?", (desde,)).fetchall():
        k = tema.strip()
        cuenta[k] = cuenta.get(k, 0) + 1
    return sorted(cuenta.items(), key=lambda kv: -kv[1])

def candidatos(estado, cuenta_id, dominios=None, n=8, max_por_dominio=2):
    cat = [t for t in catalogo() if not dominios or t["dominio"] in dominios]
    publicados = {r[0] for r in estado.q("select tema from publicaciones where tema is not null and ts>=?", (time.time() - COOLDOWN_DIAS * 86400,)).fetchall()}
    dom_r, tem_r = _rend_dominio(estado, cuenta_id)
    pet = dict(peticiones(estado))
    vistas = {t["wiki"]: _views(estado, t["wiki"]) for t in cat if t["tema"] not in publicados}
    mx = max([math.log1p(v["m30"]) for v in vistas.values() if v] or [1]) or 1
    N = sum(len(v) for v in dom_r.values())
    res = []
    for t in cat:
        if t["tema"] in publicados: continue
        v = vistas.get(t["wiki"])
        interes = math.log1p(v["m30"]) / mx if v else .5
        tend = min(1.0, max(0.0, ((v["m7"] / max(1, v["m30"])) - .6) / 1.2)) if v else .5
        obs = dom_r.get(t["dominio"], [])
        n_d = len(obs) + 1
        propio = ((.5 + sum(obs)) / n_d) + .25 * math.sqrt(math.log(N + 2) / n_d)   # media + exploración (UCB)
        votos = max([c for k, c in pet.items() if k and (k in t["tema"].lower() or t["tema"].lower() in k)] or [0])
        pe = min(1.0, votos / 3)
        score = .38 * interes + .14 * tend + .28 * min(1.0, propio) + .20 * pe
        res.append({**t, "score": round(score, 3), "interes_wiki": round(v["m30"]) if v else None, "tendencia": round(tend, 2), "votos": votos})
    res.sort(key=lambda r: -r["score"])
    out, cont = [], {}
    for r in res:
        if cont.get(r["dominio"], 0) >= max_por_dominio: continue
        out.append(r); cont[r["dominio"]] = cont.get(r["dominio"], 0) + 1
        if len(out) >= n: break
    return out

def resumen_dominios(estado, cuenta_id):
    dom_r, _ = _rend_dominio(estado, cuenta_id)
    return {d: {"publicaciones_medidas": len(v), "rendimiento_medio": round(sum(v) / len(v), 2)} for d, v in dom_r.items()}
