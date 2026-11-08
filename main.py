import argparse, json, time
from datetime import datetime
from zoneinfo import ZoneInfo
from oficina.analitica import medir, online_ig
from oficina.ciclo import produccion_dia, publicar_pendientes
from oficina.comunidad import responder_comentarios
from oficina.estado import Estado
from oficina.organigrama import crear_oficina

def main():
    ap = argparse.ArgumentParser(description="Oficina de IA para redes sociales")
    ap.add_argument("--demonio", action="store_true", help="funcionar sin parar (producir al día, publicar a su hora, medir, responder)")
    ap.add_argument("--cuenta", help="solo esta cuenta (id)")
    ap.add_argument("--forzar", action="store_true", help="produce ahora aunque ya se haya producido hoy")
    ap.add_argument("--sin-panel", action="store_true", dest="sin_panel", help="no mide métricas ni responde comentarios (solo producción)")
    a = ap.parse_args()
    cfg = json.load(open("config.json", encoding="utf-8"))
    cuentas = [c for c in cfg["cuentas"] if not a.cuenta or c["id"] == a.cuenta]
    estado, of = Estado(), crear_oficina()
    tz = ZoneInfo(cfg.get("zona_horaria", "Europe/Madrid"))
    ultima_medicion = 0
    while True:
        hoy = datetime.now(tz).strftime("%Y-%m-%d")
        for c in cuentas:  # 1 vez al día: producir y programar
            fecha, _ = estado.ultima_nota(c["id"], "produccion")
            if fecha != hoy or a.forzar:
                try:
                    produccion_dia(c, cfg, estado, of)
                    estado.nota(c["id"], "produccion", hoy)
                except Exception as e:
                    print(f"[ERROR producción {c['id']}] {e}")
        publicar_pendientes(cfg, estado)           # publica lo que ya toca
        if not a.sin_panel and time.time() - ultima_medicion > 3600:   # cada hora: métricas + comentarios
            ultima_medicion = time.time()
            medir(estado, cuentas); online_ig(estado, cuentas)
            for c in cuentas:
                try:
                    responder_comentarios(estado, c, of)
                except Exception as e:
                    print(f"[ERROR comunidad {c['id']}] {e}")
        if not a.demonio:
            break
        time.sleep(60)

if __name__ == "__main__":
    main()
