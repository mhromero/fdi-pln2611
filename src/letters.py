"""
Generación y análisis de cartas: prompts para Ollama y carta de estado.
"""

import json
from typing import Any, Dict

from .config import GOLD_RESOURCE_NAME, PROMPT_BASE
from .ollama_client import ollama


def build_status_letter(
    alias: str,
    inventario: Dict[str, int],
    objetivo: Dict[str, int],
    needs: Dict[str, int],
    surplus: Dict[str, int],
) -> str:
    """
    Carta preescrita que enviamos a todos los jugadores con lo que tenemos,
    lo que necesitamos y lo que podemos ofrecer (sin oro).
    """
    surplus_sin_oro = {k: v for k, v in surplus.items() if k != GOLD_RESOURCE_NAME}
    return f"""
Hola, soy {alias}.

Estos son mis recursos actuales (inventario):
{json.dumps(inventario, ensure_ascii=False, indent=2)}

Estos son mis recursos objetivo:
{json.dumps(objetivo, ensure_ascii=False, indent=2)}

Actualmente necesito (diferencia objetivo - inventario):
{json.dumps(needs, ensure_ascii=False, indent=2)}

Y puedo ofrecer sin que me perjudique (evitando oro):
{json.dumps(surplus_sin_oro, ensure_ascii=False, indent=2)}

El oro es especialmente valioso para mí, solo lo utilizaré como última opción.

Si te interesa intercambiar, por favor propón un trato indicando:
- qué recursos me ofreces y cuántas unidades
- qué recursos quieres a cambio y cuántas unidades
- si me has enviado ya recursos (confirmación de envío)
""".strip()


def analizar_carta(
    carta_dict: Dict[str, Any],
    info: Dict[str, Any],
    objetivo: Dict[str, int],
) -> Dict[str, Any]:
    """
    Usa Ollama para interpretar una carta y devolver un JSON con
    tipo (oferta|confirmacion|otro), oferta, pide, recursos_recibidos.
    """
    prompt = f"""
Eres un asistente que ayuda a interpretar cartas de intercambio de recursos
entre agentes en un juego.

Tu tarea es LEER la carta y devolver un JSON estructurado con esta forma:

{{
  "tipo": "oferta" | "confirmacion" | "otro",
  "oferta": {{
    "recurso": cantidad entero
  }},
  "pide": {{
    "recurso": cantidad entero
  }},
  "recursos_recibidos": {{
    "recurso": cantidad entero
  }}
}}

Donde:
- "tipo" = "oferta" si la carta propone un intercambio (yo te doy X, tú me das Y).
- "tipo" = "confirmacion" si la carta dice que ya nos han enviado recursos.
- "tipo" = "otro" si no encaja claramente en ninguno de los casos.
- "oferta" describe lo que EL OTRO agente nos ofrece.
- "pide" describe lo que EL OTRO agente quiere que le enviemos.
- "recursos_recibidos" son los recursos que el agente afirma que YA nos ha enviado.

IMPORTANTE:
- Devuelve SIEMPRE un JSON VÁLIDO, sin texto adicional.
- Si algún campo no está claro en la carta, devuélvelo como un objeto vacío {{}}.

NUESTRA INFO (/info):
{json.dumps(info, ensure_ascii=False, indent=2)}

NUESTROS OBJETIVOS:
{json.dumps(objetivo, ensure_ascii=False, indent=2)}

CARTA RECIBIDA (como JSON bruto de la API):
{json.dumps(carta_dict, ensure_ascii=False, indent=2)}
"""
    respuesta = ollama(prompt)
    try:
        data = json.loads(respuesta)
        if not isinstance(data, dict):
            raise ValueError("Respuesta no es un dict")
        return data
    except (json.JSONDecodeError, ValueError):
        print("ERROR: Ollama no devolvió JSON válido al analizar carta")
        print(respuesta)
        return {"tipo": "otro", "oferta": {}, "pide": {}, "recursos_recibidos": {}}


def generar_plan(info: Dict[str, Any], people: list, cartas_recibidas: list) -> Dict[str, Any] | None:
    """
    Función legacy: genera un plan (acciones + análisis) con Ollama.
    Se deja por compatibilidad o reutilización del prompt.
    """
    prompt = f"""
NUESTROS RECURSOS:
{json.dumps(info, indent=2)}

AGENTES DISPONIBLES:
{json.dumps(people, indent=2)}

CARTAS RECIBIDAS:
{json.dumps(cartas_recibidas, indent=2)}
""" + PROMPT_BASE

    respuesta = ollama(prompt)
    try:
        return json.loads(respuesta)
    except json.JSONDecodeError:
        print("ERROR: Ollama no devolvió JSON válido")
        print(respuesta)
        return None
