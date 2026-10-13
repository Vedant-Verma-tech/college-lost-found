
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import User
from reports.models import EmailOTP


OTP_LIFETIME_MINUTES = 10
OTP_MAX_ATTEMPTS = 5


def _create_and_send_otp(*, user, purpose, claim=None):
    """Create and email a hashed, short-lived, single-use OTP."""

    if not user.email:
        raise ValueError("Your account must have an email address.")

    # Remove older, unused codes for this purpose.
    EmailOTP.objects.filter(
        user=user,
        purpose=purpose,
        claim=claim,
        used_at__isnull=True,
    ).delete()

    code = f"{secrets.randbelow(1_000_000):06d}"

    otp = EmailOTP.objects.create(
        user=user,
        purpose=purpose,
        claim=claim,
        code_hash=make_password(code),
        expires_at=timezone.now()
        + timedelta(minutes=OTP_LIFETIME_MINUTES),
    )

    subject_by_purpose = {
        "LOGIN": "CampusFind login verification code",
        "REGISTER": "CampusFind registration verification code",
        "CLAIM": "CampusFind claim verification code",
    }

    try:
        send_mail(
            subject=subject_by_purpose.get(
                purpose,
                "CampusFind verification code",
            ),
            message=(
                f"Your CampusFind verification code is {code}.\n\n"
                f"It expires in {OTP_LIFETIME_MINUTES} minutes "
                "and can only be used once.\n"
                "If you did not request this code, ignore this email."
            ),
            from_email=getattr(
                settings,
                "DEFAULT_FROM_EMAIL",
                None,
            ),
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        otp.delete()
        raise

    return otp


def _redirect_after_login(user):
    """Send users to the correct dashboard for their role."""

    if user.is_superuser or getattr(user, "role", "") == "ADMIN":
        return redirect("admin_dashboard")

    if getattr(user, "role", "") == "TEACHER":
        return redirect("teacher_dashboard")

    return redirect("home")


@ensure_csrf_cookie
def login_view(request):
    """Normal sign-in using username and password only."""

    if request.user.is_authenticated:
        return _redirect_after_login(request.user)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is None:
            messages.error(request, "Invalid username or password.")
            return render(request, "accounts/login.html")

        if not user.is_active:
            messages.error(
                request,
                "This account is not verified or is disabled. "
                "Complete sign-up verification or contact an administrator.",
            )
            return render(request, "accounts/login.html")

        login(request, user)
        messages.success(request, "You have logged in successfully.")

        return _redirect_after_login(user)

    return render(request, "accounts/login.html")


@require_http_methods(["GET", "POST"])
def verify_registration_otp(request):
    """Activate a new account only after its email OTP is verified."""

    otp_id = request.session.get("pending_registration_otp_id")
    user_id = request.session.get("pending_registration_user_id")

    if not otp_id or not user_id:
        messages.error(request, "Please create your account first.")
        return redirect("register")

    user = User.objects.filter(pk=user_id).first()

    if user is None:
        request.session.pop("pending_registration_otp_id", None)
        request.session.pop("pending_registration_user_id", None)

        messages.error(
            request,
            "Registration was not found. Please sign up again.",
        )
        return redirect("register")

    if user.is_active:
        request.session.pop("pending_registration_otp_id", None)
        request.session.pop("pending_registration_user_id", None)

        messages.info(
            request,
            "Your email is already verified. Please log in.",
        )
        return redirect("login")

    otp = EmailOTP.objects.filter(
        pk=otp_id,
        user_id=user_id,
        purpose="REGISTER",
        claim__isnull=True,
        used_at__isnull=True,
    ).first()

    if otp is None or otp.expires_at <= timezone.now():
        user.delete()

        request.session.pop("pending_registration_otp_id", None)
        request.session.pop("pending_registration_user_id", None)

        messages.error(
            request,
            "Your registration code expired. Please create your "
            "account again.",
        )
        return redirect("register")

    if request.method == "POST":
        code = request.POST.get("code", "").strip()

        valid_code = (
            code.isdigit()
            and len(code) == 6
            and check_password(code, otp.code_hash)
        )

        if not valid_code:
            otp.attempts += 1
            otp.save(update_fields=["attempts"])

            if otp.attempts >= OTP_MAX_ATTEMPTS:
                user.delete()

                request.session.pop(
                    "pending_registration_otp_id", None
                )
                request.session.pop(
                    "pending_registration_user_id", None
                )

                messages.error(
                    request,
                    "Too many incorrect codes. Please register again.",
                )
                return redirect("register")

            messages.error(
                request,
                "The verification code is incorrect. Please try again.",
            )

            return render(
                request,
                "accounts/verify_otp.html",
                {
                    "purpose": "register",
                    "email": user.email,
                },
            )

        # Mark the code as used before activating the account.
        otp.used_at = timezone.now()
        otp.save(update_fields=["used_at"])

        user.is_active = True
        user.save(update_fields=["is_active"])

        request.session.pop("pending_registration_otp_id", None)
        request.session.pop("pending_registration_user_id", None)

        messages.success(
            request,
            "Your email has been verified. You can now log in.",
        )
        return redirect("login")

    return render(
        request,
        "accounts/verify_otp.html",
        {
            "purpose": "register",
            "email": user.email,
        },
    )


def register_view(request):
    """Create an inactive account and send its registration OTP."""

    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get(
            "confirm_password", ""
        )
        college_id = request.POST.get("college_id", "").strip()
        department = request.POST.get("department", "").strip()
        phone = request.POST.get("phone", "").strip()

        if not all([
            username,
            email,
            password,
            confirm_password,
            college_id,
        ]):
            messages.error(
                request,
                "Please fill in all required fields.",
            )
            return redirect("register")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")

        if User.objects.filter(email__iexact=email).exists():
            messages.error(
                request,
                "Email address is already registered.",
            )
            return redirect("register")

        if User.objects.filter(college_id=college_id).exists():
            messages.error(request, "College ID already exists.")
            return redirect("register")

        # The new account cannot log in until email verification.
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            college_id=college_id,
            department=department,
            phone=phone,
            role="STUDENT",
            is_active=False,
        )

        try:
            otp = _create_and_send_otp(
                user=user,
                purpose="REGISTER",
            )
        except Exception:
            user.delete()

            messages.error(
                request,
                "We could not send the verification email. "
                "Please check the email configuration and try again.",
            )
            return redirect("register")

        request.session["pending_registration_otp_id"] = otp.pk
        request.session["pending_registration_user_id"] = user.pk

        messages.success(
            request,
            f"A verification code was sent to {email}.",
        )
        return redirect("verify_registration_otp")

    return render(request, "accounts/register.html")


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("home")
