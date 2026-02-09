"""
Lógica principal del bot: flujo de negociación (main) y flujo legacy.
"""

import json
from typing import Any, Dict

from . import api
from .config import GOLD_RESOURCE_NAME
from .game_state import (
    compute_needs_and_surplus,
    extract_game_state,
    has_reached_objective,
)
from .letters import analizar_carta, build_status_letter, generar_plan
from .trader import analizar_oferta


def legacy_main() -> None:
    """Flujo antiguo: obtener info, gente, generar plan con Ollama e imprimir acciones."""
    print("→ Obteniendo nuestros recursos...")
    info = api.get_info()
    print(info)

    print("→ Obteniendo agentes...")
    people = api.remove_myself(info, api.get_people())
    people = people[:10]
    print(people)

    cartas_recibidas: list = []
    print("→ Generando plan con Ollama...")
    plan = generar_plan(info, people, cartas_recibidas)

    if not plan:
        return

    print("\n=== CARTAS A ENVIAR ===")
    for accion in plan.get("acciones", []):
        print(f"\nPara: {accion['agente']}")
        print(accion["mensaje"])

    print("\n=== ANÁLISIS DE CARTAS RECIBIDAS ===")
    for a in plan.get("analisis_recibidos", []):
        print(a)


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
    
    """
    for p in people:
        try:
            print(f"→ Enviando carta de estado a {p}...")
            api.send_letter(p, carta_estado)
        except Exception as e:
            print(f"ERROR enviando carta a {p}: {e}")
    """
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
            decision = analizar_oferta(analisis, needs, surplus)
            print(decision)

        """
            if not oferta or not pide:
                print("Oferta sin datos claros, se ignora.")
                continue

            oferta_valida = True
            for recurso, cant in oferta.items():
                cant_int = int(cant)
                if needs.get(recurso, 0) <= 0 or cant_int > needs.get(recurso, 0):
                    oferta_valida = False
                    break

            if not oferta_valida:
                print("Oferta no alineada con nuestras necesidades, se rechaza.")
                continue

            puede_enviarse = True
            for recurso, cant in pide.items():
                cant_int = int(cant)
                if recurso == GOLD_RESOURCE_NAME:
                    puede_enviarse = False
                    break
                if needs.get(recurso, 0) > 0:
                    puede_enviarse = False
                    break
                if inventario.get(recurso, 0) < cant_int:
                    puede_enviarse = False
                    break

            if not puede_enviarse:
                print("No podemos/queremos enviar lo que nos piden, se rechaza la oferta.")
                continue

            try:
                print(f"Aceptando oferta de {remitente}. Enviando paquete: {pide}")
                api.send_package(remitente, {k: int(v) for k, v in pide.items()})
                recursos_cambiaron = True
            except Exception as e:
                print(f"ERROR enviando paquete de oferta a {remitente}: {e}")

        elif tipo == "confirmacion":
            recursos_recibidos = analisis.get("recursos_recibidos") or {}
            pide = analisis.get("pide") or {}

            if not recursos_recibidos:
                print("Confirmación sin recursos claros, se ignora.")
                continue

            info_antes = inventario
            nueva_info = api.get_info()
            _, nuevo_inventario, _ = extract_game_state(nueva_info)

            incremento_valido = True
            for recurso, cant in recursos_recibidos.items():
                cant_int = int(cant)
                if nuevo_inventario.get(recurso, 0) < info_antes.get(recurso, 0) + cant_int:
                    incremento_valido = False
                    break

            if not incremento_valido:
                print("No se detecta claramente el incremento de recursos indicado, no hacemos nada.")
                continue

            if not pide:
                print("Confirmación sin recursos a enviar a cambio, se asume regalo.")
                recursos_cambiaron = True
                continue

            total_recibidos = sum(int(v) for v in recursos_recibidos.values())
            total_a_enviar = sum(int(v) for v in pide.values())

            if total_recibidos != total_a_enviar:
                print(f"No enviamos recursos a {remitente}: cantidades no equivalentes.")
                recursos_cambiaron = True
                continue

            needs, surplus = compute_needs_and_surplus(nuevo_inventario, objetivo)

            puede_enviar_conf = True
            for recurso, cant in pide.items():
                cant_int = int(cant)
                if recurso == GOLD_RESOURCE_NAME:
                    print(f"No enviamos oro a {remitente} en confirmación.")
                    puede_enviar_conf = False
                    break
                if needs.get(recurso, 0) > 0:
                    print(f"No enviamos recurso necesario '{recurso}' a {remitente}.")
                    puede_enviar_conf = False
                    break
                if nuevo_inventario.get(recurso, 0) < cant_int:
                    print(f"No tenemos suficientes '{recurso}' para enviar a {remitente}.")
                    puede_enviar_conf = False
                    break

            if not puede_enviar_conf:
                continue

            try:
                print(f"Confirmación correcta de {remitente}. Enviando paquete de vuelta: {pide}")
                api.send_package(remitente, {k: int(v) for k, v in pide.items()})
                recursos_cambiaron = True
            except Exception as e:
                print(f"ERROR enviando paquete de confirmación a {remitente}: {e}")

        else:
            print("Carta clasificada como 'otro', no se realiza ninguna acción automática.")

    if recursos_cambiaron:
        print("→ Nuestros recursos han cambiado, reenviando carta de estado actualizada...")
        info_actualizada = api.get_info()
        alias_act, inventario_act, objetivo_act = extract_game_state(info_actualizada)
        needs_act, surplus_act = compute_needs_and_surplus(inventario_act, objetivo_act)
        carta_estado_act = build_status_letter(
            alias_act, inventario_act, objetivo_act, needs_act, surplus_act
        )
        people_act = api.remove_myself(info_actualizada, api.get_people())
        for p in people_act:
            try:
                print(f"→ Reenviando carta de estado a {p}...")
                api.send_letter(p, carta_estado_act)
            except Exception as e:
                print(f"ERROR reenviando carta a {p}: {e}")
    """
