from django.conf import settings
from django.db import models
import secrets
from datetime import timedelta
from django.utils import timezone



class ClaimRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('RETURNED', 'Item Returned'),
    )

    item = models.ForeignKey(
        'reports.ItemReport',
        on_delete=models.CASCADE,
        related_name='claim_requests'
    )

    claimant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='item_claims'
    )

    explanation = models.TextField(
        help_text='Describe identifying details that prove this item belongs to you.'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_claim_requests'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.item.title} - {self.claimant.username} ({self.status})'



class ItemReport(models.Model):

    TYPE_CHOICES = (

        ('LOST', 'Lost'),

        ('FOUND', 'Found'),

    )

    STATUS_CHOICES = (

        ('PENDING', 'Pending'),

        ('VERIFIED', 'Verified'),

        ('CLAIMED', 'Claimed'),

        ('RETURNED', 'Returned'),

        ('REJECTED', 'Rejected'),

    )

    CATEGORY_CHOICES = (

        ('ELECTRONICS', 'Electronics'),

        ('DOCUMENT', 'Document'),

        ('BAG', 'Bag'),

        ('BOOK', 'Book'),

        ('KEYS', 'Keys'),

        ('CLOTHING', 'Clothing'),

        ('ACCESSORIES', 'Accessories'),

        ('OTHER', 'Other'),

    )

    title = models.CharField(
        max_length=200
    )

    description = models.TextField()

    report_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES
    )

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES
    )

    location = models.CharField(
        max_length=200
    )

    date_occurred = models.DateField()

    image = models.ImageField(
        upload_to='items/',
        blank=True,
        null=True
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='item_reports'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):

        return self.title

class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="campus_notifications"
    )

    title = models.CharField(max_length=200)
    message = models.TextField()

    report = models.ForeignKey(
        "reports.ItemReport",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications"
    )

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.recipient.username}"


import secrets
from datetime import timedelta

from django.utils import timezone


class HandoverVerification(models.Model):
    claim = models.OneToOneField(
        "reports.ClaimRequest",
        on_delete=models.CASCADE,
        related_name="handover_verification"
    )

    code = models.CharField(
        max_length=6,
        unique=True
    )

    expires_at = models.DateTimeField()

    is_used = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_handovers"
    )

    @classmethod
    def generate_code(cls):
        return f"{secrets.randbelow(1_000_000):06d}"

    @classmethod
    def create_for_claim(cls, claim):
        # A code is issued only for an approved claim.
        if claim.status != "APPROVED":
            raise ValueError(
                "A handover code can only be issued for an approved claim."
            )

        # Reuse an existing unused, unexpired code.
        existing = cls.objects.filter(
            claim=claim,
            is_used=False,
            expires_at__gt=timezone.now()
        ).first()

        if existing:
            return existing

        # Generate a unique six-digit code.
        for _ in range(10):
            code = cls.generate_code()

            if not cls.objects.filter(code=code).exists():
                return cls.objects.create(
                    claim=claim,
                    code=code,
                    expires_at=timezone.now() + timedelta(minutes=10)
                )

        raise ValueError("Could not generate a unique handover code.")

    def __str__(self):
        return f"Handover for claim #{self.claim_id}"