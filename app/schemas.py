from typing import Optional

from pydantic import BaseModel, Field, field_validator, EmailStr


class BaseSchema(BaseModel):
    """Root schema — shared Pydantic config inherited by all others."""

    model_config = {
        "from_attributes": True,
        "str_strip_whitespace": True,
        "str_min_length": 1,
    }


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


class NoteBase(BaseSchema):
    """Shared fields and validators for note schemas."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Short descriptive title for the note.",
        examples=["Meeting notes"],
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Full body content of the note.",
        examples=["Discussed Q3 targets and action items."],
    )

    @field_validator("title", "content", mode="before")
    @classmethod
    def reject_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field must not be blank or whitespace only.")
        return stripped


class NoteCreate(NoteBase):
    """Request body for **POST /notes/**."""

    model_config = {
        **BaseSchema.model_config,
        "json_schema_extra": {
            "example": {
                "title": "Meeting notes",
                "content": "Discussed Q3 targets and action items.",
            }
        },
    }


class NoteUpdate(BaseSchema):
    """
    Request body for **PUT /notes/{note_id}**.
    Send only the fields you want to change — both are optional.
    """

    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="New title. Omit to leave unchanged.",
        examples=["Updated meeting notes"],
    )
    content: Optional[str] = Field(
        default=None,
        min_length=1,
        description="New content. Omit to leave unchanged.",
        examples=["Added follow-up tasks from the Q3 review."],
    )

    model_config = {
        **BaseSchema.model_config,
        "json_schema_extra": {
            "example": {
                "title": "Updated meeting notes",
                "content": "Added follow-up tasks from the Q3 review.",
            }
        },
    }

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
    Response schema for a single note.
    Extends NoteBase with server-managed fields and associated labels.
    """

    id: str = Field(
        ...,
        description="Server-assigned UUID.",
        examples=["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
    )
    created_at: str = Field(
        ...,
        description="ISO 8601 UTC timestamp of creation.",
        examples=["2026-04-02T10:00:00+00:00"],
    )
    updated_at: str = Field(
        ...,
        description="ISO 8601 UTC timestamp of last update.",
        examples=["2026-04-02T11:30:00+00:00"],
    )
    labels: list[LabelResponse] = Field(
        default_factory=list,
        description="Labels currently attached to this note.",
    )

    model_config = {
        **BaseSchema.model_config,
        "json_schema_extra": {
            "example": {
                "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                "title": "Meeting notes",
                "content": "Discussed Q3 targets and action items.",
                "created_at": "2026-04-02T10:00:00+00:00",
                "updated_at": "2026-04-02T11:30:00+00:00",
                "labels": [
                    {
                        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "name": "Work",
                    }
                ],
            }
        },
    }


class UserBase(BaseSchema):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    id: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[str] = None
