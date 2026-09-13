"""
Domain exceptions for the application.
"""


class EmailAlreadyRegisteredError(Exception):
    """Raised when a signup email is already registered."""

    def __init__(self, message: str = "Email already registered"):
        self.message = message
        super().__init__(message)


class InvalidCredentialsError(Exception):
    """Raised when login credentials are invalid."""

    def __init__(self, message: str = "Invalid email or password"):
        self.message = message
        super().__init__(message)


class InactiveUserError(Exception):
    """Raised when an inactive (unverified) user attempts a restricted action."""

    def __init__(self, message: str = "Account is not active. Please verify your email"):
        self.message = message
        super().__init__(message)


class InvalidTokenError(Exception):
    """Raised when a token is missing, malformed, or already used."""

    def __init__(self, message: str = "Invalid token"):
        self.message = message
        super().__init__(message)


class TokenExpiredError(Exception):
    """Raised when a token has expired."""

    def __init__(self, message: str = "Token has expired"):
        self.message = message
        super().__init__(message)


class WrongPasswordError(Exception):
    """Raised when the current password does not match during change-password."""

    def __init__(self, message: str = "Current password is incorrect"):
        self.message = message
        super().__init__(message)
