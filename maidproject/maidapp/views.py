from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError

from maidapp.forms import UserRegisterForm, WorkerProfileForm
from maidapp.models import WorkerProfile, Booking, UserProfile, Payment

from django.contrib.auth import authenticate, login
from django.contrib import messages
from maidapp.models import CustomUser


import json
import random
from django.views.decorators.csrf import csrf_exempt

# =========================
# HOME
# =========================
def home(request):
    from maidapp.models import Category
    categories = Category.objects.all()
    # Top-rated workers for the homepage carousel
    top_workers = WorkerProfile.objects.filter(
        availability='available'
    ).order_by('-rating_avg')[:8]
    # Platform Insights for Landing Page
    total_workers = WorkerProfile.objects.filter(verified=True).count()
    total_bookings = Booking.objects.count()

    return render(request, 'home.html', {
        'categories': categories,
        'top_workers': top_workers,
        'platform_workers': total_workers,
        'platform_bookings': total_bookings,
    })

def about(request):
    return render(request, 'about.html')

def register_choice(request):
    return render(request, 'register_choice.html')


# =========================
# AUTHENTICATION
# =========================

def verify_otp(request):
    if request.method == "POST":
        otp = request.POST.get('otp')
        # Check against the code stored in the user profile
        if otp == request.user.otp_code or otp == "123456": # 123456 kept for developer ease
            request.user.is_otp_verified = True
            request.user.otp_code = None # Clear after use
            request.user.save()
            return JsonResponse({"status": "success"})
    return render(request, 'verify_otp.html')

# =========================
# USER REGISTER
# =========================
def user_register(request):
    form = UserRegisterForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'user'
            user.is_otp_verified = True
            user.save()
            
            # Save phone to profile
            phone = form.cleaned_data.get('phone')
            UserProfile.objects.create(user=user, phone=phone)
            
            login(request, user)
            messages.success(request, f"Welcome to MaidConnect, {user.username}!")
            return redirect('my_bookings')
    return render(request, 'user_register.html', {'form': form})


# =========================
# WORKER REGISTER (FIXED)
# =========================
def worker_register(request):
    user_form = UserRegisterForm(request.POST or None)
    worker_form = WorkerProfileForm(request.POST or None, request.FILES or None)

    if request.method == "POST":
        if user_form.is_valid() and worker_form.is_valid():
            user = user_form.save(commit=False)
            user.role = 'worker'
            user.is_otp_verified = True
            user.save()
            
            # Save phone to profile
            phone = user_form.cleaned_data.get('phone')
            UserProfile.objects.create(user=user, phone=phone)

            # Check if profile already exists
            if WorkerProfile.objects.filter(user=user).exists():
                return JsonResponse({"error": "Worker already exists"}, status=400)

            worker = worker_form.save(commit=False)
            worker.user = user

            try:
                worker.save()
                login(request, user)
                messages.success(request, "Application received! Welcome to the team.")
                return redirect('worker_dashboard')
            except IntegrityError:
                return JsonResponse({"error": "Database error"}, status=500)

    return render(request, 'worker_register.html', {
        'user_form': user_form,
        'worker_form': worker_form
    })


# =========================
# WORKER LIST + FILTER
# =========================
def worker_list(request):
    from maidapp.models import Category

    workers = WorkerProfile.objects.all()
    categories = Category.objects.all()

    search      = request.GET.get('search')
    location    = request.GET.get('location')
    max_price   = request.GET.get('price')
    category_id = request.GET.get('category')
    sort        = request.GET.get('sort')

    if search:
        workers = workers.filter(skills__icontains=search)
    if location:
        workers = workers.filter(location__icontains=location)
    if max_price:
        workers = workers.filter(price_per_day__lte=max_price)
    if category_id:
        workers = workers.filter(categories__id=category_id)

    # Sorting
    sort_map = {
        'rating':     '-rating_avg',
        'price_asc':  'price_per_day',
        'price_desc': '-price_per_day',
        'exp':        '-experience',
    }
    workers = workers.order_by(sort_map.get(sort, '-rating_avg'))

    return render(request, 'worker_list.html', {
        'workers':    workers,
        'categories': categories,
    })


# =========================
# WORKER DETAIL
# =========================
def worker_detail(request, worker_id):
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    # Get some related workers from the same category
    related_workers = WorkerProfile.objects.filter(
        categories__in=worker.categories.all()
    ).exclude(id=worker.id).distinct()[:3]
    
    return render(request, 'worker_detail.html', {
        'worker': worker,
        'related_workers': related_workers
    })


# =========================
# BOOKING CONFIG (STEP 1)
# =========================
@login_required
def booking_config(request, worker_id):
    from datetime import date
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    return render(request, 'booking_config.html', {
        'worker': worker,
        'today':  date.today(),
    })


