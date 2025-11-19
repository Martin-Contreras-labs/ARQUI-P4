import sys
import re

TOKEN_RE = re.compile(
    r"""
    [A-Za-z_][A-Za-z0-9_]* |
    [+\-*/%(),=]
    """,
    re.VERBOSE,
)

class Token:
    def __init__(self, kind, value):
        self.kind = kind
        self.value = value

def tokenize(s):
    raw = TOKEN_RE.findall(s.replace(" ",""))
    tokens=[]
    for r in raw:
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", r):
            tokens.append(Token("id", r))
        elif r=="=":
            tokens.append(Token("eq", r))
        elif r=="(":
            tokens.append(Token("lpar", r))
        elif r==")":
            tokens.append(Token("rpar", r))
        elif r==",":
            tokens.append(Token("comma", r))
        else:
            tokens.append(Token("op", r))
    return tokens

class Expr: pass

class Var(Expr):
    def __init__(self,name): self.name=name

class BinOp(Expr):
    def __init__(self,op,l,r):
        self.op=op; self.l=l; self.r=r

class UnaryOp(Expr):
    def __init__(self,op,e):
        self.op=op; self.e=e

class Call(Expr):
    def __init__(self,f,args):
        self.f=f; self.args=args

class Parser:
    def __init__(self,tokens):
        self.t=tokens
        self.i=0

    def peek(self):
        return self.t[self.i] if self.i<len(self.t) else None

    def eat(self,kind=None,value=None):
        tok=self.peek()
        if tok is None:
            raise ValueError("Unexpected end.")
        if kind and tok.kind!=kind:
            raise ValueError(f"Expected {kind}")
        if value and tok.value!=value:
            raise ValueError(f"Expected {value}")
        self.i+=1
        return tok

    def parse_assignment(self):
        t0=self.eat("id")
        if t0.value!="result":
            raise ValueError("Debe comenzar con result = ...")
        self.eat("eq")
        expr=self.parse_expr()
        if self.peek():
            raise ValueError("Sobraron tokens.")
        return expr

    def parse_expr(self):
        node=self.parse_term()
        while True:
            tok=self.peek()
            if tok and tok.kind=="op" and tok.value in ("+","-"):
                op=tok.value; self.eat("op")
                node=BinOp(op,node,self.parse_term())
            else:
                break
        return node

    def parse_term(self):
        node=self.parse_factor()
        while True:
            tok=self.peek()
            if tok and tok.kind=="op" and tok.value in ("*","/","%"):
                op=tok.value; self.eat("op")
                node=BinOp(op,node,self.parse_factor())
            else:
                break
        return node

    def parse_factor(self):
        tok=self.peek()
        if tok and tok.kind=="op" and tok.value=="-":
            self.eat("op")
            return UnaryOp("-", self.parse_factor())
        return self.parse_primary()

    def parse_primary(self):
        tok=self.peek()
        if tok.kind=="id":
            name=tok.value; self.eat("id")
            if self.peek() and self.peek().kind=="lpar":
                self.eat("lpar")
                args=[]
                if self.peek().kind!="rpar":
                    args.append(self.parse_expr())
                    while self.peek() and self.peek().kind=="comma":
                        self.eat("comma")
                        args.append(self.parse_expr())
                self.eat("rpar")
                return Call(name,args)
            return Var(name)

        if tok.kind=="lpar":
            self.eat("lpar")
            e=self.parse_expr()
            self.eat("rpar")
            return e

        raise ValueError("Token inesperado")

