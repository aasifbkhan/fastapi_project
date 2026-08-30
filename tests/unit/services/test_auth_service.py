"""
Test AuthService
"""
from unittest.mock import AsyncMock, patch
import pytest
from services.auth_service import AuthService
from schemas.auth import SignupRequest

@pytest.mark.asyncio
async def test_signup_success():
    """
    Test auth service signup success
    """
    repository = AsyncMock()

    repository.get_by_email.return_value = None

    expected_user = object()
    repository.create.return_value = expected_user

    auth_service = AuthService(repository)

    data = SignupRequest(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="Password123!",
        confirm_password="Password123!"
    )

    session = AsyncMock()

    result = await auth_service.signup(data, session)

    assert result is expected_user
    repository.get_by_email.assert_awaited_once_with(
        data.email,
        session,
    )

@pytest.mark.asyncio
async def test_signup_with_existing_email():
    """
    Test signup with  existing email
    """
    repository = AsyncMock()

    existing_user = object()
    repository.get_by_email.return_value = existing_user

    auth_service = AuthService(repository)

    data = SignupRequest(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="Password123!",
        confirm_password="Password123!"
    )

    session = AsyncMock()

    with pytest.raises(
        ValueError,
        match="Email already registered"
    ):
        await auth_service.signup(data, session)

    repository.create.assert_not_awaited()

@pytest.mark.asyncio
async def test_signup_hashes_password():
    """
    Test signup hashes password
    """
    repository = AsyncMock()
    repository.get_by_email.return_value = None
    repository.create.return_value = object()

    auth_service = AuthService(repository)

    data = SignupRequest(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="Password123!",
        confirm_password="Password123!"
    )

    session = AsyncMock()

    with patch(
        "services.auth_service.hash_password",
        return_value="hashed_password"
    ) as mock_hash:
        await auth_service.signup(data, session)

    mock_hash.assert_called_once_with("Password123!")

    created_user = repository.create.call_args.args[0]

    assert created_user.first_name == "John"
    assert created_user.last_name == "Doe"
    assert created_user.email == "john@example.com"
    assert created_user.password == "hashed_password"
