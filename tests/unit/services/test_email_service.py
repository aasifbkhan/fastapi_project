"""
Test EmailService
"""
from unittest.mock import MagicMock, patch

import pytest

from services.email_service import EmailService

@pytest.mark.asyncio
async def test_send_email():
    """
    Test send email function
    """
    email_service = EmailService()

    email_service.smtp_use_tls = True
    email_service.smtp_username = "username"
    email_service.smtp_password = "password"

    smtp = MagicMock()

    # The object returned by `with SMTP(...) as smtp`
    smtp.__enter__.return_value = smtp

    with patch(
        "services.email_service.smtplib.SMTP",
        return_value=smtp
    ) as smtp_class:
        await email_service.send_email(
            to="john@example.com",
            subject="Welcome",
            body="Welcome to DevFlow!"
        )


    smtp_class.assert_called_once_with(
        email_service.smtp_host,
        email_service.smtp_port,
    )

    smtp.starttls.assert_called_once_with()

    smtp.login.assert_called_once_with(
        email_service.smtp_username,
        email_service.smtp_password,
    )

    smtp.send_message.assert_called_once()

    message = smtp.send_message.call_args.args[0]

    assert message["From"] == email_service.smtp_from
    assert message["To"] == "john@example.com"
    assert message["Subject"] == "Welcome"
    assert message.get_content().strip() == "Welcome to DevFlow!"
    