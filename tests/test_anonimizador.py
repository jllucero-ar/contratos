"""Tests de anonimización y restauración. Todos los datos son ficticios."""

import json
from unittest.mock import patch

from contratos import analizador
from core.anonimizador import Anonimizador

TEXTO = (
    "María Ejemplo, DNI Nº 12.345.678, CUIL 20-12345678-3, con domicilio en Calle Falsa 123, "
    "y Empresa Ficticia S.A., CUIT 30-71234567-8, email contacto@ficticia.example, "
    "Tel: 011 4444-5555 y cel +54 9 11 5555-1234. Canon $1.250.000 desde 01/02/2025."
)


def test_reemplaza_cada_tipo():
    a = Anonimizador()
    r = a.anonimizar(TEXTO)
    for crudo in ("12.345.678", "20-12345678-3", "30-71234567-8", "contacto@ficticia.example",
                  "011 4444-5555", "+54 9 11 5555-1234"):
        assert crudo not in r
    assert a.conteo == {"EMAIL": 1, "CUIT": 1, "CUIL": 1, "DNI": 1, "TEL": 2}
    assert "[DNI_1]" in r and "[CUIL_1]" in r and "[CUIT_1]" in r and "[EMAIL_1]" in r and "[TEL_2]" in r


def test_no_toca_montos_ni_fechas_ni_nombres():
    r = Anonimizador().anonimizar(TEXTO)
    assert "$1.250.000" in r and "01/02/2025" in r and "María Ejemplo" in r


def test_mismo_valor_mismo_marcador():
    a = Anonimizador()
    r = a.anonimizar("DNI 12.345.678 ... DNI 12.345.678")
    assert r.count("[DNI_1]") == 2 and a.conteo == {"DNI": 1}


def test_restaura_en_estructura_anidada():
    a = Anonimizador()
    r = a.anonimizar(TEXTO)
    datos = {"partes": {"a": "x [CUIT_1] y"}, "riesgos": ["mail [EMAIL_1]"], "n": 3, "v": None}
    restaurado = a.restaurar(datos)
    assert restaurado["partes"]["a"] == "x 30-71234567-8 y"
    assert restaurado["riesgos"] == ["mail contacto@ficticia.example"]
    assert restaurado["n"] == 3 and restaurado["v"] is None
    assert a.restaurar(r) == TEXTO  # ida y vuelta exacta


def test_marcador_desconocido_se_deja_y_se_cuenta():
    a = Anonimizador()
    a.anonimizar("DNI 12.345.678")
    out = a.restaurar({"x": "[DNI_1] y [DNI_9]"})
    assert out["x"] == "12.345.678 y [DNI_9]"
    assert Anonimizador.contar_marcadores(out) == 1


def test_repr_no_expone_valores():
    a = Anonimizador()
    a.anonimizar("DNI 12.345.678")
    assert "12.345.678" not in repr(a)


def test_pipeline_no_envia_pii_al_proveedor_y_restaura(tmp_path):
    enviados = []
    respuesta = {
        "partes": {
            "parte_a": {"nombre": "Empresa Ficticia S.A.", "identificacion": "[CUIT_1]", "rol": "prestador"},
            "parte_b": {"nombre": "María Ejemplo", "identificacion": "DNI [DNI_1]", "rol": "cliente"},
        },
        "objeto": None,
        "plazo": {"inicio": None, "vencimiento": None, "duracion": None, "observaciones": None},
        "canon": {"monto_inicial": None, "ajuste": None, "vencimiento_pago": None},
        "clausulas": {"rescision": None, "mora": None, "limitacion_responsabilidad": None,
                      "jurisdiccion": None, "notificaciones": None},
        "riesgos": [],
        "observaciones_generales": "Contactar a [EMAIL_1].",
    }

    def falsa_ia(prompt, sistema=""):
        enviados.append(prompt)
        return {"exito": True, "respuesta": json.dumps(respuesta), "proveedor": "mock", "modelo": "m",
                "truncada": False, "tokens": {"entrada": 1, "salida": 1}, "error": None}

    extraccion = {"exito": True, "texto": TEXTO, "paginas": 1, "metodo": "pdfplumber", "error": None}
    with patch.object(analizador, "extraer_texto", return_value=extraccion), \
         patch.object(analizador, "llamar_ia", side_effect=falsa_ia):
        res = analizador.analizar_contrato("x.pdf", str(tmp_path / "o.json"))

    assert res["exito"], res["error"]
    assert enviados and all("30-71234567-8" not in p and "12.345.678" not in p
                            and "contacto@ficticia.example" not in p for p in enviados)
    datos = res["datos"]
    assert datos["partes"]["parte_a"]["identificacion"] == "30-71234567-8"
    assert datos["partes"]["parte_b"]["identificacion"] == "DNI 12.345.678"
    assert datos["observaciones_generales"] == "Contactar a contacto@ficticia.example."
    assert datos["anonimizacion"]["total"] == 6
    assert datos["anonimizacion"]["por_tipo"]["TEL"] == 2
    assert datos["anonimizacion"]["marcadores_sin_restaurar"] == 0
