"""Validation for every request body (Pydantic)."""
import re
from typing import Annotated, ClassVar, Literal, Optional

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)


def check_email(value):
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
        raise ValueError("must be a valid email address")
    return value


def check_password(value):
    if not 8 <= len(value.encode("utf-8")) <= 72:
        raise ValueError("must be 8 to 72 characters long")
    return value


# Reusable field types
Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, max_length=150),
    AfterValidator(check_email),
]
Password = Annotated[str, AfterValidator(check_password)]
Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=150)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)]
ProjectDescription = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
RevisionDescription = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
ProjectStatus = Literal["Active", "Completed", "On-hold"]
RevisionStatus = Literal["Pending", "Completed", "Rejected"]
IntId = Annotated[int, Field(strict=True, ge=1, le=2147483647)]  # strict: "3" and true are not accepted and 2147483647 is the max for a signed 32-bit integer


class Body(BaseModel):
    """Base for every request body: unknown fields are rejected."""
    model_config = ConfigDict(extra="forbid")


class UpdateBody(Body):
    """Base for PATCH bodies: send at least one field, and only nullable fields may be null."""
    nullable_fields: ClassVar[tuple] = ()

    @model_validator(mode="after")
    def check_sent_fields(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        for name in self.model_fields_set:
            if getattr(self, name) is None and name not in self.nullable_fields:
                raise ValueError(f"{name} cannot be null")
        return self


# Authentication

class RegisterBody(Body):
    username: Username
    email: Email
    password: Password


class LoginBody(Body):
    email: Email
    password: Password


# Clients 

class ClientCreate(Body):
    name: Name
    email: Email


class ClientUpdate(UpdateBody):
    name: Optional[Name] = None
    email: Optional[Email] = None


# Projects 

class ProjectCreate(Body):
    title: Name
    description: Optional[ProjectDescription] = None
    client_id: Optional[IntId] = None
    agreed_revisions: Annotated[int, Field(strict=True, ge=0, le=1000)]
    status: ProjectStatus = "Active"


class ProjectUpdate(UpdateBody):
    nullable_fields: ClassVar[tuple] = ("description", "client_id")

    title: Optional[Name] = None
    description: Optional[ProjectDescription] = None
    client_id: Optional[IntId] = None
    agreed_revisions: Optional[Annotated[int, Field(strict=True, ge=0, le=1000)]] = None
    status: Optional[ProjectStatus] = None


# Revision requests 

class RevisionRequestCreate(Body):
    description: RevisionDescription


class RevisionRequestUpdate(UpdateBody):
    description: Optional[RevisionDescription] = None
    status: Optional[RevisionStatus] = None
