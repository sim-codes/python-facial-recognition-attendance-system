from django.db import models
from django.conf import settings
from django.db.models import Count

class Course(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    lecturer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='courses',
        limit_choices_to={'user_type': 'lecturer'}
    )
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='enrolled_courses',
        limit_choices_to={'user_type': 'student'}
    )

    def __str__(self):
        return f"{self.code} - {self.name}"

    def average_attendance_percentage(self):
        num_students = self.students.count()
        num_sessions = self.sessions.count()

        if num_students == 0 or num_sessions == 0:
            return 0

        total_possible_attendances = num_students * num_sessions
        total_actual_attendances = Attendance.objects.filter(session__course=self).count()
        
        if total_possible_attendances == 0:
            return 0
        
        percentage = (total_actual_attendances / total_possible_attendances) * 100
        return round(percentage)

class Session(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sessions')
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.course.code} - {self.date} {self.start_time} - {self.end_time}"

class Attendance(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attendances',
        limit_choices_to={'user_type': 'student'}
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    face_verified = models.BooleanField(default=False)

    class Meta:
        unique_together = ('session', 'student')

    def __str__(self):
        return f"{self.student.username} - {self.session}"