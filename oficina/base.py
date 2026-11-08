import json
from .llm import pedir_json, MODELO_JEFE, MODELO_RAPIDO

class Agente:
    def __init__(self, nombre, rol, jefe=False, web=False, modelo=None):
        self.nombre, self.rol, self.web = nombre, rol, web
        self.modelo = modelo or (MODELO_JEFE if jefe else MODELO_RAPIDO)

    def hacer(self, cuenta, tarea, ejemplo, imagenes=None, max_tokens=3000, presupuesto=None):
        system = (f"Eres {self.nombre}: {self.rol}. Trabajas en una oficina de IA con jerarquía que "
                  f"hace crecer cuentas de redes sociales hasta 100.000+ seguidores de forma orgánica "
                  f"y autónoma. Cuenta: nicho='{cuenta['nicho']}', idioma={cuenta['idioma']}, "
                  f"tono='{cuenta['tono']}'. Estilo visual/formato obligatorio: {cuenta.get('estilo','libre')}. Todo texto de cara al público (títulos, narración, captions, hashtags, respuestas) va en el idioma '{cuenta['idioma']}' (en = inglés americano natural, audiencia de EE. UU./Reino Unido/global). Sé concreto, original y cumple las normas de cada plataforma "
                  f"(sin copyright ajeno, sin spam, sin desinformación).")
        return pedir_json(system, tarea, ejemplo, self.modelo, web=self.web, imagenes=imagenes, max_tokens=max_tokens, presupuesto=presupuesto)

class Departamento:
    """El director coordina: el equipo propone, el director consolida y decide."""
    def __init__(self, nombre, director, equipo):
        self.nombre, self.director, self.equipo = nombre, director, equipo

    def ejecutar(self, cuenta, tarea, ejemplo, max_tokens=3000, presupuesto=None):
        aportes = {a.nombre: a.hacer(cuenta, tarea, ejemplo, max_tokens=max_tokens, presupuesto=presupuesto) for a in self.equipo}
        return self.director.hacer(
            cuenta,
            f"{tarea}\n\nAportes de tu equipo:\n{json.dumps(aportes, ensure_ascii=False)}\n"
            f"Consolida, corrige y entrega el resultado final.", ejemplo, max_tokens=max_tokens, presupuesto=presupuesto)
