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

from core.extractor import extraer_texto
from core.ia_client import llamar_ia
from core.pdf_report import generar_reporte


# --- Esquema JSON esperado ---
ESQUEMA = {
    "partes": {
        "locador": "nombre y CUIT/DNI de quien da en locación o presta el servicio",
        "locatario": "nombre y CUIT/DNI de quien recibe"
    },
    "objeto": "descripción del bien, servicio u obligación principal del contrato",
    "plazo": {
        "inicio": "fecha de inicio",
        "vencimiento": "fecha de vencimiento",
        "duracion": "duración expresada en años/meses",
        "observaciones": "condiciones de renovación o preaviso si las hay"
    },
    "canon": {
        "monto_inicial": "monto y moneda del precio o canon inicial",
        "ajuste": "mecanismo de ajuste si lo hay (IPC, dólar, etc.)",
        "vencimiento_pago": "plazo o fecha de pago"
    },
    "clausulas": {
        "rescision": "condiciones y penalidades por rescisión anticipada",
        "mora": "intereses y condiciones de mora",
        "limitacion_responsabilidad": "límites a la responsabilidad de las partes si los hay",
        "jurisdiccion": "tribunales competentes pactados",
        "notificaciones": "medios y plazos para notificaciones entre partes"
    },
    "riesgos": [
        "lista de cláusulas o condiciones que representan un riesgo para alguna de las partes"
    ],
    "observaciones_generales": "resumen ejecutivo del contrato y recomendaciones principales"
}


# --- Prompt del sistema ---
SISTEMA = """Sos un especialista en análisis y redacción de contratos bajo el derecho argentino.
Tu análisis se basa estrictamente en el Código Civil y Comercial de la Nación (CCyCN) y la jurisprudencia aplicable.
Tu tarea es analizar el contrato provisto y extraer información estructurada en formato JSON.

Reglas estrictas:
- Respondé ÚNICAMENTE con un objeto JSON válido, sin texto adicional, sin explicaciones, sin bloques de código.
- Si un campo no está presente en el contrato, usá el valor null. Nunca inferís ni inventás información.
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

    # 2. Llamar a la IA
    print("[analizador] Enviando a IA para análisis...")
    prompt = _construir_prompt(extraccion["texto"])
    respuesta_ia = llamar_ia(prompt=prompt, sistema=SISTEMA)

    if not respuesta_ia["exito"]:
        return _error(f"Error en IA: {respuesta_ia['error']}")

    if respuesta_ia.get("truncada"):
        return _error("Respuesta truncada por límite de tokens. Aumentá IA_MAX_TOKENS en .env.")

    print(f"[analizador] ✓ Respuesta recibida (proveedor: {respuesta_ia['proveedor']})")

    # 3. Parsear JSON
    datos = _parsear_json(respuesta_ia["respuesta"])
    if datos is None:
        return _error("La IA no devolvió un JSON válido.")

    print("[analizador] ✓ JSON parseado correctamente")

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


def _construir_prompt(texto: str) -> str:
    esquema_str = json.dumps(ESQUEMA, ensure_ascii=False, indent=2)
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
