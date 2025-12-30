from pydantic import BaseModel, Field, field_validator
import re
from typing import List, Optional


class CreateValidatorRequest(BaseModel):
    num_validators: int = Field(..., gt=0, description="Number of validators to create")
    fee_recipient: str = Field(..., description="Ethereum address for validator rewards")

    @field_validator("fee_recipient")
    @classmethod
    def validate_ethereum_address(cls, v: str) -> str:
        """Validate Ethereum address format (0x followed by 40 hex characters)"""
        pattern = r"^0x[a-fA-F0-9]{40}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid Ethereum address format. Must be 0x followed by 40 hex characters.")
        return v


class CreateValidatorResponse(BaseModel):
    request_id: str
    message: str


class ValidatorStatusResponse(BaseModel):
    status: str
    keys: Optional[List[str]] = None
    message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    database: str


