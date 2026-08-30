"""
Security module creates and verify hash password
"""
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

password_hasher = PasswordHasher()

def hash_password(password: str) -> str:
    """
    This function creates hash password
    """
    return password_hasher.hash(password)

def verify_password(password, hashed_password) -> bool:
    """
    This function verfiy the hash password
    """
    try:
        password_hasher.verify(hashed_password, password)
        return True
    except VerifyMismatchError:
        return False
