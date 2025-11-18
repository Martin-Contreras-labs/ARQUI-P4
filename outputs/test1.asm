; expr: result = a - (b + c - d)
; lineas: 7
; accesos_mem: 7
MOV A, b
ADD A, c
SUB A, d
MOV __t0, A
MOV A, a
SUB A, __t0
MOV result, A
