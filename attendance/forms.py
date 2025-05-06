from django import forms
from .models import Course, Session, Attendance

class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['course', 'date', 'start_time', 'end_time']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, *kwargs)
        if user and user.is_lecturer():
            self.fields['course'].queryset = Course.objects.filter(lecturer=user)

        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            })

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'code', 'students']
        widgets = {
            'students': forms.SelectMultiple()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import User
        self.fields['students'].queryset = User.objects.filter(user_type='student')

        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
            })
