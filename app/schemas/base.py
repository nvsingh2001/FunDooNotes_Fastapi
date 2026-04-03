from pydantic import BaseModel

class BaseSchema(BaseModel):
    """Root schema — shared Pydantic config inherited by all others."""

    model_config = {
        "from_attributes": True,
        "str_strip_whitespace": True,
        "str_min_length": 1,
    }
