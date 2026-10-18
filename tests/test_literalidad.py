"""Tests del control de literalidad (valores extraídos vs. texto del contrato). Datos ficticios."""

from core.controles import verificar_literalidad

TEXTO = (
    "Entre INVERSIONES DEL SUR S.A., CUIT 30-71234567-8, y María Pérez, se celebra locación desde el "
    "1° de abril de 2025 hasta el 31 de marzo de 2028 por tres (3) años. Canon: $250.000 mensuales, "
    "pagaderos dentro de los primeros cinco días hábiles."
)


def _datos(**cambios):
    d = {
        "partes": {
            "parte_a": {"nombre": "Inversiones del Sur S.A.", "identificacion": "CUIT 30-71234567-8", "rol": "locador"},
            "parte_b": {"nombre": "Maria Perez", "identificacion": None, "rol": "locatario"},
        },
        "plazo": {"inicio": "1 de abril de 2025", "vencimiento": "31 de marzo de 2028", "duracion": "3 años"},
        "canon": {"monto_inicial": "$250.000 mensuales", "vencimiento_pago": "Primeros 5 días hábiles"},
    }
    for ruta, valor in cambios.items():
        a, b = ruta.split("__")
        d[a][b] = valor
    return d


def test_valores_fieles_pasan_aunque_cambie_formato_mayusculas_y_acentos():
    r = verificar_literalidad(_datos(), TEXTO)
    assert r["paso"] and r["no_encontrados"] == []
    assert r["verificados"] >= 5


def test_monto_inventado_se_detecta():
    r = verificar_literalidad(_datos(canon__monto_inicial="$300.000 mensuales"), TEXTO)
    assert r["no_encontrados"] == [{"campo": "canon.monto_inicial", "motivo": "numero_no_encontrado"}]
    assert r["paso"] is False


def test_formato_de_monto_distinto_es_tolerado():
    assert verificar_literalidad(_datos(canon__monto_inicial="ARS 250000 por mes"), TEXTO)["paso"]


def test_fecha_alterada_se_detecta():
    r = verificar_literalidad(_datos(plazo__vencimiento="31 de marzo de 2030"), TEXTO)
    assert [i["campo"] for i in r["no_encontrados"]] == ["plazo.vencimiento"]


def test_cuit_alterado_se_detecta():
    d = _datos()
    d["partes"]["parte_a"]["identificacion"] = "CUIT 30-99999999-9"
    r = verificar_literalidad(d, TEXTO)
    assert r["no_encontrados"][0]["campo"] == "partes.parte_a.identificacion"


def test_nombre_inventado_se_detecta():
    d = _datos()
    d["partes"]["parte_b"]["nombre"] = "Juan Gómez"
    r = verificar_literalidad(d, TEXTO)
    assert r["no_encontrados"] == [{"campo": "partes.parte_b.nombre", "motivo": "nombre_no_encontrado"}]


def test_nulls_y_numeros_de_un_digito_no_cuentan():
    d = _datos(plazo__inicio=None, plazo__duracion="7 años")  # 1 dígito: no verificable, no es error
    r = verificar_literalidad(d, TEXTO)
    assert r["paso"] and r["no_verificables"] >= 1


def test_bloque_en_el_pipeline_y_log(tmp_path):
    """El pipeline agrega controles.literalidad y recalcula el `paso` global."""
    import json
    from unittest.mock import patch

    from contratos import analizador

    resp = {
        "partes": {"parte_a": {"nombre": "EMPRESA INVENTADA S.A.", "identificacion": None, "rol": None},
                   "parte_b": {"nombre": None, "identificacion": None, "rol": None}},
        "objeto": None,
        "plazo": {"inicio": None, "vencimiento": None, "duracion": None, "observaciones": None},
        "canon": {"monto_inicial": None, "ajuste": None, "vencimiento_pago": None},
        "clausulas": {"rescision": None, "mora": None, "limitacion_responsabilidad": None,
                      "jurisdiccion": None, "notificaciones": None},
        "riesgos": [], "observaciones_generales": None,
    }
    ia = {"exito": True, "respuesta": json.dumps(resp), "proveedor": "mock", "modelo": "m",
          "truncada": False, "tokens": {"entrada": 1, "salida": 1}, "error": None}
    ext = {"exito": True, "texto": TEXTO, "paginas": 1, "metodo": "pdfplumber", "error": None}
    logs = tmp_path / "logs"
    with patch.object(analizador, "extraer_texto", return_value=ext), \
         patch.object(analizador, "llamar_ia", return_value=ia):
        res = analizador.analizar_contrato(str(tmp_path / "x.pdf"), dir_logs=str(logs))

    c = res["datos"]["controles"]
    assert c["literalidad"]["no_encontrados"][0]["campo"] == "partes.parte_a.nombre"
    assert c["citas_ccycn"]["paso"] is True and c["paso"] is False
    linea = json.loads(next(logs.glob("*.jsonl")).read_text(encoding="utf-8"))
    assert linea["controles"]["literalidad"] == {"paso": False, "verificados": 1, "no_encontrados": 1}
