"""
Cliente para Ollama (generación con LLM local).
"""

import requests

from .config import MODEL


def ollama(prompt: str) -> str:
    try:
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
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
