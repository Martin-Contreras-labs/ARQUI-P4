#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, sys
from typing import List

# ---------- utilidades ----------
VAR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def is_int(tok: str) -> bool:
    try:
        int(tok)
        return True
    except ValueError:
        return False

def is_var(tok: str) -> bool:
    return bool(VAR_RE.match(tok))

class CompileError(Exception):
    pass

# ---------- lexer ----------
def tokenize(s: str) -> List[str]:
    s = s.strip()
    for ch in ["(", ")", "+", "-", "*", "/", "%", "=", ","]:
        s = s.replace(ch, f" {ch} ")
    return [t for t in s.split() if t]

# ---------- AST ----------
class Node: ...
class Leaf(Node):
    def __init__(self, tok: str):
        self.tok = tok
class Bin(Node):
    def __init__(self, op: str, l: Node, r: Node):
        self.op, self.l, self.r = op, l, r
class FuncCall(Node):
    def __init__(self, name: str, args: List[Node]):
        self.name, self.args = name, args

# ---------- parser recursivo ----------
class Parser:
    def __init__(self, toks: List[str]):
        self.toks = toks
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else None

    def eat(self, expected=None):
        if self.i >= len(self.toks):
            raise CompileError("Fin inesperado")
        t = self.toks[self.i]
        if expected is not None and t != expected:
            raise CompileError(f"Se esperaba '{expected}' y se encontró '{t}'")
        self.i += 1
        return t

    def parse_assign(self):
        lhs = self.eat()
        if not is_var(lhs):
            raise CompileError("LHS debe ser un identificador (ej: result)")
        self.eat("=")
        rhs = self.parse_expr()
        if self.i != len(self.toks):
            raise CompileError("Tokens sobrantes al final")
        return lhs, rhs

    def parse_expr(self) -> Node:
        node = self.parse_term()
        while self.peek() in ("+", "-"):
            op = self.eat()
            rhs = self.parse_term()
            node = Bin(op, node, rhs)
        return node

    def parse_term(self) -> Node:
        node = self.parse_factor()
        while self.peek() in ("*", "/", "%"):
            op = self.eat()
            rhs = self.parse_factor()
            node = Bin(op, node, rhs)
        return node

    def parse_factor(self) -> Node:
        t = self.peek()
        if t is None:
            raise CompileError("Factor vacío")

        if is_int(t):
            self.eat()
            return Leaf(t)

        if is_var(t):
            name = self.eat()
            if self.peek() == "(":
                return self.parse_func_after_name(name)
            return Leaf(name)

        if t == "(":
            self.eat("(")
            node = self.parse_expr()
            self.eat(")")
            return node

        raise CompileError(f"Token inesperado en factor: {t}")

    def parse_func_after_name(self, name: str) -> Node:
        lname = name.lower()
        self.eat("(")
        args: List[Node] = []
        if self.peek() != ")":
            args.append(self.parse_expr())
            if self.peek() == ",":
                self.eat(",")
                args.append(self.parse_expr())
        self.eat(")")

        if lname not in ("max", "min", "abs"):
            raise CompileError(f"Función no soportada: {name}")

        if lname == "abs" and len(args) != 1:
            raise CompileError("abs espera 1 argumento")
        if lname in ("max", "min") and len(args) != 2:
            raise CompileError(f"{name} espera 2 argumentos")

        return FuncCall(lname, args)