class CodeGen:
    def __init__(self):
        self.asm=[]
        self.vars=set(["zero"])
        self.tmp=0
        self.lbl=0
        self.need_mul=False
        self.need_div=False
        self.need_mod=False

    def emit(self,s): self.asm.append(s)
    def new_tmp(self):
        t=f"t{self.tmp}"; self.tmp+=1
        self.vars.add(t); return t
    def new_lbl(self,base):
        l=f"{base}_{self.lbl}"; self.lbl+=1; return l
    def m(self,x): return f"({x})"
    def mapv(self,n):
        if n in ("result","error"): return n
        v=""+n; self.vars.add(v); return v


    def gen(self,node):
        # variable
        if isinstance(node,Var):
            return self.mapv(node.name)

        # -x
        if isinstance(node,UnaryOp):
            x=self.gen(node.e)
            t=self.new_tmp()
            self.emit(f"MOV A,{self.m('zero')}")
            self.emit(f"MOV B,{self.m(x)}")
            self.emit("SUB A,B")
            self.emit(f"MOV {self.m(t)},A")
            return t

        # binarios
        if isinstance(node,BinOp):
            if node.op in ("+","-"):
                L=self.gen(node.l)
                R=self.gen(node.r)
                t=self.new_tmp()
                self.emit(f"MOV A,{self.m(L)}")
                self.emit(f"MOV B,{self.m(R)}")
                if node.op=="+": self.emit("ADD A,B")
                else: self.emit("SUB A,B")
                self.emit(f"MOV {self.m(t)},A")
                return t

            # mul
            if node.op=="*":
                self.need_mul=True
                L=self.gen(node.l); R=self.gen(node.r)
                t=self.new_tmp()
                self.emit(f"MOV A,{self.m(L)}")
                self.emit(f"MOV B,{self.m(R)}")
                self.emit("CALL mul")
                self.emit(f"MOV {self.m(t)},A")
                return t

            # div
            if node.op=="/":
                self.need_div=True
                L=self.gen(node.l); R=self.gen(node.r)
                t=self.new_tmp()
                self.emit(f"MOV A,{self.m(L)}")
                self.emit(f"MOV B,{self.m(R)}")
                self.emit("CALL div")
                self.emit(f"MOV {self.m(t)},A")
                return t

            # mod
            if node.op=="%":
                self.need_mod=True
                L=self.gen(node.l); R=self.gen(node.r)
                t=self.new_tmp()
                self.emit(f"MOV A,{self.m(L)}")
                self.emit(f"MOV B,{self.m(R)}")
                self.emit("CALL mod")
                self.emit(f"MOV {self.m(t)},A")
                return t

        # funciones
        if isinstance(node, Call):
            f = node.f.lower()

            #abs(x)
            if f == "abs":
                x = self.gen(node.args[0])
                t = self.new_tmp()
                l_neg = self.new_lbl("abs_neg")
                l_end = self.new_lbl("abs_end")
                self.emit(f"MOV A,{self.m(x)}")
                self.emit("MOV B,128")
                self.emit("CMP A,B")
                self.emit(f"JGE {l_neg}")         

                # abs(x) = x
                self.emit(f"MOV A,{self.m(x)}")
                self.emit(f"JMP {l_end}")

                # abs(x) = 0 - x
                self.emit(f"{l_neg}:")
                self.emit(f"MOV A,{self.m('zero')}")
                self.emit(f"MOV B,{self.m(x)}")
                self.emit("SUB A,B")

                self.emit(f"{l_end}:")
                self.emit(f"MOV {self.m(t)},A")
                return t

            #min(a,b)
            if f == "min":
                a = self.gen(node.args[0])
                b = self.gen(node.args[1])

                tdiff = self.new_tmp()          
                tres  = self.new_tmp()         
                l_a   = self.new_lbl("min_a")
                l_end = self.new_lbl("min_end")

                # diff = a - b
                self.emit(f"MOV A,{self.m(a)}")
                self.emit(f"MOV B,{self.m(b)}")
                self.emit("SUB A,B")
                self.emit(f"MOV {self.m(tdiff)},A")

                # si diff < 0 (signed) -> a < b -> min = a
                self.emit(f"MOV A,{self.m(tdiff)}")
                self.emit("MOV B,128")
                self.emit("CMP A,B")
                self.emit(f"JGE {l_a}")          

                # diff >= 0 -> a >= b -> min = b
                self.emit(f"MOV A,{self.m(b)}")
                self.emit(f"MOV {self.m(tres)},A")
                self.emit(f"JMP {l_end}")

                # usar a
                self.emit(f"{l_a}:")
                self.emit(f"MOV A,{self.m(a)}")
                self.emit(f"MOV {self.m(tres)},A")

                self.emit(f"{l_end}:")
                return tres

            # max(a,b)
            if f == "max":
                a = self.gen(node.args[0])
                b = self.gen(node.args[1])

                tdiff = self.new_tmp()         
                tres  = self.new_tmp()          
                l_a   = self.new_lbl("max_a")
                l_end = self.new_lbl("max_end")

                # diff = a - b
                self.emit(f"MOV A,{self.m(a)}")
                self.emit(f"MOV B,{self.m(b)}")
                self.emit("SUB A,B")
                self.emit(f"MOV {self.m(tdiff)},A")

                # si diff < 0 -> a < b -> max = b
                self.emit(f"MOV A,{self.m(tdiff)}")
                self.emit("MOV B,128")
                self.emit("CMP A,B")
                self.emit(f"JGE {l_a}")         

                # diff >= 0 -> a >= b -> max = a
                self.emit(f"MOV A,{self.m(a)}")
                self.emit(f"MOV {self.m(tres)},A")
                self.emit(f"JMP {l_end}")

                # diff < 0 -> usar b
                self.emit(f"{l_a}:")
                self.emit(f"MOV A,{self.m(b)}")
                self.emit(f"MOV {self.m(tres)},A")

                self.emit(f"{l_end}:")
                return tres

            # min
            if f=="min":
                a=self.gen(node.args[0])
                b=self.gen(node.args[1])
                t=self.new_tmp()
                l1=self.new_lbl("min_a")
                le=self.new_lbl("min_end")

                self.emit(f"MOV A,{self.m(a)}")
                self.emit(f"MOV B,{self.m(b)}")
                self.emit("CMP A,B")    
                self.emit(f"JGE {l1}")

                self.emit(f"MOV A,{self.m(b)}")
                self.emit(f"JMP {le}")

                self.emit(f"{l1}:")
                self.emit(f"MOV A,{self.m(a)}")

                self.emit(f"{le}:")
                self.emit(f"MOV {self.m(t)},A")
                return t

            # max
            if f=="max":
                a=self.gen(node.args[0])
                b=self.gen(node.args[1])
                t=self.new_tmp()
                l1=self.new_lbl("max_a")
                le=self.new_lbl("max_end")

                self.emit(f"MOV A,{self.m(b)}")
                self.emit(f"MOV B,{self.m(a)}")
                self.emit("CMP A,B") 
                self.emit(f"JGE {l1}")

                self.emit(f"MOV A,{self.m(b)}")
                self.emit(f"JMP {le}")

                self.emit(f"{l1}:")
                self.emit(f"MOV A,{self.m(a)}")

                self.emit(f"{le}:")
                self.emit(f"MOV {self.m(t)},A")
                return t

        raise ValueError("Nodo no soportado.")

