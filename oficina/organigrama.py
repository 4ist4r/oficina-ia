from .base import Agente, Departamento
from .llm import MODELO_ARTE

def crear_oficina():
    A = Agente
    return {
        # Nivel 1
        "ceo": A("CEO", "Director General: fija objetivos y estrategia por cuenta, lee informes y decide cambios de rumbo", jefe=True),
        # Nivel 2: departamentos (director + equipo)
        "estrategia": Departamento("Estrategia y Tendencias",
            A("Dir. Estrategia", "gestor de DEMANDA: decide qué temas atacar hoy según lo que el público más busca y pide (robótica, ingeniería, espacio, ciencia, medicina)", jefe=True),
            # sin búsqueda web: la demanda real (Wikipedia + rendimiento propio) ya la calcula oficina/demanda.py gratis;
            # la búsqueda web aquí salía muy cara (contenido de las páginas encontradas) para poco beneficio real
            [A("Investigador de tendencias", "detecta temas, sonidos y formatos virales en TikTok/IG/YouTube/Facebook, a partir de los datos de demanda que te pasan"),
             A("Analista de competencia", "estudia qué temas funcionan en el nicho y qué huecos hay, a partir de los datos de demanda que te pasan")]),
        "contenido": Departamento("Contenido",
            A("Dir. Contenido", "dirige guionistas y redactores; garantiza ganchos y retención", jefe=True),
            [A("Guionista", "escribe guiones de vídeo corto con gancho, desarrollo y cierre con llamada a la acción"),
             A("Redactor SEO", "escribe títulos, descripciones, captions y hashtags optimizados por plataforma")]),
        # Producción visual: director + artista de píxeles + crítico que MIRA los fotogramas renderizados
        "director_visual": A("Director visual", "diseñas la escena animada pixel-art: eliges componentes, sprites, cámara, eventos y los sincronizas con la narración para máxima retención", jefe=True),
        "artista": A("Artista de píxeles", "dibujas sprites pixel-art 8-bit nítidos y expresivos, con siluetas claras y sombreado de 3-4 tonos", modelo=MODELO_ARTE),
        "critico": A("Crítico visual", "miras fotogramas renderizados y evalúas con ojo exigente: legibilidad, composición, ritmo, errores visuales; propones correcciones concretas", jefe=True),
        "publicacion": Departamento("Publicación",
            A("Dir. Publicación", "dirige el calendario y la publicación", jefe=True),
            [A("Planificador", "elige la mejor hora y frecuencia por plataforma"),
             A("Adaptador de formato", "adapta una pieza a cada plataforma (ratio, duración, texto)")]),
        "comunidad": Departamento("Comunidad",
            A("Dir. Comunidad", "dirige la interacción con la audiencia", jefe=True),
            [A("Community manager", "responde comentarios y mensajes con la voz de la marca"),
             A("Captador de colaboraciones", "propone colaboraciones y menciones con cuentas afines")]),
        "analitica": Departamento("Analítica y Crecimiento",
            A("Dir. Analítica", "dirige la medición y los experimentos de crecimiento", jefe=True),
            [A("Analista de métricas", "interpreta alcance, retención, seguidores ganados"),
             A("Experimentador", "diseña tests A/B de ganchos, horarios y formatos")]),
        # Nivel 2 transversal: veto de calidad
        "calidad": A("Control de Calidad", "revisa cada pieza antes de publicar: VERIFICA cada dato y cifra (veta si no es comprobable), normas de plataforma, copyright, calidad del gancho; puede vetar (usa búsqueda web para comprobar datos); en MEDICINA veta cualquier diagnóstico, dosis o consejo de tratamiento y exige el aviso 'not medical advice'", jefe=True, web=True),
    }
