"""Tests del comparador y del runner de evaluación. Sin llamadas a APIs: el analizador se reemplaza por un falso."""

import json

import pytest

from evaluacion import evaluar
from evaluacion.comparador import comparar_campo, valor_en_ruta


# --- comparador ---

def test_nulo_esperado():
    assert comparar_campo(None, {"nulo": True})[0]
    assert comparar_campo("", {"nulo": True})[0]
    ok, motivo = comparar_campo("$100", {"nulo": True})
    assert not ok and "null" in motivo


def test_null_donde_se_esperaba_valor_y_permite_nulo():
    assert not comparar_campo(None, {"contiene": ["x"]})[0]
    assert comparar_campo(None, {"permite_nulo": True, "alguno": ["convenir"]})[0]


def test_contiene_tolera_formato_de_numeros_acentos_y_mayusculas():
    spec = {"contiene": ["400.000"]}
    for v in ("$400.000 mensuales", "ARS 400000", "400.000,00"):
        assert comparar_campo(v, spec)[0], v
    assert not comparar_campo("$4.000.000", spec)[0]
    assert comparar_campo("Tribunales de la CIUDAD AUTÓNOMA de Buenos Aires",
                          {"contiene": ["Ciudad Autonoma"]})[0]


def test_numero_exige_palabra_completa():
    assert not comparar_campo("hasta el día 25", {"contiene": ["5"]})[0]
    assert comparar_campo("del 1 al 5 de cada mes", {"contiene": ["5"]})[0]


def test_texto_sin_digitos_es_prefijo_de_palabra():
    assert comparar_campo("ajuste semestralmente", {"contiene": ["semest"]})[0]
    assert not comparar_campo("ajuste anual", {"contiene": ["semest"]})[0]


def test_no_contiene_y_alguno():
    assert not comparar_campo("1 de enero de 2026", {"contiene": ["2026"], "no_contiene": ["enero"]})[0]
    assert comparar_campo("Locador", {"alguno": ["locador", "locadora"]})[0]
    assert not comparar_campo("Cliente", {"alguno": ["locador", "locadora"]})[0]


def test_valor_en_ruta():
    d = {"plazo": {"inicio": "x"}}
    assert valor_en_ruta(d, "plazo.inicio") == "x"
    assert valor_en_ruta(d, "plazo.fin") is None and valor_en_ruta(d, "canon.monto") is None


# --- runner ---

def _lc01_bueno():
    return {
        "partes": {"parte_a": {"nombre": "PARQUE LOGÍSTICO NORTE S.A.", "identificacion": "30-70000001-1", "rol": "Locador"},
                   "parte_b": {"nombre": "TECNOALIMENTOS ARGENTINA S.R.L.", "identificacion": "30-70000002-9", "rol": "Locatario"}},
        "plazo": {"inicio": "1 de febrero de 2026", "vencimiento": "31 de enero de 2028", "duracion": "24 meses"},
        "canon": {"monto_inicial": "$400.000 mensuales", "ajuste": "Semestral por ICL del BCRA",
                  "vencimiento_pago": "Del 1 al 10 de cada mes"},
        "clausulas": {"mora": "Interés punitorio 1,5% mensual",
                      "jurisdiccion": "Tribunales Ordinarios de la Ciudad Autónoma de Buenos Aires"},
        "controles": {"citas_ccycn": {"encontradas": ["886", "9999"], "invalidas": [{"cita": "9999"}]},
                      "literalidad": {"no_encontrados": []}},
    }


def _falso(pdf):
    if "lc01" in pdf:
        datos = _lc01_bueno()
        datos["canon"]["monto_inicial"] = "$900.000 mensuales"  # error deliberado
        return {"exito": True, "datos": datos, "error": None,
                "meta": {"proveedor": "mock", "modelo": "m1", "prompt_version": "9.9", "intentos": 2,
                         "tokens_entrada": 100, "tokens_salida": 50}}
    return {"exito": False, "datos": None, "error": "Respuesta truncada", "meta": {}}


def test_correr_calcula_metricas():
    rep = evaluar.correr(["lc01", "mt05"], analizar=_falso)
    assert rep["proveedor"] == "mock" and rep["prompt_version"] == "9.9"
    lc, mt = rep["casos"]
    assert lc["id"].startswith("lc01") and lc["campos_total"] == 14 and lc["campos_ok"] == 13
    assert [f["campo"] for f in lc["fallos"]] == ["canon.monto_inicial"]
    assert lc["citas_invalidas"] == 1 and lc["intentos"] == 2
    assert mt["exito"] is False and mt["campos_ok"] == 0 and mt["nulos_respetados"] == 0 and mt["nulos_esperados"] > 0
    r = rep["resumen"]
    assert r["casos_con_error"] == 1 and r["reintentos"] == 1
    assert r["tasa_citas_invalidas"] == 0.5
    assert r["tokens_entrada"] == 100


def test_guardar_y_markdown(tmp_path):
    rep = evaluar.correr(["lc01"], analizar=_falso)
    j, m = evaluar.guardar(rep, tmp_path)
    assert json.loads(j.read_text(encoding="utf-8"))["resumen"] == rep["resumen"]
    md = m.read_text(encoding="utf-8")
    assert "Exactitud de campos" in md and "canon.monto_inicial" in md and "p9.9" in j.name


def test_comparar_reportes():
    a = evaluar.correr(["lc01"], analizar=_falso)
    b = json.loads(json.dumps(a))
    b["modelo"], b["prompt_version"], b["timestamp"] = "m2", "10.0", "2999-01-01T00:00:00+00:00"
    tabla = evaluar.comparar([b, a])
    lineas = tabla.splitlines()
    assert "m1" in lineas[2] and "m2" in lineas[3] and "10.0" in lineas[3]


def test_filtro_de_casos_inexistente():
    with pytest.raises(SystemExit):
        evaluar.correr(["zz99"], analizar=_falso)
