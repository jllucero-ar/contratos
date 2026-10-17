"""
audit_log.py — core/audit_log.py
Registro de auditoría: una línea JSONL por análisis en data/logs/analisis_YYYYMMDD.jsonl.

El registro se arma con campos explícitos y de tipos acotados (hash, contadores, booleanos,
códigos de error). NO recibe ni escribe texto del contrato, de la respuesta del modelo, valores
de datos personales ni mensajes de error libres (esos pueden contener fragmentos del contrato).
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR_DEFAULT = Path(__file__).parent.parent / "data" / "logs"

# Códigos de error permitidos (el mensaje libre nunca se loguea)
CODIGOS_ERROR = {
    "extraccion",        # no se pudo extraer texto del PDF
    "proveedor",         # error de la API del proveedor / configuración
    "truncada",          # respuesta cortada por límite de tokens
    "esquema_invalido",  # no cumplió el esquema tras el reintento
    "desconocido",
}


def hash_pdf(path_pdf: str) -> str | None:
    """SHA-256 del contenido del archivo, o None si no se puede leer."""
    try:
        h = hashlib.sha256()
        with open(path_pdf, "rb") as f:
            for bloque in iter(lambda: f.read(1024 * 1024), b""):
                h.update(bloque)
        return h.hexdigest()
    except OSError:
        return None


def construir_registro(
    *,
    proveedor: str | None,
    modelo: str | None,
    prompt_version: str,
    pdf_sha256: str | None,
    tokens_entrada: int | None,
    tokens_salida: int | None,
    intentos: int,
    controles: dict,
    exito: bool,
    error_codigo: str | None = None,
) -> dict:
    """
    `controles` esperado (solo booleanos y contadores):
        {"esquema_valido": bool, "respuesta_completa": bool,
         "citas_ccycn": {"paso": bool|None, "encontradas": int, "invalidas": int} | None,
         "anonimizacion": {"por_tipo": {tipo: int}, "total": int, "marcadores_sin_restaurar": int} | None}
    """
    if error_codigo is not None and error_codigo not in CODIGOS_ERROR:
        error_codigo = "desconocido"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "proveedor": proveedor,
        "modelo": modelo,
        "prompt_version": prompt_version,
        "pdf_sha256": pdf_sha256,
        "tokens": {"entrada": tokens_entrada, "salida": tokens_salida},
        "intentos": intentos,
        "controles": controles,
        "exito": exito,
        "error_codigo": error_codigo,
    }


def registrar(registro: dict, dir_logs=None) -> Path:
    """Agrega `registro` como una línea JSON al log del día. Devuelve la ruta del archivo."""
    carpeta = Path(dir_logs) if dir_logs else LOG_DIR_DEFAULT
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = carpeta / f"analisis_{datetime.now(timezone.utc):%Y%m%d}.jsonl"
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return archivo
