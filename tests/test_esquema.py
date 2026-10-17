"""Tests de validación del esquema y del reintento. La IA se mockea."""

import copy
import json
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from contratos import analizador
from contratos.esquema import AnalisisContrato

VALIDO = {
    "partes": {
        "parte_a": {"nombre": "Empresa Ficticia S.A.", "identificacion": "CUIT 30-00000000-0", "rol": "prestador"},
        "parte_b": {"nombre": "Cliente Ejemplo S.R.L.", "identificacion": None, "rol": "cliente"},
    },
    "objeto": "Servicio de ejemplo",
    "plazo": {"inicio": None, "vencimiento": None, "duracion": "12 meses", "observaciones": None},
    "canon": {"monto_inicial": None, "ajuste": None, "vencimiento_pago": None},
    "clausulas": {
        "rescision": None, "mora": None, "limitacion_responsabilidad": None,
        "jurisdiccion": None, "notificaciones": None,
    },
    "riesgos": ["Mora automática (art. 886 CCyCN)."],
    "observaciones_generales": "Resumen.",
}


def _ia(texto, truncada=False):
    return {"exito": True, "respuesta": texto, "proveedor": "mock", "modelo": "m",
            "truncada": truncada, "tokens": {"entrada": 1, "salida": 1}, "error": None}


def test_esquema_acepta_valido_con_nulls():
    AnalisisContrato.model_validate(VALIDO)


def test_esquema_rechaza_clave_faltante():
    malo = copy.deepcopy(VALIDO)
    del malo["plazo"]
    with pytest.raises(ValidationError):
        AnalisisContrato.model_validate(malo)


def test_esquema_rechaza_clave_extra_y_tipo_incorrecto():
    malo = copy.deepcopy(VALIDO)
    malo["inventado"] = 1
    with pytest.raises(ValidationError):
        AnalisisContrato.model_validate(malo)
    malo = copy.deepcopy(VALIDO)
    malo["riesgos"] = "no es lista"
    with pytest.raises(ValidationError):
        AnalisisContrato.model_validate(malo)


def test_validar_tolera_bloque_de_codigo():
    datos, err = analizador._validar("```json\n" + json.dumps(VALIDO) + "\n```")
    assert err == "" and datos["objeto"] == "Servicio de ejemplo"


def test_reintento_exitoso_pasa_el_error_al_modelo():
    incompleto = copy.deepcopy(VALIDO)
    del incompleto["canon"]
    with patch.object(analizador, "llamar_ia", side_effect=[_ia(json.dumps(incompleto)), _ia(json.dumps(VALIDO))]) as m:
        datos, error = analizador._obtener_analisis("PROMPT")
    assert error is None and datos is not None
    assert m.call_count == 2
    segundo_prompt = m.call_args_list[1].kwargs["prompt"]
    assert "canon" in segundo_prompt  # el error de validación viaja en el reintento


def test_dos_fallos_devuelven_error_claro():
    with patch.object(analizador, "llamar_ia", return_value=_ia("no es json")) as m:
        datos, error = analizador._obtener_analisis("PROMPT")
    assert datos is None
    assert "2 intentos" in error
    assert m.call_count == 2


def test_truncada_no_reintenta():
    with patch.object(analizador, "llamar_ia", return_value=_ia('{"a":', truncada=True)) as m:
        datos, error = analizador._obtener_analisis("PROMPT")
    assert datos is None and "truncada" in error.lower()
    assert m.call_count == 1
