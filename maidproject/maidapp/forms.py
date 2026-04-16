from django import forms
from django.contrib.auth import get_user_model
from .models import WorkerProfile

User = get_user_model()

class UserRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']

    phone = forms.CharField(max_length=15, required=True, widget=forms.TextInput(attrs={'placeholder': 'Enter your mobile number'}))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class WorkerProfileForm(forms.ModelForm):
    class Meta:
        model = WorkerProfile
        exclude = ['user', 'verified', 'rating_avg', 'availability']
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
        }