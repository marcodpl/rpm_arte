import math
"""
NEVER USE f"". Won't work on Ti nSpire CX II T.
Use "".format() instead.
"""
HELP = """
Guida semplificata per l'utilizzo.
Scrivere, in linea di comando, l'espressione matematica desiderata.
Le frazioni si scrivono con frac(a,b) che rappresentano a/b.
Alcune omissioni del moltiplicatore sono concesse, non tutte. Ad es:
5sin(x) SI
(x)(x) SI
xsin(x) NO
Di base, la variabile della funzione è x. Modificare la variabile con cambiavar.
Ad es: cambiaVar("y") trasforma la variabile in y.
Sono aggiunti di base i simboli: pi, e. Questi simboli restano nel risultato.
Ad es: e^x -> la derivata in uscita è e^x. e non viene calcolata come 2.72.
Aggiungere altri simboli con aggsimb.
"""

FUNCS = """
a + b addizione
a - b sottrazione
a * b moltiplicazione
frac(a,b) divisione
a^b potenza
sqrt(a) radice quadrata
sin(a) seno
cos(a) coseno
tan(a) tangente
asin(a) arcsin
acos(a) arccos
atan(a) arctan
ln(a) logaritmo naturale
log(a,b) logaritmo di base b
e^a esponenziale
mod(a) valore assoluto
Solo in output: signOf(a) segno della variabile. Ovvero, 1 o -1, a seconda che x sia positiva o negativa.
"""
def sqrt(xv):
    return Pow(xv, Const(1 , 2))

def cubrt(xv):
    return Pow(xv, Const(1 , 3))

def root(xv, n):
    return Pow(xv, Const(1, n))

def frac(a, b):
    # Promote ints automatically
    if isinstance(a, int):
        a = Const(a)
    if isinstance(b, int):
        b = Const(b)

    # Pure rational case
    if isinstance(a, Const) and isinstance(b, Const):
        return Const(a.num * b.den, a.den * b.num)

    # General symbolic division
    return Mul(a, Pow(b, Const(-1)))

def gcd(a, b):
    while b:
        a, b = b, a % b
    return a


class Expr:
    def diff(self, var):
        raise NotImplementedError()

    def diff_n(self, var, n):
        result = self
        for _ in range(n):
            result = result.diff(var).simplify()
        return result

    def simplify(self):
        return self

    def precedence(self):
        return 0

    def depends_on(self, var):
        return False

    def __add__(self, other):
        return Add(self, self._to_expr(other))

    def __radd__(self, other):
        return Add(self._to_expr(other), self)

    def __sub__(self, other):
        return Add(self, Mul(Const(-1), self._to_expr(other)))

    def __rsub__(self, other):
        return Add(self._to_expr(other), Mul(Const(-1), self))

    def __mul__(self, other):
        return Mul(self, self._to_expr(other))

    def __rmul__(self, other):
        return Mul(self._to_expr(other), self)

    def __truediv__(self, other):
        return Mul(self, Pow(self._to_expr(other), Const(-1)))

    def __rtruediv__(self, other):
        return Mul(self._to_expr(other), Pow(self, Const(-1)))

    def __pow__(self, other):
        if not isinstance(other, Expr):
            other = Const(other)
        return Pow(self, other)

    def __rpow__(self, other):
        if not isinstance(other, Expr):
            other = Const(other)
        return Pow(other, self)

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.__dict__ == other.__dict__

    def __hash__(self):
        return hash((type(self), self._hashable_content()))

    def _hashable_content(self):
        items = []
        for k, v in sorted(self.__dict__.items()):
            if isinstance(v, Expr):
                items.append((k, v._hashable_content()))
            else:
                items.append((k, v))
        return tuple(items)

    def _to_expr(self, other):
        if isinstance(other, Expr):
            return other
        if isinstance(other, int):
            return Const(other)
        raise TypeError("Cannot convert {} to Expr".format(type(other)))


class Unary(Expr):
    def precedence(self):
        return 4


class Symbol(Expr):
    def __init__(self, name):
        self.name = name

    def depends_on(self, var):
        return self.name == var.name

    def precedence(self):
        return 5

    def diff(self, var):
        if self.name == var.name:
            return Const(1)
        return Const(0)

    def simplify(self):
        return self

    def __repr__(self):
        return self.name

    def size(self):
        return 1

    def pretty(self):
        return str(self)


