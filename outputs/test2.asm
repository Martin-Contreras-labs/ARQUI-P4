; === ASUA generado (parcial optimizado) ===
; Expr: result = (d + e) - (a + 2)
; Líneas: 7
; Accesos memoria (estim.): 7
LOAD a
ADD __lit_2
STORE __t0
LOAD d
ADD e
SUB __t0
STORE result
;
; Literales sugeridos para DATA:
DATA:
__lit_2 2
; ... más a..g, result, error

