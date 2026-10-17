"""Regresión: el PDF se genera con el esquema nuevo (parte_a/parte_b, campos null)."""

from contratos.esquema import AnalisisContrato
from core.pdf_report import generar_reporte


def _vacio():
    nulos = lambda *ks: {k: None for k in ks}  # noqa: E731
    return {
        "partes": {"parte_a": nulos("nombre", "identificacion", "rol"),
                   "parte_b": {"nombre": "Ficticia S.A.", "identificacion": "CUIT 30-00000000-0", "rol": "cliente"}},
        "objeto": None,
        "plazo": nulos("inicio", "vencimiento", "duracion", "observaciones"),
        "canon": nulos("monto_inicial", "ajuste", "vencimiento_pago"),
        "clausulas": nulos("rescision", "mora", "limitacion_responsabilidad", "jurisdiccion", "notificaciones"),
        "riesgos": [],
        "observaciones_generales": None,
    }


def test_pdf_con_nulls(tmp_path):
    datos = AnalisisContrato.model_validate(_vacio()).model_dump()
    salida = tmp_path / "a.pdf"
    r = generar_reporte(datos, str(salida))
    assert r["exito"], r["error"]
    assert salida.stat().st_size > 0
