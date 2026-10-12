
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import User, EmailOTP
from .otp_utils import create_and_send_otp, verify_otp


@ensure_csrf_cookie
def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.role == "ADMIN":
            return redirect("admin_dashboard")
        if request.user.role == "TEACHER":
            return redirect("teacher_dashboard")
        return redirect("home")

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

        if not user.email:
            messages.error(
                request,
                "Your account needs an email address before you can log in."
            )
            return render(request, "accounts/login.html")

        try:
            challenge = create_and_send_otp(user, "LOGIN")
        except Exception:
            messages.error(
                request,
                "We couldn't send your verification code. "
                "Please check the email configuration and try again."
            )
            return render(request, "accounts/login.html")

        request.session["login_otp_token"] = str(challenge.token)
        messages.success(request, "A verification code has been sent to your email.")
        return redirect("verify_login_otp")

    return render(request, "accounts/login.html")


def verify_login_otp(request):
    token = request.session.get("login_otp_token")

    if not token:
        messages.error(request, "Please log in to request a verification code.")
        return redirect("login")

    challenge = get_object_or_404(
        EmailOTP,
        token=token,
        purpose="LOGIN",
    )

    if request.method == "POST":
        code = request.POST.get("otp", "")
        valid, error_message = verify_otp(challenge, code)

        if not valid:
            messages.error(request, error_message)
            return render(request, "accounts/verify_otp.html")

        user = challenge.user

        # Remove the pending challenge before creating the session.
        request.session.pop("login_otp_token", None)
        login(request, user)

        messages.success(request, "Email verified. You are now logged in.")

        if user.is_superuser or user.role == "ADMIN":
            return redirect("admin_dashboard")
        if user.role == "TEACHER":
            return redirect("teacher_dashboard")
        return redirect("home")

    return render(request, "accounts/verify_otp.html")

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        college_id = request.POST.get('college_id', '').strip()
        department = request.POST.get('department', '').strip()
        phone = request.POST.get('phone', '').strip()

        # Validate required fields.
        if not all([
            username,
            email,
            password,
            confirm_password,
            college_id
        ]):
            messages.error(
                request,
                'Please fill in all required fields.'
            )
            return redirect('register')

        # Check password confirmation.
        if password != confirm_password:
            messages.error(
                request,
                'Passwords do not match.'
            )
            return redirect('register')

        # Check for duplicate username.
        if User.objects.filter(username=username).exists():
            messages.error(
                request,
                'Username already exists.'
            )
            return redirect('register')

        # Check for duplicate college ID.
        if User.objects.filter(college_id=college_id).exists():
            messages.error(
                request,
                'College ID already exists.'
            )
            return redirect('register')

        # Public registration always creates a student.
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            college_id=college_id,
            department=department,
            phone=phone,
            role='STUDENT'
        )

        login(request, user)
        messages.success(
            request,
            'Your account has been created successfully.'
        )

        return redirect('home')

    return render(request, 'accounts/register.html')


def logout_view(request):
    logout(request)

    messages.success(
        request,
        'You have been logged out successfully.'
    )

    return redirect('home')