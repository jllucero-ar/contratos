"""
pdf_report.py — core/pdf_report.py
Genera un PDF de análisis a partir del JSON estructurado devuelto por la IA.
Reutilizable en todos los proyectos del portfolio.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.units import cm
from datetime import datetime
from pathlib import Path


# --- Colores ---
COLOR_PRIMARIO   = colors.HexColor("#1a3a5c")
COLOR_SECUNDARIO = colors.HexColor("#2e6da4")
COLOR_FONDO      = colors.HexColor("#f0f4f8")
COLOR_RIESGO     = colors.HexColor("#c0392b")
COLOR_OK         = colors.HexColor("#27ae60")
COLOR_GRIS       = colors.HexColor("#7f8c8d")


def generar_reporte(datos: dict, path_output: str) -> dict:
    """
    Genera un PDF de análisis a partir del JSON estructurado.

    Args:
        datos:       dict con el análisis estructurado devuelto por la IA
        path_output: ruta donde guardar el PDF generado

    Returns:
        dict con exito (bool) y error (str o None)
    """
    try:
        Path(path_output).parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            path_output,
            pagesize=A4,
            leftMargin=2.5*cm,
            rightMargin=2.5*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm
        )

        estilos = _definir_estilos()
        historia = _construir_contenido(datos, estilos)
        doc.build(historia)

        return {"exito": True, "error": None}

    except Exception as e:
        return {"exito": False, "error": str(e)}


def _definir_estilos() -> dict:
    base = getSampleStyleSheet()

    return {
        "titulo": ParagraphStyle(
            "titulo",
            parent=base["Title"],
            fontSize=18,
            textColor=COLOR_PRIMARIO,
            spaceAfter=4,
            fontName="Helvetica-Bold"
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo",
            parent=base["Normal"],
            fontSize=10,
            textColor=COLOR_GRIS,
            spaceAfter=16
        ),
        "seccion": ParagraphStyle(
            "seccion",
            parent=base["Heading2"],
            fontSize=12,
            textColor=COLOR_SECUNDARIO,
            spaceBefore=14,
            spaceAfter=6,
            fontName="Helvetica-Bold"
        ),
        "cuerpo": ParagraphStyle(
            "cuerpo",
            parent=base["Normal"],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=6,
            leading=15
        ),
        "etiqueta": ParagraphStyle(
            "etiqueta",
            parent=base["Normal"],
            fontSize=9,
            textColor=COLOR_GRIS,
            spaceAfter=2,
            fontName="Helvetica-Bold"
        ),
        "riesgo": ParagraphStyle(
            "riesgo",
            parent=base["Normal"],
            fontSize=10,
            textColor=COLOR_RIESGO,
            spaceAfter=4,
            leading=14
        ),
        "pie": ParagraphStyle(
            "pie",
            parent=base["Normal"],
            fontSize=8,
            textColor=COLOR_GRIS,
            spaceBefore=10
        ),
    }


def _construir_contenido(datos: dict, estilos: dict) -> list:
    historia = []
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    # --- Encabezado ---
    historia.append(Paragraph("ANÁLISIS DE CONTRATO", estilos["titulo"]))
    historia.append(Paragraph(f"Generado el {fecha}", estilos["subtitulo"]))
    historia.append(HRFlowable(width="100%", thickness=2, color=COLOR_PRIMARIO, spaceAfter=12))

    # --- Partes ---
    _agregar_seccion(historia, "PARTES", estilos)
    partes = datos.get("partes", {})
    _agregar_campo(historia, "Parte A", _fmt_parte(partes.get("parte_a") or partes.get("locador")), estilos)
    _agregar_campo(historia, "Parte B", _fmt_parte(partes.get("parte_b") or partes.get("locatario")), estilos)

    # --- Objeto ---
    _agregar_seccion(historia, "OBJETO", estilos)
    historia.append(Paragraph(datos.get("objeto") or "—", estilos["cuerpo"]))

    # --- Plazo ---
    _agregar_seccion(historia, "PLAZO Y VIGENCIA", estilos)
    plazo = datos.get("plazo", {})
    _agregar_campo(historia, "Inicio",     plazo.get("inicio", "—"), estilos)
    _agregar_campo(historia, "Vencimiento", plazo.get("vencimiento", "—"), estilos)
    _agregar_campo(historia, "Duración",   plazo.get("duracion", "—"), estilos)
    if plazo.get("observaciones"):
        historia.append(Paragraph(plazo["observaciones"], estilos["cuerpo"]))

    # --- Canon ---
    _agregar_seccion(historia, "CANON / PRECIO", estilos)
    canon = datos.get("canon", {})
    _agregar_campo(historia, "Monto inicial", canon.get("monto_inicial", "—"), estilos)
    _agregar_campo(historia, "Ajuste",        canon.get("ajuste", "—"), estilos)
    _agregar_campo(historia, "Vencimiento de pago", canon.get("vencimiento_pago", "—"), estilos)

    # --- Cláusulas clave ---
    _agregar_seccion(historia, "CLÁUSULAS CLAVE", estilos)

    clausulas = datos.get("clausulas", {})

    _agregar_campo(historia, "Rescisión anticipada",
                   clausulas.get("rescision", "—"), estilos)
    _agregar_campo(historia, "Penalidades por mora",
                   clausulas.get("mora", "—"), estilos)
    _agregar_campo(historia, "Limitación de responsabilidad",
                   clausulas.get("limitacion_responsabilidad", "—"), estilos)
    _agregar_campo(historia, "Jurisdicción",
                   clausulas.get("jurisdiccion", "—"), estilos)
    _agregar_campo(historia, "Notificaciones",
                   clausulas.get("notificaciones", "—"), estilos)

    # --- Riesgos ---
    riesgos = datos.get("riesgos", [])
    if riesgos:
        _agregar_seccion(historia, "RIESGOS DETECTADOS", estilos)
        for r in riesgos:
            historia.append(Paragraph(f"⚠ {r}", estilos["riesgo"]))
            historia.append(Spacer(1, 4))

    # --- Observaciones generales ---
    obs = datos.get("observaciones_generales", "")
    if obs:
        _agregar_seccion(historia, "OBSERVACIONES GENERALES", estilos)
        historia.append(Paragraph(obs, estilos["cuerpo"]))

    # --- Pie ---
    historia.append(Spacer(1, 20))
    historia.append(HRFlowable(width="100%", thickness=1, color=COLOR_GRIS))
    historia.append(Paragraph(
        "Este análisis fue generado automáticamente con asistencia de inteligencia artificial. "
        "No reemplaza el asesoramiento jurídico profesional.",
        estilos["pie"]
    ))

    return historia


def _agregar_seccion(historia: list, titulo: str, estilos: dict):
    historia.append(Spacer(1, 6))
    historia.append(Paragraph(titulo, estilos["seccion"]))
    historia.append(HRFlowable(width="100%", thickness=0.5, color=COLOR_SECUNDARIO, spaceAfter=6))


def _fmt_parte(parte) -> str:
    """Acepta el formato nuevo (dict nombre/identificacion/rol) o un string (formato viejo)."""
    if not parte:
        return "—"
    if isinstance(parte, str):
        return parte
    texto = ", ".join(x for x in (parte.get("nombre"), parte.get("identificacion")) if x)
    if parte.get("rol"):
        texto = f"{texto} ({parte['rol']})" if texto else parte["rol"]
    return texto or "—"


def _agregar_campo(historia: list, etiqueta: str, valor: str, estilos: dict):
    historia.append(Paragraph(etiqueta.upper(), estilos["etiqueta"]))
    historia.append(Paragraph(str(valor) if valor else "—", estilos["cuerpo"]))


# --- Test rápido con datos de ejemplo ---
if __name__ == "__main__":
    datos_ejemplo = {
        "partes": {
            "parte_a": {"nombre": "INVERSIONES DEL SUR S.A.", "identificacion": "CUIT 30-71234567-8", "rol": "locador"},
            "parte_b": {"nombre": "COMERCIAL PATAGONIA S.R.L.", "identificacion": "CUIT 30-68901234-5", "rol": "locatario"}
        },
        "objeto": "Local comercial en Av. Rivadavia 2345, PB, CABA. 120 m². Destino: indumentaria y accesorios.",
        "plazo": {
            "inicio": "1° de abril de 2025",
            "vencimiento": "31 de marzo de 2028",
            "duracion": "3 años",
            "observaciones": "Preaviso de no renovación: 90 días."
        },
        "canon": {
            "monto_inicial": "$250.000 mensuales (primeros 6 meses)",
            "ajuste": "Trimestral por IPC-INDEC a partir del 7° mes",
            "vencimiento_pago": "Primeros 5 días hábiles de cada mes"
        },
        "clausulas": {
            "rescision": "Preaviso 60 días. Penalidad: 1,5 meses si rescinde en el 1° año; 1 mes después.",
            "mora": "Interés punitorio: 2x tasa activa BNA a 30 días. Mora automática sin interpelación.",
            "limitacion_responsabilidad": "Tope: 3 meses de canon vigente. Excluye caso fortuito, fuerza mayor y actos de terceros.",
            "jurisdiccion": "Tribunales Ordinarios de la Ciudad Autónoma de Buenos Aires.",
            "notificaciones": "Carta documento, telegrama colacionado o acta notarial. Cambio de domicilio con 10 días de anticipación."
        },
        "riesgos": [
            "Cláusula de prórroga automática por igual período si no se notifica con 90 días de anticipación.",
            "Mora de pleno derecho — no requiere interpelación previa.",
            "Limitación de responsabilidad del locador acotada a 3 meses de canon."
        ],
        "observaciones_generales": "Contrato estándar de locación comercial. Las cláusulas de ajuste por IPC y mora automática son favorables al locador. Se recomienda evaluar la cláusula de prórroga automática antes del vencimiento."
    }

    resultado = generar_reporte(datos_ejemplo, "/home/claude/test_reporte.pdf")

    if resultado["exito"]:
        print("✓ PDF generado: /home/claude/test_reporte.pdf")
    else:
        print(f"✗ Error: {resultado['error']}")
