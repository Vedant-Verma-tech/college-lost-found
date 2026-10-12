
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import EmailOTP
from accounts.otp_utils import create_and_send_otp, verify_otp

from .forms import ItemReportForm
from .models import (
    ItemReport,
    ClaimRequest,
    Notification,
    HandoverVerification,
)
from .notifications import create_notification

User = get_user_model()


# =========================================================
# ACCESS CONTROL
# =========================================================

def staff_role_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if (
            getattr(request.user, "role", "")
            not in ("TEACHER", "ADMIN")
            and not request.user.is_superuser
        ):
            messages.error(
                request,
                "You are not authorized to access this page."
            )
            return redirect("home")

        return view_func(request, *args, **kwargs)

    return wrapper


def admin_role_required(view_func):
    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        is_admin = (
            getattr(request.user, "role", "") == "ADMIN"
            or request.user.is_superuser
        )

        if not is_admin:
            messages.error(
                request,
                "Only administrators can access this page."
            )
            return redirect("home")

        return view_func(request, *args, **kwargs)

    return wrapper


# =========================================================
# HOME AND ITEM REPORTS
# =========================================================

def home(request):
    recent_items = ItemReport.objects.filter(
        status="VERIFIED"
    ).order_by("-created_at")[:6]

    lost_count = ItemReport.objects.filter(
        report_type="LOST"
    ).count()

    found_count = ItemReport.objects.filter(
        report_type="FOUND"
    ).count()

    returned_count = ItemReport.objects.filter(
        status="RETURNED"
    ).count()

    return render(
        request,
        "home.html",
        {
            "recent_items": recent_items,
            "lost_count": lost_count,
            "found_count": found_count,
            "returned_count": returned_count,
        }
    )


def lost_items(request):
    items = ItemReport.objects.filter(
        report_type="LOST",
        status="VERIFIED"
    ).order_by("-created_at")

    return render(
        request,
        "reports/lost.html",
        {"items": items}
    )


def found_items(request):
    items = ItemReport.objects.filter(
        report_type="FOUND",
        status__in=["VERIFIED", "CLAIMED", "RETURNED"]
    ).select_related("owner").order_by("-created_at")

    return render(
        request,
        "reports/found.html",
        {"items": items}
    )


@login_required
def report_lost(request):
    if request.method == "POST":
        form = ItemReportForm(request.POST, request.FILES)

        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.report_type = "LOST"
            item.status = "PENDING"
            item.save()

            messages.success(
                request,
                "Your lost-item report was submitted for verification."
            )
            return redirect("my_reports")
    else:
        form = ItemReportForm()

    return render(
        request,
        "reports/report_form.html",
        {
            "form": form,
            "report_type": "LOST",
            "page_title": "Report a Lost Item",
            "button_text": "Submit Lost Report",
        }
    )


@login_required
def report_found(request):
    if request.method == "POST":
        form = ItemReportForm(request.POST, request.FILES)

        if form.is_valid():
            item = form.save(commit=False)
            item.owner = request.user
            item.report_type = "FOUND"
            item.status = "PENDING"
            item.save()

            messages.success(
                request,
                "Your found-item report was submitted for verification."
            )
            return redirect("my_reports")
    else:
        form = ItemReportForm()

    return render(
        request,
        "reports/report_form.html",
        {
            "form": form,
            "report_type": "FOUND",
            "page_title": "Report a Found Item",
            "button_text": "Submit Found Report",
        }
    )


@login_required
def my_reports(request):
    items = ItemReport.objects.filter(
        owner=request.user
    ).order_by("-created_at")

    return render(
        request,
        "reports/my_reports.html",
        {"items": items}
    )


# =========================================================
# TEACHER DASHBOARD AND REPORT REVIEW
# =========================================================

@staff_role_required
def teacher_dashboard(request):
    items = ItemReport.objects.filter(
        status="PENDING"
    ).select_related("owner").order_by("-created_at")

    return render(
        request,
        "reports/teacher_dashboard.html",
        {"items": items}
    )


