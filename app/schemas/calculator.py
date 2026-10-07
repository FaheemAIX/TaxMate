from pydantic import BaseModel, Field
from typing import Literal


class TaxCalculationRequest(BaseModel):
    annual_income: float = Field(..., gt=0, description="Annual income in PKR")
    person_type: Literal["salaried", "aop", "property_rental"] = Field(
        ..., description="Type of taxpayer / income category"
    )


class TaxCalculationResponse(BaseModel):
    annual_income: float
    person_type: str
    bracket_lower_bound: float
    bracket_upper_bound: float | None
    marginal_rate: float
    tax_owed: float