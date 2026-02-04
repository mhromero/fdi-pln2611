"""
Persistencia de deudas (quién nos debe qué) en JSON local.
"""

import json
import os
from typing import Any, Dict

from .config import DEBT_FILE


def load_debts() -> Dict[str, Any]:
    """
    Carga deudas pendientes desde un JSON local.
    Formato: { "alias1": [ {"enviados": {...}, "esperados": {...} }, ... ], ... }
    """
    if not os.path.exists(DEBT_FILE):
        return {}
    try:
        with open(DEBT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_debts(debts: Dict[str, Any]) -> None:
    try:
        with open(DEBT_FILE, "w", encoding="utf-8") as f:
            json.dump(debts, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print("ERROR guardando deudas:", e)


def record_debt(alias: str, sent: Dict[str, int], expected: Dict[str, int]) -> None:
    debts = load_debts()
    lista = debts.get(alias, [])
    lista.append({"enviados": sent, "esperados": expected})
    debts[alias] = lista
    save_debts(debts)


def clear_debts_for(alias: str) -> None:
    debts = load_debts()
    if alias in debts:
        del debts[alias]
        save_debts(debts)
