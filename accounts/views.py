
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import User


@ensure_csrf_cookie
def login_view(request):
    # Redirect users who are already logged in.
    if request.user.is_authenticated:
        if (
            request.user.is_superuser
            or getattr(request.user, 'role', '') == 'ADMIN'
        ):
            return redirect('admin_dashboard')

        elif getattr(request.user, 'role', '') == 'TEACHER':
            return redirect('teacher_dashboard')

        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)

            # Custom CampusFind admin dashboard.
            if (
                user.is_superuser
                or getattr(user, 'role', '') == 'ADMIN'
            ):
                return redirect('admin_dashboard')

            # Teacher dashboard.
            elif getattr(user, 'role', '') == 'TEACHER':
                return redirect('teacher_dashboard')

            # Student homepage.
            return redirect('home')

        messages.error(
            request,
            'Invalid username or password.'
        )

    return render(request, 'accounts/login.html')


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