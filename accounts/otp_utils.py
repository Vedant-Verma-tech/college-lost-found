
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import EmailOTP


OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5


def create_and_send_otp(user, purpose, claim_id=None):
    if not user.email:
        raise ValueError("Your account does not have an email address.")

    EmailOTP.objects.filter(
        user=user,
        purpose=purpose,
        is_used=False,
    ).update(is_used=True)

    code = f"{secrets.randbelow(1_000_000):06d}"
    code_hash = hashlib.sha256(code.encode()).hexdigest()

    challenge = EmailOTP.objects.create(
        user=user,
        purpose=purpose,
        code_hash=code_hash,
        claim_id=claim_id,
        expires_at=timezone.now() + timedelta(
            minutes=OTP_EXPIRY_MINUTES
        ),
    )

    try:
        send_mail(
            subject="Your CampusFind verification code",
            message=(
                f"Hello {user.username},\n\n"
                f"Your CampusFind verification code is: {code}\n\n"
                f"This code expires in {OTP_EXPIRY_MINUTES} minutes "
                "and can only be used once.\n\n"
                "If you did not request this code, you can ignore "
                "this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        challenge.delete()
        raise

    return challenge


def verify_otp(challenge, submitted_code):
    if challenge.is_used:
        return False, "This code has already been used."

    if timezone.now() >= challenge.expires_at:
        challenge.is_used = True
        challenge.save(update_fields=["is_used"])
        return False, "This code has expired. Request a new one."

    if challenge.attempts >= OTP_MAX_ATTEMPTS:
        challenge.is_used = True
        challenge.save(update_fields=["is_used"])
        return False, "Too many attempts. Request a new code."

    challenge.attempts += 1
    submitted_hash = hashlib.sha256(
        submitted_code.strip().encode()
    ).hexdigest()

    if secrets.compare_digest(challenge.code_hash, submitted_hash):
        challenge.is_used = True
        challenge.save(update_fields=["attempts", "is_used"])
        return True, "Email verified successfully."

    if challenge.attempts >= OTP_MAX_ATTEMPTS:
        challenge.is_used = True
        challenge.save(update_fields=["attempts", "is_used"])
        return False, "Too many attempts. Request a new code."

    challenge.save(update_fields=["attempts"])
    return False, "Incorrect verification code."