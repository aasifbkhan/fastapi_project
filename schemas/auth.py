"""
This module contains classes of auth api request and response pydantic model
"""
from pydantic import BaseModel, EmailStr, Field, model_validator


def validate_password_complexity(password: str) -> None:
    """Raise ValueError when password does not meet complexity rules."""
    if not any(char.islower() for char in password):
        raise ValueError("Password must contain at least one lowercase letter")

    if not any(char.isupper() for char in password):
        raise ValueError("Password must contain at least one uppercase letter")

    if not any(char.isdigit() for char in password):
        raise ValueError("Password must contain at least one number")

    if not any(not char.isalnum() for char in password):
        raise ValueError("Password must contain at least one special character")


class SignupRequest(BaseModel):
    """
    This class contains the signup request field and validation
    """
    first_name: str = Field(min_length=1, max_length=15)
    last_name: str = Field(min_length=1, max_length=15)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_password(self):
        """
        This function containes the password validation constrains.
        """
        if self.password != self.confirm_password:
            raise ValueError("Password not matched with confirm password")

        validate_password_complexity(self.password)
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": "john@example.com",
                    "password": "Password123!",
                    "confirm_password": "Password123!"
                }
            ]
        }
    }


class MessageResponse(BaseModel):
    """Shared message-only response for auth endpoints."""

    message: str


class SignupResponse(MessageResponse):
    """
    This class contains the signup request response field
    """


class VerifyEmailRequest(BaseModel):
    """Request body for email verification."""

    token: str = Field(min_length=1)


class LoginRequest(BaseModel):
    """Login credentials."""

    email: EmailStr
    password: str = Field(min_length=1)


class TokenPairResponse(BaseModel):
    """Access + refresh JWT pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginResponse(TokenPairResponse):
    """Login success response."""


class RefreshRequest(BaseModel):
    """Request body for refresh token rotation."""

    refresh_token: str = Field(min_length=1)


class RefreshResponse(TokenPairResponse):
    """Refresh success response."""


class ForgetPasswordRequest(BaseModel):
    """Request body for forget-password."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request body for reset-password."""

    token: str = Field(min_length=1)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_password(self):
        """Ensure confirm matches and password meets complexity rules."""
        if self.password != self.confirm_password:
            raise ValueError("Password not matched with confirm password")
        validate_password_complexity(self.password)
        return self


class ChangePasswordRequest(BaseModel):
    """Request body for change-password."""

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_password(self):
        """Ensure confirm matches, differs from current, and meets complexity."""
        if self.new_password != self.confirm_password:
            raise ValueError("Password not matched with confirm password")
        if self.new_password == self.current_password:
            raise ValueError("New password must be different from current password")
        validate_password_complexity(self.new_password)
        return self
