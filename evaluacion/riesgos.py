"""
riesgos.py — evaluacion/riesgos.py
Evalúa los RIESGOS que devuelve el modelo contra los riesgos esperados anotados a mano.

Para cada riesgo esperado (golden set):
    detectado   -> algún riesgo del modelo menciona alguna de las palabras clave (`alguno`)
    respaldado  -> entre los artículos del CCyCN citados en ese riesgo hay al menos uno de los
                   `articulos` anotados como aceptables (si no se anotó ninguno, no se exige cita)
    no_respaldadas -> artículos citados que NO figuran entre los aceptables ni entre los neutros:
                   no significa "mal citado", significa "revisar a mano"

LÍMITE: las anotaciones son un criterio jurídico de una sola persona/versión. Un artículo fuera de
la lista puede ser igualmente pertinente; por eso se reporta como "a revisar" y no como error.
Los riesgos del modelo que no coinciden con ninguno esperado se listan aparte (no se penalizan).
"""

import json
from pathlib import Path

from core.controles import citas_ccycn_en
from evaluacion.comparador import _contiene

REFERENCIA = Path(__file__).parent / "referencia_ccycn.json"
# Artículos genéricos que se toleran en cualquier riesgo (principios, no fundamento específico)
NEUTROS = {729, 961}


def cargar_referencia(path: Path = REFERENCIA) -> dict[int, str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {int(k): v for k, v in data["articulos"].items()}


def evaluar_riesgos(riesgos_modelo: list[str], esperados: list[dict], referencia: dict[int, str] | None = None) -> dict:
    referencia = referencia if referencia is not None else {}
    riesgos_modelo = [r for r in (riesgos_modelo or []) if isinstance(r, str)]
    usados: set[int] = set()
    detalle = []

    for esp in esperados:
        coinciden = [i for i, r in enumerate(riesgos_modelo) if any(_contiene(r, k) for k in esp["alguno"])]
        usados.update(coinciden)
        citados = sorted({int(a) for i in coinciden for a in citas_ccycn_en(riesgos_modelo[i])})
        aceptables = {int(a) for a in esp.get("articulos", [])}
        respaldados = [a for a in citados if a in aceptables]
        a_revisar = [a for a in citados if a not in aceptables and a not in NEUTROS]
        detalle.append({
            "id": esp["id"],
            "descripcion": esp["descripcion"],
            "detectado": bool(coinciden),
            "requiere_cita": bool(aceptables),
            "respaldado": (bool(respaldados) if aceptables else None) if coinciden else False,
            "citados": citados,
            "respaldados": respaldados,
            "a_revisar": [{"articulo": a, "rubro": referencia.get(a)} for a in a_revisar],
        })

    adicionales = [{"texto": riesgos_modelo[i][:160],
                    "citados": sorted({int(a) for a in citas_ccycn_en(riesgos_modelo[i])})}
                   for i in range(len(riesgos_modelo)) if i not in usados]
    return {
        "esperados": len(esperados),
        "detectados": sum(d["detectado"] for d in detalle),
        "requieren_cita": sum(d["detectado"] and d["requiere_cita"] for d in detalle),
        "respaldados": sum(bool(d["respaldado"]) for d in detalle),
        "citas_a_revisar": sum(len(d["a_revisar"]) for d in detalle),
        "citas_evaluadas": sum(len(d["citados"]) for d in detalle),
        "detalle": detalle,
        "riesgos_adicionales": adicionales,
    }
