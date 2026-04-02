from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class BaseSchema(BaseModel):
    """
    Root schema every other schema inherits from.
    Centralises model configuration so it never needs repeating.
    """

    model_config = {
        "from_attributes": True,
        "str_strip_whitespace": True,
        "str_min_length": 1,
    }


class LabelBase(BaseSchema):
    """Shared fields for all label schemas."""

    name: str = Field(..., min_length=1, max_length=50, examples=["Work"])


class LabelCreate(LabelBase):
    """Request body for creating a label."""

    pass


class LabelUpdate(BaseSchema):
    """Request body for updating a label — name is required."""

    name: str = Field(..., min_length=1, max_length=50, examples=["Personal"])


class LabelResponse(LabelBase):
    """Response body for a label — includes server-assigned id."""

    id: str = Field(..., examples=["a1b2c3d4-..."])


class NoteBase(BaseSchema):
    """
    Shared fields for all note schemas.
    Validators defined here are inherited by NoteCreate and NoteResponse.
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        examples=["Meeting notes"],
    )
    content: str = Field(
        ...,
        min_length=1,
        examples=["Discussed Q3 targets and action items."],
    )

    @field_validator("title", "content", mode="before")
    @classmethod
    def strip_and_reject_blank(cls, v: str) -> str:
        """Reject strings that are blank after stripping whitespace."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field must not be blank or whitespace only.")
        return stripped


class NoteCreate(NoteBase):
    """
    Request body for POST /notes/.
    Inherits title + content + validators from NoteBase.
    """

    pass


class NoteUpdate(BaseSchema):
    """
    Request body for PUT /notes/{id}.
    Both fields are optional — send only what you want to change.
    """

    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        examples=["Updated title"],
    )
    content: Optional[str] = Field(
        default=None,
        min_length=1,
        examples=["Updated content."],
    )

    @field_validator("title", "content", mode="before")
    @classmethod
    def strip_if_provided(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field must not be blank or whitespace only.")
        return stripped


class NoteResponse(NoteBase):
    """
    Response body for all note endpoints.
    Extends NoteBase with server-managed fields: id, timestamps, labels.
    """

    id: str = Field(..., examples=["f7e6d5c4-..."])
    created_at: str = Field(..., examples=["2026-04-02T10:00:00+00:00"])
    updated_at: str = Field(..., examples=["2026-04-02T11:30:00+00:00"])
    labels: list[LabelResponse] = Field(default_factory=list)
