"""Tests de detección de citas inválidas del CCyCN (solo existencia y formato)."""

from core.controles import verificar_citas_ccycn


def _r(*textos):
    return verificar_citas_ccycn({"riesgos": list(textos)})


def test_cita_valida():
    r = _r("Mora automática (art. 886 CCyCN).")
    assert r["encontradas"] == ["886"]
    assert r["invalidas"] == []
    assert r["paso"] is True


def test_limites_del_rango():
    assert _r("art. 1 CCyCN y art. 2671 CCyCN")["paso"] is True
    r = _r("art. 2672 CCyCN")
    assert r["paso"] is False
    assert r["invalidas"] == [{"cita": "2672", "motivo": "fuera_de_rango"}]
    assert _r("art. 0 CCyCN")["invalidas"][0]["cita"] == "0"


def test_lista_y_rango():
    r = _r("Ver arts. 1198 y 3000 del Código Civil y Comercial.")
    assert r["encontradas"] == ["1198", "3000"]
    assert [i["cita"] for i in r["invalidas"]] == ["3000"]
    r = _r("arts. 765 a 767 CCyCN")
    assert r["encontradas"] == ["765", "767"] and r["paso"]


def test_hereda_norma_en_citas_consecutivas():
    r = _r("art. 1198 y art. 9999 CCyCN")
    assert [i["cita"] for i in r["invalidas"]] == ["9999"]
    assert "1198" in r["encontradas"]


def test_norma_antes_de_la_cita():
    r = _r("Según el CCyCN, art. 5000, corresponde.")
    assert [i["cita"] for i in r["invalidas"]] == ["5000"]


def test_formato_irreconocible():
    r = _r("art. XX CCyCN")
    assert r["invalidas"] == [{"cita": "XX", "motivo": "formato_irreconocible"}]
    r = _r("art. 1198 bis CCyCN")
    assert r["invalidas"][0]["motivo"] == "formato_irreconocible"
    r = _r("art. 12a4 CCyCN")
    assert r["paso"] is False


def test_separador_de_miles():
    r = _r("art. 1.198 CCyCN")
    assert r["encontradas"] == ["1198"] and r["paso"]


def test_otras_normas_no_se_validan_como_ccycn():
    r = _r("Ley 24.240, art. 37, y art. 5000 de la Ley 27.551.")
    assert r["encontradas"] == []
    assert r["invalidas"] == []
    assert r["otras_normas_no_verificadas"] == 2


def test_texto_sin_citas_pasa():
    r = _r("Sin citas.")
    assert r == {"encontradas": [], "invalidas": [], "otras_normas_no_verificadas": 0, "paso": True}


def test_busca_en_todos_los_strings_anidados():
    datos = {"clausulas": {"mora": "art. 9999 CCyCN"}, "riesgos": ["art. 886 CCyCN"]}
    r = verificar_citas_ccycn(datos)
    assert r["encontradas"] == ["9999", "886"]
    assert [i["cita"] for i in r["invalidas"]] == ["9999"]


def test_palabras_comunes_no_son_citas():
    r = _r("Los artículos pertinentes del CCyCN; art. 765 y siguientes CCyCN")
    assert r["encontradas"] == ["765"] and r["paso"]


def test_bloque_controles_del_analizador():
    from contratos import analizador

    datos = {"riesgos": ["art. 886 CCyCN", "art. 9999 CCyCN"], "objeto": None}
    c = analizador._ejecutar_controles(datos)
    assert c["paso"] is False
    assert c["citas_ccycn"]["encontradas"] == ["886", "9999"]
    assert c["citas_ccycn"]["invalidas"][0]["cita"] == "9999"
