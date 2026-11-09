from .base import Agente
from .llm import MODELO_ARTE

# NOTA DE COSTE: antes cada paso de "oficina" (Estrategia, Contenido, Publicación, Analítica) era un Departamento
# de 3 llamadas (2 del equipo + 1 director que las consolida), y cada una repetía el mismo contexto grande.
# Eso multiplicaba el gasto por 3 sin que se notara en la calidad. Ahora son agentes únicos: menos llamadas,
# mismo trabajo. Donde sí importa el criterio (visión del vídeo, verificación de datos) se queda con Sonnet;
# donde es una tarea más mecánica (elegir de una lista ya puntuada, adaptar texto, leer métricas) se usa Haiku.
def crear_oficina():
    A = Agente
    return {
        "ceo": A("CEO", "Director General: fija objetivos y estrategia por cuenta, lee informes y decide cambios de rumbo. Sé muy breve."),
        "estrategia": A("Dir. Estrategia", "gestor de DEMANDA: elige qué temas atacar hoy de una lista YA puntuada por interés real, tendencia y rendimiento propio. No inventes temas nuevos. Sé breve."),
        "contenido": A("Dir. Contenido", "escribes el guion del vídeo corto (gancho, desarrollo, cierre) y los textos por plataforma; garantiza ganchos y retención", jefe=True),
        # Producción visual: director + artista de píxeles + crítico que MIRA los fotogramas renderizados
        "director_visual": A("Director visual", "diseñas la escena animada pixel-art: eliges componentes, sprites, cámara, eventos y los sincronizas con la narración para máxima retención", jefe=True),
        "artista": A("Artista de píxeles", "dibujas sprites pixel-art 8-bit nítidos y expresivos, con siluetas claras y sombreado de 3-4 tonos", modelo=MODELO_ARTE),
        "critico": A("Crítico visual", "miras fotogramas renderizados y evalúas con ojo exigente: legibilidad, composición, ritmo, errores visuales; propones correcciones concretas", jefe=True),
        "publicacion": A("Dir. Publicación", "adapta títulos, captions y hashtags al formato de cada plataforma. Sé breve."),
        "comunidad": A("Dir. Comunidad", "respondes comentarios y mensajes con la voz de la marca, y extraes peticiones de temas. Sé breve."),
        "analitica": A("Dir. Analítica", "interpretas qué está funcionando (alcance, retención, seguidores) y propones 2 experimentos A/B. Sé breve."),
        # Nivel 2 transversal: veto de calidad
        "calidad": A("Control de Calidad", "revisa cada pieza antes de publicar: VERIFICA cada dato y cifra (veta si no es comprobable), normas de plataforma, copyright, calidad del gancho; puede vetar (usa búsqueda web para comprobar datos); en MEDICINA veta cualquier diagnóstico, dosis o consejo de tratamiento y exige el aviso 'not medical advice'", jefe=True, web=True),
    }
