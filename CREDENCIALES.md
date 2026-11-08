# Qué necesitas (y cómo conseguirlo)

## Obligatorio
**1. Clave de la API de Claude** → console.anthropic.com → API Keys. Variable de entorno: `ANTHROPIC_API_KEY`.
Sin más cuentas puedes ya generar vídeos completos (modo simulación: se guardan en `outbox/`).

## Para publicar (una cuenta por red; se hace una vez)
**2. Facebook + Instagram (Meta)**
- Instagram en modo **Profesional** (Creador/Empresa) y **vinculado a una Página de Facebook**.
- developers.facebook.com → crear app (tipo Empresa) → añadirte como administrador/tester (con tu propia cuenta no hace falta revisión de Meta).
- Permisos: `instagram_basic`, `instagram_content_publish`, `instagram_manage_comments`, `instagram_manage_insights`, `pages_show_list`, `pages_manage_posts`, `pages_read_engagement`, `pages_manage_engagement`.
- Genera un token de usuario **de larga duración** (dura ~60 días; hay que renovarlo) y anota el ID de la Página y el ID de usuario de Instagram.
- Variables: `CUENTA1_FACEBOOK_TOKEN`, `CUENTA1_FACEBOOK_PAGE_ID`, `CUENTA1_INSTAGRAM_TOKEN`, `CUENTA1_INSTAGRAM_USER_ID`.

**3. YouTube**
- console.cloud.google.com → proyecto → activar **YouTube Data API v3** → credenciales: *ID de cliente OAuth (aplicación de escritorio)* → guarda `client_secret.json` en la carpeta.
- Ejecuta una vez `python autorizar_youtube.py cuenta1` (abre el navegador, inicias sesión con el canal).
- Crea además una **clave de API** (para leer estadísticas y comentarios) y anota el ID del canal.
- Variables: `CUENTA1_YOUTUBE_API_KEY`, `CUENTA1_YOUTUBE_CHANNEL_ID`.
- OJO: los proyectos de API sin auditar publican los vídeos como **privados**. Para que sean públicos hay que pasar la auditoría de Google (formulario de YouTube API Services). Hasta entonces, sube y publícalos tú desde YouTube Studio, o solicita la auditoría.

**4. TikTok**
- developers.tiktok.com → crear app → producto **Content Posting API** (y Login Kit) → permisos `video.publish`/`video.upload` y `video.list`.
- Autoriza tu cuenta y guarda el token de acceso. Variable: `CUENTA1_TIKTOK_TOKEN`.
- OJO: mientras TikTok no audite tu app, los vídeos se publican solo como **privados**. Pide la auditoría; hasta entonces puedes publicarlos tú desde la app (ya están generados).

## Opcional
- `OPENAI_API_KEY`: voz de mayor calidad. Si no, se usa edge-tts (gratis, sin cuenta).

## No necesitan cuenta ni clave
Datos de demanda (Wikipedia pageviews), búsqueda web (la hace Claude), voz edge-tts, música y animación (se generan en tu PC).

## Requisitos del PC
Python 3.10+, `pip install -r requirements.txt`, internet y el PC encendido para el modo `--demonio`.
Windows (PowerShell): `setx ANTHROPIC_API_KEY "sk-ant-..."` y reabre la terminal.
