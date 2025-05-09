from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count, Q
import json
import base64
import io
import numpy as np
import face_recognition

from .models import Course, Session, Attendance
from .forms import SessionForm, CourseForm
from accounts.models import User

def is_student(user):
    return user.is_authenticated and user.is_student()

def is_lecturer(user):
    return user.is_authenticated and user.is_lecturer()

@login_required
@user_passes_test(is_student)
def mark_attendance(request):
    # Get sessions available for the student
    now = timezone.now()
    
    # Find all current sessions for courses the student is enrolled in
    current_sessions = Session.objects.filter(
        course__students=request.user,
        date=now.date(),
        start_time__lte=now.time(),
        end_time__gte=now.time()
    ).exclude(
        attendances__student=request.user
    )
    
    # Find all sessions for today that the student already marked attendance
    marked_sessions = Session.objects.filter(
        attendances__student=request.user,
        date=now.date()
    )
    
    context = {
        'current_sessions': current_sessions,
        'marked_sessions': marked_sessions,
    }
    
    return render(request, 'attendance/mark_attendance.html', context)

@login_required
@user_passes_test(is_student)
@csrf_exempt
def verify_face(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            image_data = data.get('image')
            
            if not session_id or not image_data:
                return JsonResponse({'status': 'error', 'message': 'Missing required data'})
            
            # Get the session
            try:
                session = Session.objects.get(id=session_id)
            except Session.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Invalid session'})
            
            # Check if student is enrolled in the course
            if request.user not in session.course.students.all():
                return JsonResponse({'status': 'error', 'message': 'You are not enrolled in this course'})
            
            # Check if attendance already marked
            if Attendance.objects.filter(session=session, student=request.user).exists():
                return JsonResponse({'status': 'error', 'message': 'Attendance already marked for this session'})
            
            # Convert base64 to image
            format, imgstr = image_data.split(';base64,')
            image_data = base64.b64decode(imgstr)
            
            # Process with face_recognition
            image = face_recognition.load_image_file(io.BytesIO(image_data))
            face_locations = face_recognition.face_locations(image, model='hog')
            
            if not face_locations:
                return JsonResponse({'status': 'error', 'message': 'No face detected in the image'})
            
            if len(face_locations) > 1:
                return JsonResponse({'status': 'error', 'message': 'Multiple faces detected. Please ensure only your face is visible'})
            
            # Get face encoding
            new_encoding = face_recognition.face_encodings(image, face_locations)[0]
            
            # Retrieve stored encoding
            if not request.user.face_encoding:
                return JsonResponse({'status': 'error', 'message': 'Face verification not set up. Please set up face verification first'})
            
            stored_encoding = np.frombuffer(request.user.face_encoding, dtype=np.float64)
            
            # Compare faces
            results = face_recognition.compare_faces([stored_encoding], new_encoding, tolerance=0.5)
            
            if not results[0]:
                return JsonResponse({'status': 'error', 'message': 'Face verification failed. Please try again'})
            
            # Mark attendance
            attendance = Attendance(
                session=session,
                student=request.user,
                face_verified=True
            )
            attendance.save()
            
            return JsonResponse({'status': 'success', 'message': 'Attendance marked successfully'})
        
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
@user_passes_test(is_student)
def attendance_history(request):
    # Get attendance history for the student
    attendances = Attendance.objects.filter(student=request.user).order_by('-session__date', '-session__start_time')
    
    context = {
        'attendances': attendances,
    }
    
    return render(request, 'attendance/attendance_history.html', context)

@login_required
@user_passes_test(is_lecturer)
def course_list(request):
    courses = Course.objects.filter(lecturer=request.user)
    
    context = {
        'courses': courses,
    }
    
    return render(request, 'attendance/course_list.html', context)

@login_required
@user_passes_test(is_lecturer)
def add_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.lecturer = request.user
            course.save()
            form.save_m2m()  # Save the many-to-many relations
            return redirect('course_list')
    else:
        form = CourseForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'attendance/add_course.html', context)

