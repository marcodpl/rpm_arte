import math

print("Use integrate only on simplified expressions. For safer use, use primitive instead.")

def Sqrt(xv):
    return Pow(xv, Const(1 / 2))


class Expr:
    def diff(self, var):
        raise NotImplementedError()

    def diff_n(self, var, n):
        result = self
        for _ in range(n):
            result = result.diff(var).simplify()
        return result

    def primitive(self, var):
        return self.simplify().integrate(var)

    def integrate(self, var):
        raise NotImplementedError()

    def definite_integral(self, var, bounds):
        a = bounds[0]
        b = bounds[1]
        F = self.primitive(var)
        return self._evaluateintg(F, var, b) - self._evaluateintg(F, var, a)

    def taylor(self, var, a, order):
        result = Const(0)
        for n in range(order + 1):
            deriv = self.diff_n(var, n)
            coeff = self._evaluateintg(deriv, var, a) / math.factorial(n)
            term = Mul(Const(coeff),
                       Pow(Add(var, Const(-a)), Const(n)))
            result = Add(result, term)
        return result.simplify()

    def _evaluateintg(self, intg, var, value):
        if isinstance(intg, Const):
            return intg.value
        if isinstance(intg, Var):
            return value
        if isinstance(intg, Add):
            return self._evaluateintg(intg.left, var, value) + \
                self._evaluateintg(intg.right, var, value)
        if isinstance(intg, Mul):
            return self._evaluateintg(intg.left, var, value) * \
                self._evaluateintg(intg.right, var, value)
        if isinstance(intg, Pow):
            return self._evaluateintg(intg.base, var, value) ** \
                self._evaluateintg(intg.exponent, var, value)
        if isinstance(intg, Sin):
            return math.sin(self._evaluateintg(intg.arg, var, value))
        if isinstance(intg, Cos):
            return math.cos(self._evaluateintg(intg.arg, var, value))
        raise NotImplementedError()

    def get_factors(self):
        if isinstance(self, Mul):
            return self.left.get_factors() + self.right.get_factors()
        return [self]

    def simplify(self):
        return self

    def depends_on(self, var):
        return False

    def __add__(self, other):
        return Add(self, other)

    def __mul__(self, other):
        return Mul(self, other)

    def __pow__(self, other):
        return Pow(self, other)

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


class Const(Expr):
    def __init__(self, value):
        self.value = value

    def diff(self, var):
        return Const(0)

    def integrate(self, var):
        return Mul(self, var)

    def simplify(self):
        return self

    def __repr__(self):
        return str(self.value)


class Var(Expr):
    def __init__(self, name):
        self.name = name

    def diff(self, var):
        return Const(1) if self.name == var.name else Const(0)

    def integrate(self, var):
        if self.name == var.name:
            return Mul(
                Pow(self, Const(2)),
                Const(1 / 2)
            )
        return Mul(self, var)

    def depends_on(self, var):
        return self.name == var.name

    def __repr__(self):
        return self.name


