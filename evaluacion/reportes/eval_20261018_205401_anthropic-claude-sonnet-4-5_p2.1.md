# Evaluación — anthropic / claude-sonnet-4-5 (prompt 2.1)

_2026-10-18T20:54:01+00:00 · golden set ficticio · 5 casos_

| Métrica | Valor |
|---|---|
| Exactitud de campos | 100.0% |
| Respeto de nulos (no inventar) | 100.0% |
| Citas CCyCN inválidas | 0.0% de 40 |
| Riesgos esperados detectados (recall) | 76.9% (10/13) |
| Riesgos detectados con artículo anotado como correcto | 42.9% |
| Citas de riesgos a revisar a mano | 20 de 24 |
| Riesgos adicionales del modelo (sin anotar) | 11 |
| Valores no hallados en el texto (literalidad) | 1 |
| Casos con error | 0 |
| Reintentos | 0 |
| Tokens (entrada / salida) | 7401 / 6410 |

## Por caso

| Caso | Campos | Nulos | Citas inv. | Literalidad | Intentos |
|---|---|---|---|---|---|
| lc01_locacion_comercial | 14/14 | 0/0 | 0/6 | 0 | 1 |
| lv04_locacion_vivienda | 14/14 | 0/0 | 0/5 | 0 | 1 |
| mt05_mantenimiento_incompleto | 11/11 | 5/5 | 0/10 | 0 | 1 |
| sm03_suministro | 11/11 | 0/0 | 0/11 | 1 | 1 |
| sv02_servicios_profesionales | 13/13 | 3/3 | 0/8 | 0 | 1 |

## Riesgos

| Caso | Riesgo esperado | Detectado | Artículo respaldado | Citados | A revisar |
|---|---|---|---|---|---|
| lc01_locacion_comercial | R1 Mora automática sin interpelación con interés punitorio del 1,5% mensual | sí | sí | 771, 886, 1221 | 1221 (Resolución anticipada) |
| lc01_locacion_comercial | R2 Exoneración de responsabilidad del locador por caso fortuito / fuerza mayor | sí | no | 1200, 1204, 1733 | 1200 (Entregar la cosa), 1204 (sin rubro en referencia), 1733 (sin rubro en referencia) |
| lv04_locacion_vivienda | R1 Interés punitorio del 0,5% diario (desproporcionado) | sí | no | 332, 1154 | 332 (sin rubro en referencia), 1154 (sin rubro en referencia) |
| lv04_locacion_vivienda | R2 Preaviso de 60 días para que la locataria resuelva (más gravoso que el régimen legal) | NO | no | — | — |
| lv04_locacion_vivienda | R3 Depósito en garantía sin plazo de devolución ni actualización | sí | n/a | 765, 766, 1197 | 765 (sin rubro en referencia), 766 (sin rubro en referencia), 1197 (sin rubro en referencia) |
| mt05_mantenimiento_incompleto | R1 Plazo y precio indeterminados (a acordar por adenda / por orden de trabajo) | sí | sí | 958, 990, 991, 1011, 1133, 1251 | 958 (sin rubro en referencia), 990 (sin rubro en referencia), 991 (sin rubro en referencia), 1011 (sin rubro en referencia), 1133 (sin rubro en referencia) |
| mt05_mantenimiento_incompleto | R2 Responsabilidad de la contratista sin tope y exigencia de seguro | sí | no | 1744 | 1744 (sin rubro en referencia) |
| sm03_suministro | R1 Limitación de la responsabilidad del proveedor al valor de la partida no entregada | sí | no | 1117, 1118, 1122 | 1117 (sin rubro en referencia), 1118 (sin rubro en referencia), 1122 (sin rubro en referencia) |
| sm03_suministro | R2 Precio fijo en dólares por 18 meses sin ajuste (riesgo de desequilibrio / imprevisión) | sí | sí | 1091 | — |
| sm03_suministro | R3 Plazo muy breve (48 horas) para rechazar partidas | sí | n/a | 1153 | 1153 (sin rubro en referencia) |
| sv02_servicios_profesionales | R1 Rescisión sin causa con preaviso de 15 días y sin indemnización | NO | no | — | — |
| sv02_servicios_profesionales | R2 No hay cláusula de jurisdicción ni ley aplicable | sí | n/a | 2609 | 2609 (sin rubro en referencia) |
| sv02_servicios_profesionales | R3 Independencia / riesgo de recalificación de la relación como dependiente | NO | no | — | — |
