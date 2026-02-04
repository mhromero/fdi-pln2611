"""
Utilidades sobre el estado del juego: inventario, objetivo, necesidades y excedentes.
"""

from typing import Any, Dict, Tuple


def extract_game_state(info: Dict[str, Any]) -> Tuple[str, Dict[str, int], Dict[str, int]]:
    """
    Extrae alias, inventario y recursos objetivo desde la respuesta de /info.
    Intenta ser robusto ante distintas claves.
    """
    alias = info.get("Alias") or info.get("alias")
    if not alias:
        raise ValueError("No se ha encontrado el alias en la respuesta de /info")

    inventario = (
        info.get("inventario")
        or info.get("inventory")
        or info.get("recursos")
        or {}
    )
    objetivo = (
        info.get("objetivo")
        or info.get("objetivos")
        or info.get("target")
        or {}
    )

    if not isinstance(inventario, dict) or not isinstance(objetivo, dict):
        raise ValueError("Los campos de inventario/objetivo no tienen el formato esperado (dict)")

    return (
        alias,
        {k: int(v) for k, v in inventario.items()},
        {k: int(v) for k, v in objetivo.items()},
    )


def compute_needs_and_surplus(
    inventario: Dict[str, int], objetivo: Dict[str, int]
) -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    Calcula:
    - needs: recursos que nos faltan para el objetivo.
    - surplus: recursos que nos sobran (incluidos los que no están en el objetivo).
    """
    needs: Dict[str, int] = {}
    surplus: Dict[str, int] = {}

    for recurso, objetivo_cant in objetivo.items():
        actual = inventario.get(recurso, 0)
        if objetivo_cant > actual:
            needs[recurso] = objetivo_cant - actual
        elif actual > objetivo_cant:
            surplus[recurso] = actual - objetivo_cant

    for recurso, actual in inventario.items():
        if recurso not in objetivo and actual > 0:
            surplus[recurso] = surplus.get(recurso, 0) + actual

    return needs, surplus


def has_reached_objective(
    inventario: Dict[str, int], objetivo: Dict[str, int]
) -> bool:
    for recurso, objetivo_cant in objetivo.items():
        if inventario.get(recurso, 0) < objetivo_cant:
            return False
    return True
