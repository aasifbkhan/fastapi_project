"""
This madule has the email integration setup 
"""
import logging
import smtplib
from email.message import EmailMessage

from core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    This email service class provide the send email functions to user.
    """
    def __init__(self):
        self.smtp_host = settings.email_settings.get('smtp_host')
        self.smtp_port = settings.email_settings.get('smtp_port')
        self.smtp_username = settings.email_settings.get('smtp_username')
        self.smtp_password = settings.email_settings.get('smtp_password')
        self.smtp_from = settings.email_settings.get('smtp_from')
        self.smtp_use_tls = settings.email_settings.get("smtp_use_tls", False)

    def send_email(self, to: str, subject: str, body: str):
        """
        Send an email synchronously. Failures are logged and not raised
        so signup can still return 201 when SMTP fails.
        """
        message = EmailMessage()

        message["From"] = self.smtp_from
        message["To"] = to
        message["Subject"] = subject

        message.set_content(body)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
                if self.smtp_use_tls:
                    smtp.starttls()

                if self.smtp_username and self.smtp_password:
                    smtp.login(
                        self.smtp_username,
                        self.smtp_password,
                    )

                smtp.send_message(message)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception(
                "Failed to send email to=%s subject=%s",
                to,
                subject,
            )