# ---------- backend: solo + y - para ASUA emulator ----------
class CodeGen:
    def __init__(self):
        self.code: List[str] = []
        self.lits = set()
        self.mem_access = 0
        self.tmp_id = 0    # genera t_0, t_1, ...
        self.label_id = 0  # genera labels __L_0, __L_1, ...

    # ---------- helpers básicos ----------
    def emit(self, ins: str):
        self.code.append(ins)
        op = ins.split()[0].upper()
        if op in ("MOV", "ADD", "SUB"):
            self.mem_access += 1

    def emit_label(self, name: str):
        self.code.append(f"{name}:")

    def new_tmp(self) -> str:
        t = f"t_{self.tmp_id}"
        self.tmp_id += 1
        return t

    def new_label(self, base: str) -> str:
        name = f"__{base}_{self.label_id}"
        self.label_id += 1
        return name

    def lit_sym(self, k: int) -> str:
        name = f"__lit_{k}"
        self.lits.add(name)
        return name

    def is_leaf(self, n: Node) -> bool:
        return isinstance(n, Leaf)

    def leaf_sym(self, leaf: Leaf) -> str:
        t = leaf.tok
        if is_int(t):
            return self.lit_sym(int(t))
        return t

    def load_leaf_to_A(self, leaf: Leaf):
        sym = self.leaf_sym(leaf)
        self.emit(f"MOV A, ({sym})")

    def spill_A_to_tmp(self) -> str:
        t = self.new_tmp()
        self.emit(f"MOV ({t}), A")
        return t

    # ---------- generación principal ----------
    def gen(self, n: Node):
        if isinstance(n, FuncCall):
            self.gen_func(n)
            return

        if isinstance(n, Leaf):
            self.load_leaf_to_A(n)
            return

        if not isinstance(n, Bin):
            raise CompileError("Nodo desconocido en AST")

        op, L, R = n.op, n.l, n.r

        if op == "+":
            self.gen_add(L, R)
        elif op == "-":
            self.gen_sub(L, R)
        elif op == "*":
            self.gen_mul(L, R)
        elif op in ("/", "%"):
            self.gen_divmod(L, R, want_mod=(op == "%"))
        else:
            raise CompileError(f"Operador no soportado en backend: {op}")

    # ---------- + y - optimizados ----------
    def gen_add(self, L: Node, R: Node):
        if self.is_leaf(R):
            self.gen(L)
            rsym = self.leaf_sym(R)
            self.emit(f"ADD A, ({rsym})")
        else:
            self.gen(R)
            t = self.spill_A_to_tmp()
            self.gen(L)
            self.emit(f"ADD A, ({t})")

    def gen_sub(self, L: Node, R: Node):
        if self.is_leaf(R):
            self.gen(L)
            rsym = self.leaf_sym(R)
            self.emit(f"SUB A, ({rsym})")
        else:
            self.gen(R)
            t = self.spill_A_to_tmp()
            self.gen(L)
            self.emit(f"SUB A, ({t})")

    # ---------- * por sumas repetidas ----------
        # ---------- * por sumas repetidas ----------
    def gen_mul(self, L: Node, R: Node):
        # Asumimos R >= 0 (multiplicador no negativo)

        # 1) tL = L
        self.gen(L)
        tL = self.spill_A_to_tmp()

        # 2) tR = R
        self.gen(R)
        tR = self.spill_A_to_tmp()

        # 3) t_res = 0
        t_res = self.new_tmp()
        self.emit("MOV A, 0")
        self.emit(f"MOV ({t_res}), A")

        loop = self.new_label("mul_loop")
        end  = self.new_label("mul_end")

        self.emit_label(loop)
        # A = contador (tR)
        self.emit(f"MOV A, ({tR})")
        # si A == 0 → fin
        self.emit("CMP A, 0")
        self.emit(f"JEQ {end}")

        # A = t_res
        self.emit(f"MOV A, ({t_res})")
        # A = A + tL
        self.emit(f"ADD A, ({tL})")
        # t_res = A
        self.emit(f"MOV ({t_res}), A")

        # tR = tR - 1
        self.emit(f"MOV A, ({tR})")
        self.emit("SUB A, 1")        # usamos inmediato 1
        self.emit(f"MOV ({tR}), A")

        # repetir
        self.emit(f"JMP {loop}")

        self.emit_label(end)
        # resultado final en A
        self.emit(f"MOV A, ({t_res})")



    # ---------- / y % por restas repetidas ----------
        # ---------- / y % por restas repetidas ----------
    def gen_divmod(self, L: Node, R: Node, want_mod: bool):
        # Asumimos L >= 0, R > 0

        # tN = L (numerador)
        self.gen(L)
        tN = self.spill_A_to_tmp()

        # tD = R (denominador)
        self.gen(R)
        tD = self.spill_A_to_tmp()

        # tQ = 0 (cociente)
        tQ = self.new_tmp()
        self.emit("MOV A, 0")
        self.emit(f"MOV ({tQ}), A")

        loop = self.new_label("div_loop")
        end  = self.new_label("div_end")

        self.emit_label(loop)
        # A = tN - tD
        self.emit(f"MOV A, ({tN})")
        self.emit(f"SUB A, ({tD})")
        # si A < 0 → fin (tN < tD)
        self.emit("CMP A, 0")
        self.emit(f"JLT {end}")

        # tN = A (nuevo numerador)
        self.emit(f"MOV ({tN}), A")

        # tQ = tQ + 1
        self.emit(f"MOV A, ({tQ})")
        self.emit("ADD A, 1")
        self.emit(f"MOV ({tQ}), A")

        # repetir
        self.emit(f"JMP {loop}")

        self.emit_label(end)

        # según / o %
        if want_mod:
            # A = resto
            self.emit(f"MOV A, ({tN})")
        else:
            # A = cociente
            self.emit(f"MOV A, ({tQ})")


    # ---------- funciones abs, max, min ----------
        # ---------- funciones abs, max, min ----------
    def gen_func(self, f: FuncCall):
        name = f.name  # 'abs', 'max', 'min'

        if name == "abs":
            # abs(x):
            x = f.args[0]
            self.gen(x)              # A = x
            # si A >= 0 → fin
            self.emit("CMP A, 0")
            label_end = self.new_label("abs_end")
            self.emit(f"JGE {label_end}")

            # negativo: A = -A  (A = 0 - A)
            self.emit("MOV B, A")   # guardo x en B
            self.emit("MOV A, 0")
            self.emit("SUB A, B")

            self.emit_label(label_end)
            return

        if name in ("max", "min"):
            a1, a2 = f.args

            # evalúo a1, guardo en tA
            self.gen(a1)
            tA = self.spill_A_to_tmp()
            # evalúo a2, guardo en tB
            self.gen(a2)
            tB = self.spill_A_to_tmp()

            # diff = tA - tB
            self.emit(f"MOV A, ({tA})")
            self.emit(f"SUB A, ({tB})")
            # comparar diff con 0
            self.emit("CMP A, 0")

            label_ge = self.new_label("ge")
            label_end = self.new_label("end")

            # si diff >= 0 → a1 >= a2
            self.emit(f"JGE {label_ge}")

            # diff < 0 → a2 > a1
            if name == "max":
                # max = a2
                self.emit(f"MOV A, ({tB})")
            else:
                # min = a1 (porque a1 < a2)
                self.emit(f"MOV A, ({tA})")
            self.emit(f"JMP {label_end}")

            self.emit_label(label_ge)
            if name == "max":
                # max = a1
                self.emit(f"MOV A, ({tA})")
            else:
                # min = a2 (porque a1 >= a2)
                self.emit(f"MOV A, ({tB})")

            self.emit_label(label_end)
            return

        raise CompileError(f"Función '{name}' no soportada en backend")


