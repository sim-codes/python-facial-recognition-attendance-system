from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count, Q
import json
import base64
import io
import numpy as np
import face_recognition
import csv
from datetime import datetime

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
    selected_course = None
    sessions = Session.objects.none()
    student_attendance = []
    course_average_attendance_percentage = 0

    course_id = request.GET.get('course')
    student_query = request.GET.get('student_query')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if course_id:
        try:
            selected_course = courses.get(id=course_id)
            sessions_query = Session.objects.filter(course=selected_course)

            # Date range filtering for sessions
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                sessions_query = sessions_query.filter(date__gte=start_date)
            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                sessions_query = sessions_query.filter(date__lte=end_date)
            
            sessions = sessions_query.order_by('-date', '-start_time')

            # Filter students based on student_query
            students_query = selected_course.students.all()
            if student_query:
                students_query = students_query.filter(
                    Q(username__icontains=student_query) | 
                    Q(email__icontains=student_query) | 
                    Q(first_name__icontains=student_query) | 
                    Q(last_name__icontains=student_query)
                )
            
            total_sessions_for_course_in_range = sessions.count()
            total_attended_count_for_course = 0
            
            for student in students_query:
                # Consider only sessions the student is part of for their individual rate
                # but for overall course average, we use all sessions in range for the selected course.
                attended_sessions_count = Attendance.objects.filter(
                    student=student,
                    session__in=sessions # Filter by sessions in the date range
                ).count()
                
                # The number of sessions a student could have attended is total_sessions_for_course_in_range
                # if they were enrolled for all of them.
                # For simplicity, we'll use total_sessions_for_course_in_range for rate calculation here.
                # A more complex calculation might consider student enrollment dates vs session dates.
                
                attendance_rate = (attended_sessions_count / total_sessions_for_course_in_range * 100) if total_sessions_for_course_in_range > 0 else 0
                
                student_attendance.append({
                    'student': student,
                    'attended': attended_sessions_count,
                    'total_sessions_for_student': total_sessions_for_course_in_range, # Total sessions in filtered range for this course
                    'rate': attendance_rate,
                })
                total_attended_count_for_course += attended_sessions_count

            if students_query.count() > 0 and total_sessions_for_course_in_range > 0:
                course_average_attendance_percentage = round((total_attended_count_for_course / (students_query.count() * total_sessions_for_course_in_range)) * 100)
            else:
                course_average_attendance_percentage = 0

            if 'export_csv' in request.GET:
                response = HttpResponse(content_type='text/csv')
                response['Content-Disposition'] = f'attachment; filename="attendance_report_{selected_course.code}_{timezone.now().strftime("%Y%m%d")}.csv"'
                
                writer = csv.writer(response)
                writer.writerow(['Student Name', 'Student Email', 'Sessions Attended', 'Total Sessions in Filter', 'Attendance Rate (%)'])
                
                for stat in student_attendance:
                    writer.writerow([
                        stat['student'].get_full_name() or stat['student'].username,
                        stat['student'].email,
                        stat['attended'],
                        stat['total_sessions_for_student'],
                        f"{stat['rate']:.2f}"
                    ])
                return response

        except Course.DoesNotExist:
            selected_course = None # Handled by template
        except ValueError: # Handle invalid date format
            # Optionally, add a message to the user about invalid date format
            pass


    context = {
        'courses': courses,
        'selected_course': selected_course,
        'sessions': sessions, # These are already filtered sessions if a course is selected
        'student_attendance': student_attendance,
        'course_average_attendance_percentage': course_average_attendance_percentage,
        'request': request, # Pass request to access GET params in template if needed
    }
    
    return render(request, 'attendance/attendance_reports.html', context)
