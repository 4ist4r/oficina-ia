"""Narración: OpenAI TTS si hay OPENAI_API_KEY; si no, edge-tts (gratis). Devuelve ruta mp3 o None."""
import asyncio, os, requests

def sintetizar(texto, salida, voz_edge="es-ES-AlvaroNeural", voz_openai="onyx"):
    os.makedirs(os.path.dirname(salida) or ".", exist_ok=True)
    if os.getenv("OPENAI_API_KEY"):
        try:
            r = requests.post("https://api.openai.com/v1/audio/speech",
                headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                json={"model": "gpt-4o-mini-tts", "voice": voz_openai, "input": texto,
                      "instructions": "Narrador de divulgación: claro, serio y con asombro contenido."}, timeout=120)
            r.raise_for_status()
            open(salida, "wb").write(r.content)
            return salida
        except Exception as e:
            print("[voz] OpenAI falló:", e)
    try:
        import edge_tts
        asyncio.run(edge_tts.Communicate(texto, voz_edge).save(salida))
        return salida
    except Exception as e:
        print("[voz] edge-tts falló (vídeo solo con música):", e)
        return None