def resolve_labels(code_lines):
        """
        Toma una lista de líneas con labels "foo:" y saltos "JLT foo"
        y retorna una lista de líneas sin labels, con saltos numéricos.
        """

        # 1. Registrar PC real para cada label
        label_to_pc = {}
        pc = 0

        for line in code_lines:
            stripped = line.strip()
            if stripped.endswith(":"):
                label = stripped[:-1]
                label_to_pc[label] = pc
            else:
                pc += 1  # solo instrucciones reales incrementan PC

        # 2. Reconstruir output final: instrucciones sin labels
        final_code = []
        pc = 0

        for line in code_lines:
            stripped = line.strip()

            if stripped.endswith(":"):
                # los labels no se copian al código final
                continue

            # Buscar saltos condicionales y JMP
            parts = stripped.split()
            if len(parts) >= 2 and parts[0] in ("JMP", "JEQ", "JNE", "JLT", "JGT", "JLE", "JGE", "JCR", "JOV"):
                target = parts[1]

                # Si es label, reemplazar por número
                if target in label_to_pc:
                    numeric = label_to_pc[target]
                    stripped = f"{parts[0]} {numeric}"

            final_code.append(stripped)
            pc += 1

        return final_code

# ---------- orquestación ----------
def compile_line(expr: str) -> str:
    toks = tokenize(expr)
    p = Parser(toks)
    lhs, rhs_ast = p.parse_assign()

    cg = CodeGen()
    cg.gen(rhs_ast)
    cg.emit(f"MOV ({lhs}), A")

    header = [
        f"; expr: {expr}",
        f"; lineas: {len(cg.code)}",
        f"; accesos_mem: {cg.mem_access}",
    ]

    data_lits = []
    for name in sorted(cg.lits, key=lambda s: int(s.split("_")[-1])):
        val = name.split("_")[-1]
        data_lits.append(f"{name} {val}")

    resolved = resolve_labels(cg.code)
    out = header + resolved

    if data_lits:
        out.append("")
        out.append("; Literales sugeridos para DATA:")
        out.extend(data_lits)
        out.append("; ... y tus variables V1,V2,..., result, error, temporales t_0,t_1,...")

    return "\n".join(out)

def main():
    if len(sys.argv) < 2:
        print('Uso:\n  python compiler.py "result = V1 - (V2 + V3 - V4)"')
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