class Const(Expr):

    def __init__(self, num, den=1):

        if not isinstance(num, int) or not isinstance(den, int):
            raise TypeError("Const requires integer numerator and denominator.")

        if den == 0:
            raise ZeroDivisionError("Denominator cannot be zero.")

        # Normalize sign
        if den < 0:
            num = -num
            den = -den

        g = gcd(abs(num), abs(den))

        self.num = num // g
        self.den = den // g

    def depends_on(self, var):
        return False

    def pretty(self):
        return str(self)

    def precedence(self):
        return 5

    def diff(self, var):
        return Const(0)

    def simplify(self):
        return self

    def __repr__(self):
        if self.den == 1:
            return str(self.num)
        return "{}/{}".format(self.num, self.den)


class Var(Expr):
    def __init__(self, name):
        self.name = name

    def diff(self, var):
        return Const(1) if self.name == var.name else Const(0)

    def depends_on(self, var):
        return self.name == var.name

    def precedence(self):
        return 5

    def __repr__(self):
        return self.name

    def pretty(self):
        return str(self)


# integratable # linear-integration
class Add(Expr):
    def __init__(self, left, right):
        self.left = left if isinstance(left, Expr) else Const(left)
        self.right = right if isinstance(right, Expr) else Const(right)

    def diff(self, var):
        return Add(self.left.diff(var), self.right.diff(var))

    def precedence(self):
        return 1

    def pretty(self):
        terms = []

        def flatten(e):
            if isinstance(e, Add):
                flatten(e.left)
                flatten(e.right)
            else:
                terms.append(e)

        flatten(self)

        pieces = []
        for t in terms:
            s = t.pretty()
            pieces.append(s)

        result = " + ".join(pieces)
        return result.replace("+ -", "- ")

    def simplify(self):

        # 1️⃣ Flatten additions
        terms = []

        def flatten(expr):
            if isinstance(expr, Add):
                flatten(expr.left.simplify())
                flatten(expr.right.simplify())
            else:
                terms.append(expr.simplify())

        flatten(self)

        # 2️⃣ Collect like terms
        collected = []

        for t in terms:

            # Separate coefficient and symbolic part
            if isinstance(t, Mul):

                coeff_num = 1
                coeff_den = 1
                symbolic_parts = []

                def flatten_mul(e):
                    nonlocal coeff_num, coeff_den
                    if isinstance(e, Mul):
                        flatten_mul(e.left)
                        flatten_mul(e.right)
                    else:
                        if isinstance(e, Const):
                            coeff_num *= e.num
                            coeff_den *= e.den
                        else:
                            symbolic_parts.append(e)

                flatten_mul(t)

                coeff = Const(coeff_num, coeff_den)

            elif isinstance(t, Const):
                coeff = t
                symbolic_parts = []

            else:
                coeff = Const(1)
                symbolic_parts = [t]

            # Try merging
            merged = False

            for i, (symb, c) in enumerate(collected):
                if symb == symbolic_parts:
                    # Rational addition
                    num = c.num * coeff.den + coeff.num * c.den
                    den = c.den * coeff.den
                    collected[i] = (symb, Const(num, den))
                    merged = True
                    break

            if not merged:
                collected.append((symbolic_parts, coeff))

        # 3️⃣ Rebuild expression
        result = None

        for symb, coeff in collected:

            if coeff.num == 0:
                continue

            if symb == []:
                term = coeff
            else:
                symbolic = None
                for part in symb:
                    symbolic = part if symbolic is None else Mul(symbolic, part)

                if coeff.num == coeff.den:
                    term = symbolic
                else:
                    term = Mul(coeff, symbolic)

            result = term if result is None else Add(result, term)

        return result if result is not None else Const(0)

    def depends_on(self, var):
        return self.left.depends_on(var) or self.right.depends_on(var)

    def __repr__(self):
        return "({} + {})".format(self.left, self.right)


