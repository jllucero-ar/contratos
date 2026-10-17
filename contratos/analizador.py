"""
analizador.py — contratos/analizador.py
Prompt específico y esquema JSON para análisis de contratos.
Usa los módulos del core: extractor, ia_client, pdf_report.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Agregar el directorio padre al path para importar core
sys.path.append(str(Path(__file__).parent.parent))

from pydantic import ValidationError

from contratos.esquema import AnalisisContrato, plantilla_json, resumir_errores
from core.extractor import extraer_texto
from core.ia_client import llamar_ia
from core.pdf_report import generar_reporte


# --- Prompt del sistema ---
SISTEMA = """Sos un especialista en análisis y redacción de contratos bajo el derecho argentino.
Tu análisis se basa estrictamente en el Código Civil y Comercial de la Nación (CCyCN) y la jurisprudencia aplicable.
Tu tarea es analizar el contrato provisto y extraer información estructurada en formato JSON.

Reglas estrictas:
- Respondé ÚNICAMENTE con un objeto JSON válido, sin texto adicional, sin explicaciones, sin bloques de código.
- Si un campo no está presente en el contrato, usá el valor null (todas las claves deben estar presentes). Nunca inferís ni inventás información.
- Toda observación de riesgo debe estar fundada en una norma concreta del CCyCN o en jurisprudencia reconocida. Citá obligatoriamente el artículo del CCyCN u otra norma aplicable y/o la fuente jurisprudencial.
- No emitas opiniones personales ni recomendaciones sin sustento normativo.
- Las observaciones generales deben ser un resumen ejecutivo de no más de 3 oraciones, con referencia a la normativa aplicable."""


def analizar_contrato(path_pdf: str, path_output_json: str = None, path_output_pdf: str = None) -> dict:
    """
    Pipeline completo: extrae texto del PDF → llama a la IA → guarda JSON → genera PDF.

    Args:
        path_pdf:         ruta al PDF del contrato
        path_output_json: ruta donde guardar el JSON (opcional)
        path_output_pdf:  ruta donde guardar el PDF de análisis (opcional)

    Returns:
        dict con:
            - datos:      dict con el análisis estructurado
            - json_path:  ruta al JSON guardado (o None)
            - pdf_path:   ruta al PDF generado (o None)
            - exito:      bool
            - error:      str o None
    """

    # 1. Extraer texto del PDF
    print(f"[analizador] Extrayendo texto de: {path_pdf}")
    extraccion = extraer_texto(path_pdf)

    if not extraccion["exito"]:
        return _error(f"Error en extracción: {extraccion['error']}")

    print(f"[analizador] ✓ Texto extraído ({extraccion['paginas']} páginas, método: {extraccion['metodo']})")

    # 2. Llamar a la IA y validar contra el esquema (1 reintento con el error de validación)
    prompt = _construir_prompt(extraccion["texto"])
    datos, error = _obtener_analisis(prompt)
    if error:
        return _error(error)

    print("[analizador] ✓ Respuesta validada contra el esquema")

    resultado = {"datos": datos, "json_path": None, "pdf_path": None, "exito": True, "error": None}

    # 4. Guardar JSON
    if path_output_json:
        try:
            Path(path_output_json).parent.mkdir(parents=True, exist_ok=True)
            with open(path_output_json, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
            resultado["json_path"] = path_output_json
            print(f"[analizador] ✓ JSON guardado en: {path_output_json}")
        except Exception as e:
            print(f"[analizador] ✗ Error guardando JSON: {e}")

    # 5. Generar PDF
    if path_output_pdf:
        rep = generar_reporte(datos, path_output_pdf)
        if rep["exito"]:
            resultado["pdf_path"] = path_output_pdf
            print(f"[analizador] ✓ PDF generado en: {path_output_pdf}")
        else:
            print(f"[analizador] ✗ Error generando PDF: {rep['error']}")

    return resultado


def _obtener_analisis(prompt: str) -> tuple[dict | None, str | None]:
    """Llama a la IA y valida. Devuelve (datos, None) o (None, mensaje_de_error)."""
    prompt_actual = prompt
    ultimo_error = ""

    for intento in (1, 2):
        print(f"[analizador] Enviando a IA para análisis (intento {intento}/2)...")
        respuesta_ia = llamar_ia(prompt=prompt_actual, sistema=SISTEMA)

        if not respuesta_ia["exito"]:
            return None, f"Error en IA: {respuesta_ia['error']}"

        if respuesta_ia.get("truncada"):
            return None, "Respuesta truncada por límite de tokens. Aumentá IA_MAX_TOKENS en .env."

        print(f"[analizador] ✓ Respuesta recibida (proveedor: {respuesta_ia['proveedor']})")

        datos, ultimo_error = _validar(respuesta_ia["respuesta"])
        if datos is not None:
            return datos, None

        print(f"[analizador] ✗ Validación fallida:\n{ultimo_error}")
        prompt_actual = (
            f"{prompt}\n\nTu respuesta anterior no cumplió el esquema:\n{ultimo_error}\n"
            f"Respuesta anterior:\n{respuesta_ia['respuesta']}\n\n"
            "Corregí los errores y respondé ÚNICAMENTE con el JSON completo y válido."
        )

    return None, f"La respuesta de la IA no cumple el esquema tras 2 intentos:\n{ultimo_error}"


def _validar(texto: str) -> tuple[dict | None, str]:
    """Parsea y valida contra AnalisisContrato. Devuelve (datos, '') o (None, descripción_del_error)."""
    crudo = _parsear_json(texto)
    if crudo is None:
        return None, "- La respuesta no es un JSON válido."
    try:
        return AnalisisContrato.model_validate(crudo).model_dump(), ""
    except ValidationError as e:
        return None, resumir_errores(e)


def _construir_prompt(texto: str) -> str:
    esquema_str = plantilla_json()
    return f"""Analizá el siguiente contrato y devolvé un JSON con exactamente esta estructura:

{esquema_str}

CONTRATO:
---
{texto}
---

Recordá: respondé ÚNICAMENTE con el JSON, sin texto adicional."""


def _parsear_json(texto: str) -> dict | None:
    """Intenta parsear el JSON devuelto por la IA, tolerando bloques de código."""
    texto = texto.strip()
    # Limpiar bloques de código si la IA los incluyó de todas formas
    if texto.startswith("```"):
        lineas = texto.split("\n")
        texto = "\n".join(lineas[1:-1])
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return None


def _error(mensaje: str) -> dict:
    return {"datos": None, "json_path": None, "pdf_path": None, "exito": False, "error": mensaje}


# --- Punto de entrada ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python analizador.py <ruta_al_pdf>")
        print("Ejemplo: python analizador.py ../data/test/contrato.pdf")
        sys.exit(1)

    path_pdf = sys.argv[1]
    nombre   = Path(path_pdf).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    path_json = f"../data/json/{nombre}_{timestamp}.json"
    path_pdf_out = f"../data/pdf/{nombre}_{timestamp}_analisis.pdf"

    resultado = analizar_contrato(path_pdf, path_json, path_pdf_out)

    if resultado["exito"]:
        print("\n✓ Análisis completado.")
        if resultado["json_path"]:
            print(f"  JSON: {resultado['json_path']}")
        if resultado["pdf_path"]:
            print(f"  PDF:  {resultado['pdf_path']}")
    else:
        print(f"\n✗ Error: {resultado['error']}")
