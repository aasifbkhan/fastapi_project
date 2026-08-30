"""
Unit tests for password hashing and verfications
"""
from core.security import hash_password, verify_password

def test_hash_password():
    """
    Test password is getting hashed
    """
    password = "Password123!"
    hashed_password = hash_password(password)

    assert hashed_password != password
    assert hashed_password

def test_verify_password_success():
    """
    Test password verification is success
    """
    password = "Password123!"
    hashed_password = hash_password(password)

    assert verify_password(password,  hashed_password) is True

def test_verify_password_failure():
    """
    Test password verification is failed
    """
    password = "Password123!"
    hashed_password = hash_password(password)

    assert verify_password("WrongPassword123!",  hashed_password) is False
