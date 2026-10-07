"""
Structured tax rate data for Tax Year 2025-26 (Pakistan).
Source: ICMA International Tax Rate Card, Tax Year 2025-26.
Hand-extracted from the official PDF to guarantee accuracy for calculations.
Each slab: (lower_bound, upper_bound, base_tax, marginal_rate)
upper_bound = None means "and above" (no upper limit).
"""

SALARIED_INCOME_TAX_SLABS = [
    (0, 600_000, 0, 0.00),
    (600_000, 1_200_000, 0, 0.01),
    (1_200_000, 2_200_000, 6_000, 0.11),
    (2_200_000, 3_200_000, 116_000, 0.23),
    (3_200_000, 4_100_000, 346_000, 0.30),
    (4_100_000, None, 616_000, 0.35),
]

AOP_NON_SALARIED_INCOME_TAX_SLABS = [
    (0, 600_000, 0, 0.00),
    (600_000, 1_200_000, 0, 0.15),
    (1_200_000, 1_600_000, 90_000, 0.20),
    (1_600_000, 3_200_000, 170_000, 0.30),
    (3_200_000, 5_600_000, 650_000, 0.40),
    (5_600_000, None, 1_610_000, 0.45),  # 0.40 if professional firm barred from incorporation
]

PROPERTY_RENTAL_INCOME_TAX_SLABS = [
    (0, 300_000, 0, 0.00),
    (300_000, 600_000, 0, 0.05),
    (600_000, 2_000_000, 15_000, 0.10),
    (2_000_000, None, 155_000, 0.25),
]

SURCHARGE_ON_TAX_PAYABLE = {
    "threshold_income": 10_000_000,
    "rate_on_tax_payable": 0.09,
    "applies_to": ["salaried_individuals", "aops"],
}