class Mul(Expr):
    def __init__(self, left, right):
        self.left = left if isinstance(left, Expr) else Const(left)
        self.right = right if isinstance(right, Expr) else Const(right)

    def diff(self, var):
        if isinstance(self.right, Pow):
            if isinstance(self.right.exponent, Const) and self.right.exponent.num == -1:
                f = self.left
                g = self.right.base

                numerator = Add(
                    Mul(f.diff(var), g),
                    Mul(Const(-1), Mul(f, g.diff(var)))
                )

                denominator = Pow(g, Const(2))

                return Mul(numerator, Pow(denominator, Const(-1)))
        return Add(
            Mul(self.left.diff(var), self.right),
            Mul(self.left, self.right.diff(var))
        )

    def precedence(self):
        return 2

    def simplify(self):

        if isinstance(self.right, Const) and self.right.num == self.right.den:
            return self.left.simplify()
        elif isinstance(self.left, Const) and self.left.num == self.left.den:
            return self.right.simplify()

        if isinstance(self.left, Const) and isinstance(self.right, Add):
            return Add(
                Mul(self.left, self.right.left).simplify(),
                Mul(self.left, self.right.right).simplify()
            )

        if isinstance(self.right, Const) and isinstance(self.left, Add):
            return Add(
                Mul(self.right, self.left.left).simplify(),
                Mul(self.right, self.left.right).simplify()
            )

        factors = []

        def flatten(expr):
            if isinstance(expr, Mul):
                flatten(expr.left.simplify())
                flatten(expr.right.simplify())
            else:
                factors.append(expr.simplify())

        flatten(self)

        coeff_num = 1
        coeff_den = 1
        symbolic = []

        for f in factors:
            if isinstance(f, Const):
                coeff_num *= f.num
                coeff_den *= f.den
            else:
                symbolic.append(f)

        coeff = Const(coeff_num, coeff_den)

        if coeff.num == 0:
            return Const(0)

        power_map = {}

        for f in symbolic:
            if isinstance(f, Pow) and isinstance(f.exponent, Const):
                base = f.base
                exp = f.exponent
            elif isinstance(f, Var) or isinstance(f, Symbol):
                base = f
                exp = Const(1)
            else:
                base = f
                exp = Const(1)

            if base in power_map:
                # rational exponent addition
                e1 = power_map[base]
                num = e1.num * exp.den + exp.num * e1.den
                den = e1.den * exp.den
                power_map[base] = Const(num, den)
            else:
                power_map[base] = exp

        # --- SIGN SIMPLIFICATION ---
        # Detect x * |x|^-1 → sgn(x)

        for base, exp in list(power_map.items()):
            if isinstance(base, Var) and isinstance(exp, Const) and exp.num == exp.den:
                # look for Abs(base)^-1
                for other_base, other_exp in list(power_map.items()):
                    if isinstance(other_base, mod):
                        if other_base.arg == base:
                            if isinstance(other_exp, Const) and other_exp.num == -other_exp.den:
                                # Remove both
                                del power_map[base]
                                del power_map[other_base]
                                power_map[Sign(base)] = Const(1)
                                break

        result = None

        for base, exp in power_map.items():

            if exp.num == 0:
                continue

            if exp.num == exp.den:
                term = base
            else:
                term = Pow(base, exp)

            if result is None:
                result = term
            else:
                result = Mul(result, term)

        if coeff.num != coeff.den:
            if result is None:
                return coeff
            result = Mul(coeff, result)

        return result if result is not None else coeff

    def depends_on(self, var):
        return self.left.depends_on(var) or self.right.depends_on(var)

    def pretty(self):
        factors = []

        def flatten(e):
            if isinstance(e, Mul):
                flatten(e.left)
                flatten(e.right)
            else:
                factors.append(e)

        flatten(self)

        pieces = []
        for f in factors:
            s = f.pretty()
            if f.precedence() < self.precedence():
                s = "({})".format(s)
            pieces.append(s)

        return "•".join(pieces)

    def __repr__(self):
        return "({} * {})".format(self.left, self.right)


