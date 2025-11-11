; === ASUA generado (parcial optimizado) ===
; Expr: result = (g - 5) + (f + b)
; Líneas: 7
; Accesos memoria (estim.): 7
LOAD f
ADD b
STORE __t0
LOAD g
SUB __lit_5
ADD __t0
STORE result
;
; Literales sugeridos para DATA:
DATA:
__lit_5 5
; ... más a..g, result, error

