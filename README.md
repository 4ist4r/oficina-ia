# Oficina de IA para redes (TikTok, Instagram, YouTube, Facebook)

Ver `CREDENCIALES.md` para lo que necesitas. Arranque:
1. `pip install -r requirements.txt`
2. Pon `ANTHROPIC_API_KEY`.
3. Edita `config.json` (cuentas, marca, dominios, `zona_audiencia`).
4. Prueba sin publicar: `python main.py` (con `modo_simulacion_publicacion: true`, los vídeos quedan en `outbox/`). Revísalos 2-3 días.
5. Real: pon `modo_simulacion_publicacion: false` y `python main.py --demonio`.

## Qué hace sola, cada día
CEO → **Gestor de demanda** elige temas (interés real en Wikipedia, tendencia, rendimiento propio por dominio, peticiones de los comentarios, exploración de dominios nuevos) → Contenido (guion, en inglés) → Calidad (comprueba datos con búsqueda web; en medicina veta consejos clínicos) → Director visual diseña la escena → Artista de píxeles dibuja sprites → Crítico visual MIRA los fotogramas y pide correcciones → voz + música 8-bit + vídeo 1080x1920 → cola → publica a la mejor hora (optimizada con tus métricas, en la zona horaria de la audiencia) → mide, responde comentarios y aprende.

## Biblioteca visual
- 3D isométrico (voxels que giran): brazo_robotico, dron, rover, motor_abierto, tren_engranajes, aerogenerador, grua, noria, cinta, cohete, satelite, estacion_espacial, atomo, adn, virus, volcan, molecula_agua. Más: Claude compone modelos con formas (caja, cilindro, esfera, cono, engranaje, hélice, barra, anillo, emisor).
- 2D alta definición: engranajes, pistón, rotor Wankel, turbina, flujo, resorte, ondas, circuito, órbitas, levas, corazón, neurona, pulmones, péndulo.
- Sprites ilimitados dibujados por Claude (se guardan en `sprites/`).
- Catálogo base de 75 temas en `oficina/temas.py` (robótica, ingeniería, espacio, ciencia, medicina); Estrategia puede añadir otros por búsqueda web.

## Coste y control
~15 llamadas a Claude por vídeo (3 con imágenes; Opus solo para sprites nuevos, que se reutilizan). Controla el gasto con `publicaciones_por_dia` y mira el consumo en console.anthropic.com.

## Limitaciones
- Las APIs de publicación no se han probado con cuentas reales; TikTok y YouTube publican en privado hasta ser auditadas.
- La calidad de los modelos 3D/sprites inventados por Claude varía; el crítico visual ayuda, pero revisa los primeros días.
- Las métricas de TikTok son aproximadas. Ninguna cifra de seguidores está garantizada.