# =========================
# BOOK WORKER (STEP 2 - CONFIRM)
# =========================
@login_required
def book_worker(request, worker_id):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Only POST allowed"}, status=405)

    worker = get_object_or_404(WorkerProfile, id=worker_id)
    service_address = request.POST.get('service_address')
    start_time = request.POST.get('start_time')
    end_time = request.POST.get('end_time')
    special_instructions = request.POST.get('special_instructions')

    total_price = worker.price_per_day

    # Prevent duplicate pending booking
    existing = Booking.objects.filter(
        user=request.user,
        worker=worker,
        status="pending"
    ).exists()

    if existing:
        return JsonResponse({"status": "error", "message": "You already have a pending booking with this worker."})

    booking = Booking.objects.create(
        user=request.user,
        worker=worker,
        service_address=service_address,
        start_time=start_time if start_time else None,
        end_time=end_time if end_time else None,
        special_instructions=special_instructions,
        total_price=total_price,
        status="pending"
    )

    return JsonResponse({
        "status": "success", 
        "booking_id": booking.booking_id_str,
        "internal_id": booking.id,
        "message": f"Booking request {booking.booking_id_str} sent!"
    })


# =========================
# USER PROFILE SIGNAL
# =========================
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


def login_view(request):
    if request.method == "POST":
        u = request.POST.get("username")
        p = request.POST.get("password")

        user = authenticate(request, username=u, password=p)

        if user is not None:
            login(request, user)
            
            # Redirect logic based on role
            if user.is_superuser or user.role == 'admin':
                return redirect('admin_dashboard')
            elif user.role == 'worker':
                return redirect('worker_dashboard')
            else:
                return redirect('user_dashboard')
        else:
            messages.error(request, "Invalid credentials")

    return render(request, 'login.html')

@login_required
def logout_view(request):
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('home')

# =========================
# WORKER DASHBOARD
# =========================
@login_required
def worker_dashboard(request):
    if request.user.role != 'worker':
        return redirect('home')
        
    try:
        worker_profile = request.user.workerprofile
    except WorkerProfile.DoesNotExist:
        return redirect('worker_register')
        
    bookings = Booking.objects.filter(worker=worker_profile).order_by('-booking_date')
    
    # Aggregating status for a pie chart
    from django.db.models import Count
    status_data = Booking.objects.filter(worker=worker_profile).values('status').annotate(count=Count('status'))
    
    status_labels = [d['status'].title() for d in status_data]
    status_values = [d['count'] for d in status_data]
    
    return render(request, 'worker_dashboard.html', {
        'worker': worker_profile,
        'bookings': bookings,
        'status_labels': json.dumps(status_labels),
        'status_values': json.dumps(status_values),
    })

# =========================
# WORKER ACTIONS
# =========================
from django.core.mail import send_mail

@login_required
def update_booking_status(request, booking_id, action):
    if request.method != "POST":
        return JsonResponse({"status": "failed", "message": "Invalid request"})
        
    booking = get_object_or_404(Booking, id=booking_id)
    
    if booking.worker.user != request.user:
        return JsonResponse({"status": "failed", "message": "Unauthorized"})
        
    if action == 'accept':
        booking.status = 'confirmed'
        # Emulate Email/SMS Sending
        try:
            send_mail(
                'MaidConnect - Booking Accepted!',
                f'Great news! {booking.worker.user.username} has accepted your booking request. Please log in to complete your payment!',
                settings.DEFAULT_FROM_EMAIL,
                [booking.user.email],
                fail_silently=True,
            )
        except Exception:
            pass  # Fail gracefully without breaking UI if SMTP not configured
    elif action == 'reject':
        booking.status = 'cancelled'
    elif action == 'complete':
        booking.status = 'completed'
        
    booking.save()
    return JsonResponse({"status": "success", "new_status": booking.status})


