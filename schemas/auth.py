"""
This module contains classes of auth api request and response pydantic model
"""
from pydantic import BaseModel, Field, EmailStr, model_validator, ValidationError

class SignupRequest(BaseModel):
    """
    This class contains the signup request field and validation
    """
    first_name: str = Field(max_length=15)
    last_name: str = Field(max_length=15)
    email: EmailStr
    password:str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_password(self):
        """
        This function containes the password validation constrains.
        """
        if self.password != self.confirm_password:
            raise ValueError("Password not matched with confirm password")

        password = self.password

        if not any (char.islower() for char in password):
            raise ValueError("Password must contain at least one lowercase letter")

        if not any (char.isupper() for char in password):
            raise ValueError("Password must contain at least one uppercase letter")

        if not any (char.isdigit() for char in password):
            raise ValueError("Password must contain at least one number")

        if not any(not char.isalnum() for char in password):
            raise ValueError("Password must contain at least one special character")

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

class SignupResponse(BaseModel):
    """
    This class contains the signup request response field
    """
    message: str
