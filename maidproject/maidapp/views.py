from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError

from .forms import UserRegisterForm, WorkerProfileForm
from .models import WorkerProfile, Booking, UserProfile

from django.contrib.auth import authenticate, login
from django.contrib import messages
from .models import CustomUser


# =========================
# HOME
# =========================
def home(request):
    return render(request, 'home.html')


# =========================
# LOGIN PAGE
# =========================
def login_view(request):
    return render(request, 'login.html')

# =========================
# USER REGISTER
# =========================
def user_register(request):
    form = UserRegisterForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            messages.success(request, "Account created! You can now log in.")
            return redirect('login')
    return render(request, 'user_register.html', {'form': form})


# =========================
# WORKER REGISTER (FIXED)
# =========================
def worker_register(request):

    user_form = UserRegisterForm(request.POST or None)
    worker_form = WorkerProfileForm(request.POST or None, request.FILES or None)

    if request.method == "POST":

        if user_form.is_valid() and worker_form.is_valid():

            user = user_form.save()

            # ✅ SAFE duplicate check (FIXED POSITION)
            if WorkerProfile.objects.filter(user=user).exists():
                return JsonResponse(
                    {"error": "Worker already exists"},
                    status=400
                )

            worker = worker_form.save(commit=False)
            worker.user = user

            try:
                worker.save()
            except IntegrityError:
                return JsonResponse({"error": "Database error"}, status=500)

            return redirect('worker_list')

    return render(request, 'worker_register.html', {
        'user_form': user_form,
        'worker_form': worker_form
    })


# =========================
# WORKER LIST + FILTER
# =========================
def worker_list(request):

    workers = WorkerProfile.objects.all()

    search = request.GET.get('search')
    location = request.GET.get('location')
    max_price = request.GET.get('price')

    if search:
        workers = workers.filter(skills__icontains=search)

    if location:
        workers = workers.filter(location__icontains=location)

    if max_price:
        workers = workers.filter(price_per_day__lte=max_price)

    return render(request, 'worker_list.html', {
        'workers': workers
    })


# =========================
# BOOK WORKER (AJAX SAFE)
# =========================
@login_required
def book_worker(request, worker_id):

    if request.method != "POST":
        return JsonResponse({"status": "invalid request"}, status=400)

    worker = get_object_or_404(WorkerProfile, id=worker_id)

    # ❗ prevent duplicate booking
    existing = Booking.objects.filter(
        user=request.user,
        worker=worker,
        status="pending"
    ).exists()

    if existing:
        return JsonResponse({
            "status": "failed",
            "message": "Already booked"
        })

    Booking.objects.create(
        user=request.user,
        worker=worker,
        status="pending"
    )

    return JsonResponse({
        "status": "success",
        "message": "Booking created"
    })


# =========================
# USER PROFILE SIGNAL
# =========================
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


def login_view(request):

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            
            # Redirect logic based on role
            if user.role == 'worker':
                return redirect('worker_dashboard')
            elif user.role == 'admin':
                return redirect('/admin/')
            else:
                return redirect('worker_list')
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
    
    return render(request, 'worker_dashboard.html', {
        'worker': worker_profile,
        'bookings': bookings
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
        
    booking.save()
    return JsonResponse({"status": "success", "new_status": booking.status})


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
def initiate_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # We will charge them the 'price_per_day' of the worker for now.
    amount = booking.worker.price_per_day * 100  # Razorpay expects amount in paise (1 INR = 100 paise)
    
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
    payment_data = {
        "amount": amount,
        "currency": "INR",
        "receipt": f"receipt_order_{booking.id}",
        "notes": {
            "booking_id": booking.id
        }
    }
    
    razorpay_order = client.order.create(data=payment_data)
    
    payment = Payment.objects.create(
        booking=booking,
        user=request.user,
        amount=booking.worker.price_per_day,
        razorpay_order_id=razorpay_order['id'],
        status='pending'
    )
    
    context = {
        'order_id': razorpay_order['id'],
        'amount': payment.amount,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'payment': payment,
        'booking': booking
    }
    return render(request, 'payment_checkout.html', context)

@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        
        try:
            payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = 'successful'
            payment.save()
            
            # Booking becomes completed or paid
            booking = payment.booking
            booking.status = 'completed'
            booking.save()
            
            messages.success(request, "Payment successful! Your booking is locked.")
            return redirect('my_bookings')
            
        except Payment.DoesNotExist:
            return JsonResponse({"error": "Payment record not found"}, status=400)
            
    return redirect('home')