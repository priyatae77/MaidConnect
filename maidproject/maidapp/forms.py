from django import forms
from django.contrib.auth import get_user_model
from maidapp.models import WorkerProfile, UserProfile

User = get_user_model()

STATE_CHOICES = (
    ('', 'Select State'),
    ('Tamil Nadu', 'Tamil Nadu'), ('Kerala', 'Kerala'), ('Karnataka', 'Karnataka'),
    ('Andhra Pradesh', 'Andhra Pradesh'), ('Telangana', 'Telangana'), ('Maharashtra', 'Maharashtra'),
    ('Gujarat', 'Gujarat'), ('Delhi', 'Delhi'), ('Uttar Pradesh', 'Uttar Pradesh'),
    ('West Bengal', 'West Bengal'), ('Rajasthan', 'Rajasthan'), ('Punjab', 'Punjab'),
    ('Haryana', 'Haryana'), ('Madhya Pradesh', 'Madhya Pradesh'), ('Bihar', 'Bihar'),
)

class UserRegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Minimum 8 characters', 'id': 'regPassword'}),
        min_length=8
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Repeat your password', 'id': 'confirmPassword'}),
        min_length=8
    )
    phone = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': '98765 43210',
            'pattern': '[6-9][0-9]{9}',
            'maxlength': '10',
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data

    # Address fields for UserProfile
    address_line1 = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'placeholder': 'Enter house no / street', 'class': 'vibrant-input'}))
    address_line2 = forms.CharField(max_length=255, required=False, widget=forms.TextInput(attrs={'placeholder': 'Enter area / landmark', 'class': 'vibrant-input'}))
    city = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'placeholder': 'Enter city', 'class': 'vibrant-input'}))
    state = forms.ChoiceField(choices=STATE_CHOICES, required=True, widget=forms.Select(attrs={'class': 'vibrant-input'}))
    pincode = forms.CharField(max_length=6, min_length=6, required=True, widget=forms.TextInput(attrs={'placeholder': 'Enter 6-digit pincode', 'class': 'vibrant-input'}))

    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode')
        if not pincode.isdigit() or len(pincode) != 6:
            raise forms.ValidationError("Pincode must be exactly 6 numeric digits.")
        return pincode

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class WorkerProfileForm(forms.ModelForm):
    state = forms.ChoiceField(choices=STATE_CHOICES, required=True, widget=forms.Select(attrs={'class': 'vibrant-input'}))
    pincode = forms.CharField(max_length=6, min_length=6, required=True, widget=forms.TextInput(attrs={'placeholder': 'Enter 6-digit pincode', 'class': 'vibrant-input'}))
    
    # Optional KYC for testing
    photo = forms.ImageField(required=False)
    selfie = forms.ImageField(required=False)
    aadhar_front = forms.ImageField(required=False)
    aadhar_back = forms.ImageField(required=False)
    pan_photo = forms.ImageField(required=False)

    class Meta:
        model = WorkerProfile
        fields = [
            'photo', 'selfie', 'mobile', 'address', 'address_line1', 'address_line2', 
            'city', 'state', 'pincode', 'district', 'location', 'skills', 
            'languages', 'work_timings', 'age', 'gender', 'experience', 'price_per_day',
            'aadhar_no', 'pan_no', 'aadhar_front', 'aadhar_back', 'pan_photo', 'categories'
        ]
        widgets = {
            'categories': forms.CheckboxSelectMultiple(),
            'address': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Full Address for reference', 'class': 'vibrant-input'}),
            'address_line1': forms.TextInput(attrs={'placeholder': 'Enter house no / street', 'class': 'vibrant-input'}),
            'address_line2': forms.TextInput(attrs={'placeholder': 'Enter area / landmark', 'class': 'vibrant-input'}),
            'city': forms.TextInput(attrs={'placeholder': 'Enter city', 'class': 'vibrant-input'}),
            'aadhar_no': forms.TextInput(attrs={'placeholder': '12-digit Aadhaar Number', 'class': 'vibrant-input'}),
            'pan_no': forms.TextInput(attrs={'placeholder': 'PAN Number (ABCDE1234F)', 'class': 'vibrant-input'}),
        }

    def clean_aadhar_no(self):
        aadhar = self.cleaned_data.get('aadhar_no')
        if aadhar:
            if not aadhar.isdigit() or len(aadhar) != 12:
                raise forms.ValidationError("Aadhaar must be exactly 12 numeric digits.")
            if WorkerProfile.objects.filter(aadhar_no=aadhar).exists():
                raise forms.ValidationError("This Aadhaar number is already registered.")
        return aadhar

    def clean_pan_no(self):
        pan = self.cleaned_data.get('pan_no')
        if pan:
            import re
            if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan):
                raise forms.ValidationError("Invalid PAN format. Expected format: ABCDE1234F")
            if WorkerProfile.objects.filter(pan_no=pan).exists():
                raise forms.ValidationError("This PAN number is already registered.")
        return pan

    def clean_pincode(self):
        pincode = self.cleaned_data.get('pincode')
        if not pincode.isdigit() or len(pincode) != 6:
            raise forms.ValidationError("Pincode must be exactly 6 numeric digits.")
        return pincode


