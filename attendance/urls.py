from django.urls import path
from . import views

urlpatterns = [
    # Student urls
    path('mark/', views.mark_attendance, name='mark_attendance'),
    path('verify-face/', views.verify_face, name='verify_face'),
    path('history/', views.attendance_history, name='attendance_history'),

    # Lecturer urls
    path('courses/', views.course_list, name='course_list'),
    path('courses/add/', views.add_course, name='add_course'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('courses/<int:course_id>/edit/', views.edit_course, name='edit_course'),
    path('sessions/', views.session_list, name='session_list'),
    path('sessions/add/', views.add_session, name='add_session'),
    path('sessions/<int:session_id>/', views.session_detail, name='session_detail'),
    path('reports/', views.attendance_reports, name='attendance_reports'),
]
