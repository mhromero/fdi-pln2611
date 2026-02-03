"""
FLUJO COMPLETO: API + OLLAMA (MULTI-AGENTE)

1) GET /info → obtener nuestros recursos
2) GET /people → obtener todos los agentes
3) Usar Ollama para:
   - decidir qué recursos necesitamos/ofrecemos
   - generar cartas a otros agentes
   - procesar cartas recibidas

REQUISITOS:
- Ollama corriendo en localhost:11434
- Modelo pequeño recomendado
- pip install requests
"""

import requests
import json

# =========================
# CONFIGURACIÓN
# =========================

API_BASE = "http://147.96.81.252:8000"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3-vl:8b"

# =========================
# PROMPT OPTIMIZADO
# =========================

PROMPT_BASE = """
Eres un agente autónomo en un sistema distribuido de intercambio de recursos.

CONTEXTO:
- Tenemos nuestros propios recursos.
- Existe una lista de agentes remotos con los que podemos comunicarnos.
- Podemos enviar y recibir cartas (mensajes de texto).
- El objetivo es maximizar la obtención de recursos que no tenemos y ofrecer los que nos sobran.
- El oro es un resurso valioso no lo uses a menos que sea estrictamente necesario y no nos queden otros recursos que ofrecer.
- Sé amable, justo y persuasivo negociando
- Solicita recursos con urgencia y haciendo ver que te hace mucha falta y haz ofertas beneficiosas para otros siempre que no nos perjudiquen
- Solicita recursos poco a poco 
- Responde a cada carta que te envían si nos inteeresa la oferta y si no no les respondas, y adapta tu oferta a lo que te piden

TAREAS:
1. Analiza nuestros recursos actuales.
2. Analiza la lista de agentes disponibles.
3. Decide qué recursos necesitamos y cuáles podemos ofrecer.
4. Genera cartas claras, educadas, directas y asertivas para cada agente relevante.
5. Analiza las cartas recibidas y decide:
   - aceptar
   - rechazar
   - negociar

FORMATO DE SALIDA (OBLIGATORIO):
Devuelve exclusivamente un JSON válido con esta estructura:

{
  "acciones": [
    {
      "agente": "<id o nombre del agente>",
      "mensaje": "<carta a enviar>"
    }
  ],
  "analisis_recibidos": [
    {
      "agente": "<id del agente>",
      "decision": "aceptar | rechazar | negociar",
      "razon": "<explicación breve>"
    }
  ]
}

REGLAS:
- No inventes recursos.
- Sé conciso.
- Prioriza intercambios beneficiosos.
- Solo da recursos una vez recibidos los solicitados.
- Cuando recibas confirmación de una oferta, envía el recurso. Y envíale una carta de confirmación
- Pregunta los recursos que quieren para ver si puedes ofrecerles algo que quieran, y di lo que necesitas
- Solo haz el trato si hay intercmbio equivalente

"""

# =========================
# OLLAMA
# =========================

def ollama(prompt):
    try:
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        r.raise_for_status()
        return r.json()["response"]

    except requests.exceptions.HTTPError as e:
        print("ERROR HTTP OLLAMA:", r.status_code)
        print(r.text)
        raise

    except requests.exceptions.ConnectionError:
        print("ERROR: Ollama no está corriendo (ollama serve)")
        raise


# =========================
# API EXTERNA
# =========================

def get_info():
    r = requests.get(f"{API_BASE}/info")
    r.raise_for_status()
    return r.json()

def get_people():
    r = requests.get(f"{API_BASE}/gente")
    r.raise_for_status()
    return r.json()

def remove_myself(info, people):
    myself = info.get("Alias")
    return [p for p in people if [p] != myself]


# =========================
# GENERAR CARTAS
# =========================

def generar_plan(info, people, cartas_recibidas):
    prompt = f"""
NUESTROS RECURSOS:
{json.dumps(info, indent=2)}

AGENTES DISPONIBLES:
{json.dumps(people, indent=2)}

CARTAS RECIBIDAS:
{json.dumps(cartas_recibidas, indent=2)}
""" + PROMPT_BASE

    respuesta = ollama(prompt)

    # Parseo seguro del JSON
    try:
        return json.loads(respuesta)
    except json.JSONDecodeError:
        print("ERROR: Ollama no devolvió JSON válido")
        print(respuesta)
        return None

# =========================
# MAIN
# =========================

def main():
    print("→ Obteniendo nuestros recursos...")
    info = get_info()
    print(info)

    print("→ Obteniendo agentes...")
    people = remove_myself(info, get_people())
    

    # Limitar agentes para no matar la VRAM
    people = people[:10]
    print(people)

    cartas_recibidas = []  # aquí irían las cartas que te lleguen
 
    print("→ Generando plan con Ollama...")
    plan = generar_plan(info, people, cartas_recibidas)

    if not plan:
        return

    print("\n=== CARTAS A ENVIAR ===")
    for accion in plan["acciones"]:
        print(f"\nPara: {accion['agente']}")
        print(accion["mensaje"])

    print("\n=== ANÁLISIS DE CARTAS RECIBIDAS ===")
    for a in plan["analisis_recibidos"]:
        print(a)
    

if __name__ == "__main__":
    main()