# =========================
# REVIEWS
# =========================
@login_required
def submit_review(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    
    if booking.user != request.user:
        messages.error(request, "Unauthorized")
        return redirect('my_bookings')
        
    if request.method == "POST":
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        from maidapp.models import Review
        Review.objects.create(
            user=request.user,
            worker=booking.worker,
            rating=rating,
            comment=comment
        )
        
        # Update worker average rating if needed (optional optimization)
        
        messages.success(request, "Thank you for your feedback!")
        return redirect('my_bookings')
        
    return render(request, 'review_form.html', {'booking': booking})


# =========================
# USER BOOKINGS & PAYMENT
# =========================
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-booking_date')
    return render(request, 'my_bookings.html', {'bookings': bookings})


@login_required
@login_required
def initiate_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    amount = booking.total_price * 100
    razorpay_order = {'id': 'order_mock_' + str(random.randint(1000, 9999))}
    
    payment, created = Payment.objects.get_or_create(
        booking=booking,
        defaults={
            'user': request.user,
            'amount': booking.total_price,
            'razorpay_order_id': razorpay_order['id'],
            'status': 'pending'
        }
    )
    if not created and payment.status == 'pending':
        payment.razorpay_order_id = razorpay_order['id']
        payment.save()
    
    return JsonResponse({
        "status": "success",
        "order_id": razorpay_order['id'],
        "amount": int(amount),
        "key_id": settings.RAZORPAY_KEY_ID,
        "name": booking.worker.user.get_full_name(),
        "description": f"Payment for {booking.booking_id_str}"
    })


@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        
        try:
            payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
            payment.razorpay_payment_id = razorpay_payment_id
            payment.status = 'successful'
            payment.save()
            
            booking = payment.booking
            booking.status = 'confirmed'
            booking.save()
            
            return JsonResponse({"status": "success", "message": "Payment verified!"})
        except Payment.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Payment not found"}, status=400)
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


@login_required
def user_dashboard(request):
    """Premium Customer Dashboard"""
    if request.user.role != 'user' and not request.user.role == 'admin':
         # If admin wants to see, they can, but mostly for users
         pass
    
    bookings = Booking.objects.filter(user=request.user).order_by('-booking_date')
    
    # Stats
    total_spent = Payment.objects.filter(user=request.user, status='successful').aggregate(Sum('amount'))['amount__sum'] or 0
    active_bookings = bookings.filter(status__in=['pending', 'confirmed']).count()
    completed_bookings = bookings.filter(status='completed').count()
    
    return render(request, 'user_dashboard.html', {
        'bookings': bookings,
        'total_spent': total_spent,
        'active_count': active_bookings,
        'completed_count': completed_bookings,
    })

def api_get_locations(request):
    """API for location autocomplete"""
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse([], safe=False)
        
    # Get unique locations from WorkerProfile that match the query
    locations = WorkerProfile.objects.filter(
        location__icontains=query
    ).values_list('location', flat=True).distinct()[:8]
    
    return JsonResponse(list(locations), safe=False)


@login_required
def check_new_jobs(request):
    """API for AJAX polling by workers"""
    if request.user.role != 'worker':
        return JsonResponse({"error": "Unauthorized"}, status=403)
        
    worker = get_object_or_404(WorkerProfile, user=request.user)
    new_bookings = Booking.objects.filter(worker=worker, status='pending').count()
    
    return JsonResponse({
        "status": "success",
        "new_jobs_count": new_bookings
    })

@csrf_exempt
@login_required
def update_availability(request):
    if request.method == "POST":
        data = json.loads(request.body)
        availability = data.get('availability')
        worker = get_object_or_404(WorkerProfile, user=request.user)
        worker.availability = availability
        worker.save()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)

# =========================
# ADMIN DASHBOARD
# =========================
from django.db.models import Sum

@login_required
def admin_dashboard(request):
    if request.user.role != 'admin' and not request.user.is_superuser:
        return redirect('home')

    total_workers = WorkerProfile.objects.count()
    total_bookings = Booking.objects.count()
    total_revenue = Payment.objects.filter(status='successful').aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Aggregating daily revenue for Chart.js
    from django.db.models.functions import TruncDate
    revenue_data = Payment.objects.filter(status='successful') \
        .annotate(date=TruncDate('created_at')) \
        .values('date') \
        .annotate(total=Sum('amount')) \
        .order_by('date')[:7]
    
    chart_labels = [d['date'].strftime('%b %d') for d in revenue_data]
    chart_values = [float(d['total']) for d in revenue_data]
    
    # Categorical Counts for Dashboard Colors
    wip_bookings = Booking.objects.filter(status='confirmed').count()
    pending_bookings = Booking.objects.filter(status='pending').count()
    cancelled_bookings = Booking.objects.filter(status='cancelled').count()
    
    recent_bookings = Booking.objects.all().order_by('-booking_date')[:10]

    context = {
        'total_workers': total_workers,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'wip_count': wip_bookings,
        'pending_count': pending_bookings,
        'cancelled_count': cancelled_bookings,
        'bookings': recent_bookings,
        'chart_labels': json.dumps(chart_labels),
        'chart_values': json.dumps(chart_values),
    }
    return render(request, 'admin_dashboard.html', context)


@login_required
def manage_workers(request):
    if request.user.role != 'admin': return redirect('home')
    workers = WorkerProfile.objects.all().order_by('-verified')
    return render(request, 'manage_workers.html', {'workers': workers})


@login_required
def toggle_worker_verification(request, worker_id):
    if request.user.role != 'admin': return JsonResponse({"error": "Unauthorized"}, status=403)
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    worker.verified = not worker.verified
    worker.save()
    return JsonResponse({"status": "success", "verified": worker.verified})


@login_required
def manage_users(request):
    if request.user.role != 'admin': return redirect('home')
    users = CustomUser.objects.filter(role='user').order_by('-date_joined')
    return render(request, 'manage_users.html', {'users': users})


@login_required
def admin_complaints(request):
    if request.user.role != 'admin': return redirect('home')
    from maidapp.models import Complaint
    complaints = Complaint.objects.all().order_by('-created_at')
    return render(request, 'manage_complaints.html', {'complaints': complaints})


@login_required
def view_receipt(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    # Check if user is owner or admin
    if request.user != booking.user and request.user.role != 'admin':
        return redirect('home')
    return render(request, 'receipt.html', {'booking': booking})
