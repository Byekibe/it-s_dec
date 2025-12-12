"""
Celery tasks for background processing.

All async tasks should be defined here or in blueprint-specific task files.
"""

from app.core.celery import celery_app


@celery_app.task(bind=True, max_retries=3)
def send_email_task(self, to: str, subject: str, body: str, html: str = None):
    """
    Send email asynchronously.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Plain text body
        html: Optional HTML body

    Retries up to 3 times on failure.
    """
    try:
        from app.core.email import send_email
        send_email(to=to, subject=subject, body=body, html=html)
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task
def cleanup_expired_tokens():
    """
    Cleanup expired blacklisted tokens from database.

    Run periodically via Celery Beat to keep the table small.
    """
    from app.blueprints.auth.models import BlacklistedToken
    from app.extensions import db

    deleted_count = BlacklistedToken.cleanup_expired()
    db.session.commit()

    return f"Deleted {deleted_count} expired tokens"


@celery_app.task(bind=True, max_retries=3)
def send_password_reset_email_task(self, to: str, reset_url: str):
    """
    Send password reset email asynchronously.

    Args:
        to: User's email address
        reset_url: URL with reset token

    Retries up to 3 times on failure.
    """
    try:
        from app.core.email import send_password_reset_email
        send_password_reset_email(to=to, reset_url=reset_url)
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task
def cleanup_expired_password_reset_tokens():
    """
    Cleanup expired password reset tokens from database.

    Run periodically via Celery Beat.
    """
    from app.blueprints.auth.models import PasswordResetToken
    from app.extensions import db

    deleted_count = PasswordResetToken.cleanup_expired()
    db.session.commit()

    return f"Deleted {deleted_count} expired password reset tokens"


@celery_app.task(bind=True, max_retries=3)
def send_verification_email_task(self, to: str, verify_url: str):
    """
    Send email verification email asynchronously.

    Args:
        to: User's email address
        verify_url: URL with verification token

    Retries up to 3 times on failure.
    """
    try:
        from app.core.email import send_email_verification
        send_email_verification(to=to, verify_url=verify_url)
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task
def cleanup_expired_email_verification_tokens():
    """
    Cleanup expired email verification tokens from database.

    Run periodically via Celery Beat.
    """
    from app.blueprints.auth.models import EmailVerificationToken
    from app.extensions import db

    deleted_count = EmailVerificationToken.cleanup_expired()
    db.session.commit()

    return f"Deleted {deleted_count} expired email verification tokens"


@celery_app.task(bind=True, max_retries=3)
def send_invitation_email_task(self, to: str, inviter_name: str, tenant_name: str, invite_url: str):
    """
    Send user invitation email asynchronously.

    Args:
        to: Invitee's email address
        inviter_name: Name of person sending invite
        tenant_name: Name of the organization
        invite_url: URL to accept invitation

    Retries up to 3 times on failure.
    """
    try:
        from app.core.email import send_user_invitation
        send_user_invitation(
            to=to,
            inviter_name=inviter_name,
            tenant_name=tenant_name,
            invite_url=invite_url
        )
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task
def cleanup_expired_invitations():
    """
    Cleanup expired user invitations from database.

    Run periodically via Celery Beat.
    """
    from app.blueprints.auth.models import UserInvitation
    from app.extensions import db

    deleted_count = UserInvitation.cleanup_expired()
    db.session.commit()

    return f"Deleted {deleted_count} expired user invitations"