# integratable
class Pow(Expr):
    def __init__(self, base, exponent):
        self.base = base if isinstance(base, Expr) else Const(base)
        self.exponent = exponent if isinstance(exponent, Expr) else Const(exponent)

    def diff(self, var):
        # f^g derivative
        return Mul(
            self,
            Add(
                Mul(self.exponent.diff(var), ln(self.base)),
                Mul(self.exponent,
                    Mul(self.base.diff(var),
                        Pow(self.base, Const(-1))))
            )
        )

    def precedence(self):
        return 3

    def simplify(self):
        b = self.base.simplify()
        e = self.exponent.simplify()

        if isinstance(b, Const) and isinstance(e, Const):
            if e.den == 1 and e.num >= 0:
                return Const(b.num ** e.num, b.den ** e.num)

        if isinstance(b, Pow) and isinstance(e, Const) and isinstance(b.exponent, Const):
            # (a^m)^n = a^(m*n)
            new_num = b.exponent.num * e.num
            new_den = b.exponent.den * e.den
            return Pow(b.base, Const(new_num, new_den)).simplify()

        if isinstance(e, Const):
            if e.num == 0:
                return Const(1)
            if e.num == e.den:
                return b

        return Pow(b, e)

    def depends_on(self, var):
        return self.base.depends_on(var) or self.exponent.depends_on(var)

    def __repr__(self):
        return "({}^{})".format(self.base, self.exponent)

    def pretty(self):
        base = self.base
        exp = self.exponent
        prefix = ""
        lp, rp = "", ""
        xpsimb = "^"
        if isinstance(exp, Const) and exp.num * exp.den < 0:
            prefix = "1/"
            lp, rp = '(', ')'
            abscoord = abs(exp.num) / abs(exp.den)
            if abscoord != 1:
                exp_str = Const(abs(exp.num), abs(exp.den)).pretty()
            else:
                exp_str = ""
                xpsimb = ""
        else:
            exp_str = exp.pretty()
        base_str = base.pretty()
        if base.precedence() < self.precedence():
            base_str = "({})".format(base_str)

        # pretty up by recognizing common exponents (i.e. sqrt(x) and cubrt(x))
        if exp.precedence() <= self.precedence():
            exp_str = "({})".format(exp_str)
        if isinstance(exp, Const) and exp.num == 1 and exp.den == 2:
            return prefix + "sqrt({})".format(base_str)
        if isinstance(exp, Const) and exp.num == 1 and exp.den == 3:
            return prefix + "cubrt({})".format(base_str)
        if isinstance(exp, Const) and exp.num != 1 and exp.den == 2:
            return prefix + "sqrt({}^{})".format(base_str, exp.num)
        if isinstance(exp, Const) and exp.num != 1 and exp.den == 3:
            return prefix + "cubrt({}^{})".format(base_str, exp.num)
        if isinstance(exp, Const) and exp.num == exp.den:
            return prefix + base_str
        return prefix + lp + "{}{}{}".format(base_str, xpsimb, exp_str) + rp


# integratable
class sin(Unary):
    def __init__(self, arg):
        self.arg = arg if isinstance(arg, Expr) else Const(arg)

    def diff(self, var):
        return Mul(cos(self.arg), self.arg.diff(var))

    def pretty(self):
        arg = self.arg

        if arg.precedence() < self.precedence():
            arg_str = "({})".format(arg.pretty())
        else:
            arg_str = arg.pretty()

        return "sin({})".format(arg_str)

    def simplify(self):
        return sin(self.arg.simplify())

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return "sin({})".format(self.arg)


# integratable
class arcsin(Unary):
    def __init__(self, arg):
        self.arg = arg if isinstance(arg, Expr) else Const(arg)

    def diff(self, var):
        return Mul(
            self.arg.diff(var),
            Pow(
                Add(Const(1),
                    Mul(Const(-1),
                        Pow(self.arg, Const(2)))),
                Const(-1 , 2)
            )
        )

    def simplify(self):
        return arcsin(self.arg.simplify())

    def pretty(self):
        arg = self.arg

        if arg.precedence() < self.precedence():
            arg_str = "({})".format(arg.pretty())
        else:
            arg_str = arg.pretty()

        return "arcsin({})".format(arg_str)

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return "arcsin({})".format(self.arg)


# integratable
class cos(Unary):
    def __init__(self, arg):
        self.arg = arg if isinstance(arg, Expr) else Const(arg)

    def diff(self, var):
        return Mul(Const(-1),
                   Mul(sin(self.arg), self.arg.diff(var)))

    def simplify(self):
        return cos(self.arg.simplify())

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return "cos({})".format(self.arg)

    def pretty(self):
        arg = self.arg

        if arg.precedence() < self.precedence():
            arg_str = "({})".format(arg.pretty())
        else:
            arg_str = arg.pretty()

        return "cos({})".format(arg_str)


