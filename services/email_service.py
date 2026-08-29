"""
This madule has the email integration setup 
"""
import smtplib
from email.message import EmailMessage
from core.config import settings
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

    async def send_email(self, to: str, subject: str, body: str):
        """
        This function send the email to the user
        """
        message = EmailMessage()

        message["From"] = self.smtp_from
        message["To"] = to
        message["Subject"] = subject

        message.set_content(body)
        print("hello")

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(
                self.smtp_username,
                self.smtp_password,
            )
            smtp.send_message(message)
