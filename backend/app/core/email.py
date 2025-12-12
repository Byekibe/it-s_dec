"""
Email service for sending transactional emails.

Uses Flask-Mail for SMTP integration.
"""

from flask import current_app, render_template
from flask_mail import Mail, Message

mail = Mail()


def init_mail(app):
    """Initialize Flask-Mail with app."""
    mail.init_app(app)


def send_email(to: str, subject: str, body: str, html: str = None):
    """
    Send an email synchronously.

    For async sending, use send_email_task from tasks.py.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Plain text body
        html: Optional HTML body
    """
    msg = Message(
        subject=subject,
        recipients=[to],
        body=body,
        html=html,
        sender=current_app.config.get('MAIL_DEFAULT_SENDER')
    )
    mail.send(msg)


def send_password_reset_email(to: str, reset_url: str):
    """
    Send password reset email.

    Args:
        to: User's email address
        reset_url: URL with reset token
    """
    subject = "Reset Your Password"
    body = f"""
You requested a password reset.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour.

If you did not request this, please ignore this email.
"""
    # html = render_template('emails/password_reset.html', reset_url=reset_url)
    send_email(to=to, subject=subject, body=body)


def send_email_verification(to: str, verify_url: str):
    """
    Send email verification email.

    Args:
        to: User's email address
        verify_url: URL with verification token
    """
    subject = "Verify Your Email"
    body = f"""
Welcome! Please verify your email address.

Click the link below to verify:
{verify_url}

This link will expire in 24 hours.
"""
    send_email(to=to, subject=subject, body=body)


def send_user_invitation(to: str, inviter_name: str, tenant_name: str, invite_url: str):
    """
    Send user invitation email.

    Args:
        to: Invitee's email address
        inviter_name: Name of person sending invite
        tenant_name: Name of the organization
        invite_url: URL to accept invitation
    """
    subject = f"You've been invited to join {tenant_name}"
    body = f"""
{inviter_name} has invited you to join {tenant_name}.

Click the link below to accept the invitation and create your account:
{invite_url}

This invitation will expire in 7 days.
"""
    send_email(to=to, subject=subject, body=body)
