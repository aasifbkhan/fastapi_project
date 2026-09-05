"""
End-to-end tests for authentication.
"""
from uuid import uuid4
import pytest
from httpx import AsyncClient

class TestAuthe2e:
    """
    e2e Auth Test
    """ 
    @pytest.mark.asyncio
    async def test_user_can_signup(self):
        """
        Test complete user signup flow through HTTP.
        """
        email = f"e2e-{uuid4()}@example.com"
        payload = {
            "first_name": "E2E",
            "last_name": "User",
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!",
        }
        async with AsyncClient(
            base_url="http://localhost:8000",
        ) as client:

            response = await client.post(
                "/api/v1/auth/signup",
                json=payload,
            )

        assert response.status_code == 201
        assert response.json() == {
            "message": "Sign up successfull..!! Please check your email to verify the email."
        }

    async def test_duplicate_email_rejected(self):
        """
        Test email gets rejected, complete user signup flow through HTTP.
        """        
        email = f"e2e-{uuid4()}@example.com"
        payload = {
            "first_name": "E2E",
            "last_name": "User",
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!",
        }

        async with AsyncClient(
            base_url="http://localhost:8000",
        ) as client:

            first_response = await client.post(
                "/api/v1/auth/signup",
                json=payload,
            )

        async with AsyncClient(
            base_url="http://localhost:8000",
        ) as client:
            assert first_response.status_code == 201
            second_response = await client.post(
                "/api/v1/auth/signup",
                json=payload,
            )

        assert second_response.status_code == 409
        assert second_response.json() == {
            "detail": "Email already registered"
        }

