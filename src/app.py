"""
Lógica principal del bot: flujo de negociación (main) y flujo legacy.
"""

import json
import time

from . import api
from .config import ALIAS
from .game_state import State
from .letters import (
    analizar_carta,
    build_status_letter,
)
from . import logs
from .logs import (
    print_section,
    print_kv,
    print_carta_estado,
    print_carta_cruda,
    print_llm,
    print_error,
    print_bot,
    print_bot_dim,
    print_buzon,
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
    print_section("INICIO DEL BOT")

    # Configuramos nuestro alias según la configuración (doc: POST /alias/{nombre})
    if ALIAS:
        try:
            print_kv("Alias configurado", ALIAS)
            api.set_alias(ALIAS)
        except Exception as e:
            print_error(f"No se pudo configurar el alias '{ALIAS}': {e}")

    print_kv("Acción", "Obteniendo nuestros recursos (/info)")

    state = State(alias="", inventario={}, objetivo={}, needs={}, surplus={}, buzon={})
    state.update()

    print_section("ESTADO INICIAL")
    print_kv("Alias", state.alias)
    print_kv("Inventario inicial", json.dumps(state.inventario, ensure_ascii=False))
    print_kv("Objetivo de recursos", json.dumps(state.objetivo, ensure_ascii=False))

    print_section("AGENTES")
    print_kv("Acción", "Obteniendo agentes (/gente)")
    people = api.remove_myself({"Alias": state.alias}, api.get_people())
    print_kv("Otros agentes", people)

    print_section("NECESIDADES Y EXCEDENTES")
    print_kv("Necesitamos", json.dumps(state.needs, ensure_ascii=False))
    print_kv(
        "Podemos ofrecer (incluido oro, aunque luego lo filtraremos al enviar)",
        json.dumps(state.surplus, ensure_ascii=False),
    )

    carta_estado = build_status_letter(
        state.alias, state.inventario, state.objetivo, state.needs, state.surplus
    )
    print_section("CARTA DE ESTADO A ENVIAR")
    print_carta_estado(carta_estado)

    for p in people:
        try:
            print_kv("Enviando carta de estado a", p, color=logs.GREEN)
            api.send_letter(p, "Estado de recursos", carta_estado)
        except Exception as e:
            print_error(f"al enviar carta a {p}: {e}")

    if state.has_reached_objective():
        print_bot(
            "Ya hemos alcanzado el 100% de los recursos objetivo. "
            "No es necesario negociar más.",
            success=True,
        )
        return

    # 1) Leer buzón una vez (ya está en state.buzon); luego bucle 2–4
    print_section("BUZÓN INICIAL")
    print_kv("Acción", "Leyendo cartas del buzón")
    print_buzon(state.buzon)

    while True:
        # 2) Ordenar cartas por fecha (más antiguas primero)
        sorted_letters = sorted(
            state.buzon.items(),
            key=lambda item: item[1].get("fecha", ""),
        )

        # 3) Procesar de más antigua a más nueva y eliminar del buzón
        for id_carta, content in sorted_letters:
            remitente = content.get("remi", "??")
            asunto = content.get("asunto", "")
            fecha = content.get("fecha", "")

            print_section(f"CARTA RECIBIDA de {remitente}")
            print_kv("ID", id_carta)
            print_kv("Remitente", remitente)
            print_kv("Asunto", asunto)
            print_kv("Fecha", fecha)
            print_carta_cruda(content)

            analisis = analizar_carta(content, state.needs, state.surplus)
            print_section("ANÁLISIS LLM DE LA CARTA")
            print_llm(analisis)

            tipo = analisis.get("tipo", "otro")

            state.update()

            if tipo == "oferta":
                remitente = content.get("remi")
                if not remitente:
                    print_bot("Oferta sin remitente claro, se ignora.", warning=True)
                else:
                    print_kv("Acción", f"Gestionando OFERTA de {remitente}", color=logs.GREEN)
                    handle_offer(
                        remitente, analisis, state.needs, state.surplus, state.inventario
                    )
            elif tipo == "confirmacion":
                remitente = content.get("remi")
                if not remitente:
                    print_bot(
                        "Confirmación sin remitente claro, se ignora.",
                        warning=True,
                    )
                else:
                    print_kv(
                        "Acción",
                        f"Gestionando CONFIRMACIÓN de {remitente}",
                        color=logs.GREEN,
                    )
                    handle_confirmation(
                        remitente, analisis, state.inventario, state.needs
                    )

            print_bot_dim(f"[BOT] Eliminando carta del buzón (id={id_carta})")
            api.delete_letter(id_carta)

        if state.has_reached_objective():
            print_bot(
                "Ya hemos alcanzado el 100% de los recursos objetivo.",
                success=True,
            )
            return

        # 4) No hay cartas (o ya se procesaron): esperar 5 s y volver a leer buzón
        print_section("BUZÓN VACÍO")
        print_bot(
            "Sin cartas en buzón. Esperando 5 s y releyendo buzón...",
            warning=True,
        )
        time.sleep(5)
        state.update()
        print_buzon(state.buzon)