# integratable
class arccos(Unary):
    def __init__(self, arg):
        self.arg = arg if isinstance(arg, Expr) else Const(arg)

    def diff(self, var):
        return Mul(
            Const(-1),
            Mul(
                self.arg.diff(var),
                Pow(
                    Add(Const(1),
                        Mul(Const(-1),
                            Pow(self.arg, Const(2)))),
                    Const(-1 , 2)
                )
            )
        )

    def simplify(self):
        return arccos(self.arg.simplify())

    def pretty(self):
        arg = self.arg

        if arg.precedence() < self.precedence():
            arg_str = "({})".format(arg.pretty())
        else:
            arg_str = arg.pretty()

        return "arccos({})".format(arg_str)

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return "arccos({})".format(self.arg)


class tan(Unary):
    def __init__(self, arg):
        self.arg = arg if isinstance(arg, Expr) else Const(arg)

    def diff(self, var):
        return Mul(
            Pow(sec(self.arg), Const(2)),
            self.arg.diff(var)
        )

    def simplify(self):
        return tan(self.arg.simplify())

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return "tan({})".format(self.arg)

    def pretty(self):
        arg = self.arg

        if arg.precedence() < self.precedence():
            arg_str = "({})".format(arg.pretty())
        else:
            arg_str = arg.pretty()

        return "tan({})".format(arg_str)


# integratable
class arctan(Unary):
    def __init__(self, arg):
        self.arg = arg if isinstance(arg, Expr) else Const(arg)

    def diff(self, var):
        return Mul(
            self.arg.diff(var),
            Pow(
                Add(Const(1),
                    Pow(self.arg, Const(2))),
                Const(-1)
            )
        )

    def simplify(self):
        return arctan(self.arg.simplify())

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return "arctan({})".format(self.arg)

    def pretty(self):
        arg = self.arg

        if arg.precedence() < self.precedence():
            arg_str = "({})".format(arg.pretty())
        else:
            arg_str = arg.pretty()

        return "arctan({})".format(arg_str)


class sec(Unary):
    def __init__(self, arg):
        self.arg = arg if isinstance(arg, Expr) else Const(arg)

    def diff(self, var):
        return Mul(
            Mul(sec(self.arg), tan(self.arg)),
            self.arg.diff(var)
        )

    def simplify(self):
        return sec(self.arg.simplify())

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return "sec({})".format(self.arg)

    def pretty(self):
        arg = self.arg

        if arg.precedence() < self.precedence():
            arg_str = "({})".format(arg.pretty())
        else:
            arg_str = arg.pretty()

        return "sec({})".format(arg_str)


class arcsec(Unary):
    def __init__(self, arg):
        self.arg = arg if isinstance(arg, Expr) else Const(arg)

    def diff(self, var):
        return Mul(
            self.arg.diff(var),
            Mul(
                Pow(mod(self.arg), Const(-1)),
                Pow(
                    Add(
                        Pow(self.arg, Const(2)),
                        Const(-1)
                    ),
                    Const(-1 , 2)
                )
            )
        )

    def simplify(self):
        return arcsec(self.arg.simplify())

    def pretty(self):
        arg = self.arg

        if arg.precedence() < self.precedence():
            arg_str = "({})".format(arg.pretty())
        else:
            arg_str = arg.pretty()

        return "arcsec({})".format(arg_str)

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return "arcsec({})".format(self.arg)


class ln(Unary):
    def __init__(self, arg):
        self.arg = arg if isinstance(arg, Expr) else Const(arg)

    def diff(self, var):
        return Mul(
            Pow(self.arg, Const(-1)),
            self.arg.diff(var)
        )

    def simplify(self):
        if isinstance(self.arg, Pow):
            if isinstance(self.arg.exponent, Const):
                return Mul(self.arg.exponent, ln(self.arg.base)).simplify()
        if isinstance(self.arg, Symbol) and self.arg.name == "e":
            return Const(1)
        return ln(self.arg.simplify())

    def pretty(self):
        arg = self.arg
        if isinstance(arg, Pow):
            if isinstance(arg.exponent, Const):
                return Mul(arg.exponent, ln(arg.base)).simplify()
        if arg.precedence() < self.precedence():
            arg_str = "({})".format(arg.pretty())
        else:
            arg_str = arg.pretty()

        return "ln({})".format(arg_str)

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return "ln({})".format(self.arg)


