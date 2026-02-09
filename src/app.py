"""
Lógica principal del bot: flujo de negociación (main) y flujo legacy.
"""

import json
from typing import Any, Dict

from . import api
from .game_state import State
from .letters import (
    analizar_carta,
    build_status_letter,
    generar_plan,
)
from .trader import handle_offer, handle_confirmation


def main() -> None:
    """
    Flujo de negociación:
    1) Leer /info y construir estado (alias, inventario, objetivo, buzón).
    2) Enviar a todos una carta preescrita con lo que tenemos y necesitamos.
    3) Leer buzón del estado, analizar cada carta y actuar (ofertas/confirmaciones).
    4) Si cambian nuestros recursos, reenviar carta de estado actualizada.
    """
    print("→ Obteniendo nuestros recursos (/info)...")

    state = State(alias="", inventario={}, objetivo={}, needs={}, surplus={}, buzon={})
    state.update()
    
    print(json.dumps(state.to_dict(), ensure_ascii=False, indent=2))
    print(f"Alias: {state.alias}")
    print("Inventario inicial:", state.inventario)
    print("Objetivo de recursos:", state.objetivo)

    print("→ Obteniendo agentes (/gente)...")
    people = api.remove_myself({"Alias": state.alias}, api.get_people())
    print("Otros agentes:", people)

    print("Necesitamos:", state.needs)
    print("Podemos ofrecer (incluido oro, aunque luego lo filtraremos al enviar):", state.surplus)

    carta_estado = build_status_letter(
        state.alias, state.inventario, state.objetivo, state.needs, state.surplus
    )
    print(carta_estado)

    for p in people:
        try:
            print(f"→ Enviando carta de estado a {p}...")
            api.send_letter(p, carta_estado)
        except Exception as e:
            print(f"ERROR enviando carta a {p}: {e}")

    if state.has_reached_objective():
        print("Ya hemos alcanzado el 100% de los recursos objetivo. No es necesario negociar más.")
        return

    print("→ Leyendo cartas del buzón...")
    print(state.buzon)

    recursos_cambiaron = False

    for id_carta, content in state.buzon.items():
        print("===================================")
        print("Carta recibida (cruda):")
        print(json.dumps(content, ensure_ascii=False, indent=2))

        analisis = analizar_carta(content, state.needs, state.surplus)
        print("Análisis LLM de la carta:")
        print(json.dumps(analisis, ensure_ascii=False, indent=2))

        tipo = analisis.get("tipo", "otro")

        state.update()

        if tipo == "oferta":
            remitente = content.get("remi")
            if not remitente:
                print("Oferta sin remitente claro, se ignora.")
                continue
            recursos_cambiaron |= handle_offer(
                remitente, analisis, state.needs, state.surplus, state.inventario
            )

        elif tipo == "confirmacion":
            remitente = content.get("remi")
            if not remitente:
                print("Confirmación sin remitente claro, se ignora.")
                continue
            recursos_cambiaron |= handle_confirmation(
                remitente, analisis, state.inventario, state.needs
            )
