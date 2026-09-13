"""
Test AuthService
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from core.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
    WrongPasswordError,
)
from models import AuthToken, AuthTokenType, User
from schemas.auth import LoginRequest, SignupRequest
from services.auth_service import AuthService


def _make_service():
    user_repo = AsyncMock()
    token_repo = AsyncMock()
    return AuthService(user_repo, token_repo), user_repo, token_repo


@pytest.mark.asyncio
async def test_signup_success():
    """Test auth service signup success returns user and raw token."""
    auth_service, repository, token_repo = _make_service()
    repository.get_by_email.return_value = None
    expected_user = User(
        id=uuid4(),
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="hashed",
    )
    repository.create.return_value = expected_user
    token_repo.invalidate_user_tokens = AsyncMock()
    token_repo.create = AsyncMock()

    data = SignupRequest(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="Password123!",
        confirm_password="Password123!",
    )
    session = AsyncMock()

    with patch(
        "services.auth_service.generate_url_safe_token",
        return_value="raw-verify-token",
    ):
        user, raw_token = await auth_service.signup(data, session)

    assert user is expected_user
    assert raw_token == "raw-verify-token"
    repository.get_by_email.assert_awaited_once_with(data.email, session)
    token_repo.create.assert_awaited()


@pytest.mark.asyncio
async def test_signup_with_existing_email():
    """Test signup with existing email."""
    auth_service, repository, _token_repo = _make_service()
    repository.get_by_email.return_value = object()

    data = SignupRequest(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="Password123!",
        confirm_password="Password123!",
    )
    session = AsyncMock()

    with pytest.raises(EmailAlreadyRegisteredError, match="Email already registered"):
        await auth_service.signup(data, session)

    repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_signup_hashes_password():
    """Test signup hashes password."""
    auth_service, repository, token_repo = _make_service()
    repository.get_by_email.return_value = None
    repository.create.return_value = User(
        id=uuid4(),
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="hashed_password",
    )
    token_repo.invalidate_user_tokens = AsyncMock()
    token_repo.create = AsyncMock()

    data = SignupRequest(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="Password123!",
        confirm_password="Password123!",
    )
    session = AsyncMock()

    with patch(
        "services.auth_service.hash_password",
        return_value="hashed_password",
    ) as mock_hash, patch(
        "services.auth_service.generate_url_safe_token",
        return_value="token",
    ):
        await auth_service.signup(data, session)

    mock_hash.assert_called_once_with("Password123!")
    created_user = repository.create.call_args.args[0]
    assert created_user.password == "hashed_password"


@pytest.mark.asyncio
async def test_signup_maps_integrity_error_to_email_already_registered():
    """Test concurrent duplicate email raises EmailAlreadyRegisteredError."""
    auth_service, repository, _token_repo = _make_service()
    repository.get_by_email.return_value = None
    repository.create.side_effect = IntegrityError(
        "duplicate key",
        params=None,
        orig=Exception("unique violation"),
    )

    data = SignupRequest(
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="Password123!",
        confirm_password="Password123!",
    )
    session = AsyncMock()

    with pytest.raises(EmailAlreadyRegisteredError, match="Email already registered"):
        await auth_service.signup(data, session)

    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_verify_email_success():
    auth_service, user_repo, token_repo = _make_service()
    user_id = uuid4()
    auth_token = AuthToken(
        id=uuid4(),
        user_id=user_id,
        token_hash="hash",
        token_type=AuthTokenType.EMAIL_VERIFICATION.value,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    user = User(
        id=user_id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="hashed",
        is_active=False,
    )
    token_repo.get_valid_by_hash_and_type.return_value = auth_token
    user_repo.get_by_id.return_value = user
    token_repo.mark_used = AsyncMock()
    user_repo.update = AsyncMock(return_value=user)
    session = AsyncMock()

    result = await auth_service.verify_email("raw-token", session)

    assert result.is_active is True
    token_repo.mark_used.assert_awaited()
    user_repo.update.assert_awaited()


@pytest.mark.asyncio
async def test_verify_email_invalid_token():
    auth_service, _user_repo, token_repo = _make_service()
    token_repo.get_valid_by_hash_and_type.return_value = None
    token_repo.get_by_hash_and_type.return_value = None
    session = AsyncMock()

    with pytest.raises(InvalidTokenError):
        await auth_service.verify_email("bad", session)


@pytest.mark.asyncio
async def test_verify_email_expired_token():
    auth_service, _user_repo, token_repo = _make_service()
    token_repo.get_valid_by_hash_and_type.return_value = None
    token_repo.get_by_hash_and_type.return_value = AuthToken(
        id=uuid4(),
        user_id=uuid4(),
        token_hash="hash",
        token_type=AuthTokenType.EMAIL_VERIFICATION.value,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        used_at=None,
    )
    session = AsyncMock()

    with pytest.raises(TokenExpiredError):
        await auth_service.verify_email("expired", session)


@pytest.mark.asyncio
async def test_verify_email_already_used_token():
    auth_service, _user_repo, token_repo = _make_service()
    token_repo.get_valid_by_hash_and_type.return_value = None
    token_repo.get_by_hash_and_type.return_value = AuthToken(
        id=uuid4(),
        user_id=uuid4(),
        token_hash="hash",
        token_type=AuthTokenType.EMAIL_VERIFICATION.value,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        used_at=datetime.now(timezone.utc),
    )
    session = AsyncMock()

    with pytest.raises(InvalidTokenError, match="already been used"):
        await auth_service.verify_email("used", session)


@pytest.mark.asyncio
async def test_login_success():
    auth_service, user_repo, token_repo = _make_service()
    user = User(
        id=uuid4(),
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="hashed",
        is_active=True,
    )
    user_repo.get_by_email.return_value = user
    token_repo.create = AsyncMock()
    session = AsyncMock()

    with patch(
        "services.auth_service.verify_password",
        return_value=True,
    ), patch(
        "services.auth_service.create_access_token",
        return_value="access",
    ), patch(
        "services.auth_service.create_refresh_token",
        return_value="refresh",
    ):
        result = await auth_service.login(
            LoginRequest(email="john@example.com", password="Password123!"),
            session,
        )

    assert result["access_token"] == "access"
    assert result["refresh_token"] == "refresh"
    assert result["token_type"] == "bearer"
    token_repo.create.assert_awaited()


@pytest.mark.asyncio
async def test_login_wrong_password():
    auth_service, user_repo, _token_repo = _make_service()
    user_repo.get_by_email.return_value = User(
        id=uuid4(),
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="hashed",
        is_active=True,
    )
    session = AsyncMock()

    with patch("services.auth_service.verify_password", return_value=False):
        with pytest.raises(InvalidCredentialsError):
            await auth_service.login(
                LoginRequest(email="john@example.com", password="bad"),
                session,
            )


@pytest.mark.asyncio
async def test_login_unknown_email():
    auth_service, user_repo, _token_repo = _make_service()
    user_repo.get_by_email.return_value = None
    session = AsyncMock()

    with pytest.raises(InvalidCredentialsError):
        await auth_service.login(
            LoginRequest(email="missing@example.com", password="Password123!"),
            session,
        )


@pytest.mark.asyncio
async def test_login_inactive_user():
    auth_service, user_repo, _token_repo = _make_service()
    user_repo.get_by_email.return_value = User(
        id=uuid4(),
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="hashed",
        is_active=False,
    )
    session = AsyncMock()

    with patch("services.auth_service.verify_password", return_value=True):
        with pytest.raises(InactiveUserError):
            await auth_service.login(
                LoginRequest(email="john@example.com", password="Password123!"),
                session,
            )


@pytest.mark.asyncio
async def test_refresh_success():
    auth_service, user_repo, token_repo = _make_service()
    user_id = uuid4()
    user = User(
        id=user_id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="hashed",
        is_active=True,
    )
    stored = AuthToken(
        id=uuid4(),
        user_id=user_id,
        token_hash="hash",
        token_type=AuthTokenType.REFRESH.value,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    token_repo.get_valid_by_hash_and_type.return_value = stored
    token_repo.mark_used = AsyncMock()
    token_repo.create = AsyncMock()
    user_repo.get_by_id.return_value = user
    session = AsyncMock()

    with patch(
        "services.auth_service.decode_token",
        return_value={"sub": str(user_id), "type": "refresh"},
    ), patch(
        "services.auth_service.create_access_token",
        return_value="new-access",
    ), patch(
        "services.auth_service.create_refresh_token",
        return_value="new-refresh",
    ):
        result = await auth_service.refresh("old-refresh", session)

    assert result["access_token"] == "new-access"
    assert result["refresh_token"] == "new-refresh"
    token_repo.mark_used.assert_awaited()


@pytest.mark.asyncio
async def test_refresh_invalid_token():
    auth_service, _user_repo, _token_repo = _make_service()
    session = AsyncMock()

    with patch(
        "services.auth_service.decode_token",
        side_effect=ValueError("bad"),
    ):
        with pytest.raises(InvalidTokenError):
            await auth_service.refresh("bad", session)


@pytest.mark.asyncio
async def test_forget_password_known_email():
    auth_service, user_repo, token_repo = _make_service()
    user = User(
        id=uuid4(),
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="hashed",
    )
    user_repo.get_by_email.return_value = user
    token_repo.invalidate_user_tokens = AsyncMock()
    token_repo.create = AsyncMock()
    session = AsyncMock()

    with patch(
        "services.auth_service.generate_url_safe_token",
        return_value="reset-token",
    ):
        raw = await auth_service.forget_password("john@example.com", session)

    assert raw == "reset-token"


@pytest.mark.asyncio
async def test_forget_password_unknown_email():
    auth_service, user_repo, token_repo = _make_service()
    user_repo.get_by_email.return_value = None
    session = AsyncMock()

    raw = await auth_service.forget_password("missing@example.com", session)

    assert raw is None
    token_repo.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_reset_password_success():
    auth_service, user_repo, token_repo = _make_service()
    user_id = uuid4()
    auth_token = AuthToken(
        id=uuid4(),
        user_id=user_id,
        token_hash="hash",
        token_type=AuthTokenType.PASSWORD_RESET.value,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    user = User(
        id=user_id,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="old-hash",
    )
    token_repo.get_valid_by_hash_and_type.return_value = auth_token
    user_repo.get_by_id.return_value = user
    token_repo.mark_used = AsyncMock()
    token_repo.invalidate_user_tokens = AsyncMock()
    user_repo.update = AsyncMock(return_value=user)
    session = AsyncMock()

    with patch(
        "services.auth_service.hash_password",
        return_value="new-hash",
    ):
        result = await auth_service.reset_password("raw", "NewPassword123!", session)

    assert result.password == "new-hash"
    assert token_repo.invalidate_user_tokens.await_count >= 1


@pytest.mark.asyncio
async def test_change_password_success():
    auth_service, user_repo, token_repo = _make_service()
    user = User(
        id=uuid4(),
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="old-hash",
        is_active=True,
    )
    user_repo.get_by_id.return_value = user
    token_repo.invalidate_user_tokens = AsyncMock()
    user_repo.update = AsyncMock(return_value=user)
    session = AsyncMock()

    with patch(
        "services.auth_service.verify_password",
        return_value=True,
    ), patch(
        "services.auth_service.hash_password",
        return_value="new-hash",
    ):
        result = await auth_service.change_password(
            user,
            "Password123!",
            "NewPassword123!",
            session,
        )

    assert result.password == "new-hash"
    token_repo.invalidate_user_tokens.assert_awaited()


@pytest.mark.asyncio
async def test_change_password_wrong_current():
    auth_service, user_repo, _token_repo = _make_service()
    user = User(
        id=uuid4(),
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        password="old-hash",
        is_active=True,
    )
    user_repo.get_by_id.return_value = user
    session = AsyncMock()

    with patch("services.auth_service.verify_password", return_value=False):
        with pytest.raises(WrongPasswordError):
            await auth_service.change_password(
                user,
                "WrongPassword123!",
                "NewPassword123!",
                session,
            )