@staff_role_required
@require_POST
def review_report(request, report_id):
    with transaction.atomic():
        item = get_object_or_404(
            ItemReport.objects.select_for_update(),
            pk=report_id,
            status="PENDING"
        )

        if item.owner_id == request.user.id:
            messages.error(
                request,
                "You cannot review your own report."
            )
            return redirect("teacher_dashboard")

        action = request.POST.get("action", "").lower()

        if action == "approve":
            item.status = "VERIFIED"
            notification_title = "Report approved"
            notification_message = (
                f'Your report "{item.title}" has been approved '
                "and verified on CampusFind."
            )
            success_message = f'"{item.title}" has been approved.'

        elif action == "reject":
            item.status = "REJECTED"
            notification_title = "Report rejected"
            notification_message = (
                f'Your report "{item.title}" has been rejected. '
                "Please contact college staff if you need clarification."
            )
            success_message = f'"{item.title}" has been rejected.'

        else:
            messages.error(request, "Invalid review action.")
            return redirect("teacher_dashboard")

        item.save(update_fields=["status", "updated_at"])

        create_notification(
            recipient=item.owner,
            title=notification_title,
            message=notification_message,
            report=item
        )

    messages.success(request, success_message)
    return redirect("teacher_dashboard")


# =========================================================
# STUDENT: SUBMIT A CLAIM WITH EMAIL OTP
# =========================================================

@login_required
@require_POST
def submit_claim(request, report_id):
    item = get_object_or_404(
        ItemReport,
        pk=report_id,
        report_type="FOUND",
        status="VERIFIED"
    )

    if item.owner_id == request.user.id:
        messages.error(
            request,
            "You cannot claim an item you reported."
        )
        return redirect("found_items")

    explanation = request.POST.get("explanation", "").strip()

    if len(explanation) < 20:
        messages.error(
            request,
            "Please provide at least 20 characters explaining "
            "how you identify the item."
        )
        return redirect("found_items")

    if not request.user.email:
        messages.error(
            request,
            "Add an email address to your account before claiming an item."
        )
        return redirect("found_items")

    active_claim = ClaimRequest.objects.filter(
        item=item,
        claimant=request.user,
        status__in=["PENDING", "APPROVED"]
    ).exists()

    if active_claim:
        messages.info(
            request,
            "You already have an active claim for this item."
        )
        return redirect("my_claims")

    request.session["pending_claim"] = {
        "item_id": item.pk,
        "explanation": explanation,
    }

    try:
        challenge = create_and_send_otp(request.user, "CLAIM")
    except Exception:
        request.session.pop("pending_claim", None)
        messages.error(
            request,
            "We couldn't send the claim verification code. "
            "Please try again later."
        )
        return redirect("found_items")

    request.session["claim_otp_token"] = str(challenge.token)

    messages.success(
        request,
        "A claim verification code has been sent to your email."
    )
    return redirect("verify_claim_otp")


