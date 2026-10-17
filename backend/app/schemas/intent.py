from pydantic import BaseModel
from typing import Literal, Optional

class QueryIntent(BaseModel):
    intent_type: Literal["calculation", "conceptual", "both"]
    annual_income: Optional[float] = None
    person_type: Optional[Literal["salaried", "aop", "property_rental"]] = None
    reasoning: str