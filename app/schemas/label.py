from pydantic import Field
from .base import BaseSchema

class LabelBase(BaseSchema):
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Display name of the label.",
        examples=["Work"],
    )


class LabelCreate(LabelBase):
    """Request body for **POST /labels/**."""

    model_config = {
        **BaseSchema.model_config,
        "json_schema_extra": {"example": {"name": "Work"}},
    }


class LabelUpdate(BaseSchema):
    """Request body for **PUT /labels/{label_id}**."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="New name for the label.",
        examples=["Personal"],
    )

    model_config = {
        **BaseSchema.model_config,
        "json_schema_extra": {"example": {"name": "Personal"}},
    }


class LabelResponse(LabelBase):
    """Response schema for a single label."""

    id: str = Field(
        ...,
        description="Server-assigned UUID.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )

    model_config = {
        **BaseSchema.model_config,
        "json_schema_extra": {
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "Work",
            }
        },
    }
