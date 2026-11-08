"""Autoriza la subida a YouTube una vez por cuenta. Uso: python autorizar_youtube.py cuenta1
Necesitas client_secret.json (Google Cloud -> API YouTube Data v3 -> credenciales OAuth tipo 'Aplicación de escritorio')."""
import os, sys
from google_auth_oauthlib.flow import InstalledAppFlow
cid = sys.argv[1]
flujo = InstalledAppFlow.from_client_secrets_file("client_secret.json", ["https://www.googleapis.com/auth/youtube.upload"])
cred = flujo.run_local_server(port=0)
os.makedirs("credenciales", exist_ok=True)
open(f"credenciales/{cid}_youtube.json", "w").write(cred.to_json())
print("Listo:", f"credenciales/{cid}_youtube.json")
