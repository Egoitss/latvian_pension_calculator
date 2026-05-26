from data import ANNUITY_DIVISOR


def test_annuity_divisor_structure():
    for gender in ("male", "female"):
        assert gender in ANNUITY_DIVISOR
        tbl = ANNUITY_DIVISOR[gender]
        assert set(tbl.keys()) == set(range(62, 70))
        for age, div in tbl.items():
            assert 100 < div < 400, f"{gender} age {age}: {div}"


def test_annuity_divisor_decreasing():
    for gender in ("male", "female"):
        tbl = ANNUITY_DIVISOR[gender]
        for age in range(62, 69):
            assert tbl[age] > tbl[age + 1], (
                f"{gender}: divisor at {age} not > {age+1}"
            )


def test_annuity_women_exceed_men():
    for age in range(62, 70):
        assert ANNUITY_DIVISOR["female"][age] > ANNUITY_DIVISOR["male"][age]
