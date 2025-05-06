from django.db import models
from django.contrib.auth.models import AbstractUser
import os

def user_face_path(instance, filename):
    return f"faces/user_{instance.id}/{filename}"

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ("student", "Student"),
        ("lecturer", "Lecturer"),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default="student")
    face_image = models.ImageField(upload_to=user_face_path, blank=True, null=True)
    face_encoding = models.BinaryField(blank=True, null=True)

    class Meta:
        db_table = "auth_user"

    def is_student(self):
        return self.user_type == "student"

    def is_lecturer(self):
        return self.user_type == "lecturer"
