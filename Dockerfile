# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE core.settings
ENV DJANGO_DEBUG False
# Set DJANGO_ALLOWED_HOSTS to '*' for now, but it should be configured more securely for production
ENV DJANGO_ALLOWED_HOSTS '*'

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required by dlib and other packages
# libgl1-mesa-glx is often needed for OpenCV/dlib GUI features, though might not be strictly necessary for a headless server.
# It's included here for broader compatibility.
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libjpeg-dev \
    libpng-dev \
    libx11-dev \
    libgtk-3-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . /app/

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port 8000 to the outside world
EXPOSE 8000

# Define the command to run your app using Gunicorn
# Ensure your project's WSGI application is correctly pointed to (e.g., core.wsgi:application)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "core.wsgi:application"]