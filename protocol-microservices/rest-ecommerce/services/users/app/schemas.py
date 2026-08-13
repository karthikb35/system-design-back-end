"""Pydantic schemas — the service's public contract (request/response shapes).

These are separate from the ORM models on purpose: the wire contract can evolve
independently of the database schema, and the password never appears in output.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    """Input for creating a user. Validated at the HTTP boundary."""
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    """Output shape — note there is NO password field."""
    model_config = ConfigDict(from_attributes=True)  # allow ORM -> schema

    id: str
    email: EmailStr
    full_name: str
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