# integratable # linear-integration
class Add(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def diff(self, var):
        return Add(self.left.diff(var), self.right.diff(var))

    def integrate(self, var):
        return Add(self.left.integrate(var), self.right.integrate(var))

    def simplify(self):

        # flatten additions
        terms = []

        def flatten(expr):
            if isinstance(expr, Add):
                flatten(expr.left.simplify())
                flatten(expr.right.simplify())
            else:
                terms.append(expr.simplify())

        flatten(self)

        # collect constants
        constant_sum = 0
        symbolic = []

        for t in terms:
            if isinstance(t, Const):
                constant_sum += t.value
            else:
                symbolic.append(t)

        result = None

        for t in symbolic:
            if result is None:
                result = t
            else:
                result = Add(result, t)

        if constant_sum != 0:
            const_term = Const(constant_sum)
            if result is None:
                return const_term
            result = Add(result, const_term)

        return result if result is not None else Const(0)

    def depends_on(self, var):
        return self.left.depends_on(var) or self.right.depends_on(var)

    def __repr__(self):
        return f"({self.left} + {self.right})"


class Mul(Expr):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def diff(self, var):
        return Add(
            Mul(self.left.diff(var), self.right),
            Mul(self.left, self.right.diff(var))
        )

    def simplify(self):

        # 1. Flatten factors
        factors = []

        def flatten(expr):
            if isinstance(expr, Mul):
                flatten(expr.left.simplify())
                flatten(expr.right.simplify())
            else:
                factors.append(expr.simplify())

        flatten(self)

        # 2. Extract constant coefficient
        coeff = 1
        symbolic = []

        for f in factors:
            if isinstance(f, Const):
                coeff *= f.value
            else:
                symbolic.append(f)

        if coeff == 0:
            return Const(0)

        # 3. Combine powers
        power_map = {}  # base -> exponent

        for f in symbolic:
            if isinstance(f, Pow) and isinstance(f.exponent, Const):
                base = f.base
                exp = f.exponent.value
            elif isinstance(f, Var):
                base = f
                exp = 1
            else:
                # treat non-power as exponent 1
                base = f
                exp = 1

            if base in power_map:
                power_map[base] += exp
            else:
                power_map[base] = exp

        # 4. Rebuild expression
        result = None

        for base, exp in power_map.items():
            if isinstance(base, Var) and exp == 1:
                term = base
            elif exp == 1:
                term = base
            else:
                term = Pow(base, Const(exp))

            if result is None:
                result = term
            else:
                result = Mul(result, term)

        if coeff != 1:
            if result is None:
                return Const(coeff)
            result = Mul(Const(coeff), result)

        return result if result is not None else Const(coeff)

    def integrate(self, var):

        sub_result = self.try_substitution(var)
        if sub_result is not None:
            return sub_result

        # Constant multiple rule
        if not self.left.depends_on(var):
            print("running left")
            return Mul(
                self.left,
                self.right.integrate(var)
            )

        if not self.right.depends_on(var):
            print("running right")
            return Mul(
                self.right,
                self.left.integrate(var)
            )

        # (other special patterns below)
        raise NotImplementedError()

    def depends_on(self, var):
        return self.left.depends_on(var) or self.right.depends_on(var)

    def try_substitution(self, var):

        # Only attempt for multiplicative expressions
        factors = self.get_factors()

        # Collect unique candidate subexpressions
        candidates = []

        def collect_subexpr(e):
            candidates.append(e)
            if hasattr(e, "arg"):
                collect_subexpr(e.arg)
            if hasattr(e, "left"):
                collect_subexpr(e.left)
                collect_subexpr(e.right)

        collect_subexpr(self)
        candidates.sort(key=lambda expr: expr.size(), reverse=True)

        for g in candidates:

            if not g.depends_on(var):
                continue

            if isinstance(g, Var):
                continue

            if g == self:
                continue

            print(f"Trying substitution for {g}")
            g_prime = g.diff(var).simplify()

            # Try removing g' from factor list
            remaining = factors.copy()
            g_prime_factors = g_prime.get_factors()

            matched = True

            for gf in g_prime_factors:
                if gf in remaining:
                    remaining.remove(gf)
                else:
                    matched = False
                    break

            if not matched:
                continue

            from functools import reduce
            import operator

            rest = reduce(operator.mul, remaining, Const(1)).simplify()

            # arcsin
            # arcsin(g)

            if isinstance(rest, Pow):
                print("its a pow!")

                if isinstance(rest.exponent, Const) and abs(rest.exponent.value + 0.5) < 1e-12:

                    if isinstance(rest.base, Add):

                        terms = []

                        def flatten_add(expr):
                            if isinstance(expr, Add):
                                flatten_add(expr.left)
                                flatten_add(expr.right)
                            else:
                                terms.append(expr)

                        flatten_add(rest.base)

                        found_one = False
                        found_minus_g = False

                        for t in terms:
                            if isinstance(t, Const) and t.value == 1:
                                found_one = True

                            if isinstance(t, Mul):
                                if isinstance(t.left, Const) and t.left.value == -1:
                                    if t.right == g:
                                        found_minus_g = True

                        if found_one and found_minus_g:
                            return Arcsin(g)

            # arctan
            if isinstance(rest, Pow):
                if isinstance(rest.exponent, Const) and rest.exponent.value == -1:

                    if isinstance(rest.base, Add):

                        a = rest.base.left
                        b = rest.base.right

                        if isinstance(a, Const) and a.value == 1:
                            if isinstance(b, Pow) and b.base == g:
                                return Arctan(g)

            # arccos
            if isinstance(rest, Pow):
                if isinstance(rest.exponent, Const) and rest.exponent.value == -1 / 2:

                    if isinstance(rest.base, Add):

                        a = rest.base.left
                        b = rest.base.right

                        if isinstance(a, Const) and a.value == 1:
                            if isinstance(b, Mul) and isinstance(b.left, Const) and b.left.value == -1:
                                if isinstance(b.right, Pow) and b.right.base == g:
                                    return Mul(Const(-1), Arccos(g))


            # rest must be of the form F(g)
            if not hasattr(rest, "arg"):
                continue

            if rest.arg.simplify() != g.simplify():
                continue

            # Try integrating f(g)
            if isinstance(rest, Tan):
                return Mul(Const(-1), Ln(Abs(Cos(g))))

            if isinstance(rest, Sin):
                return Mul(Const(-1), Cos(g))

            if isinstance(rest, Cos):
                return Sin(g)

        return None

    def __repr__(self):
        return f"({self.left} * {self.right})"


# integratable
class Pow(Expr):
    def __init__(self, base, exponent):
        self.base = base
        self.exponent = exponent

    def diff(self, var):
        # f^g derivative
        return Mul(
            self,
            Add(
                Mul(self.exponent.diff(var), Ln(self.base)),
                Mul(self.exponent,
                    Mul(self.base.diff(var),
                        Pow(self.base, Const(-1))))
            )
        )

    def integrate(self, var):
        if isinstance(self.base, Var) and \
                self.base.name == var.name and \
                isinstance(self.exponent, Const):
            n = self.exponent.value
            if n != -1:
                return Mul(
                    Pow(self.base, Const(n + 1)),
                    Const(1 / (n + 1))
                )
            elif n == -1:
                return Ln(Abs(self.base))
        raise NotImplementedError("Integration rule not implemented")

    def simplify(self):
        b = self.base.simplify()
        e = self.exponent.simplify()

        if isinstance(e, Const):
            if e.value == 0:
                return Const(1)
            if e.value == 1:
                return b

        return Pow(b, e)

    def depends_on(self, var):
        return self.base.depends_on(var) or self.exponent.depends_on(var)

    def __repr__(self):
        return f"({self.base}^{self.exponent})"


# integratable
class Sin(Expr):
    def __init__(self, arg):
        self.arg = arg

    def diff(self, var):
        return Mul(Cos(self.arg), self.arg.diff(var))

    def integrate(self, var):
        if isinstance(self.arg, Var) and \
                self.arg.name == var.name:
            return Mul(Const(-1), Cos(self.arg))
        raise NotImplementedError()

    def simplify(self):
        return Sin(self.arg.simplify())

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return f"sin({self.arg})"


# integratable
class Arcsin(Expr):
    def __init__(self, arg):
        self.arg = arg

    def diff(self, var):
        return Mul(
            self.arg.diff(var),
            Pow(
                Add(Const(1),
                    Mul(Const(-1),
                        Pow(self.arg, Const(2)))),
                Const(-1 / 2)
            )
        )

    def simplify(self):
        return Arcsin(self.arg.simplify())

    def integrate(self, var):
        # ∫ arcsin(x) dx = x*arcsin(x) + sqrt(1-x^2)
        if isinstance(self.arg, Var) and self.arg.name == var.name:
            return Add(
                Mul(var, self),
                Sqrt(Add(Const(1),
                         Mul(Const(-1),
                             Pow(var, Const(2)))))
            )
        raise NotImplementedError()

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return f"arcsin({self.arg})"


# integratable
class Cos(Expr):
    def __init__(self, arg):
        self.arg = arg

    def diff(self, var):
        return Mul(Const(-1),
                   Mul(Sin(self.arg), self.arg.diff(var)))

    def integrate(self, var):
        if isinstance(self.arg, Var) and \
                self.arg.name == var.name:
            return Sin(self.arg)
        raise NotImplementedError()

    def simplify(self):
        return Cos(self.arg.simplify())

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return f"cos({self.arg})"


# integratable
class Arccos(Expr):
    def __init__(self, arg):
        self.arg = arg

    def diff(self, var):
        return Mul(
            Const(-1),
            Mul(
                self.arg.diff(var),
                Pow(
                    Add(Const(1),
                        Mul(Const(-1),
                            Pow(self.arg, Const(2)))),
                    Const(-1 / 2)
                )
            )
        )

    def simplify(self):
        return Arccos(self.arg.simplify())

    def integrate(self, var):
        # ∫ arccos(x) dx = x*arccos(x) - sqrt(1-x^2)
        if isinstance(self.arg, Var) and self.arg.name == var.name:
            return Add(
                Mul(var, self),
                Mul(
                    Const(-1),
                    Sqrt(Add(Const(1),
                             Mul(Const(-1),
                                 Pow(var, Const(2)))))
                )
            )
        raise NotImplementedError()

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return f"arccos({self.arg})"


class Tan(Expr):
    def __init__(self, arg):
        self.arg = arg

    def diff(self, var):
        return Mul(
            Pow(Sec(self.arg), Const(2)),
            self.arg.diff(var)
        )

    def simplify(self):
        return Tan(self.arg.simplify())

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return f"tan({self.arg})"


# integratable
class Arctan(Expr):
    def __init__(self, arg):
        self.arg = arg

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
        return Arctan(self.arg.simplify())

    def integrate(self, var):
        # ∫ arctan(x) dx = x arctan(x) - 1/2 ln(1+x^2)
        if isinstance(self.arg, Var) and self.arg.name == var.name:
            return Add(
                Mul(var, self),
                Mul(
                    Const(-1 / 2),
                    Ln(Add(Const(1),
                           Pow(var, Const(2))))
                )
            )
        raise NotImplementedError()

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return f"arctan({self.arg})"


class Sec(Expr):
    def __init__(self, arg):
        self.arg = arg

    def diff(self, var):
        return Mul(
            Mul(Sec(self.arg), Tan(self.arg)),
            self.arg.diff(var)
        )

    def simplify(self):
        return Sec(self.arg.simplify())

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return f"sec({self.arg})"


class Arcsec(Expr):
    def __init__(self, arg):
        self.arg = arg

    def diff(self, var):
        return Mul(
            self.arg.diff(var),
            Mul(
                Pow(Abs(self.arg), Const(-1)),
                Pow(
                    Add(
                        Pow(self.arg, Const(2)),
                        Const(-1)
                    ),
                    Const(-1 / 2)
                )
            )
        )

    def simplify(self):
        return Arcsec(self.arg.simplify())

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return f"arcsec({self.arg})"


class Ln(Expr):
    def __init__(self, arg):
        self.arg = arg

    def diff(self, var):
        return Mul(
            Pow(self.arg, Const(-1)),
            self.arg.diff(var)
        )

    def simplify(self):
        return Ln(self.arg.simplify())

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return f"ln({self.arg})"


class Abs(Expr):
    def __init__(self, arg):
        self.arg = arg

    def diff(self, var):
        return Mul(
            Mul(
                self.arg,
                Pow(Abs(self.arg), Const(-1))
            ),
            self.arg.diff(var)
        )

    def simplify(self):
        return Abs(self.arg.simplify())

    def depends_on(self, var):
        return self.arg.depends_on(var)

    def __repr__(self):
        return f"|{self.arg}|"


e = Const(math.e)
pi = Const(math.pi)

if __name__ == "__main__":
    x = Var("x")
    y = Var("y")

    expr = Mul(
    Mul(Const(2), x),
    Pow(
        Add(Const(1),
            Mul(Const(-1), Pow(x, Const(2)))
        ),
        Const(-1/2)
    )
)

    print("Expression:", expr.simplify())
    print("Derivative:", expr.diff(x).simplify())
    print(expr.get_factors())
    print(expr.primitive(x))