@login_required
def verify_claim_otp(request):
    token = request.session.get("claim_otp_token")
    pending_claim = request.session.get("pending_claim")

    if not token or not pending_claim:
        messages.error(
            request,
            "Your pending claim has expired. Please submit it again."
        )
        return redirect("found_items")

    challenge = get_object_or_404(
        EmailOTP,
        token=token,
        user=request.user,
        purpose="CLAIM"
    )

    if request.method == "POST":
        code = request.POST.get("otp", "")
        valid, error_message = verify_otp(challenge, code)

        if not valid:
            messages.error(request, error_message)
            return render(
                request,
                "accounts/verify_claim_otp.html"
            )

        with transaction.atomic():
            item = get_object_or_404(
                ItemReport.objects.select_for_update(),
                pk=pending_claim["item_id"],
                report_type="FOUND",
                status="VERIFIED"
            )

            if item.owner_id == request.user.id:
                messages.error(
                    request,
                    "You cannot claim an item you reported."
                )
                return redirect("found_items")

            active_claim = ClaimRequest.objects.filter(
                item=item,
                claimant=request.user,
                status__in=["PENDING", "APPROVED"]
            ).exists()

            if active_claim:
                request.session.pop("pending_claim", None)
                request.session.pop("claim_otp_token", None)
                messages.info(
                    request,
                    "You already have an active claim for this item."
                )
                return redirect("my_claims")

            claim = ClaimRequest.objects.create(
                item=item,
                claimant=request.user,
                explanation=pending_claim["explanation"]
            )

            create_notification(
                recipient=item.owner,
                title="New claim submitted",
                message=(
                    f'A student has submitted a verified claim '
                    f'for "{item.title}". '
                    "The claim is awaiting staff review."
                ),
                report=item
            )

        request.session.pop("pending_claim", None)
        request.session.pop("claim_otp_token", None)

        messages.success(
            request,
            "Your email has been verified and your claim "
            "has been submitted for staff review."
        )
        return redirect("my_claims")

    return render(
        request,
        "accounts/verify_claim_otp.html"
    )


# =========================================================
# STUDENT: MY CLAIMS
# =========================================================

@login_required
def my_claims(request):
    claims = ClaimRequest.objects.filter(
        claimant=request.user
    ).select_related(
        "item",
        "item__owner",
        "reviewed_by"
    ).order_by("-created_at")

    return render(
        request,
        "reports/my_claims.html",
        {
            "claims": claims,
            "now": timezone.now(),
        }
    )


# =========================================================
# TEACHER/ADMIN: CLAIMS DASHBOARD
# =========================================================

@staff_role_required
def claims_dashboard(request):
    claims = ClaimRequest.objects.select_related(
        "item",
        "claimant",
        "item__owner",
        "reviewed_by"
    ).order_by("-created_at")

    status = request.GET.get("status", "").strip()

    valid_statuses = [
        choice[0] for choice in ClaimRequest.STATUS_CHOICES
    ]

    if status in valid_statuses:
        claims = claims.filter(status=status)

    return render(
        request,
        "reports/claims_dashboard.html",
        {
            "claims": claims,
            "statuses": ClaimRequest.STATUS_CHOICES,
            "selected_status": status,
        }
    )


# =========================================================
# STAFF: APPROVE OR REJECT A CLAIM
# =========================================================