#(MUL / DIV / MOD) 

def build_subroutines(gen: CodeGen):
    out = []

    if gen.need_mul:
        out += [
            "",
            "mul:",
            "    MOV (m_tempA),A",
            "    MOV (m_tempB),B",
            "    MOV A,(zero)",
            "    MOV (m_res),A",

            "mul_loop:",
            "    MOV A,(m_tempB)",
            "    CMP A,(zero)",
            "    JEQ mul_end",

            "    MOV A,(m_res)",
            "    MOV B,(m_tempA)",
            "    ADD A,B",
            "    MOV (m_res),A",

            "    MOV A,(m_tempB)",
            "    SUB A,1",
            "    MOV (m_tempB),A",
            "    JMP mul_loop",

            "mul_end:",
            "    MOV A,(m_res)",
            "    RET",
        ]

    if gen.need_div:
        out += [
            "",
            "div:",
            "    MOV (d_tempA),A", 
            "    MOV (d_tempB),B",  
            "    MOV A,(d_tempB)",
            "    CMP A,(zero)",
            "    JEQ div_error",

            "    MOV A,(zero)",
            "    MOV (d_qiu),A",    

            "div_loop:",
            "    MOV A,(d_tempB)", 
            "    MOV B,(d_tempA)",  
            "    CMP A,B",
            "    JLE div_do_sub",  
            "    JMP div_end",     

            "div_do_sub:",
            "    MOV A,(d_tempA)",
            "    MOV B,(d_tempB)",
            "    SUB A,B",
            "    MOV (d_tempA),A",   

            "    MOV A,(d_qiu)",
            "    ADD A,(one)",
            "    MOV (d_qiu),A",   
            "    JMP div_loop",

            "div_end:",
            "    MOV A,(d_qiu)",     
            "    RET",

            "div_error:",
            "    MOV A,1",
            "    MOV (error),A",
            "    MOV A,(zero)",   
            "    RET",
        ]

    if gen.need_mod:
        out += [
            "",
            "mod:",
            "    MOV (r_tempA),A",   
            "    MOV (r_tempB),B",  
            "    MOV A,(r_tempB)",
            "    CMP A,(zero)",
            "    JEQ mod_error",

            "mod_loop:",
            "    MOV A,(r_tempB)",  
            "    MOV B,(r_tempA)", 
            "    CMP A,B",
            "    JLE mod_do_sub",  
            "    JMP mod_end",     

            "mod_do_sub:",
            "    MOV A,(r_tempA)",
            "    MOV B,(r_tempB)",
            "    SUB A,B",
            "    MOV (r_tempA),A", 
            "    JMP mod_loop",

            "mod_end:",
            "    MOV A,(r_tempA)",  
            "    RET",

            "mod_error:",
            "    MOV A,1",
            "    MOV (error),A",
            "    MOV A,(zero)",
            "    RET",
        ]

    return out

