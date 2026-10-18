"""Smoke test de la planilla de revisión jurídica (usa el último reporte versionado)."""

import pytest

from evaluacion import generar_planilla as gp


def test_planilla_se_construye_y_las_listas_no_tienen_comas_internas():
    if not list(gp.REPORTES.glob("eval_*.json")):
        pytest.skip("sin reportes")
    ruta = gp.ultimo_reporte()
    rep, ref, esperados = gp.cargar_datos(ruta)
    wb = gp.construir(rep, ref, esperados, ruta.name)

    assert wb.sheetnames == ["Instrucciones", "Riesgos esperados", "Citas a revisar", "Riesgos adicionales", "Resumen"]
    assert wb["Riesgos esperados"].max_row - 1 == sum(len(c["riesgos"]["detalle"]) for c in rep["casos"])
    for nombre in wb.sheetnames[1:4]:
        for dv in wb[nombre].data_validations.dataValidation:
            opciones = dv.formula1.strip('"').split(",")
            # una opción con coma interna se partiría en Excel: ninguna opción debe quedar vacía ni truncada
            assert all(o.strip() and not o.strip().startswith("con ") for o in opciones), dv.formula1
            assert len(dv.formula1) <= 255
    assert wb["Resumen"]["B4"].value.startswith("=COUNTA(")