@staff_role_required
@require_POST
def review_claim(request, claim_id):
    action = request.POST.get("action", "").lower()
    email_to_send = None
    email_subject = None
    email_message = None

    with transaction.atomic():
        claim = get_object_or_404(
            ClaimRequest.objects.select_for_update(),
            pk=claim_id
        )

        item = ItemReport.objects.select_for_update().get(
            pk=claim.item_id
        )

        if claim.status != "PENDING":
            messages.error(
                request,
                "This claim has already been reviewed."
            )
            return redirect("claims_dashboard")

        if action == "approve":
            if (
                item.report_type != "FOUND"
                or item.status != "VERIFIED"
            ):
                messages.error(
                    request,
                    "This item is no longer available for a claim."
                )
                return redirect("claims_dashboard")

            other_approved = ClaimRequest.objects.filter(
                item=item,
                status__in=["APPROVED", "RETURNED"]
            ).exclude(pk=claim.pk).exists()

            if other_approved:
                messages.error(
                    request,
                    "Another claim has already been approved "
                    "for this item."
                )
                return redirect("claims_dashboard")

            claim.status = "APPROVED"
            item.status = "CLAIMED"

            notification_title = "Your claim was approved"
            notification_message = (
                f'Your claim for "{item.title}" has been approved. '
                "Please coordinate with college staff to collect the item."
            )
            success_message = f'Claim for "{item.title}" approved.'

        elif action == "reject":
            claim.status = "REJECTED"

            notification_title = "Your claim was rejected"
            notification_message = (
                f'Your claim for "{item.title}" has been rejected. '
                "Please contact college staff if you need clarification."
            )
            success_message = f'Claim for "{item.title}" rejected.'

        else:
            messages.error(request, "Invalid claim review action.")
            return redirect("claims_dashboard")

        claim.reviewed_by = request.user
        claim.save(update_fields=[
            "status",
            "reviewed_by",
            "updated_at"
        ])

        if action == "approve":
            item.save(update_fields=["status", "updated_at"])

            # Create the handover code only after approval.
            verification = HandoverVerification.create_for_claim(claim)

            # Prepare the email; send it only after the transaction commits.
            if claim.claimant.email:
                email_to_send = claim.claimant.email
                email_subject = (
                    "CampusFind - Item Handover Verification Code"
                )
                email_message = (
                    f"Hello {claim.claimant.username},\n\n"
                    f'Your claim for "{item.title}" has been approved.\n\n'
                    f"Your 6-digit handover verification code is: "
                    f"{verification.code}\n\n"
                    f"This code expires at "
                    f"{verification.expires_at.strftime('%d %b %Y, %I:%M %p')}.\n\n"
                    "Show this code to authorized college staff "
                    "when collecting your item. Do not share it "
                    "with anyone else.\n\n"
                    "Regards,\nCampusFind Team"
                )

                transaction.on_commit(
                    lambda recipient=email_to_send,
                    subject=email_subject,
                    body=email_message: send_handover_email(
                        recipient, subject, body
                    )
                )

        create_notification(
            recipient=claim.claimant,
            title=notification_title,
            message=notification_message,
            report=item
        )

    messages.success(request, success_message)

    if action == "approve" and not claim.claimant.email:
        messages.warning(
            request,
            "The claim was approved, but the claimant has no email address. "
            "Please update their account email."
        )

    return redirect("claims_dashboard")


