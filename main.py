"""
main.py — punto de entrada del proyecto CONTRATOS
Uso: python main.py <ruta_al_pdf>
"""

import sys
from pathlib import Path
from datetime import datetime

# Agregar raíz al path
sys.path.append(str(Path(__file__).parent))

from contratos.analizador import analizar_contrato


def procesar(path_pdf: str):
    if not Path(path_pdf).exists():
        print(f"✗ Archivo no encontrado: {path_pdf}")
        return

    nombre    = Path(path_pdf).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    path_json    = f"data/json/{nombre}_{timestamp}.json"
    path_pdf_out = f"data/pdf/{nombre}_{timestamp}_analisis.pdf"

    print(f"\n{'='*50}")
    print(f"  ANALIZADOR DE CONTRATOS")
    print(f"{'='*50}")
    print(f"  Archivo: {path_pdf}\n")

    resultado = analizar_contrato(path_pdf, path_json, path_pdf_out)

    print(f"\n{'='*50}")
    if resultado["exito"]:
        print("  ✓ ANÁLISIS COMPLETADO")
        if resultado["json_path"]:
            print(f"  JSON : {resultado['json_path']}")
        if resultado["pdf_path"]:
            print(f"  PDF  : {resultado['pdf_path']}")
    else:
        print(f"  ✗ ERROR: {resultado['error']}")
    print(f"{'='*50}\n")


def main():
    if len(sys.argv) < 2:
        print("Uso: python main.py <ruta_al_pdf> [<ruta_al_pdf2> ...]")
        print("Ejemplo: python main.py data/test/contrato1.pdf data/test/contrato2.pdf")
        sys.exit(1)

    for path_pdf in sys.argv[1:]:
        procesar(path_pdf)


if __name__ == "__main__":
    main()
