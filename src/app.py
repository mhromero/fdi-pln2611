"""
Lógica principal del bot: flujo de negociación (main) y flujo legacy.
"""

import json
from typing import Any, Dict

from . import api
from .game_state import (
    compute_needs_and_surplus,
    extract_game_state,
    has_reached_objective,
)
from .letters import (
    analizar_carta,
    build_status_letter,
    generar_plan,
)
from .trader import handle_offer, handle_confirmation


def main() -> None:
    """
    Flujo de negociación:
    1) Leer /info (alias, inventario, objetivo).
    2) Enviar a todos una carta preescrita con lo que tenemos y necesitamos.
    3) Leer buzón, analizar cada carta con el LLM y actuar (ofertas/confirmaciones).
    4) Si cambian nuestros recursos, reenviar carta de estado actualizada.
    """
    print("→ Obteniendo nuestros recursos (/info)...")
    info = api.get_info()
    print(json.dumps(info, ensure_ascii=False, indent=2))

    alias, inventario, objetivo = extract_game_state(info)
    print(f"Alias: {alias}")
    print("Inventario inicial:", inventario)
    print("Objetivo de recursos:", objetivo)

    print("→ Obteniendo agentes (/gente)...")
    people = api.remove_myself(info, api.get_people())
    print("Otros agentes:", people)

    needs, surplus = compute_needs_and_surplus(inventario, objetivo)

    print("Necesitamos:", needs)
    print("Podemos ofrecer (incluido oro, aunque luego lo filtraremos al enviar):", surplus)

    carta_estado = build_status_letter(alias, inventario, objetivo, needs, surplus)
    print(carta_estado)
    
    for p in people:
        try:
            print(f"→ Enviando carta de estado a {p}...")
            api.send_letter(p, carta_estado)
        except Exception as e:
            print(f"ERROR enviando carta a {p}: {e}")

    if has_reached_objective(inventario, objetivo):
        print("Ya hemos alcanzado el 100% de los recursos objetivo. No es necesario negociar más.")
        return


    print("→ Leyendo cartas del buzón...")
    try:
        mailbox = info["Buzon"]
    except Exception as e:
        print("ERROR leyendo buzón:", e)
        mailbox = []

    print(mailbox)

    recursos_cambiaron = False

    for id, content in zip(mailbox.keys(), mailbox.values()):
        print("===================================")
        print("Carta recibida (cruda):")
        print(json.dumps(content, ensure_ascii=False, indent=2))

        analisis = analizar_carta(content, needs, surplus)

        print("Análisis LLM de la carta:")
        print(json.dumps(analisis, ensure_ascii=False, indent=2))

        tipo = analisis.get("tipo", "otro")

        _, inventario, objetivo = extract_game_state(api.get_info())
        needs, surplus = compute_needs_and_surplus(inventario, objetivo)

        if tipo == "oferta":
            remitente = content.get("remi")
            if not remitente:
                print("Oferta sin remitente claro, se ignora.")
                continue
            recursos_cambiaron |= handle_offer(remitente, analisis, needs, surplus, inventario)

        elif tipo == "confirmacion":
            remitente = content.get("remi")
            if not remitente:
                print("Confirmación sin remitente claro, se ignora.")
                continue
            recursos_cambiaron |= handle_confirmation(remitente, analisis, inventario, needs)
