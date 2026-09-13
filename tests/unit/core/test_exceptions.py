"""
Unit tests for domain exceptions.
"""
from core.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    WrongPasswordError,
)


def test_email_already_registered_error_default_message():
    error = EmailAlreadyRegisteredError()
    assert str(error) == "Email already registered"
    assert error.message == "Email already registered"


def test_email_already_registered_error_custom_message():
    error = EmailAlreadyRegisteredError("custom")
    assert str(error) == "custom"


def test_invalid_credentials_error_default_message():
    error = InvalidCredentialsError()
    assert error.message == "Invalid email or password"


def test_inactive_user_error_default_message():
    error = InactiveUserError()
    assert "not active" in error.message.lower()


def test_invalid_token_error_default_message():
    error = InvalidTokenError()
    assert error.message == "Invalid token"


def test_token_expired_error_default_message():
    error = TokenExpiredError()
    assert error.message == "Token has expired"


def test_wrong_password_error_default_message():
    error = WrongPasswordError()
    assert error.message == "Current password is incorrect"
