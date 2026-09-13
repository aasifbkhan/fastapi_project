"""
Domain exceptions for the application.
"""


class EmailAlreadyRegisteredError(Exception):
    """Raised when a signup email is already registered."""

    def __init__(self, message: str = "Email already registered"):
        self.message = message
        super().__init__(message)
