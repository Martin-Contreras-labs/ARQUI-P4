#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, sys
from typing import List

# ====================== CONFIGURACIÓN ISA =========================
# Elige un preset (1, 2 o 3)
# ====================== CONFIGURACIÓN ISA =========================
ISA = {
    "lowercase": False,          # True si tu emulador exige minúsculas
    "needs_sections": False,     # True si exige DATA:/CODE:, False si no
    "ACC": "A",                  # nombre del acumulador
    "fmt": {
        "load":  "{mn} {acc}, {arg}",   # MOV A, var
        "store": "{mn} {arg}, {acc}",   # MOV var, A
        "add":   "{mn} {acc}, {arg}",   # ADD A, var
        "sub":   "{mn} {acc}, {arg}",   # SUB A, var
    },
    "mn": { "load":"MOV", "store":"MOV", "add":"ADD", "sub":"SUB" },
    "labels": { "data":"DATA:", "code":"CODE:" }  # se ignoran si needs_sections=False
}
# =================================================================

# =================================================================

VAR_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

def is_int(tok: str) -> bool:
    try: int(tok); return True
    except: return False

def is_var(tok: str) -> bool:
    return bool(VAR_RE.match(tok))

class CompileError(Exception): pass

# ----------- Léxico -----------
def tokenize(s: str) -> List[str]:
    s = s.strip()
    s = (s.replace("(", " ( ").replace(")", " ) ")
           .replace("+"," + ").replace("-"," - ").replace("="," = "))
    return [t for t in s.split() if t]

# ----------- Shunting Yard -----------
PREC = {"+":1, "-":1}; LEFT = {"+":True, "-":True}
def to_rpn(tokens_rhs: List[str]) -> List[str]:
    out, st = [], []
    for t in tokens_rhs:
        if is_int(t) or is_var(t): out.append(t)
        elif t in PREC:
            while st and st[-1] in PREC and (PREC[st[-1]] > PREC[t] or (PREC[st[-1]]==PREC[t] and LEFT[t])):
                out.append(st.pop())
            st.append(t)
        elif t == "(":
            st.append(t)
        elif t == ")":
            while st and st[-1] != "(":
                out.append(st.pop())
            if not st: raise CompileError("Paréntesis desbalanceados")
            st.pop()
        else:
            raise CompileError(f"Token no soportado: {t}")
    while st:
        top = st.pop()
        if top in ("(",")"): raise CompileError("Paréntesis desbalanceados al final")
        out.append(top)
    return out

# ----------- AST sencillo -----------
class Node: ...
class Leaf(Node):
    def __init__(self, tok: str): self.tok = tok
class Bin(Node):
    def __init__(self, op: str, l: Node, r: Node): self.op, self.l, self.r = op,l,r

def rpn_to_ast(rpn: List[str]) -> Node:
    st: List[Node] = []
    for t in rpn:
        if is_int(t) or is_var(t):
            st.append(Leaf(t))
        elif t in {"+","-"}:
            if len(st)<2: raise CompileError("Faltan operandos")
            r, l = st.pop(), st.pop()
            st.append(Bin(t,l,r))
        else:
            raise CompileError(f"Operador no soportado: {t}")
    if len(st)!=1: raise CompileError("Expresión inválida")
    return st[0]

# ----------- Backend ACC-first configurable -----------
class CodeGen:
    def __init__(self):
        self.code: List[str] = []
        self.lits = set()
        self.mem_access = 0
        self.tmp_id = 0

    def _mn(self, k): return ISA["mn"][k]
    def _acc(self): return ISA["ACC"]

    def _emit_op(self, kind: str, arg: str):
        line = ISA["fmt"][kind].format(
            mn=self._mn(kind),
            acc=self._acc(),
            arg=arg
        )
        if ISA["lowercase"]: line = line.lower()
        self.code.append(line)
        # Acceso a memoria por instrucción aritmética o load/store
        if kind in ("load","store","add","sub"):
            self.mem_access += 1

    def _tmp(self) -> str:
        t = f"__t{self.tmp_id}"; self.tmp_id += 1; return t

    def _lit(self, k: int) -> str:
        name = f"__lit_{k}"
        self.lits.add(name)
        return name

    def is_leaf(self, n: Node) -> bool: return isinstance(n, Leaf)

    def leaf_sym(self, leaf: Leaf) -> str:
        t = leaf.tok
        return self._lit(int(t)) if is_int(t) else t

    def load_leaf(self, leaf: Leaf):
        self._emit_op("load", self.leaf_sym(leaf))

    def spill_acc(self) -> str:
        t = self._tmp()
        self._emit_op("store", t)
        return t

    def gen(self, n: Node):
        if isinstance(n, Leaf):
            self.load_leaf(n); return

        op, L, R = n.op, n.l, n.r
        if op == "+":
            if self.is_leaf(R):
                self.gen(L); self._emit_op("add", self.leaf_sym(R))
            else:
                self.gen(R); t = self.spill_acc()
                self.gen(L); self._emit_op("add", t)
        elif op == "-":
            if self.is_leaf(R):
                self.gen(L); self._emit_op("sub", self.leaf_sym(R))
            else:
                self.gen(R); t = self.spill_acc()
                self.gen(L); self._emit_op("sub", t)
        else:
            raise CompileError(f"Operador no soportado: {op}")

def compile_line(expr: str) -> str:
    tokens = tokenize(expr)
    if "=" not in tokens: raise CompileError("Falta '='")
    i = tokens.index("=")
    lhs = tokens[0]
    if not is_var(lhs): raise CompileError("LHS inválido")
    rhs_tokens = tokens[i+1:]
    ast = rpn_to_ast(to_rpn(rhs_tokens))

    cg = CodeGen()
    cg.gen(ast)
    cg._emit_op("store", lhs)

    header = [
        f"; expr: {expr}",
        f"; lineas: {len(cg.code)}",
        f"; accesos_mem: {cg.mem_access}",
    ]
    data_rows = []
    for name in sorted(cg.lits, key=lambda s: int(s.split('_')[-1])):
        data_rows.append(f"{name} {name.split('_')[-1]}")

    parts = []
    if ISA["needs_sections"]:
        parts.append(ISA["labels"]["code"])
    parts += header + cg.code
    if data_rows:
        if ISA["needs_sections"]:
            parts.append("")  # línea en blanco
            parts.append(ISA["labels"]["data"])
        parts += data_rows
        parts.append("; ... agrega a..g, result, error según base-data")

    return "\n".join(parts)

def main():
    if len(sys.argv)<2:
        print("Uso:\n  python compiler.py \"result = a + (b - c) + 7\"")
        sys.exit(1)
    try:
        print(compile_line(sys.argv[1]))
    except CompileError as e:
        print(f"[Error] {e}"); sys.exit(2)

if __name__ == "__main__":
    main()