class mod(Unary):
    def __init__(self, arg):
        self.arg = arg if isinstance(arg, Expr) else Const(arg)

    def diff(self, var):
        return Mul(
            Mul(
                self.arg,
                Pow(mod(self.arg), Const(-1))
            ),
            self.arg.diff(var)
        )

    def simplify(self):
        return mod(self.arg.simplify())

    def pretty(self):
        arg = self.arg

        if arg.precedence() < self.precedence():
            arg_str = "({})".format(arg.pretty())
        else:
            arg_str = arg.pretty()

        return "|{}|".format(arg_str)

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return "|{}|".format(self.arg)


class Sign(Unary):
    def __init__(self, arg):
        self.arg = arg

    def diff(self, var):
        # distributional derivative not handled
        return Const(0)

    def simplify(self):
        return Sign(self.arg.simplify())

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return "signOf({})".format(self.arg)

    def pretty(self):
        return "signOf({})".format(self.arg.pretty())


class Limit(Expr):

    def __init__(self, expr, var, point, direction=None):
        self.expr = expr
        self.var = var
        self.point = point
        self.direction = direction

    def simplify(self):
        return compute_limit(self.expr, self.var, self.point, self.direction)

    def pretty(self):
        dir_part = ""
        if self.direction:
            dir_part = self.direction
        return f"lim_{self.var.pretty()}→{self.point.pretty()}{dir_part} {self.expr.pretty()}"

def compute_limit(expr, var, point, direction=None):
    if not expr.depends_on(var):
        return expr

    if isinstance(point, Const):
        substituted = substitute(expr, var, point).simplify()

        if not isinstance(substituted, Infinity):
            return substituted

    frac = as_fraction(expr)

    if frac:
        num, den = frac

        num_lim = compute_limit(num, var, point)
        den_lim = compute_limit(den, var, point)

        # regular division
        if not is_zero(den_lim):
            return Mul(num_lim, Pow(den_lim, Const(-1))).simplify()

        # indeterminate forms
        if is_zero(num_lim) and is_zero(den_lim):
            return hopital(expr, var, point, direction)

        if is_infinite(num_lim) and is_infinite(den_lim):
            return hopital(expr, var, point, direction)

        # denominator zero → infinite limit
        if is_zero(den_lim):
            sign = sign_of(expr, point, direction)
            return Infinity(sign)

    if isinstance(point, Infinity):

        deg_num = degree(expr, var)

        if deg_num == 0:
            return substitute(expr, var, Const(10**6)).simplify()

        if deg_num > 0:
            return Infinity(point.sign)

    return Limit(expr, var, point, direction)

class Infinity(Expr):
    def __init__(self, sign):
        self.sign = sign

    def pretty(self):
        return "+∞" if self.sign > 0 else "-∞"

    def __repr__(self):
        return "Infinity()" if self.sign > 0 else "-Infinity()"

    def simplify(self):
        return self

def substitute(expr, var, value):

    if isinstance(expr, Var):
        return value if expr == var else expr

    if isinstance(expr, Const):
        return expr

    if isinstance(expr, Pow):
        return Pow(
            substitute(expr.base, var, value),
            substitute(expr.exponent, var, value)
        )

    if isinstance(expr, Add):
        return Add(
            substitute(expr.left, var, value),
            substitute(expr.right, var, value)
        )

    if isinstance(expr, Mul):
        return Mul(
            substitute(expr.left, var, value),
            substitute(expr.right, var, value)
        )

    if hasattr(expr, "arg"):
        return type(expr)(
            substitute(expr.arg, var, value)
        )

    return expr

def is_zero(expr):
    return isinstance(expr, Const) and expr.num == 0

def is_infinite(expr):
    return isinstance(expr, Infinity)

def as_fraction(expr):

    if isinstance(expr, Mul):
        if isinstance(expr.right, Pow):
            if isinstance(expr.right.exponent, Const) and expr.right.exponent.num == -expr.right.exponent.den:
                return expr.left, expr.right.base

    if isinstance(expr, Pow):
        if isinstance(expr.exponent, Const) and expr.exponent.num == -expr.exponent.den:
            return Const(1), expr.base

    return None

