"""
evaluar.py — evaluacion/evaluar.py
Corre el analizador sobre el golden set, lo compara con las respuestas esperadas y guarda un
reporte (JSON + Markdown) comparable entre proveedores, modelos y versiones de PROMPT_VERSION.

Uso:
    python evaluacion/evaluar.py                       # todos los casos con el proveedor de .env
    python evaluacion/evaluar.py --casos lc01,sv02     # solo algunos (prefijo del id)
    python evaluacion/evaluar.py --comparar evaluacion/reportes/*.json   # tabla comparativa

ATENCIÓN: cada corrida llama a la API real del proveedor configurado (consume tokens).
Los contratos del golden set son ficticios; los reportes no contienen datos reales.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from contratos import analizador
from evaluacion.comparador import comparar_campo, es_nulo, valor_en_ruta

GOLDEN = Path(__file__).parent / "golden"
REPORTES = Path(__file__).parent / "reportes"


def cargar_casos(prefijos: list[str] | None = None) -> list[dict]:
    casos = []
    for f in sorted(GOLDEN.glob("*.esperado.json")):
        esperado = json.loads(f.read_text(encoding="utf-8"))
        if prefijos and not any(esperado["id"].startswith(p) for p in prefijos):
            continue
        esperado["pdf"] = str(GOLDEN / f"{esperado['id']}.pdf")
        casos.append(esperado)
    return casos


def evaluar_caso(caso: dict, resultado: dict) -> dict:
    """Puntúa el resultado de analizar_contrato contra la expectativa del caso."""
    exito = bool(resultado.get("exito"))
    datos = resultado.get("datos") or {}
    controles = datos.get("controles") or {}
    meta = resultado.get("meta") or {}

    campos = []
    for ruta, spec in caso["campos"].items():
        valor = valor_en_ruta(datos, ruta) if exito else None
        ok, motivo = comparar_campo(valor, spec) if exito else (False, "el análisis falló")
        campos.append({"campo": ruta, "ok": ok, "motivo": motivo,
                       "esperaba_nulo": bool(spec.get("nulo")),
                       "obtuvo_nulo": es_nulo(valor), "obtenido": valor})

    nulos = [c for c in campos if c["esperaba_nulo"]]
    citas = controles.get("citas_ccycn") or {}
    lit = controles.get("literalidad") or {}
    return {
        "id": caso["id"],
        "trampa": caso.get("trampa"),
        "exito": exito,
        "error": None if exito else resultado.get("error"),
        "campos_ok": sum(c["ok"] for c in campos),
        "campos_total": len(campos),
        "nulos_esperados": len(nulos),
        "nulos_respetados": sum(c["ok"] for c in nulos),
        "citas_encontradas": len(citas.get("encontradas", [])),
        "citas_invalidas": len(citas.get("invalidas", [])),
        "literalidad_no_encontrados": len(lit.get("no_encontrados", [])),
        "literalidad_campos": [i["campo"] for i in lit.get("no_encontrados", [])],
        "intentos": meta.get("intentos") or 0,
        "tokens_entrada": meta.get("tokens_entrada") or 0,
        "tokens_salida": meta.get("tokens_salida") or 0,
        "fallos": [{"campo": c["campo"], "motivo": c["motivo"], "obtenido": c["obtenido"]}
                   for c in campos if not c["ok"]],
    }


def resumir(casos: list[dict]) -> dict:
    def tasa(num, den):
        return round(num / den, 3) if den else None

    n = len(casos)
    return {
        "casos": n,
        "casos_con_error": sum(not c["exito"] for c in casos),
        "exactitud_campos": tasa(sum(c["campos_ok"] for c in casos), sum(c["campos_total"] for c in casos)),
        "respeto_de_nulos": tasa(sum(c["nulos_respetados"] for c in casos), sum(c["nulos_esperados"] for c in casos)),
        "citas_encontradas": sum(c["citas_encontradas"] for c in casos),
        "tasa_citas_invalidas": tasa(sum(c["citas_invalidas"] for c in casos), sum(c["citas_encontradas"] for c in casos)),
        "literalidad_no_encontrados": sum(c["literalidad_no_encontrados"] for c in casos),
        "reintentos": sum(max(c["intentos"] - 1, 0) for c in casos),
        "tokens_entrada": sum(c["tokens_entrada"] for c in casos),
        "tokens_salida": sum(c["tokens_salida"] for c in casos),
    }


def correr(prefijos: list[str] | None = None, analizar=None) -> dict:
    """Corre el set. `analizar` permite inyectar una función falsa en los tests."""
    analizar = analizar or (lambda pdf: analizador.analizar_contrato(pdf))
    casos = cargar_casos(prefijos)
    if not casos:
        raise SystemExit("No hay casos que coincidan.")

    resultados, meta = [], {}
    for caso in casos:
        print(f"[evaluar] {caso['id']} ...")
        r = analizar(caso["pdf"])
        meta = {**meta, **{k: v for k, v in (r.get("meta") or {}).items() if v}}
        resultados.append(evaluar_caso(caso, r))
        e = resultados[-1]
        print(f"[evaluar]   campos {e['campos_ok']}/{e['campos_total']}"
              + ("" if e["exito"] else f"  ✗ ERROR: {e['error']}"))

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "proveedor": meta.get("proveedor"),
        "modelo": meta.get("modelo"),
        "prompt_version": meta.get("prompt_version") or analizador.PROMPT_VERSION,
        "resumen": resumir(resultados),
        "casos": resultados,
    }


def a_markdown(rep: dict) -> str:
    r = rep["resumen"]
    pct = lambda x: "n/a" if x is None else f"{x:.1%}"  # noqa: E731
    out = [
        f"# Evaluación — {rep['proveedor']} / {rep['modelo']} (prompt {rep['prompt_version']})",
        f"\n_{rep['timestamp']} · golden set ficticio · {r['casos']} casos_\n",
        "| Métrica | Valor |", "|---|---|",
        f"| Exactitud de campos | {pct(r['exactitud_campos'])} |",
        f"| Respeto de nulos (no inventar) | {pct(r['respeto_de_nulos'])} |",
        f"| Citas CCyCN inválidas | {pct(r['tasa_citas_invalidas'])} de {r['citas_encontradas']} |",
        f"| Valores no hallados en el texto (literalidad) | {r['literalidad_no_encontrados']} |",
        f"| Casos con error | {r['casos_con_error']} |",
        f"| Reintentos | {r['reintentos']} |",
        f"| Tokens (entrada / salida) | {r['tokens_entrada']} / {r['tokens_salida']} |",
        "\n## Por caso\n",
        "| Caso | Campos | Nulos | Citas inv. | Literalidad | Intentos |", "|---|---|---|---|---|---|",
    ]
    for c in rep["casos"]:
        out.append(f"| {c['id']} | {c['campos_ok']}/{c['campos_total']} | {c['nulos_respetados']}/{c['nulos_esperados']} "
                   f"| {c['citas_invalidas']}/{c['citas_encontradas']} | {c['literalidad_no_encontrados']} | {c['intentos']} |")
    fallos = [(c["id"], f) for c in rep["casos"] for f in c["fallos"]]
    if fallos:
        out += ["\n## Fallos\n", "| Caso | Campo | Motivo | Obtenido |", "|---|---|---|---|"]
        for cid, f in fallos:
            obtenido = str(f["obtenido"]).replace("|", "/").replace("\n", " ")[:80]
            out.append(f"| {cid} | {f['campo']} | {f['motivo']} | {obtenido} |")
    return "\n".join(out) + "\n"


def guardar(rep: dict, carpeta: Path = REPORTES) -> tuple[Path, Path]:
    carpeta.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9.]+", "-", f"{rep['proveedor']}_{rep['modelo']}".lower())
    base = carpeta / f"eval_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}_{slug}_p{rep['prompt_version']}"
    j, m = Path(f"{base}.json"), Path(f"{base}.md")  # no usar with_suffix: la versión puede ser "2.1"
    j.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    m.write_text(a_markdown(rep), encoding="utf-8")
    return j, m


def comparar(reportes: list[dict]) -> str:
    """Tabla comparativa entre corridas (proveedor / modelo / versión de prompt)."""
    pct = lambda x: "n/a" if x is None else f"{x:.1%}"  # noqa: E731
    filas = ["| Proveedor | Modelo | Prompt | Exactitud | Nulos | Citas inv. | Errores | Reintentos | Tokens ent./sal. |",
             "|---|---|---|---|---|---|---|---|---|"]
    for rep in sorted(reportes, key=lambda r: r["timestamp"]):
        r = rep["resumen"]
        filas.append(f"| {rep['proveedor']} | {rep['modelo']} | {rep['prompt_version']} | {pct(r['exactitud_campos'])} "
                     f"| {pct(r['respeto_de_nulos'])} | {pct(r['tasa_citas_invalidas'])} | {r['casos_con_error']} "
                     f"| {r['reintentos']} | {r['tokens_entrada']}/{r['tokens_salida']} |")
    return "\n".join(filas) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Evalúa el analizador sobre el golden set (llama a la API real).")
    ap.add_argument("--casos", help="ids o prefijos separados por coma (ej: lc01,sv02)")
    ap.add_argument("--comparar", nargs="+", help="reportes .json a comparar (no llama a la API)")
    args = ap.parse_args()

    if args.comparar:
        reps = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.comparar]
        print(comparar(reps))
        return

    rep = correr(args.casos.split(",") if args.casos else None)
    j, m = guardar(rep)
    print("\n" + a_markdown(rep))
    print(f"Reporte: {j}\n         {m}")


if __name__ == "__main__":
    main()
