from django import forms
from django.contrib.auth.models import User
from accounts.models import MemberProfile

class MemberForm(forms.ModelForm):
    class Meta:
        model = MemberProfile
        fields = ['member_code', 'name', 'email', 'phone', 'department', 'role', 'status']
        widgets = {
            'member_code': forms.TextInput(attrs={'class': 'input', 'placeholder': 'e.g. STU-2024-005'}),
            'name': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Full Name'}),
            'email': forms.EmailInput(attrs={'class': 'input', 'placeholder': 'student@diu.edu.bd'}),
            'phone': forms.TextInput(attrs={'class': 'input', 'placeholder': '017XXXXXXXX'}),
            'department': forms.TextInput(attrs={'class': 'input', 'placeholder': 'Software Engineering'}),
            'role': forms.Select(attrs={'class': 'input'}),
            'status': forms.Select(attrs={'class': 'input'}),
        }
