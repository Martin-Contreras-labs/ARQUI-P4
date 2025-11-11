#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import sys
from typing import List, Tuple, Union

# ---------- Utilidades básicas ----------
VAR_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

def is_int(tok: str) -> bool:
    try:
        int(tok, 10)
        return True
    except ValueError:
        return False

def is_var(tok: str) -> bool:
    return bool(VAR_RE.match(tok))

class CompileError(Exception): pass

# ---------- Léxico ----------
def tokenize(s: str) -> List[str]:
    s = s.strip()
    spaced = (
        s.replace("(", " ( ")
         .replace(")", " ) ")
         .replace("+", " + ")
         .replace("-", " - ")
         .replace("=", " = ")
    )
    return [t for t in spaced.split() if t]

# ---------- Shunting-yard (a RPN) ----------
PREC = {"+":1, "-":1}
ASSOC_LEFT = {"+":True, "-":True}

def to_rpn(tokens_rhs: List[str]) -> List[str]:
    out, ops = [], []
    for t in tokens_rhs:
        if is_int(t) or is_var(t):
            out.append(t)
        elif t in PREC:
            while ops and ops[-1] in PREC and (PREC[ops[-1]] > PREC[t] or (PREC[ops[-1]] == PREC[t] and ASSOC_LEFT[t])):
                out.append(ops.pop())
            ops.append(t)
        elif t == "(":
            ops.append(t)
        elif t == ")":
            while ops and ops[-1] != "(":
                out.append(ops.pop())
            if not ops: raise CompileError("Paréntesis desbalanceados")
            ops.pop()
        else:
            raise CompileError(f"Token no soportado: {t}")
    while ops:
        top = ops.pop()
        if top in ("(", ")"): raise CompileError("Paréntesis desbalanceados al final")
        out.append(top)
    return out

# ---------- AST desde RPN ----------
class Node: ...
class Leaf(Node):
    def __init__(self, tok: str): self.tok = tok  # var o literal
class Bin(Node):
    def __init__(self, op: str, left: Node, right: Node):
        self.op, self.left, self.right = op, left, right

def rpn_to_ast(rpn: List[str]) -> Node:
    st: List[Node] = []
    for t in rpn:
        if is_int(t) or is_var(t):
            st.append(Leaf(t))
        elif t in {"+","-"}:
            if len(st) < 2: raise CompileError("Faltan operandos")
            r = st.pop(); l = st.pop()
            st.append(Bin(t,l,r))
        else:
            raise CompileError(f"Operador no soportado en parcial: {t}")
    if len(st) != 1: raise CompileError("Expresión inválida")
    return st[0]

# ---------- Backend optimizado (ACC-first) ----------
class CodeGen:
    def __init__(self):
        self.code: List[str] = []
        self.lits = set()
        self.temp_id = 0
        self.mem_access = 0

    def emit(self, ins: str):
        self.code.append(ins)
        op = ins.split()[0]
        if op in ("LOAD","STORE","ADD","SUB"):
            self.mem_access += 1

    def lit_sym(self, k: int) -> str:
        name = f"__lit_{k}"
        self.lits.add(name)
        return name

    def new_tmp(self) -> str:
        t = f"__t{self.temp_id}"
        self.temp_id += 1
        return t

    def gen_leaf_into_acc(self, leaf: Leaf):
        t = leaf.tok
        if is_int(t):
            sym = self.lit_sym(int(t))
            self.emit(f"LOAD {sym}")
        else:
            self.emit(f"LOAD {t}")

    def is_leaf(self, n: Node) -> bool:
        return isinstance(n, Leaf)

    def gen(self, n: Node):
        """Genera código dejando el valor de 'n' en ACC, minimizando temporales."""
        if isinstance(n, Leaf):
            self.gen_leaf_into_acc(n)
            return

        # n es Bin
        op, L, R = n.op, n.left, n.right
        # Heurística explicada en el mensaje:
        if op == "+":
            if self.is_leaf(R):
                # ACC = L; ADD R
                self.gen(L)                          # ACC <- L
                self.emit(f"ADD {self.leaf_to_sym(R)}")
            else:
                # Evalúa R a temp, luego L en ACC, luego ADD temp
                self.gen(R); t = self.spill_acc()
                self.gen(L)
                self.emit(f"ADD {t}")
        elif op == "-":
            if self.is_leaf(R):
                # ACC = L; SUB R
                self.gen(L)
                self.emit(f"SUB {self.leaf_to_sym(R)}")
            else:
                # ACC = R -> temp ; ACC = L ; SUB temp
                self.gen(R); t = self.spill_acc()
                self.gen(L)
                self.emit(f"SUB {t}")
        else:
            raise CompileError(f"Operador no soportado: {op}")

    def leaf_to_sym(self, leaf: Leaf) -> str:
        t = leaf.tok
        if is_int(t):
            return self.lit_sym(int(t))
        return t

    def spill_acc(self) -> str:
        """Guarda ACC en un temporal (solo cuando es estrictamente necesario)."""
        t = self.new_tmp()
        self.emit(f"STORE {t}")
        return t

def compile_line(expr: str) -> str:
    tokens = tokenize(expr)
    if "=" not in tokens: raise CompileError("Falta '=' en la asignación.")
    eq = tokens.index("=")
    if eq == 0 or eq == len(tokens)-1: raise CompileError("Asignación inválida")

    lhs = tokens[0]
    if not is_var(lhs): raise CompileError("LHS inválido")

    rhs = tokens[eq+1:]
    rpn = to_rpn(rhs)
    ast = rpn_to_ast(rpn)

    cg = CodeGen()
    # Genera RHS en ACC minimizando stores
    cg.gen(ast)
    # Final: guarda en result
    cg.emit(f"STORE {lhs}")

    lines = len(cg.code)
    header = [
        f"; === ASUA generado (parcial optimizado) ===",
        f"; Expr: {expr}",
        f"; Líneas: {lines}",
        f"; Accesos memoria (estim.): {cg.mem_access}",
    ]

    data_block = ""
    if cg.lits:
        # ojo: para imprimir el valor numérico del literal tomamos el sufijo
        rows = []
        for name in sorted(cg.lits, key=lambda s: int(s.split('_')[-1])):
            val = name.split('_')[-1]
            rows.append(f"{name} {val}")
        data_block = ";\n; Literales sugeridos para DATA:\nDATA:\n" + "\n".join(rows) + "\n; ... más a..g, result, error\n"

    return "\n".join(header + cg.code + ([data_block] if data_block else []))

def main():
    if len(sys.argv) < 2:
        print("Uso:\n  python compiler.py \"result = a + b - (c + 5) - d\"")
        sys.exit(1)
    expr = sys.argv[1]
    try:
        asm = compile_line(expr)
    except CompileError as e:
        print(f"[Error de compilación] {e}")
        sys.exit(2)
    print(asm)

if __name__ == "__main__":
    main()
