"""Elige la hora de publicación con datos propios: bandido UCB1 sobre horas locales.
Cada publicación medida a +20h aporta una recompensa (rendimiento relativo) a su hora."""
import math, time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PRIOR = {  # prior suave por plataforma (horas locales con más actividad típica); los datos lo sustituyen
    "tiktok": {12: .5, 13: .5, 19: .7, 20: .8, 21: .8, 22: .6},
    "instagram": {12: .5, 13: .5, 18: .6, 19: .7, 20: .7, 21: .6},
    "youtube": {14: .5, 15: .6, 17: .6, 18: .7, 19: .7, 20: .6},
    "facebook": {9: .5, 13: .6, 19: .7, 20: .7, 21: .6},
}

def puntuacion(m):
    vistas, likes, coment, comp, seg = m[:5]
    return (vistas + 5 * likes + 10 * coment + 15 * comp) / max(seg or 0, 100)

def estadisticas(estado, cuenta, plat):
    """{hora: [recompensas]} con recompensa normalizada [0,1] por el máximo de la cuenta/plataforma."""
    datos = []
    for pid, c, p, _, ts, hora, *_ in estado.publicaciones(cuenta):
        if p != plat:
            continue
        m = estado.ultima_metrica(pid)
        if m and m[5] - ts >= 20 * 3600:
            datos.append((hora, puntuacion(m)))
    if not datos:
        return {}
    mx = max(s for _, s in datos) or 1
    res = {}
    for h, s in datos:
        res.setdefault(h, []).append(s / mx)
    return res

def elegir_hora(estado, cuenta, plat, excluir=(), ventana=range(8, 24)):
    est = estadisticas(estado, cuenta, plat)
    online, _ = estado.ultima_nota(cuenta, f"online_{plat}")
    total = sum(len(v) for v in est.values()) + 1
    mejor, mejor_s = None, -1
    for h in ventana:
        if h in excluir:
            continue
        prior = PRIOR[plat].get(h, 0.15)
        if online and str(h) in online:
            mx = max(online.values()) or 1
            prior = max(prior, online[str(h)] / mx)
        obs = est.get(h, [])
        n = len(obs) + 1  # el prior cuenta como 1 observación
        media = (prior + sum(obs)) / n
        s = media + 0.35 * math.sqrt(math.log(total + 1) / n)
        if s > mejor_s:
            mejor, mejor_s = h, s
    return mejor

def proxima_ocurrencia(hora, tz, min_antes=5):
    z = ZoneInfo(tz); ahora = datetime.now(z)
    t = ahora.replace(hour=hora, minute=0, second=0, microsecond=0)
    if t < ahora + timedelta(minutes=min_antes):
        t += timedelta(days=1)
    return t.timestamp()

def tabla_horas(estado, cuenta, plat):
    return {h: round(sum(v) / len(v), 2) for h, v in sorted(estadisticas(estado, cuenta, plat).items())}
