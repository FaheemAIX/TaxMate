from app.data.tax_rates_2025_26 import (
    SALARIED_INCOME_TAX_SLABS,
    AOP_NON_SALARIED_INCOME_TAX_SLABS,
    PROPERTY_RENTAL_INCOME_TAX_SLABS,
)


def calculate_tax_from_slabs(annual_income: float, slabs: list[tuple]) -> dict:
    if annual_income < 0:
        raise ValueError("Income cannot be negative")

    for lower_bound, upper_bound, base_tax, marginal_rate in slabs:
        is_in_this_bracket = annual_income > lower_bound and (
            upper_bound is None or annual_income <= upper_bound
        )

        if is_in_this_bracket:
            taxable_excess = annual_income - lower_bound
            tax_owed = base_tax + (taxable_excess * marginal_rate)

            return {
                "annual_income": annual_income,
                "bracket_lower_bound": lower_bound,
                "bracket_upper_bound": upper_bound,
                "marginal_rate": marginal_rate,
                "tax_owed": round(tax_owed, 2),
            }

    # if income is 0 or negative somehow slipped through
    return {
        "annual_income": annual_income,
        "bracket_lower_bound": 0,
        "bracket_upper_bound": slabs[0][1],
        "marginal_rate": 0,
        "tax_owed": 0.0,
    }


def calculate_salaried_tax(annual_income: float) -> dict:
    return calculate_tax_from_slabs(annual_income, SALARIED_INCOME_TAX_SLABS)


def calculate_aop_tax(annual_income: float) -> dict:
    return calculate_tax_from_slabs(annual_income, AOP_NON_SALARIED_INCOME_TAX_SLABS)


def calculate_property_rental_tax(annual_income: float) -> dict:
    return calculate_tax_from_slabs(annual_income, PROPERTY_RENTAL_INCOME_TAX_SLABS)