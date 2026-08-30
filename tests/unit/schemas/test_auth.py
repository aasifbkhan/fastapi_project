"""
Test auth request response schemas
"""
from pydantic import ValidationError
import pytest
from schemas.auth import SignupRequest

def test_signup_request_valid():
    """
    Test SignupRequest with valid data
    """
    data = SignupRequest(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="Password123!",
        confirm_password="Password123!",
    )

    assert data.first_name == "John"
    assert data.last_name == "Doe"
    assert data.email == "john@example.com"
    assert data.password == "Password123!"

def test_signup_request_password_mismatch():
    """
    Test SignupRequest with "password" and "confirm_password" mismatch
    """
    with pytest.raises(
        ValidationError,
        match="Password not matched with confirm password"
    ):
        SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password123!",
            confirm_password="Password456!",
        )

def test_signup_request_password_should_contain_lower_case_letter():
    """
    Test SignupRequest with password should contain lower case letter
    """
    with pytest.raises(
        ValidationError,
        match="Password must contain at least one lowercase letter"
    ):
        SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="PASSWORD123!",
            confirm_password="PASSWORD123!",
        )

def test_signup_request_password_should_contain_upper_case_letter():
    """
    Test SignupRequest with password should contain upper case letter
    """
    with pytest.raises(
        ValidationError,
        match="Password must contain at least one uppercase letter"
    ):
        SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="password123!",
            confirm_password="password123!",
        )

def test_signup_request_password_should_contain_number():
    """
    Test SignupRequest with password should contain numbers
    """
    with pytest.raises(
        ValidationError,
        match="Password must contain at least one number"
    ):
        SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password!",
            confirm_password="Password!",
        )

def test_signup_request_password_should_contain_special_character():
    """
    Test SignupRequest with password should contain special character
    """
    with pytest.raises(
        ValidationError,
        match="Password must contain at least one special character"
    ):
        SignupRequest(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            password="Password123",
            confirm_password="Password123",
        )
