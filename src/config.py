"""
Configuración del bot: API, Ollama, endpoints y prompts.
"""

API_BASE = "http://127.0.0.1:7719"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen3-vl:8b"

# Endpoints para cartas/paquetes. Ajusta al esquema real de la API de la práctica.
MAILBOX_ENDPOINT = f"{API_BASE}/buzon"
LETTER_ENDPOINT = f"{API_BASE}/carta"
PACKAGE_ENDPOINT = f"{API_BASE}/paquete"

GOLD_RESOURCE_NAME = "oro"