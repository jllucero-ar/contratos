"""
ia_client.py — core/ia_client.py
Cliente unificado para llamadas a IA (Anthropic, OpenAI, Google Gemini).
El proveedor y modelo se configuran en .env.
Reutilizable en todos los proyectos del portfolio.
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

PROVEEDOR = os.getenv("IA_PROVEEDOR", "anthropic").lower()

# Límite de tokens de salida (configurable en .env). 8000 entra en el techo
# de salida de los tres proveedores por defecto (gemini-2.0-flash: 8192).
MAX_TOKENS_DEFAULT = 8000


def _max_tokens_env() -> int:
    try:
        valor = int(os.getenv("IA_MAX_TOKENS", MAX_TOKENS_DEFAULT))
        return valor if valor > 0 else MAX_TOKENS_DEFAULT
    except ValueError:
        return MAX_TOKENS_DEFAULT

# Modelos por defecto por proveedor
MODELOS_DEFAULT = {
    "anthropic": "claude-opus-4-5",
    "openai":    "gpt-4o",
    "gemini":    "gemini-2.0-flash"
}


def llamar_ia(prompt: str, sistema: str = "", max_tokens: int = None) -> dict:
    """
    Llama al proveedor de IA configurado en .env y devuelve la respuesta.

    Args:
        prompt:     mensaje del usuario
        sistema:    instrucción de sistema (rol, formato esperado, etc.)
        max_tokens: límite de tokens en la respuesta (default: IA_MAX_TOKENS de .env)

    Returns:
        dict con:
            - respuesta: string con el texto devuelto por la IA
            - proveedor: nombre del proveedor usado
            - modelo:    nombre del modelo usado
            - truncada:  bool, True si la respuesta se cortó por límite de tokens
            - tokens:    dict {"entrada": int|None, "salida": int|None}
            - exito:     bool
            - error:     str o None
    """
    if max_tokens is None:
        max_tokens = _max_tokens_env()
    try:
        if PROVEEDOR == "anthropic":
            return _llamar_anthropic(prompt, sistema, max_tokens)
        elif PROVEEDOR == "openai":
            return _llamar_openai(prompt, sistema, max_tokens)
        elif PROVEEDOR == "gemini":
            return _llamar_gemini(prompt, sistema, max_tokens)
        else:
            return _resultado_error(f"Proveedor no soportado: {PROVEEDOR}")
    except Exception as e:
        return _resultado_error(str(e))


# --- Anthropic ---

def _llamar_anthropic(prompt: str, sistema: str, max_tokens: int) -> dict:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _resultado_error("ANTHROPIC_API_KEY no configurada en .env")

    modelo = os.getenv("IA_MODELO", MODELOS_DEFAULT["anthropic"])
    cliente = anthropic.Anthropic(api_key=api_key)

    kwargs = {
        "model":      modelo,
        "max_tokens": max_tokens,
        "messages":   [{"role": "user", "content": prompt}]
    }
    if sistema:
        kwargs["system"] = sistema

    respuesta = cliente.messages.create(**kwargs)
    texto = "".join(b.text for b in respuesta.content if getattr(b, "type", "text") == "text")
    uso = getattr(respuesta, "usage", None)

    return _resultado_ok(
        texto, "anthropic", modelo,
        truncada=(respuesta.stop_reason == "max_tokens"),
        tokens_entrada=getattr(uso, "input_tokens", None),
        tokens_salida=getattr(uso, "output_tokens", None),
    )


# --- OpenAI ---

def _llamar_openai(prompt: str, sistema: str, max_tokens: int) -> dict:
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _resultado_error("OPENAI_API_KEY no configurada en .env")

    modelo = os.getenv("IA_MODELO", MODELOS_DEFAULT["openai"])
    cliente = OpenAI(api_key=api_key)

    mensajes = []
    if sistema:
        mensajes.append({"role": "system", "content": sistema})
    mensajes.append({"role": "user", "content": prompt})

    respuesta = cliente.chat.completions.create(
        model=modelo,
        max_tokens=max_tokens,
        messages=mensajes
    )
    eleccion = respuesta.choices[0]
    texto = eleccion.message.content or ""
    uso = getattr(respuesta, "usage", None)

    return _resultado_ok(
        texto, "openai", modelo,
        truncada=(eleccion.finish_reason == "length"),
        tokens_entrada=getattr(uso, "prompt_tokens", None),
        tokens_salida=getattr(uso, "completion_tokens", None),
    )


# --- Google Gemini ---

def _llamar_gemini(prompt: str, sistema: str, max_tokens: int) -> dict:
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _resultado_error("GEMINI_API_KEY no configurada en .env")

    modelo = os.getenv("IA_MODELO", MODELOS_DEFAULT["gemini"])
    cliente = genai.Client(api_key=api_key)

    config = types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        system_instruction=sistema if sistema else None
    )

    respuesta = cliente.models.generate_content(
        model=modelo,
        contents=prompt,
        config=config
    )
    texto = respuesta.text or ""
    candidatos = getattr(respuesta, "candidates", None) or []
    finish = getattr(candidatos[0], "finish_reason", None) if candidatos else None
    uso = getattr(respuesta, "usage_metadata", None)

    return _resultado_ok(
        texto, "gemini", modelo,
        truncada=("MAX_TOKENS" in str(finish).upper()),
        tokens_entrada=getattr(uso, "prompt_token_count", None),
        tokens_salida=getattr(uso, "candidates_token_count", None),
    )


# --- Helpers ---

def _resultado_ok(respuesta: str, proveedor: str, modelo: str,
                  truncada: bool = False, tokens_entrada=None, tokens_salida=None) -> dict:
    return {
        "respuesta": respuesta,
        "proveedor": proveedor,
        "modelo":    modelo,
        "truncada":  truncada,
        "tokens":    {"entrada": tokens_entrada, "salida": tokens_salida},
        "exito":     True,
        "error":     None
    }

def _resultado_error(mensaje: str) -> dict:
    return {
        "respuesta": "",
        "proveedor": PROVEEDOR,
        "modelo":    None,
        "truncada":  False,
        "tokens":    {"entrada": None, "salida": None},
        "exito":     False,
        "error":     mensaje
    }


# --- Test rápido ---
if __name__ == "__main__":
    print(f"Proveedor configurado: {PROVEEDOR}")

    resultado = llamar_ia(
        prompt="Respondé solo con JSON válido, sin texto adicional: {\"estado\": \"ok\", \"mensaje\": \"conexión exitosa\"}",
        sistema="Sos un asistente de prueba. Devolvé exactamente el JSON que te pidan."
    )

    if resultado["exito"]:
        print(f"✓ Proveedor: {resultado['proveedor']}")
        print(f"✓ Modelo:    {resultado['modelo']}")
        print(f"✓ Respuesta: {resultado['respuesta']}")
    else:
        print(f"✗ Error: {resultado['error']}")
