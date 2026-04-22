"""
extractor.py — core/extractor.py
Extrae texto de PDFs usando pdfplumber con fallback a pytesseract (OCR).
Reutilizable en todos los proyectos del portfolio.
"""

import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from pathlib import Path


# Umbral mínimo de caracteres para considerar que pdfplumber extrajo bien
UMBRAL_OCR = 100


def extraer_texto(path_pdf: str) -> dict:
    """
    Extrae el texto de un PDF.
    Intenta primero con pdfplumber. Si el resultado es insuficiente,
    hace fallback a pytesseract (OCR).

    Args:
        path_pdf: ruta al archivo PDF

    Returns:
        dict con:
            - texto: string con el contenido completo
            - paginas: int con la cantidad de páginas
            - metodo: 'pdfplumber' o 'ocr'
            - exito: bool
            - error: str o None
    """
    path = Path(path_pdf)

    if not path.exists():
        return _resultado_error(f"Archivo no encontrado: {path_pdf}")

    if path.suffix.lower() != ".pdf":
        return _resultado_error(f"El archivo no es un PDF: {path_pdf}")

    # Intento 1: pdfplumber
    try:
        texto, paginas = _extraer_con_pdfplumber(path)

        if len(texto.strip()) >= UMBRAL_OCR:
            return {
                "texto": texto.strip(),
                "paginas": paginas,
                "metodo": "pdfplumber",
                "exito": True,
                "error": None
            }

        print(f"[extractor] pdfplumber extrajo poco texto ({len(texto.strip())} chars). Intentando OCR...")

    except Exception as e:
        print(f"[extractor] pdfplumber falló: {e}. Intentando OCR...")

    # Intento 2: pytesseract (OCR)
    try:
        texto, paginas = _extraer_con_ocr(path)

        return {
            "texto": texto.strip(),
            "paginas": paginas,
            "metodo": "ocr",
            "exito": True,
            "error": None
        }

    except Exception as e:
        return _resultado_error(f"OCR también falló: {e}")


def _extraer_con_pdfplumber(path: Path) -> tuple[str, int]:
    """Extrae texto página por página con pdfplumber."""
    texto = ""
    with pdfplumber.open(path) as pdf:
        paginas = len(pdf.pages)
        for page in pdf.pages:
            contenido = page.extract_text()
            if contenido:
                texto += contenido + "\n"
    return texto, paginas


def _extraer_con_ocr(path: Path) -> tuple[str, int]:
    """Convierte el PDF a imágenes y aplica OCR con pytesseract."""
    imagenes = convert_from_path(str(path))
    texto = ""
    for imagen in imagenes:
        texto += pytesseract.image_to_string(imagen, lang="spa") + "\n"
    return texto, len(imagenes)


def _resultado_error(mensaje: str) -> dict:
    return {
        "texto": "",
        "paginas": 0,
        "metodo": None,
        "exito": False,
        "error": mensaje
    }


# --- Test rápido ---
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python extractor.py <ruta_al_pdf>")
        sys.exit(1)

    resultado = extraer_texto(sys.argv[1])

    if resultado["exito"]:
        print(f"✓ Método: {resultado['metodo']}")
        print(f"✓ Páginas: {resultado['paginas']}")
        print(f"✓ Caracteres extraídos: {len(resultado['texto'])}")
        print("\n--- Primeros 500 caracteres ---")
        print(resultado["texto"][:500])
    else:
        print(f"✗ Error: {resultado['error']}")
