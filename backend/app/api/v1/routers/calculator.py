from fastapi import APIRouter
from app.schemas.calculator import TaxCalculationRequest, TaxCalculationResponse
from app.services.tax_calculator import (
    calculate_salaried_tax,
    calculate_aop_tax,
    calculate_property_rental_tax,
)

router = APIRouter(prefix="/calculator", tags=["Calculator"])

TAX_FUNCTION_MAP = {
    "salaried": calculate_salaried_tax,
    "aop": calculate_aop_tax,
    "property_rental": calculate_property_rental_tax,
}


@router.post("/", response_model=TaxCalculationResponse)
def calculate_tax(request: TaxCalculationRequest):
    calculation_function = TAX_FUNCTION_MAP[request.person_type]
    result = calculation_function(request.annual_income)

    return TaxCalculationResponse(
        annual_income=result["annual_income"],
        person_type=request.person_type,
        bracket_lower_bound=result["bracket_lower_bound"],
        bracket_upper_bound=result["bracket_upper_bound"],
        marginal_rate=result["marginal_rate"],
        tax_owed=result["tax_owed"],
    )