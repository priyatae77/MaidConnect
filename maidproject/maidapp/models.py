from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):

    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('worker', 'Worker'),
        ('user', 'User'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    is_otp_verified = models.BooleanField(default=False)
    is_doc_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    session_key = models.CharField(max_length=40, blank=True, null=True)
    is_blocked = models.BooleanField(default=False, help_text="Block fraudulent users")

# =========================
# OTP VERIFICATION
# =========================
class OTPVerification(models.Model):
    DELIVERY_CHOICES = (
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
    )

    contact = models.CharField(max_length=100)  # Email or Phone
    otp = models.CharField(max_length=6)
    delivery_method = models.CharField(max_length=10, choices=DELIVERY_CHOICES, default='email')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    is_used = models.BooleanField(default=False)

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.contact} - {self.otp} ({self.delivery_method})"

# =========================
# USER PROFILE
# =========================
class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    
    # Structured Address
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(
        max_length=6, 
        validators=[RegexValidator(r'^\d{6}$', 'Enter a valid 6-digit pincode.')],
        blank=True, 
        null=True
    )

    district = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.username


# =========================
# CATEGORY
# =========================
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True, null=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# =========================
# WORKER PROFILE
# =========================
class WorkerProfile(models.Model):

    AVAILABILITY_CHOICES = (
        ('available', 'Available'),
        ('busy', 'Busy'),
    )

    KYC_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='workers/')
    selfie = models.ImageField(upload_to='kyc/selfies/', blank=True, null=True)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    
    # Structured Address
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(
        max_length=6, 
        validators=[RegexValidator(r'^\d{6}$', 'Enter a valid 6-digit pincode.')],
        blank=True, 
        null=True
    )

    address = models.TextField()
    district = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=100)
    categories = models.ManyToManyField(Category, related_name='workers')
    skills = models.CharField(max_length=150, help_text="Specific skills beyond categories")
    languages = models.CharField(max_length=150, blank=True, null=True)
    work_timings = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., Full-day, Part-time, specific slots")
    age = models.IntegerField(blank=True, null=True)
    gender = models.CharField(max_length=20, blank=True, null=True)
    experience = models.IntegerField()
    price_per_day = models.IntegerField()

    availability = models.CharField(
        max_length=10,
        choices=AVAILABILITY_CHOICES,
        default='available'
    )

    # KYC Verification
    verified = models.BooleanField(default=False)
    kyc_status = models.CharField(max_length=20, choices=KYC_STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    
    kyc_submitted_at = models.DateTimeField(blank=True, null=True)
    kyc_verified_at = models.DateTimeField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)

    aadhar_no = models.CharField(
        max_length=12,
        validators=[RegexValidator(r'^\d{12}$', 'Enter a valid 12-digit Aadhaar number.')],
        blank=True, null=True, unique=True
    )
    pan_no = models.CharField(
        max_length=10,
        validators=[RegexValidator(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', 'Enter a valid 10-character PAN.')],
        blank=True, null=True, unique=True
    )
    aadhar_front = models.ImageField(upload_to='kyc/aadhar/', blank=True, null=True)
    aadhar_back = models.ImageField(upload_to='kyc/aadhar/', blank=True, null=True)
    pan_photo = models.ImageField(upload_to='kyc/pan/', blank=True, null=True)
    
    rating_avg = models.FloatField(default=0)

    def masked_aadhar(self):
        if self.aadhar_no and len(self.aadhar_no) == 12:
            return f"XXXX-XXXX-{self.aadhar_no[-4:]}"
        return "Not Provided"

    def masked_pan(self):
        if self.pan_no and len(self.pan_no) == 10:
            return f"{self.pan_no[:2]}XXXXX{self.pan_no[-3:]}"
        return "Not Provided"

    def __str__(self):
        return self.user.username


# =========================
# DOCUMENTS
# =========================
class Document(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=50)
    document_file = models.FileField(upload_to='documents/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.document_type


# =========================
# BOOKING
# =========================
from django.db import models
from django.utils import timezone

class Booking(models.Model):
    CATEGORY_PREFIX = {
        'babycare': 'B',
        'cleaning': 'C',
        'cooking': 'K',
        'eldercare': 'E',
        'housekeeping': 'H',
        'driver': 'D',
        'patientcare': 'P',
        'laundry': 'L',
    }

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    booking_id_str = models.CharField(max_length=20, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    worker = models.ForeignKey('WorkerProfile', on_delete=models.CASCADE, related_name='bookings')

    service_type = models.CharField(max_length=100, help_text="Specific service chosen")
    service_address = models.TextField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    booking_date = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.booking_id_str:
            # Use service_type or fallback to worker's first category
            prefix_key = self.service_type.lower() if self.service_type else 'default'
            prefix = self.CATEGORY_PREFIX.get(prefix_key, 'X')

            # Count existing bookings in same category for ID increment
            count = Booking.objects.filter(service_type__iexact=self.service_type).count() + 1
            self.booking_id_str = f"MC-{prefix}{count}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} → {self.worker.user.username}"


# =========================
# REVIEW
# =========================
class Review(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name='reviews')
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review', null=True, blank=True)

    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=5
    )

    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rating} ⭐ for {self.worker.user.username}"


# =========================
# COMPLAINT
# =========================
class Complaint(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('resolved', 'Resolved'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, null=True, blank=True)

    message = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.status

# =========================
# PAYMENT
# =========================
class Payment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
    )

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=200, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} - {self.status}"

# =========================
# NOTIFICATION
# =========================
class NotificationManager(models.Manager):
    def unread_count(self, user):
        return self.filter(user=user, is_read=False).count()

class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = NotificationManager()

    class Meta:
        ordering = ['-created_at']

    @property
    def unread(self):
        return Notification.objects.filter(user=self.user, is_read=False)

    def __str__(self):
        return f"To {self.user.username}: {self.message[:30]}..."