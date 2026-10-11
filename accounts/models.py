from django.contrib.auth.models import AbstractUser
from django.db import models


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



from accounts.models import User



