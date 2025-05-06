from django.contrib import admin
from .models import Course, Session, Attendance

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'lecturer')
    search_fields = ('code', 'name', 'lecturer__username')
    filter_horizontal = ('students',)
