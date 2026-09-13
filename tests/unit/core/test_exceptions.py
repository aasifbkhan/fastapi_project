"""
Unit tests for domain exceptions.
"""
from core.exceptions import EmailAlreadyRegisteredError


def test_email_already_registered_error_default_message():
    error = EmailAlreadyRegisteredError()
    assert str(error) == "Email already registered"
    assert error.message == "Email already registered"


def test_email_already_registered_error_custom_message():
    error = EmailAlreadyRegisteredError("custom")
    assert str(error) == "custom"
