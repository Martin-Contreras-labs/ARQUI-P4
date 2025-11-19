; Lineas de código generadas: 174
; Accesos a memoria (aprox): 92

MOV A,(v1)
MOV B,(v2)
ADD A,B
MOV (t0),A
MOV A,(v3)
MOV B,(v4)
SUB A,B
MOV (t1),A
MOV A,(t1)
MOV B,128
CMP A,B
JGE abs_neg_0
MOV A,(t1)
JMP abs_end_1
abs_neg_0:
MOV A,(zero)
MOV B,(t1)
SUB A,B
abs_end_1:
MOV (t2),A
MOV A,(t0)
MOV B,(t2)
SUB A,B
MOV (t3),A
MOV A,(t3)
MOV B,128
CMP A,B
JGE min_a_2
MOV A,(t2)
MOV (t4),A
JMP min_end_3
min_a_2:
MOV A,(t0)
MOV (t4),A
min_end_3:
MOV A,(v5)
MOV B,(v6)
CALL mul
MOV (t5),A
MOV A,(v7)
MOV B,(v8)
CALL mod
MOV (t6),A
MOV A,(v9)
MOV B,128
CMP A,B
JGE abs_neg_4
MOV A,(v9)
JMP abs_end_5
abs_neg_4:
MOV A,(zero)
MOV B,(v9)
SUB A,B
abs_end_5:
MOV (t7),A
MOV A,(t6)
MOV B,(t7)
SUB A,B
MOV (t8),A
MOV A,(t8)
MOV B,128
CMP A,B
JGE min_a_6
MOV A,(t7)
MOV (t9),A
JMP min_end_7
min_a_6:
MOV A,(t6)
MOV (t9),A
min_end_7:
MOV A,(t5)
MOV B,(t9)
CALL div
MOV (t10),A
MOV A,(t4)
MOV B,(t10)
SUB A,B
MOV (t11),A
MOV A,(t11)
MOV B,128
CMP A,B
JGE max_a_8
MOV A,(t4)
MOV (t12),A
JMP max_end_9
max_a_8:
MOV A,(t10)
MOV (t12),A
max_end_9:
MOV A,(t12)
MOV (result),A

end:
JMP end

mul:
    MOV (m_tempA),A
    MOV (m_tempB),B
    MOV A,(zero)
    MOV (m_res),A
mul_loop:
    MOV A,(m_tempB)
    CMP A,(zero)
    JEQ mul_end
    MOV A,(m_res)
    MOV B,(m_tempA)
    ADD A,B
    MOV (m_res),A
    MOV A,(m_tempB)
    SUB A,1
    MOV (m_tempB),A
    JMP mul_loop
mul_end:
    MOV A,(m_res)
    RET

div:
    MOV (d_tempA),A
    MOV (d_tempB),B
    MOV A,(d_tempB)
    CMP A,(zero)
    JEQ div_error
    MOV A,(zero)
    MOV (d_qiu),A
div_loop:
    MOV A,(d_tempB)
    MOV B,(d_tempA)
    CMP A,B
    JLE div_do_sub
    JMP div_end
div_do_sub:
    MOV A,(d_tempA)
    MOV B,(d_tempB)
    SUB A,B
    MOV (d_tempA),A
    MOV A,(d_qiu)
    ADD A,(one)
    MOV (d_qiu),A
    JMP div_loop
div_end:
    MOV A,(d_qiu)
    RET
div_error:
    MOV A,1
    MOV (error),A
    MOV A,(zero)
    RET

mod:
    MOV (r_tempA),A
    MOV (r_tempB),B
    MOV A,(r_tempB)
    CMP A,(zero)
    JEQ mod_error
mod_loop:
    MOV A,(r_tempB)
    MOV B,(r_tempA)
    CMP A,B
    JLE mod_do_sub
    JMP mod_end
mod_do_sub:
    MOV A,(r_tempA)
    MOV B,(r_tempB)
    SUB A,B
    MOV (r_tempA),A
    JMP mod_loop
mod_end:
    MOV A,(r_tempA)
    RET
mod_error:
    MOV A,1
    MOV (error),A
    MOV A,(zero)
    RET

DATA:
t0 0
t1 0
t10 0
t11 0
t12 0
t2 0
t3 0
t4 0
t5 0
t6 0
t7 0
t8 0
t9 0
v1 0
v2 0
v3 0
v4 0
v5 0
v6 0
v7 0
v8 0
v9 0
zero 0
m_tempA 0
m_tempB 0
m_res 0
d_tempA 0
d_tempB 0
d_qiu 0
one 1
r_tempA 0
r_tempB 0
result 0
error 0