def compile_expression(expr):

    tokens=tokenize(expr)
    parser=Parser(tokens)
    ast=parser.parse_assignment()

    g=CodeGen()
    sym=g.gen(ast)

    g.emit(f"MOV A,{g.m(sym)}")
    g.emit("MOV (result),A")
    g.emit("")
    g.emit("end:")
    g.emit("JMP end")

    subs=build_subroutines(g)
    g.asm += subs

    data=[]
    for v in sorted(g.vars):
        data.append(f"{v} 0")

    if g.need_mul:
        data+=["m_tempA 0","m_tempB 0","m_res 0"]
    if g.need_div:
        data+=["d_tempA 0","d_tempB 0","d_qiu 0","one 1"]
    if g.need_mod:
        data+=["r_tempA 0","r_tempB 0"]

    data.append("result 0")
    data.append("error 0")
    return g.asm,data

MEM_PATTERN = re.compile(r"\(([A-Za-z_][A-Za-z0-9_]*)\)")

def count_memory_accesses(asm_lines):
    return sum(len(MEM_PATTERN.findall(line)) for line in asm_lines)

def main():
    expr=" ".join(sys.argv[1:]) if len(sys.argv)>1 else input("Expresión: ").strip()
    asm,data=compile_expression(expr)

    line_count = len(asm)
    mem_access = count_memory_accesses(asm)

    print(f"Lineas de código generadas: {line_count}")
    print(f"Accesos a memoria (aprox): {mem_access}")
    print()
    print("\n".join(asm))
    print("\nDATA:")
    print("\n".join(data))

    with open("program.asm","w") as f:
        f.write(f"; Lineas de código generadas: {line_count}\n")
        f.write(f"; Accesos a memoria (aprox): {mem_access}\n\n")
        f.write("\n".join(asm))
        f.write("\n\nDATA:\n")
        f.write("\n".join(data))

if __name__=="__main__":
    main()