def send_handover_email(recipient, subject, body):
    """
    Send the handover email after the claim approval transaction commits.
    Failures are logged instead of turning a successful approval into
    an error page.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        sent_count = send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )

        if sent_count != 1:
            logger.error(
                "CampusFind handover email was not sent to %s",
                recipient,
            )

    except Exception:
        logger.exception(
            "Failed to send CampusFind handover email to %s",
            recipient,
        )


# =========================================================
# STAFF: VERIFY THE CLAIMANT'S HANDOVER CODE
# =========================================================

@staff_role_required
@require_POST
def verify_handover(request, claim_id):
    with transaction.atomic():
        claim = get_object_or_404(
            ClaimRequest.objects.select_for_update(),
            pk=claim_id
        )

        if claim.status != "APPROVED":
            messages.error(
                request,
                "Only approved claims can be verified."
            )
            return redirect("claims_dashboard")

        verification = HandoverVerification.objects.select_for_update().filter(
            claim=claim
        ).first()

        if verification is None:
            messages.error(
                request,
                "No handover code exists for this claim."
            )
            return redirect("claims_dashboard")

        if verification.verified_at is not None or verification.is_used:
            messages.info(
                request,
                "This handover code has already been used."
            )
            return redirect("claims_dashboard")

        if verification.expires_at <= timezone.now():
            messages.error(
                request,
                "The handover code has expired. A new code is needed."
            )
            return redirect("claims_dashboard")

        submitted_code = request.POST.get("code", "").strip()

        if (
            len(submitted_code) != 6
            or not submitted_code.isdigit()
            or submitted_code != verification.code
        ):
            messages.error(
                request,
                "Incorrect handover code. Please check with the claimant."
            )
            return redirect("claims_dashboard")

        verification.is_used = True
        verification.verified_at = timezone.now()
        verification.verified_by = request.user
        verification.save(update_fields=[
            "is_used",
            "verified_at",
            "verified_by"
        ])

    messages.success(
        request,
        "Claimant verified. After physically handing over the item, "
        "confirm the return."
    )
    return redirect("claims_dashboard")


# =========================================================
# STAFF: CONFIRM PHYSICAL ITEM RETURN
# =========================================================

@staff_role_required
@require_POST
def confirm_item_return(request, claim_id):
    with transaction.atomic():
        claim = get_object_or_404(
            ClaimRequest.objects.select_for_update(),
            pk=claim_id
        )

        item = ItemReport.objects.select_for_update().get(
            pk=claim.item_id
        )

        if (
            claim.status != "APPROVED"
            or item.status != "CLAIMED"
        ):
            messages.error(
                request,
                "Only an approved claim for a claimed item "
                "can be marked returned."
            )
            return redirect("claims_dashboard")

        verification = HandoverVerification.objects.select_for_update().filter(
            claim=claim,
            is_used=True,
            verified_at__isnull=False
        ).first()

        if verification is None:
            messages.error(
                request,
                "Verify the claimant's handover code before "
                "confirming the return."
            )
            return redirect("claims_dashboard")

        claim.status = "RETURNED"
        claim.reviewed_by = request.user
        claim.save(update_fields=[
            "status",
            "reviewed_by",
            "updated_at"
        ])

        item.status = "RETURNED"
        item.save(update_fields=["status", "updated_at"])

        create_notification(
            recipient=claim.claimant,
            title="Item return confirmed",
            message=(
                f'The return of "{item.title}" has been confirmed. '
                "Thank you for using CampusFind."
            ),
            report=item
        )

        create_notification(
            recipient=item.owner,
            title="Item marked as returned",
            message=(
                f'"{item.title}" has been marked as returned '
                "in CampusFind."
            ),
            report=item
        )

    messages.success(
        request,
        f'"{item.title}" has been marked as returned.'
    )
    return redirect("claims_dashboard")


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@login_required
def admin_dashboard(request):
    if (
        getattr(request.user, "role", "") != "ADMIN"
        and not request.user.is_superuser
    ):
        messages.error(
            request,
            "You are not authorized to access the admin dashboard."
        )
        return redirect("home")

    context = {
        "total_users": User.objects.count(),
        "total_students": User.objects.filter(role="STUDENT").count(),
        "total_teachers": User.objects.filter(role="TEACHER").count(),
        "total_reports": ItemReport.objects.count(),
        "pending_reports": ItemReport.objects.filter(
            status="PENDING"
        ).count(),
        "verified_reports": ItemReport.objects.filter(
            status="VERIFIED"
        ).count(),
        "rejected_reports": ItemReport.objects.filter(
            status="REJECTED"
        ).count(),
        "returned_reports": ItemReport.objects.filter(
            status="RETURNED"
        ).count(),
        "recent_reports": ItemReport.objects.select_related(
            "owner"
        ).order_by("-created_at")[:8],
    }

    return render(
        request,
        "reports/admin_dashboard.html",
        context
    )


# =========================================================
# ADMIN: MANAGE USERS
# =========================================================

@admin_role_required
def admin_users(request):
    users = User.objects.all().order_by("username")

    search = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()

    if search:
        users = users.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(college_id__icontains=search)
        )

    if role in ["STUDENT", "TEACHER", "ADMIN"]:
        users = users.filter(role=role)

    return render(
        request,
        "reports/admin_users.html",
        {
            "users": users,
            "search": search,
            "selected_role": role,
        }
    )


# =========================================================
# ADMIN: VIEW AND FILTER REPORTS
# =========================================================

@admin_role_required
def admin_reports(request):
    items = ItemReport.objects.select_related(
        "owner"
    ).order_by("-created_at")

    status = request.GET.get("status", "").strip()
    report_type = request.GET.get("type", "").strip()
    search = request.GET.get("q", "").strip()

    valid_statuses = [
        choice[0] for choice in ItemReport.STATUS_CHOICES
    ]
    valid_types = [
        choice[0] for choice in ItemReport.TYPE_CHOICES
    ]

    if status in valid_statuses:
        items = items.filter(status=status)

    if report_type in valid_types:
        items = items.filter(report_type=report_type)

    if search:
        items = items.filter(
            Q(title__icontains=search)
            | Q(location__icontains=search)
            | Q(owner__username__icontains=search)
        )

    return render(
        request,
        "reports/admin_reports.html",
        {
            "items": items,
            "selected_status": status,
            "selected_type": report_type,
            "search": search,
            "statuses": ItemReport.STATUS_CHOICES,
            "report_types": ItemReport.TYPE_CHOICES,
        }
    )


# =========================================================
# ADMIN: UPDATE REPORT STATUS
# =========================================================

@admin_role_required
@require_POST
def admin_update_report_status(request, report_id):
    item = get_object_or_404(ItemReport, pk=report_id)
    new_status = request.POST.get("status")

    valid_statuses = [
        choice[0] for choice in ItemReport.STATUS_CHOICES
    ]

    if new_status not in valid_statuses:
        messages.error(request, "Invalid report status.")
        return redirect("admin_reports")

    item.status = new_status
    item.save(update_fields=["status", "updated_at"])

    create_notification(
        recipient=item.owner,
        title="Report status updated",
        message=(
            f'The status of your report "{item.title}" '
            f'has been changed to {new_status}.'
        ),
        report=item
    )

    messages.success(
        request,
        f'"{item.title}" status changed to {new_status}.'
    )
    return redirect("admin_reports")


# =========================================================
# ADMIN: UPDATE USER ROLE
# =========================================================

@admin_role_required
@require_POST
def admin_update_user_role(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if user.is_superuser:
        messages.error(
            request,
            "A superuser role cannot be changed here."
        )
        return redirect("admin_users")

    if user.pk == request.user.pk:
        messages.error(
            request,
            "You cannot change your own role."
        )
        return redirect("admin_users")

    new_role = request.POST.get("role")

    if new_role not in ["STUDENT", "TEACHER", "ADMIN"]:
        messages.error(request, "Invalid role selected.")
        return redirect("admin_users")

    user.role = new_role
    user.save(update_fields=["role"])

    messages.success(
        request,
        f"{user.username} is now assigned the {new_role} role."
    )
    return redirect("admin_users")


# =========================================================
# ADMIN: ACTIVATE/DEACTIVATE USER
# =========================================================

@admin_role_required
@require_POST
def admin_toggle_user_active(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if user.is_superuser or user.pk == request.user.pk:
        messages.error(
            request,
            "You cannot deactivate yourself or a superuser."
        )
        return redirect("admin_users")

    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])

    state = "activated" if user.is_active else "deactivated"

    messages.success(
        request,
        f"{user.username} account has been {state}."
    )
    return redirect("admin_users")


# =========================================================
# IN-APP NOTIFICATIONS
# =========================================================

@login_required
def notifications_list(request):
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related("report")

    unread_count = notifications.filter(is_read=False).count()

    return render(
        request,
        "reports/notifications.html",
        {
            "notifications": notifications,
            "unread_count": unread_count,
        }
    )


@login_required
@require_POST
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(
        Notification,
        pk=notification_id,
        recipient=request.user
    )

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    return redirect("notifications")


    


# =========================================================
# ADMIN: DELETE REPORT
# =========================================================

@admin_role_required
@require_POST
def admin_delete_report(request, report_id):
    item = get_object_or_404(
        ItemReport,
        pk=report_id
    )

    title = item.title

    # Protect reports with pending or approved claims.
    if ClaimRequest.objects.filter(
        item=item,
        status__in=["PENDING", "APPROVED"]
    ).exists():
        messages.error(
            request,
            "This report cannot be deleted because it has "
            "a pending or approved claim."
        )
        return redirect("admin_reports")

    item.delete()

    messages.success(
        request,
        f'Report "{title}" was deleted successfully.'
    )

    return redirect("admin_reports")