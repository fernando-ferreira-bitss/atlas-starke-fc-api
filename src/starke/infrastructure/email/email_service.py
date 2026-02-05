"""Email service for sending reports via SMTP."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from starke.core.config import get_settings
from starke.core.logging import get_logger

logger = get_logger(__name__)


class EmailServiceError(Exception):
    """Base exception for email service errors."""

    pass


class EmailService:
    """Service for sending HTML emails via SMTP."""

    def __init__(self) -> None:
        """Initialize email service."""
        self.settings = get_settings()
        logger.info(
            "Email service initialized",
            backend=self.settings.email_backend,
            host=self.settings.smtp_host if self.settings.email_backend == "smtp" else "gmail_api",
        )

    def send_html_email(
        self,
        recipients: list[dict[str, str]],
        subject: str,
        html_body: str,
    ) -> dict[str, Any]:
        """
        Send HTML email to multiple recipients.

        Args:
            recipients: List of dicts with 'name' and 'email' keys
            subject: Email subject
            html_body: HTML email body

        Returns:
            Dict with sending results

        Raises:
            EmailServiceError: If error occurs sending email
        """
        if self.settings.email_backend == "smtp":
            return self._send_via_smtp(recipients, subject, html_body)
        else:
            raise EmailServiceError(
                f"Email backend '{self.settings.email_backend}' not yet implemented. "
                "Currently only 'smtp' is supported."
            )

    def _send_via_smtp(
        self,
        recipients: list[dict[str, str]],
        subject: str,
        html_body: str,
    ) -> dict[str, Any]:
        """
        Send email via SMTP.

        Args:
            recipients: List of recipients
            subject: Email subject
            html_body: HTML body

        Returns:
            Dict with sending results
        """
        logger.info(
            "Sending email via SMTP",
            recipient_count=len(recipients),
            subject=subject,
        )

        sent_count = 0
        failed = []

        try:
            # Connect to SMTP server
            if self.settings.smtp_use_tls:
                server = smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port)

            # Login
            if self.settings.smtp_username and self.settings.smtp_password:
                server.login(self.settings.smtp_username, self.settings.smtp_password)
                logger.debug("SMTP authentication successful")

            # Send to each recipient
            for recipient in recipients:
                try:
                    msg = self._create_message(
                        recipient=recipient,
                        subject=subject,
                        html_body=html_body,
                    )

                    server.send_message(msg)
                    sent_count += 1

                    logger.debug(
                        "Email sent successfully",
                        recipient=recipient["email"],
                    )

                except Exception as e:
                    failed.append({
                        "recipient": recipient["email"],
                        "error": str(e),
                    })
                    logger.warning(
                        "Failed to send email to recipient",
                        recipient=recipient["email"],
                        error=str(e),
                    )

            server.quit()
            logger.info(
                "Email sending completed",
                sent=sent_count,
                failed=len(failed),
            )

            return {
                "sent": sent_count,
                "failed": len(failed),
                "failures": failed,
            }

        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {e}"
            logger.error(error_msg, error=str(e))
            raise EmailServiceError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error sending email: {e}"
            logger.error(error_msg, error=str(e))
            raise EmailServiceError(error_msg) from e

    def _create_message(
        self,
        recipient: dict[str, str],
        subject: str,
        html_body: str,
    ) -> MIMEMultipart:
        """
        Create MIME message.

        Args:
            recipient: Recipient dict with 'name' and 'email'
            subject: Email subject
            html_body: HTML body

        Returns:
            MIME message
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.settings.email_from_name} <{self.settings.email_from_address}>"
        msg["To"] = f"{recipient['name']} <{recipient['email']}>"

        # Create plain text version (basic fallback)
        text_body = "Este email contém um relatório em HTML. Por favor, visualize em um cliente de email que suporte HTML."

        # Attach parts
        part1 = MIMEText(text_body, "plain", "utf-8")
        part2 = MIMEText(html_body, "html", "utf-8")

        msg.attach(part1)
        msg.attach(part2)

        return msg

    def send_test_email(self, test_recipient: str) -> bool:
        """
        Send test email to verify configuration.

        Args:
            test_recipient: Email address to send test to

        Returns:
            True if successful, False otherwise
        """
        logger.info("Sending test email", recipient=test_recipient)

        try:
            html_body = """
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: #2563eb;">Test Email - Starke</h2>
                <p>This is a test email from the Starke cash flow reporting system.</p>
                <p>If you received this email, your email configuration is working correctly!</p>
                <hr>
                <p style="color: #64748b; font-size: 0.9em;">
                    Sent from Starke - Cash Flow Reporting System
                </p>
            </body>
            </html>
            """

            result = self.send_html_email(
                recipients=[{"name": "Test User", "email": test_recipient}],
                subject="Test Email - Starke Cash Flow System",
                html_body=html_body,
            )

            success = result["sent"] > 0
            logger.info(
                "Test email result",
                success=success,
                sent=result["sent"],
                failed=result["failed"],
            )

            return success

        except Exception as e:
            logger.error("Test email failed", error=str(e))
            return False
