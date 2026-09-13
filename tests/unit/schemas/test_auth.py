"""
Test auth request response schemas
"""
from pydantic import ValidationError
import pytest
from schemas.auth import (
    ChangePasswordRequest,
    ForgetPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    VerifyEmailRequest,
)


def test_signup_request_valid():
    data = SignupRequest(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="Password123!",
        confirm_password="Password123!",
    )
    assert data.first_name == "John"
    assert data.password == "Password123!"


def test_signup_request_password_mismatch():
    with pytest.raises(ValidationError, match="Password not matched with confirm password"):
        SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password123!",
            confirm_password="Password456!",
        )


def test_signup_request_password_should_contain_lower_case_letter():
    with pytest.raises(ValidationError, match="Password must contain at least one lowercase letter"):
        SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="PASSWORD123!",
            confirm_password="PASSWORD123!",
        )


def test_signup_request_password_should_contain_upper_case_letter():
    with pytest.raises(ValidationError, match="Password must contain at least one uppercase letter"):
        SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="password123!",
            confirm_password="password123!",
        )


def test_signup_request_password_should_contain_number():
    with pytest.raises(ValidationError, match="Password must contain at least one number"):
        SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password!",
            confirm_password="Password!",
        )


def test_signup_request_password_should_contain_special_character():
    with pytest.raises(ValidationError, match="Password must contain at least one special character"):
        SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password123",
            confirm_password="Password123",
        )


def test_signup_request_rejects_empty_first_name():
    with pytest.raises(ValidationError):
        SignupRequest(
            first_name="",
            last_name="Doe",
            email="john@example.com",
            password="Password123!",
            confirm_password="Password123!",
        )


def test_signup_request_rejects_empty_last_name():
    with pytest.raises(ValidationError):
        SignupRequest(
            first_name="John",
            last_name="",
            email="john@example.com",
            password="Password123!",
            confirm_password="Password123!",
        )


def test_login_request_valid():
    data = LoginRequest(email="john@example.com", password="Password123!")
    assert data.email == "john@example.com"


def test_verify_email_request_valid():
    data = VerifyEmailRequest(token="abc")
    assert data.token == "abc"


def test_forget_password_request_valid():
    data = ForgetPasswordRequest(email="john@example.com")
    assert data.email == "john@example.com"


def test_reset_password_request_valid():
    data = ResetPasswordRequest(
        token="tok",
        password="Password123!",
        confirm_password="Password123!",
    )
    assert data.token == "tok"


def test_reset_password_mismatch():
    with pytest.raises(ValidationError, match="Password not matched"):
        ResetPasswordRequest(
            token="tok",
            password="Password123!",
            confirm_password="Password456!",
        )


def test_change_password_request_valid():
    data = ChangePasswordRequest(
        current_password="Password123!",
        new_password="NewPassword123!",
        confirm_password="NewPassword123!",
    )
    assert data.new_password == "NewPassword123!"


def test_change_password_rejects_same_as_current():
    with pytest.raises(ValidationError, match="different from current password"):
        ChangePasswordRequest(
            current_password="Password123!",
            new_password="Password123!",
            confirm_password="Password123!",
        )