class UserProfileUpdateForm(forms.ModelForm):
    state = forms.ChoiceField(choices=STATE_CHOICES, required=False, widget=forms.Select(attrs={'class': 'vibrant-input'}))
    
    class Meta:
        model = UserProfile
        fields = ['phone', 'address_line1', 'address_line2', 'city', 'state', 'pincode', 'district']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'vibrant-input'}),
            'address_line1': forms.TextInput(attrs={'class': 'vibrant-input'}),
            'address_line2': forms.TextInput(attrs={'class': 'vibrant-input'}),
            'city': forms.TextInput(attrs={'class': 'vibrant-input'}),
            'district': forms.TextInput(attrs={'class': 'vibrant-input'}),
            'pincode': forms.TextInput(attrs={'maxlength': '6', 'class': 'vibrant-input'}),
        }


class WorkerProfileUpdateForm(forms.ModelForm):
    state = forms.ChoiceField(choices=STATE_CHOICES, required=False, widget=forms.Select(attrs={'class': 'vibrant-input'}))

    class Meta:
        model = WorkerProfile
        fields = [
            'skills', 'availability', 'experience', 'work_timings', 'address_line1', 
            'address_line2', 'city', 'state', 'pincode', 'district', 'address', 'mobile',
            'aadhar_no', 'pan_no', 'aadhar_front', 'aadhar_back', 'pan_photo', 'selfie', 'categories'
        ]
        widgets = {
            'categories': forms.CheckboxSelectMultiple(),
            'skills': forms.TextInput(attrs={'class': 'vibrant-input'}),
            'availability': forms.Select(attrs={'class': 'vibrant-input'}),
            'experience': forms.NumberInput(attrs={'class': 'vibrant-input'}),
            'work_timings': forms.TextInput(attrs={'class': 'vibrant-input'}),
            'address_line1': forms.TextInput(attrs={'class': 'vibrant-input'}),
            'address_line2': forms.TextInput(attrs={'class': 'vibrant-input'}),
            'city': forms.TextInput(attrs={'class': 'vibrant-input'}),
            'district': forms.TextInput(attrs={'class': 'vibrant-input'}),
            'address': forms.Textarea(attrs={'rows': 2, 'class': 'vibrant-input'}),
            'mobile': forms.TextInput(attrs={'class': 'vibrant-input'}),
            'pincode': forms.TextInput(attrs={'maxlength': '6', 'class': 'vibrant-input'}),
            'aadhar_no': forms.TextInput(attrs={'class': 'vibrant-input'}),
            'pan_no': forms.TextInput(attrs={'class': 'vibrant-input'}),
        }

    def clean_aadhar_no(self):
        aadhar = self.cleaned_data.get('aadhar_no')
        if aadhar:
            if not aadhar.isdigit() or len(aadhar) != 12:
                raise forms.ValidationError("Aadhaar must be exactly 12 numeric digits.")
            # Exclude current instance for update
            if WorkerProfile.objects.filter(aadhar_no=aadhar).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("This Aadhaar number is already registered.")
        return aadhar

    def clean_pan_no(self):
        pan = self.cleaned_data.get('pan_no')
        if pan:
            import re
            if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', pan):
                raise forms.ValidationError("Invalid PAN format. Expected format: ABCDE1234F")
            # Exclude current instance for update
            if WorkerProfile.objects.filter(pan_no=pan).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("This PAN number is already registered.")
        return pan

from maidapp.models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.HiddenInput(),
            'comment': forms.Textarea(attrs={'class': 'vibrant-input', 'rows': 4, 'placeholder': 'Share your experience...'}),
        }