"""
generar_pdfs.py — evaluacion/generar_pdfs.py
Genera un PDF por cada contrato ficticio del golden set (evaluacion/golden/*.txt).
Los .txt son la fuente; los PDF se regeneran con:  python evaluacion/generar_pdfs.py
"""

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from xml.sax.saxutils import escape

GOLDEN = Path(__file__).parent / "golden"


def generar_pdf(path_txt: Path) -> Path:
    base = getSampleStyleSheet()
    titulo = ParagraphStyle("t", parent=base["Title"], fontSize=14, spaceAfter=14)
    cuerpo = ParagraphStyle("c", parent=base["Normal"], fontSize=10.5, leading=15, spaceAfter=8)

    bloques = [b.strip() for b in path_txt.read_text(encoding="utf-8").split("\n\n") if b.strip()]
    historia = [Paragraph(escape(bloques[0]), titulo)]
    for b in bloques[1:]:
        historia.append(Paragraph(escape(b).replace("\n", "<br/>"), cuerpo))
        historia.append(Spacer(1, 2))

    salida = path_txt.with_suffix(".pdf")
    SimpleDocTemplate(str(salida), pagesize=A4, leftMargin=2.5 * cm, rightMargin=2.5 * cm,
                      topMargin=2.5 * cm, bottomMargin=2.5 * cm,
                      title=path_txt.stem, author="Datos ficticios").build(historia)
    return salida


if __name__ == "__main__":
    for txt in sorted(GOLDEN.glob("*.txt")):
        print(f"✓ {generar_pdf(txt).name}")
