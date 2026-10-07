from app.services.tax_calculator import calculate_salaried_tax

result = calculate_salaried_tax(2_500_000)
print(result)