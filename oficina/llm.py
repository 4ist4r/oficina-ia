"""Capa única de acceso a Claude. Sin clave -> modo simulado (devuelve el ejemplo)."""
import json, os

MODELO_JEFE = "claude-sonnet-5-5"    # CEO y directores
MODELO_RAPIDO = "claude-haiku-5-5"   # trabajadores
MODELO_ARTE = "claude-opus-5-5"      # artista de píxeles (el dibujo es lo que más rinde)

# $ por millón de tokens (entrada, salida) — console.anthropic.com, nov-2026
PRECIOS = {MODELO_JEFE: (2.0, 10.0), MODELO_RAPIDO: (0.10, 0.50), MODELO_ARTE: (4.0, 20.0)}
PRECIO_BUSQUEDA = 0.01  # $ por búsqueda web

_cliente = None

def simulado():
    return os.getenv("OFICINA_SIMULAR") == "1" or not os.getenv("ANTHROPIC_API_KEY")

class PresupuestoAgotado(Exception):
    """Freno de EMERGENCIA de verdad: para TODO (incluidos CEO/Estrategia, incluso un paso obligatorio)
    en cuanto el gasto real ya pasó el límite duro. Esto NO es el objetivo normal (ver Presupuesto.agotado,
    que solo decide si vale la pena pulir más) — esto es "algo se ha ido de madre, corta ya"."""

class Presupuesto:
    """Gasto real (no estimado) de UNA pieza de contenido, calculado a partir de los tokens que devuelve cada llamada.
    Tiene dos niveles:
      - objetivo (`limite`): decide si vale la pena un reintento o una pasada extra de pulido (ciclo.py/arte.py).
      - límite duro (`limite_duro`, por defecto 3x el objetivo): si se cruza, NINGUNA llamada más se permite
        (ni las obligatorias), para que un fallo real (p.ej. búsqueda web descontrolada) no siga gastando sin fin."""
    def __init__(self, limite_usd=0.5, limite_duro=None):
        self.limite = limite_usd
        self.limite_duro = limite_duro if limite_duro is not None else limite_usd * 3
        self.gastado = 0.0
        self.llamadas = 0

    def agotado(self):
        return self.gastado >= self.limite

    def comprobar_emergencia(self):
        if self.gastado >= self.limite_duro:
            raise PresupuestoAgotado(f"${self.gastado:.3f} gastados, límite duro ${self.limite_duro:.2f} — se para todo")

    def registrar(self, modelo, usage, busquedas=0):
        pin, pout = PRECIOS.get(modelo, (2.0, 10.0))
        ent = getattr(usage, "input_tokens", 0) or 0
        sal = getattr(usage, "output_tokens", 0) or 0
        c = (ent * pin + sal * pout) / 1_000_000 + busquedas * PRECIO_BUSQUEDA
        self.gastado += c; self.llamadas += 1
        return c

def _candidatos_json(txt):
    """Todos los bloques JSON (objeto o lista) que se pueden decodificar en el texto, en orden de aparición."""
    dec = json.JSONDecoder()
    out = []
    for i, ch in enumerate(txt):
        if ch not in "{[":
            continue
        try:
            obj, _ = dec.raw_decode(txt, i)
        except json.JSONDecodeError:
            continue
        out.append(obj)
    return out

def _extraer(txt, ejemplo):
    """Elige, entre los bloques JSON hallados, el que coincide con el tipo del ejemplo
    y, si es un diccionario, el que comparte más claves con él."""
    cands = _candidatos_json(txt)
    elegibles = [c for c in cands if isinstance(c, type(ejemplo))]
    if not elegibles:
        return None   # ningún bloque tiene el tipo esperado (dict/list): mejor reintentar que devolver el tipo equivocado
    if isinstance(ejemplo, dict):
        claves = set(ejemplo.keys())
        elegibles.sort(key=lambda c: (-len(claves & set(c.keys())), -len(c)))
    return elegibles[0]

def pedir_json(system, tarea, ejemplo, modelo=MODELO_RAPIDO, max_tokens=3000, web=False, imagenes=None, presupuesto=None):
    if simulado():
        return json.loads(json.dumps(ejemplo))
    if presupuesto is not None:
        presupuesto.comprobar_emergencia()  # si ya está disparado el freno de emergencia, ni una llamada más
    global _cliente
    if _cliente is None:
        import anthropic
        _cliente = anthropic.Anthropic()
    prompt = (f"{tarea}\n\nResponde SOLO con JSON válido con esta estructura "
              f"(los valores son ejemplos de formato, no los copies):\n"
              f"{json.dumps(ejemplo, ensure_ascii=False, indent=1)}")
    for _ in range(3):
        import base64
        contenido = [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(b).decode()}}
                     for b in (imagenes or [])] + [{"type": "text", "text": prompt}]
        kw = dict(model=modelo, max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": contenido}])
        try:
            if web:  # búsqueda web del servidor de Anthropic: tendencias y comprobación de datos (cara: limitada a 2 búsquedas)
                r = _cliente.messages.create(tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 2}], **kw)
            else:
                r = _cliente.messages.create(**kw)
        except Exception:
            if not web:
                raise
            r = _cliente.messages.create(**kw)
        if presupuesto is not None:
            busquedas = getattr(getattr(r.usage, "server_tool_use", None), "web_search_requests", 0) or 0
            coste = presupuesto.registrar(modelo, r.usage, busquedas)
            print(f"  [coste] {modelo}: +${coste:.4f} (acumulado ${presupuesto.gastado:.3f} / objetivo ${presupuesto.limite:.2f} / duro ${presupuesto.limite_duro:.2f})")
            presupuesto.comprobar_emergencia()  # esta misma llamada puede haber disparado el freno: no reintentes
        txt = "".join(b.text for b in r.content if b.type == "text")
        res = _extraer(txt, ejemplo)
        if res is not None:
            return res
        print(f"[llm] JSON inválido (stop={r.stop_reason}, bloques={[b.type for b in r.content]}), respuesta: {txt[:1500]!r}")
        prompt += "\n\nTu respuesta anterior no era JSON válido. Responde solo JSON."
    raise ValueError("El modelo no devolvió JSON válido")
