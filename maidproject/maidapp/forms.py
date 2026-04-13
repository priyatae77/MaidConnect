from django import forms
from django.contrib.auth import get_user_model
from .models import WorkerProfile

User = get_user_model()

class UserRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])  # 🔥 important
        if commit:
            user.save()
        return user


class WorkerProfileForm(forms.ModelForm):
    class Meta:
        model = WorkerProfile
        exclude = ['user', 'verified', 'rating_avg']