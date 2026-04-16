from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
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

# =========================
# USER PROFILE
# =========================
class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15)
    district = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return self.user.username


# =========================
# CATEGORY
# =========================
class Category(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Categories"

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
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='workers/')
    mobile = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField()
    district = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
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

    verified = models.BooleanField(default=False)
    aadhar_no = models.CharField(max_length=20, blank=True, null=True)
    pan_no = models.CharField(max_length=20, blank=True, null=True)
    aadhar_photo = models.ImageField(upload_to='docs/', blank=True, null=True)
    pan_photo = models.ImageField(upload_to='docs/', blank=True, null=True)
    rating_avg = models.FloatField(default=0)

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
class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE)
    booking_date = models.DateTimeField(auto_now_add=True)
    
    # New detail fields
    service_address = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)
    special_instructions = models.TextField(blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    # Business-Grade Custom IDs (MC-C1, MC-K1, etc.)
    booking_id_str = models.CharField(max_length=20, unique=True, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def save(self, *args, **kwargs):
        if not self.booking_id_str:
            # 1. Determine Prefix
            try:
                # Get the first category of the worker
                category = self.worker.categories.first()
                prefix_map = {
                    'Baby Care': 'B',
                    'Master Chef': 'K',
                    'Cooking': 'K',
                    'Deep Cleaning': 'C',
                    'Cleaning': 'C',
                    'Elder Care': 'E',
                    'Guardians': 'G',
                }
                char = prefix_map.get(category.name, 'O') if category else 'O'
            except Exception:
                char = 'O'

            prefix = f"MC-{char}"
            
            # 2. Count existing for this prefix
            count = Booking.objects.filter(booking_id_str__startswith=prefix).count()
            self.booking_id_str = f"{prefix}{count + 1}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} → {self.worker.user.username}"


# =========================
# REVIEW
# =========================
class Review(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE)

    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rating} ⭐"


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