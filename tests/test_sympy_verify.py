from homosapien.tools.sympy_verify import are_equivalent, equivalent_up_to_constant


def test_equivalent_forms():
    assert are_equivalent("exp(x)*(x-1)", "x*exp(x)-exp(x)").equivalent


def test_not_equivalent():
    assert not are_equivalent("x*exp(x)+exp(x)", "x*exp(x)-exp(x)").equivalent


def test_caret_exponent_accepted():
    assert are_equivalent("x^2", "x*x").equivalent


def test_trig_identity():
    assert are_equivalent("2*sin(x)*cos(x)", "sin(2*x)").equivalent


def test_bad_input_is_handled():
    res = are_equivalent("x +", "x")
    assert res.equivalent is False
    assert res.method == "error"


def test_up_to_constant():
    assert equivalent_up_to_constant("exp(x)*(x-1)", "exp(x)*(x-1) + C").equivalent
    assert not equivalent_up_to_constant("x**2", "x**3").equivalent


# --- regression: the LIVE bug where a correct integral scored zero ---------- #
def test_implicit_multiplication_parses():
    # "x e^x" (implicit mult + caret) must equal x*exp(x).
    assert are_equivalent("x e^x", "x*exp(x)").equivalent


def test_scheme_style_expected_expr_parses_and_matches():
    # Exactly the mark-scheme string that used to crash the parser.
    assert are_equivalent("exp(x)*(x-1)", "x e^x - e^x").equivalent


def test_missing_plus_c_is_up_to_constant_not_wrong():
    # Student omits +C; expected has it. Not strictly equal...
    assert not are_equivalent("exp(x)*(x-1)", "x e^x - e^x + C").equivalent
    # ...but equal up to an additive constant (a policy call, not an error).
    assert equivalent_up_to_constant("exp(x)*(x-1)", "x e^x - e^x + C").equivalent


def test_numeric_offset_is_not_up_to_constant():
    # An answer off by a plain number is wrong, not "up to +C".
    assert not equivalent_up_to_constant("x**2 + 2", "x**2").equivalent
