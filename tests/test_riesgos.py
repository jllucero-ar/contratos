"""Tests de la evaluación de riesgos (detección, artículos respaldados, citas a revisar) y de las anotaciones."""

import json
from pathlib import Path

import pytest

from core.controles import citas_ccycn_en
from evaluacion.riesgos import NEUTROS, cargar_referencia, evaluar_riesgos

GOLDEN = Path(__file__).parent.parent / "evaluacion" / "golden"
REF = {886: "Mora del deudor", 1261: "Desistimiento unilateral", 1117: None}

ESPERADOS = [
    {"id": "R1", "descripcion": "mora", "alguno": ["mora automatica", "punitorio"], "articulos": [886, 768]},
    {"id": "R2", "descripcion": "jurisdicción", "alguno": ["jurisdiccion"], "articulos": []},
    {"id": "R3", "descripcion": "desistimiento", "alguno": ["desistimiento"], "articulos": [1261]},
]


def test_citas_ccycn_en():
    assert citas_ccycn_en("Ver art. 886 CCyCN y arts. 1198 y 3000 CCyCN; art. 37 de la Ley 24.240.") == ["886", "1198"]
    assert citas_ccycn_en("Sin citas") == []


def test_detectado_y_respaldado():
    r = evaluar_riesgos(["La mora automática es abusiva (art. 886 CCyCN)."], ESPERADOS[:1], REF)
    d = r["detalle"][0]
    assert d["detectado"] and d["respaldado"] is True and d["a_revisar"] == []
    assert r["detectados"] == 1


def test_detectado_pero_con_articulo_no_anotado_queda_a_revisar():
    r = evaluar_riesgos(["Mora automática punitorio, ver art. 1117 CCyCN."], ESPERADOS[:1], REF)
    d = r["detalle"][0]
    assert d["detectado"] and d["respaldado"] is False
    assert d["a_revisar"] == [{"articulo": 1117, "rubro": None}]
    assert r["citas_a_revisar"] == 1


def test_articulos_neutros_no_se_marcan():
    assert 961 in NEUTROS
    r = evaluar_riesgos(["Mora automática (art. 886 CCyCN y art. 961 CCyCN)."], ESPERADOS[:1], REF)
    assert r["detalle"][0]["a_revisar"] == []


def test_riesgo_sin_cita_exigida():
    r = evaluar_riesgos(["No hay cláusula de jurisdicción."], ESPERADOS[1:2], REF)
    d = r["detalle"][0]
    assert d["detectado"] and d["requiere_cita"] is False and d["respaldado"] is None
    assert r["requieren_cita"] == 0


def test_no_detectado_y_adicionales():
    r = evaluar_riesgos(["Algo totalmente distinto (art. 1117 CCyCN)."], ESPERADOS, REF)
    assert r["detectados"] == 0
    assert all(not d["detectado"] and d["respaldado"] is False for d in r["detalle"])
    assert r["riesgos_adicionales"] == [{"texto": "Algo totalmente distinto (art. 1117 CCyCN).", "citados": [1117]}]


def test_citas_de_otra_norma_no_cuentan():
    r = evaluar_riesgos(["Desistimiento sin preaviso según art. 37 de la Ley 24.240."], ESPERADOS[2:], REF)
    d = r["detalle"][0]
    assert d["detectado"] and d["citados"] == [] and d["respaldado"] is False


def test_riesgos_vacios_o_invalidos():
    assert evaluar_riesgos(None, ESPERADOS, REF)["detectados"] == 0
    assert evaluar_riesgos([None, 3], ESPERADOS, REF)["detectados"] == 0


# --- Consistencia de las anotaciones del golden set ---

CASOS = sorted(GOLDEN.glob("*.esperado.json"))


@pytest.mark.parametrize("path", CASOS, ids=lambda p: p.name)
def test_anotaciones_de_riesgos_bien_formadas(path):
    esperado = json.loads(path.read_text(encoding="utf-8"))
    assert esperado["revision_juridica"]["estado"].startswith("propuesta")
    ids = [r["id"] for r in esperado["riesgos_esperados"]]
    assert ids and len(ids) == len(set(ids))
    for r in esperado["riesgos_esperados"]:
        assert r["descripcion"] and r["alguno"] and isinstance(r["articulos"], list)


def test_todo_articulo_anotado_figura_en_la_referencia():
    """Solo se anotan artículos cuyo rubro fue contrastado con el texto publicado (referencia_ccycn.json)."""
    ref = cargar_referencia()
    for path in CASOS:
        for r in json.loads(path.read_text(encoding="utf-8"))["riesgos_esperados"]:
            for art in r["articulos"]:
                assert art in ref, f"{path.name} {r['id']}: art. {art} sin rubro verificado"
    assert all(1 <= a <= 2671 for a in ref)
