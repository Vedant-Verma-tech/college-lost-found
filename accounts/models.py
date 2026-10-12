from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):

    ROLE_CHOICES = (

        ('STUDENT', 'Student'),

        ('TEACHER', 'Teacher'),

        ('ADMIN', 'Admin'),

    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='STUDENT'
    )

    college_id = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True
    )

    department = models.CharField(
        max_length=100,
        blank=True
    )

    phone = models.CharField(
        max_length=15,
        blank=True
    )

    def __str__(self):

        return self.username


class EmailOTP(models.Model):
    PURPOSE_CHOICES = (
        ("LOGIN", "Login"),
        ("CLAIM", "Claim verification"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_otps",
    )
    purpose = models.CharField(
        max_length=10,
        choices=PURPOSE_CHOICES,
    )
    code_hash = models.CharField(max_length=64)
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    claim_id = models.PositiveBigIntegerField(null=True, blank=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.purpose}"

from accounts.models import User



