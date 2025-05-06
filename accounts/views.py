from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import base64
import json
import numpy as np
import face_recognition
import os
import io
from PIL import Image

from .forms import UserRegistrationForm, UserLoginForm, FaceImageForm
from .models import User

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'accounts/home.html')

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('face_setup')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

def user_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
    else:
        form = UserLoginForm()
    return render(request, 'accounts/login.html', {'form': form})

@login_required
def dashboard(request):
    if request.user.is_student():
        return render(request, 'accounts/student_dashboard.html')
    elif request.user.is_lecturer():
        return render(request, 'accounts/lecturer_dashboard.html')
    return render(request, 'accounts/dashboard.html')

@login_required
def profile(request):
    return render(request, 'accounts/profile.html')

@login_required
def face_setup(request):
    if request.method == 'POST':
        return redirect('dashboard')

    form = FaceImageForm()
    return render(request, 'accounts/face_setup.html', {'form': form})

@login_required
@csrf_exempt
def save_face(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_data = data.get('image')
            
            if not image_data:
                return JsonResponse({'status': 'error', 'message': 'No image data received'})
            
            # Convert base64 to image
            format, imgstr = image_data.split(';base64,')
            ext = format.split('/')[-1]
            image_data = base64.b64decode(imgstr)
            
            # Process with face_recognition
            image = face_recognition.load_image_file(io.BytesIO(image_data))
            face_locations = face_recognition.face_locations(image, model='hog')
            
            if not face_locations:
                return JsonResponse({'status': 'error', 'message': 'No face detected in the image'})
            
            if len(face_locations) > 1:
                return JsonResponse({'status': 'error', 'message': 'Multiple faces detected. Please ensure only your face is visible'})
            
            # Get face encoding
            face_encoding = face_recognition.face_encodings(image, face_locations)[0]
            
            # Save the encoding
            request.user.face_encoding = face_encoding.tobytes()
            
            # Save the image
            image_io = io.BytesIO(image_data)
            image_name = f'user_{request.user.id}_face.{ext}'
            request.user.face_image.save(image_name, io.BytesIO(image_data), save=True)
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
