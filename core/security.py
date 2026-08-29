from argon2 import PasswordHasher

password_hasher = PasswordHasher()

def hash_password(password: str) -> str:
    return password_hasher.hash(password)

def verify_password(password, hashed_password) -> bool:
    try:
        password_hasher.verify(hashed_password, password)
        return True
    except Exception:
        return False