def degree(expr, var):

    if isinstance(expr, Var):
        if expr == var:
            return 1
        return 0

    if isinstance(expr, Pow):
        if expr.base == var and isinstance(expr.exponent, Const):
            return expr.exponent.num

    if isinstance(expr, Mul):
        return degree(expr.left, var) + degree(expr.right, var)

    if isinstance(expr, Add):
        return max(degree(expr.left, var), degree(expr.right, var))

    return 0

def hopital(expr, var, point, direction):

    frac = as_fraction(expr)
    if not frac:
        return Limit(expr, var, point, direction)

    num, den = frac

    new_expr = Mul(
        num.diff(var),
        Pow(den.diff(var), Const(-1))
    )

    return compute_limit(new_expr, var, point, direction)

def sign_of(expr, point, direction):

    eps = Const(1,100000)

    if direction == "+":
        test = Add(point, eps)
    else:
        test = Add(point, Mul(Const(-1), eps))

    val = substitute(expr, Var("x"), test).simplify()

    if isinstance(val, Const):
        return 1 if val.num > 0 else -1

    return 1

def standardise_expr(expr_str:str):

    expr_str = expr_str.replace("^", "**")
    result = ""
    i = 0
    n = len(expr_str)

    while i < n:
        c = expr_str[i]
        result += c

        # Look ahead
        if i + 1 < n:
            next_c = expr_str[i + 1]

            # Determine if we need multiplication
            if _needs_mul(c, next_c):
                result += "*"

        i += 1
    return result

def _needs_mul(left, right):

    # If left is digit, letter, or ')'
    ok = (
        (left.isdigit() and (right.isalpha() or right == '('))
        or
        (left == ')' and right == '(')
    )

    if not ok:
        return False

    # Prevent splitting function names like "sin"
    if left.isalpha() and right.isalpha():
        return False

    return True


e = Symbol("e")
pi = Symbol("pi")
inf = Infinity(1)
ninf = Infinity(-1)
x = Var("x")
focused_var = x
expr: Expr = None
def main():
    global x, e, pi, focused_var, expr, inf, ninf
    namespace = globals()
    print("Computed Handheld Algebraic and Differentiation Solver")
    print("v0.1 - De Pol")
    while True:
        expr_str = input("Expr[{}]{}: ".format(focused_var.name, "[{}]".format("VUOTA") if expr is None else ""))
        if "aiuto" in expr_str:
            print(HELP)
            continue
        elif "funzioni" in expr_str:
            print(FUNCS)
            continue
        elif "esci" in expr_str or "fine" in expr_str or "exit" in expr_str or expr_str == "quit":
            print("Chiusura in corso...")
            break
        elif "cambiavar" in expr_str:
            var = input("Inserisci nuova variabile: ")
            if len(var) != 1 or not var.isalpha():
                print("Variabile non valida!")
                continue
            exec("{}=Var(\"{}\")".format(var, var), namespace)
            exec("focused_var = {}".format(var), namespace)
            continue
        elif "aggsimb" in expr_str:
            simb = input("Enter new symbol: ")
            if not simb.isalpha():
                print("Simbolo non valido!")
                continue
            exec("{} = Symbol(\"{}\")".format(simb, simb), namespace)
            continue
        elif expr_str == "deriv":
            if focused_var is not None and expr is not None:
                print("Derivata: " + expr.diff(focused_var).simplify().pretty())
            elif expr is None:
                print("Nessuna espressione selezionata.")
            elif focused_var is None:
                print("Nessuna variabile selezionata.")
            continue
        elif expr_str == "derivn":
            order = int(input("Ordine: "))
            if order >= 10:
                print("Ordine troppo grande!")
                continue
            print("Derivata di ordine {}: {}".format(order, expr.diff_n(focused_var, order).simplify().pretty()))
            continue
        elif expr_str == "lim":
            point = eval(input("Punto di limitazione: "))
            if isinstance(point, int):
                point = Const(point)
            direction = input("Direzione (opzionale): ")
            if direction == "":
                direction = None
            else:
                if direction not in ["+", "-"]:
                    print("Direzione non valida!")
                    continue
            print(Limit(expr, focused_var, point, direction).simplify().pretty())
            continue
        std = standardise_expr(expr_str)
        try:
            expr = eval(std)
        except TypeError:
            print("Espressione non valida! Controlla la sintassi.")
            continue
        if isinstance(expr, int):
            expr = Const(expr)
        print("Semplificata: " + expr.simplify().pretty())


if __name__ == "__main__":
    main()