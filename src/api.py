"""
Llamadas a la API externa: info, gente, cartas y paquetes.
"""

import requests
from typing import Any, Dict

from .config import (
    API_BASE,
    LETTER_ENDPOINT,
    MAILBOX_ENDPOINT,
    PACKAGE_ENDPOINT,
)


def get_info() -> Dict[str, Any]:
    r = requests.get(f"{API_BASE}/info")
    r.raise_for_status()
    return r.json()


def get_people() -> Any:
    r = requests.get(f"{API_BASE}/gente")
    r.raise_for_status()
    return r.json()


def set_alias(nombre: str) -> Any:
    """Configura nuestro alias en el servidor (POST /alias/{nombre})."""
    r = requests.post(f"{API_BASE}/alias/{nombre}")
    r.raise_for_status()
    return r.json()


def remove_myself(info: Dict[str, Any], people: list) -> list:
    """
    Devuelve la lista de agentes sin incluirnos a nosotros mismos.
    Asumimos que people es una lista de alias (strings).
    """
    myself = info.get("Alias") or info.get("alias")
    return [p for p in people if p != myself]


def send_letter(to_alias: str, message: str) -> Any:
    """Envía una carta a otro agente."""
    payload = {
        "alias": to_alias,
        "mensaje": message,
    }
    r = requests.post(LETTER_ENDPOINT, json=payload)
    r.raise_for_status()
    return r.json()


def get_mailbox() -> Any:
    """Obtiene las cartas del buzón."""
    r = requests.get(MAILBOX_ENDPOINT)
    r.raise_for_status()
    return r.json()


def delete_letter(uid: str) -> Any:
    """Elimina una carta del buzón (DELETE /mail/{uid})."""
    r = requests.delete(f"{API_BASE}/mail/{uid}")
    r.raise_for_status()
    return r.json()


def send_package(to_alias: str, resources: Dict[str, int]) -> Any:
    """Envía un paquete de recursos a otro agente."""
    payload = {
        "alias": to_alias,
        "recursos": resources,
    }
    r = requests.post(PACKAGE_ENDPOINT, json=payload)
    r.raise_for_status()
    return r.json()