@login_required
@user_passes_test(is_lecturer)
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id, lecturer=request.user)
    sessions = Session.objects.filter(course=course).order_by('-date', '-start_time')
    
    # Get student attendance statistics
    students = course.students.all()
    student_stats = []
    
    total_sessions = sessions.count()
    
    for student in students:
        attended = Attendance.objects.filter(student=student, session__course=course).count()
        attendance_rate = (attended / total_sessions * 100) if total_sessions > 0 else 0
        
        student_stats.append({
            'student': student,
            'attended': attended,
            'total': total_sessions,
            'attendance_rate': attendance_rate,
        })
    
    context = {
        'course': course,
        'sessions': sessions,
        'student_stats': student_stats,
    }
    
    return render(request, 'attendance/course_detail.html', context)

@login_required
@user_passes_test(is_lecturer)
def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, lecturer=request.user)
    
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            return redirect('course_detail', course_id=course.id)
    else:
        form = CourseForm(instance=course)
    
    context = {
        'form': form,
        'course': course,
    }
    
    return render(request, 'attendance/edit_course.html', context)

@login_required
@user_passes_test(is_lecturer)
def session_list(request):
    sessions = Session.objects.filter(course__lecturer=request.user).order_by('-date', '-start_time')
    
    current_tz = timezone.get_current_timezone()
    today = timezone.now().astimezone(current_tz).date()
    now = timezone.now().astimezone(current_tz).time()
    
    context = {
        'sessions': sessions,
        'today': today,
        'now': now,
    }
    
    return render(request, 'attendance/session_list.html', context)

@login_required
@user_passes_test(is_lecturer)
def add_session(request):
    if request.method == 'POST':
        form = SessionForm(request.user, request.POST)
        if form.is_valid():
            session = form.save()
            return redirect('session_list')
    else:
        form = SessionForm(request.user)
    
    context = {
        'form': form,
    }
    
    return render(request, 'attendance/add_session.html', context)

@login_required
@user_passes_test(is_lecturer)
def session_detail(request, session_id):
    session = get_object_or_404(Session, id=session_id, course__lecturer=request.user)
    
    # Get attendances for this session
    attendances = Attendance.objects.filter(session=session).order_by('timestamp')
    
    # Get students who haven't marked attendance
    absent_students = session.course.students.exclude(attendances__session=session)
    
    context = {
        'session': session,
        'attendances': attendances,
        'absent_students': absent_students,
    }
    
    return render(request, 'attendance/session_detail.html', context)

@login_required
@user_passes_test(is_lecturer)
def attendance_reports(request):
    courses = Course.objects.filter(lecturer=request.user)
    
    # If a course is selected, show detailed report
    selected_course = None
    course_id = request.GET.get('course')
    
    if course_id:
        try:
            selected_course = courses.get(id=course_id)
            sessions = Session.objects.filter(course=selected_course).order_by('-date')
            students = selected_course.students.all()
            
            # Calculate attendance rates
            student_attendance = []
            for student in students:
                attended_sessions = Attendance.objects.filter(
                    student=student,
                    session__course=selected_course
                ).count()
                
                total_sessions = sessions.count()
                attendance_rate = (attended_sessions / total_sessions * 100) if total_sessions > 0 else 0
                
                student_attendance.append({
                    'student': student,
                    'attended': attended_sessions,
                    'total': total_sessions,
                    'rate': attendance_rate,
                })
            
        except Course.DoesNotExist:
            selected_course = None
            sessions = []
            student_attendance = []
    else:
        sessions = []
        student_attendance = []
    
    context = {
        'courses': courses,
        'selected_course': selected_course,
        'sessions': sessions,
        'student_attendance': student_attendance,
    }
    
    return render(request, 'attendance/attendance_reports.html', context)
