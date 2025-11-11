; === ASUA generado (parcial optimizado) ===
; Expr: result = a + (b - c) + 7
; Líneas: 7
; Accesos memoria (estim.): 7
LOAD b
SUB c
STORE __t0
LOAD a
ADD __t0
ADD __lit_7
STORE result
;
; Literales sugeridos para DATA:
DATA:
__lit_7 7
; ... más a..g, result, error

