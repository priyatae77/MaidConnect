from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Sum, Count
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import send_mail, EmailMessage

import json
import base64
from datetime import date, timedelta
import random
import secrets
import logging
import razorpay
from maidapp.models import Notification

def create_notification(user, message):
    Notification.objects.create(user=user, message=message)

# Local App Imports
from maidapp.decorators import admin_required, user_required, worker_required
from maidapp.models import (
    WorkerProfile, Booking, UserProfile, Payment, CustomUser, OTPVerification, 
    Category, Review, Complaint, Offer, SmartOfferSettings
)
from maidapp.forms import (
    UserRegisterForm, WorkerProfileForm, UserProfileUpdateForm, 
    WorkerProfileUpdateForm, ReviewForm, OfferForm, SmartOfferSettingsForm
)

# Initialize Logger
logger = logging.getLogger(__name__)

# =========================
# OTP UTILITIES
# =========================

def _generate_otp():
    """Generate a cryptographically secure 6-digit OTP."""
    return str(secrets.randbelow(900000) + 100000)

def _build_otp_email_html(otp_code):
    """Build a professional HTML email body for the OTP."""
    return f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 480px; margin: 0 auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08);">
        <div style="background: linear-gradient(135deg, #3F4FCF 0%, #7D5FFF 100%); padding: 32px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 800; letter-spacing: 1px;">MAIDCONNECT</h1>
            <p style="color: rgba(255,255,255,0.8); margin: 8px 0 0; font-size: 13px;">Secure Verification</p>
        </div>
        <div style="padding: 40px 32px; text-align: center;">
            <p style="color: #555; font-size: 15px; margin: 0 0 24px;">Use the code below to verify your identity:</p>
            <div style="background: #F4F5FF; border: 2px dashed #3F4FCF; border-radius: 12px; padding: 20px; margin: 0 auto 24px; display: inline-block;">
                <span style="font-size: 36px; font-weight: 900; letter-spacing: 12px; color: #3F4FCF; font-family: 'Courier New', monospace;">{otp_code}</span>
            </div>
            <p style="color: #999; font-size: 13px; margin: 0;">This code is valid for <strong style="color: #3F4FCF;">5 minutes</strong>.</p>
            <p style="color: #ccc; font-size: 12px; margin: 16px 0 0;">If you didn't request this code, please ignore this email.</p>
        </div>
        <div style="background: #FAFAFA; padding: 16px; text-align: center; border-top: 1px solid #f0f0f0;">
            <p style="color: #bbb; font-size: 11px; margin: 0;">&copy; 2026 MaidConnect. All rights reserved.</p>
        </div>
    </div>
    """

def _send_otp_email(contact, otp_code):
    """Send OTP via email. Returns True on success, False on failure."""
    html_body = _build_otp_email_html(otp_code)
    email = EmailMessage(
        subject='Your MaidConnect OTP Verification Code',
        body=html_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[contact],
    )
    email.content_subtype = 'html'
    try:
        email.send(fail_silently=False)
        logger.info(f"[OTP] Email sent successfully to {contact}")
        return True, "Success"
    except Exception as e:
        logger.error(f"[OTP] Email send FAILED for {contact}: {e}")
        return False, str(e)

# =========================
# OTP API ENDPOINTS
# =========================

@csrf_exempt
def send_otp(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)
        contact = (data.get('email') or data.get('contact') or '').strip()
    except (json.JSONDecodeError, Exception):
        contact = (request.POST.get('email') or request.POST.get('contact') or '').strip()

    if not contact or '@' not in contact:
        return JsonResponse({"error": "A valid email address is required"}, status=400)

    # Rate limiting (30s)
    last_otp = OTPVerification.objects.filter(contact=contact).order_by('-created_at').first()
    if last_otp and (timezone.now() - last_otp.created_at).total_seconds() < 30:
        wait = int(30 - (timezone.now() - last_otp.created_at).total_seconds())
        return JsonResponse({"error": f"Please wait {wait} seconds before resending"}, status=429)

    OTPVerification.objects.filter(contact=contact, is_used=False).update(is_used=True)
    otp_code = _generate_otp()
    
    success, error_msg = _send_otp_email(contact, otp_code)
    if success:
        OTPVerification.objects.create(
            contact=contact,
            otp=otp_code,
            delivery_method='email',
            expires_at=timezone.now() + timedelta(minutes=5)
        )
        return JsonResponse({"message": "OTP sent successfully", "delivery_method": "email"})
    
    # Detailed error for debugging in DEBUG=True mode
    msg = f"Failed to send email: {error_msg}" if settings.DEBUG else "Failed to send email. Try again."
    return JsonResponse({"error": msg}, status=500)

@csrf_exempt
def verify_otp_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)
        contact = (data.get('email') or data.get('contact') or '').strip()
        otp = data.get('otp', '').strip()
    except (json.JSONDecodeError, Exception):
        contact = (request.POST.get('email') or request.POST.get('contact') or '').strip()
        otp = request.POST.get('otp', '').strip()

    otp_record = OTPVerification.objects.filter(contact=contact, is_used=False).order_by('-created_at').first()
    if not otp_record or otp_record.is_expired():
        return JsonResponse({"error": "OTP expired or not found."}, status=400)

    if otp_record.otp == otp:
        OTPVerification.objects.filter(contact=contact, is_used=False).update(is_used=True)
        request.session['verified_contact'] = contact
        request.session.modified = True
        return JsonResponse({"message": "Verified successfully", "success": True})
    
    otp_record.attempts += 1
    otp_record.save()
    return JsonResponse({"error": "Invalid OTP code."}, status=400)

@csrf_exempt
def resend_otp(request):
    return send_otp(request) # Reuse logic

# =========================
# GENERAL PAGES
# =========================

def home(request):
    # Fetch recent top reviews for dynamic testimonial section
    recent_reviews = Review.objects.filter(rating__gte=4).select_related('user', 'worker__user').order_by('-created_at')[:5]

    return render(request, 'home.html', {
        'categories': Category.objects.all(),
        'top_workers': WorkerProfile.objects.filter(availability='available', is_verified=True).order_by('-rating_avg')[:8],
        'platform_workers': WorkerProfile.objects.filter(is_verified=True).count(),
        'platform_bookings': Booking.objects.count(),
        'platform_users': CustomUser.objects.filter(role='user', is_active=True).count(),
        'bookings_completed': Booking.objects.filter(status__in=['completed', 'paid']).count(),
        'reviews': recent_reviews,
    })

def about(request): return render(request, 'about.html')
def services(request): return render(request, 'services.html', {'categories': Category.objects.all()})
def register_choice(request): return render(request, 'register_choice.html')
def privacy_policy(request): return render(request, 'privacy_policy.html')
def terms_of_service(request): return render(request, 'terms_of_service.html')

# =========================
# AUTHENTICATION
# =========================

def login_view(request):
    if request.method == "POST":
        identifier = request.POST.get("email", "").strip()
        password = request.POST.get("password")
        
        # 1. Look for user by email OR username (case-insensitive)
        user_obj = CustomUser.objects.filter(email__iexact=identifier).first() or \
                   CustomUser.objects.filter(username__iexact=identifier).first()
        
        if user_obj:
            if user_obj.is_blocked:
                messages.error(request, "Your account has been blocked due to suspicious activity.")
                return render(request, 'login.html')
            
            # 2. Authenticate using the actual username found in DB
            user = authenticate(request, username=user_obj.username, password=password)
            
            if user:
                login(request, user)
                if not request.session.session_key: 
                    request.session.create()
                
                user.session_key = request.session.session_key
                user.save()
                
                # ── Track login time for "Login Offer" (10-min window, once a day) ──
                today = timezone.localtime(timezone.now()).date()
                offer_used_today = Booking.objects.filter(
                    user=user,
                    created_at__date=today,
                    offer_applied=True,
                    status__in=['completed', 'paid', 'accepted']
                ).exists()
                
                if not offer_used_today:
                    request.session['login_time'] = timezone.now().isoformat()
                    request.session['offer_active'] = True
                else:
                    request.session['offer_active'] = False
                request.session.modified = True
                
                if user.role == "admin" or user.is_superuser: 
                    return redirect('admin_dashboard')
                
                return redirect('worker_home' if user.role == 'worker' else 'user_home')
        
        # If we reach here, either user_obj was None or authenticate failed
        messages.error(request, "Invalid credentials. Please check your username/email and password.")
        
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        user = CustomUser.objects.filter(email=email).first()
        if user:
            otp_code = _generate_otp()
            if _send_otp_email(email, otp_code):
                OTPVerification.objects.filter(contact=email, is_used=False).update(is_used=True)
                OTPVerification.objects.create(
                    contact=email,
                    otp=otp_code,
                    delivery_method='email',
                    expires_at=timezone.now() + timedelta(minutes=10)
                )
                request.session['reset_email'] = email
                messages.success(request, f"A 6-digit OTP has been sent to {email}")
                return redirect('verify_reset_otp')
            else:
                messages.error(request, "Failed to send OTP. Please try again.")
        else:
            messages.error(request, "Account with this email does not exist.")
    return render(request, 'forgot_password.html')

def verify_reset_otp(request):
    email = request.session.get('reset_email')
    if not email:
        return redirect('forgot_password')
    
    if request.method == "POST":
        otp = request.POST.get('otp', '').strip()
        otp_record = OTPVerification.objects.filter(contact=email, is_used=False).order_by('-created_at').first()
        
        if otp_record and not otp_record.is_expired() and otp_record.otp == otp:
            otp_record.is_used = True
            otp_record.save()
            request.session['otp_verified'] = True
            messages.success(request, "OTP Verified! You can now reset your password.")
            return redirect('reset_password')
        else:
            messages.error(request, "Invalid or expired OTP.")
            
    return render(request, 'verify_reset_otp.html', {'email': email})

def reset_password(request):
    email = request.session.get('reset_email')
    is_verified = request.session.get('otp_verified')
    
    if not email or not is_verified:
        return redirect('forgot_password')
        
    if request.method == "POST":
        p1 = request.POST.get('password')
        p2 = request.POST.get('confirm_password')
        if p1 == p2:
            user = CustomUser.objects.get(email=email)
            user.set_password(p1)
            user.save()
            # Cleanup session
            del request.session['reset_email']
            del request.session['otp_verified']
            messages.success(request, "Password reset successful! Please login.")
            return redirect('login')
        else:
            messages.error(request, "Passwords do not match.")
            
    return render(request, 'reset_password.html')

# =========================
# REGISTRATION
# =========================

def user_register(request):
    form = UserRegisterForm(request.POST or None)
    if request.method == "POST":
        if not request.session.get('verified_contact'):
            messages.error(request, "Please verify your email via OTP first.")
            return redirect('register_choice')

        if form.is_valid():
            email = form.cleaned_data.get('email')
            username = form.cleaned_data.get('username')

            if request.session.get('verified_contact') != email:
                messages.error(request, "Please verify your email via OTP first.")
            else:
                # ── Pre-save duplicate checks ──
                if CustomUser.objects.filter(username=username).exists():
                    messages.error(request, f"The username '{username}' is already taken. Please choose a different one.")
                    return render(request, 'user_register.html', {'form': form})

                if CustomUser.objects.filter(email=email).exists():
                    messages.error(request, "An account with this email already exists. Please login instead.")
                    return render(request, 'user_register.html', {'form': form})

                try:
                    user = form.save(commit=False)
                    user.role, user.is_otp_verified = 'user', True
                    user.save()
                    UserProfile.objects.create(
                        user=user,
                        phone=form.cleaned_data.get('phone'),
                        address_line1=form.cleaned_data.get('address_line1'),
                        address_line2=form.cleaned_data.get('address_line2'),
                        city=form.cleaned_data.get('city'),
                        state=form.cleaned_data.get('state'),
                        pincode=form.cleaned_data.get('pincode')
                    )
                    if 'verified_contact' in request.session:
                        del request.session['verified_contact']
                    messages.success(request, "Registration successful! You can now login.")
                    return redirect('login')
                except Exception as e:
                    logger.error(f"[User Register] Save failed: {e}")
                    messages.error(request, "Registration failed. The username or email may already exist. Please try again.")
    return render(request, 'user_register.html', {'form': form})


def worker_register(request):
    u_form = UserRegisterForm(request.POST or None)
    w_form = WorkerProfileForm(request.POST or None, request.FILES or None)

    if request.method == "POST":
        if not request.session.get('verified_contact'):
            messages.error(request, "Please verify your email via OTP first.")
            return redirect('register_choice')

        if u_form.is_valid() and w_form.is_valid():
            email = u_form.cleaned_data.get('email')
            username = u_form.cleaned_data.get('username')

            if request.session.get('verified_contact') != email:
                messages.error(request, "Verify email first.")
            else:
                # ── Pre-save duplicate checks ──
                if CustomUser.objects.filter(username=username).exists():
                    messages.error(request, f"The username '{username}' is already taken. Please choose a different one.")
                    return render(request, 'worker_register.html', {
                        'user_form': u_form, 'worker_form': w_form, 'categories': Category.objects.all()
                    })

                if CustomUser.objects.filter(email=email).exists():
                    messages.error(request, f"An account with the email '{email}' already exists. Please login instead.")
                    return render(request, 'worker_register.html', {
                        'user_form': u_form, 'worker_form': w_form, 'categories': Category.objects.all()
                    })

                try:
                    user = u_form.save(commit=False)
                    user.role, user.is_otp_verified = 'worker', True
                    user.set_password(u_form.cleaned_data.get('password'))
                    user.save()

                    # Create UserProfile
                    UserProfile.objects.create(
                        user=user,
                        phone=u_form.cleaned_data.get('phone'),
                        address_line1=u_form.cleaned_data.get('address_line1'),
                        address_line2=u_form.cleaned_data.get('address_line2'),
                        city=u_form.cleaned_data.get('city'),
                        state=u_form.cleaned_data.get('state'),
                        pincode=u_form.cleaned_data.get('pincode')
                    )

                    # Ensure mobile field is populated from phone
                    worker = w_form.save(commit=False)
                    worker.user = user
                    worker.kyc_status = 'pending'
                    worker.kyc_submitted_at = timezone.now()
                    if not worker.mobile:
                        worker.mobile = u_form.cleaned_data.get('phone')
                    worker.save()
                    w_form.save_m2m()

                    # Cleanup session
                    if 'verified_contact' in request.session:
                        del request.session['verified_contact']

                    messages.success(request, "Registration successful! Your partner account is pending verification. Please login.")
                    return redirect('login')

                except Exception as e:
                    logger.error(f"[Worker Register] Save failed: {e}")
                    messages.error(request, "Registration failed due to a conflict. The username or email may already exist. Please try again with different details.")
        else:
            # Display form validation errors
            for field, errors in u_form.errors.items():
                for error in errors: messages.error(request, f"{error}")
            for field, errors in w_form.errors.items():
                for error in errors: messages.error(request, f"{error}")

    return render(request, 'worker_register.html', {
        'user_form': u_form,
        'worker_form': w_form,
        'categories': Category.objects.all()
    })

from datetime import date, datetime, timedelta
from django.db.models import Sum, Count, Q
from .models import (
    Category, WorkerProfile, Booking, Payment, Review, 
    Complaint, Notification, CustomUser, UserProfile,
    Offer, SmartOfferSettings
)

# ── Smart Offer Helpers ──

def get_user_segment(user):
    """Determine if user is 'new', 'inactive', or 'regular'."""
    booking_count = Booking.objects.filter(user=user).count()
    if booking_count == 0:
        return 'new'
    
    settings = SmartOfferSettings.objects.first() or SmartOfferSettings.objects.create()
    threshold_date = timezone.now() - timedelta(days=settings.inactive_days_threshold)
    has_recent_booking = Booking.objects.filter(user=user, created_at__gte=threshold_date).exists()
    
    if not has_recent_booking:
        return 'inactive'
    
    return 'regular'

def get_active_smart_offer(user):
    """Retrieve the best applicable smart offer for the user."""
    segment = get_user_segment(user)
    offers = Offer.objects.filter(
        offer_type='smart',
        is_active=True,
        user_type__in=[segment, 'general']
    ).order_by('-discount')
    
    for offer in offers:
        # Check overall usage limit
        if offer.usage_limit and offer.usage_count >= offer.usage_limit:
            continue
        # Check valid dates
        now = timezone.now()
        if offer.valid_from and now < offer.valid_from: continue
        if offer.valid_to and now > offer.valid_to: continue
        
        return offer
    return None

# =========================
# DASHBOARDS
# =========================


@never_cache
@login_required
@user_required
def user_home(request):
    popular_workers = WorkerProfile.objects.filter(kyc_status='approved', is_verified=True)[:4]
    categories = Category.objects.all()
    now = timezone.now()
    today = timezone.localtime(now).date()

    # 1. ── Check Daily Limit ──
    used_booking = Booking.objects.filter(
        user=request.user,
        created_at__date=today,
        offer_applied=True,
        status__in=['completed', 'paid', 'accepted']
    ).exists()

    # ── Smart Offer Activation ──
    offer_applied, login_offer_secs, active_smart_offer = _activate_smart_offer(request)
    
    # Check if we should show the popup (only once per session)
    show_offer_popup = False
    if offer_applied and not request.session.get('offer_popup_shown', False):
        show_offer_popup = True
        request.session['offer_popup_shown'] = True
        request.session.modified = True

    # Regular UI Offers (Marketing Grid)
    priority_types = ['general']
    segment = get_user_segment(request.user)
    if segment == 'new':
        priority_types.insert(0, 'first_time')
    if now.weekday() >= 5:
        priority_types.insert(0, 'weekend')

    ui_offers = Offer.objects.filter(
        offer_type__in=priority_types,
        is_active=True,
        valid_from__lte=now,
        valid_to__gte=now
    ).order_by('offer_type')[:4]

    return render(request, 'user_home.html', {
        'popular_workers': popular_workers,
        'offers': ui_offers,
        'categories': categories,
        'offer_applied': offer_applied,
        'login_offer_secs': login_offer_secs,
        'offer_used_today': used_booking,
        'show_offer_popup': show_offer_popup,
        'active_smart_offer': active_smart_offer,
    })

@never_cache
@login_required
@user_required
def user_dashboard(request):
    # get_or_create prevents 404 crash for users without a profile object
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    bookings = Booking.objects.filter(user=request.user).order_by('-booking_date')
    total_spent = Payment.objects.filter(user=request.user, status='successful').aggregate(Sum('amount'))['amount__sum'] or 0
    
    # ── Login Offer logic ──
    offer_applied, login_offer_secs, _ = _activate_smart_offer(request)
    
    today = timezone.localtime(timezone.now()).date()
    offer_used_today = Booking.objects.filter(
        user=request.user,
        created_at__date=today,
        offer_applied=True,
        status__in=['completed', 'paid', 'accepted']
    ).exists()

    return render(request, 'user_dashboard.html', {
        'profile': profile,
        'bookings': bookings,
        'total_spent': total_spent,
        'active_count': bookings.filter(status__in=['pending','accepted','in_progress']).count(),
        'completed_count': bookings.filter(status__in=['completed', 'paid']).count(),
        'offer_applied': offer_applied,
        'login_offer_secs': login_offer_secs,
        'offer_used_today': offer_used_today,
    })

@never_cache
@login_required
@worker_required
def worker_dashboard(request):
    worker = get_object_or_404(WorkerProfile, user=request.user)
    bookings = Booking.objects.filter(worker=worker).order_by('-booking_date')
    
    # Calculate Stats for the top cards
    requested_count = bookings.filter(status='pending').count()
    ongoing_count = bookings.filter(status__in=['accepted', 'in_progress']).count()
    done_count = bookings.filter(status__in=['completed', 'paid']).count()
    
    # Earnings breakdown
    total_earnings = bookings.filter(status__in=['completed', 'paid']).aggregate(Sum('total_price'))['total_price__sum'] or 0
    pending_earnings = bookings.filter(status__in=['pending', 'accepted', 'in_progress']).aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    # 📊 Chart Data: Earnings Trend (Last 7 Days)
    seven_days_ago = timezone.now().date() - timedelta(days=6)
    daily_earnings = bookings.filter(status='paid', completed_at__date__gte=seven_days_ago)\
        .values('completed_at__date')\
        .annotate(total=Sum('total_price'))\
        .order_by('completed_at__date')
    
    earnings_labels = [(seven_days_ago + timedelta(days=i)).strftime('%a') for i in range(7)]
    earnings_data = [0] * 7
    for d in daily_earnings:
        idx = (d['completed_at__date'] - seven_days_ago).days
        if 0 <= idx < 7: earnings_data[idx] = float(d['total'])

    # 📊 Chart Data: Status Distribution
    status_counts = bookings.values('status').annotate(count=Count('status'))
    status_map = {s['status']: s['count'] for s in status_counts}
    
    # Standardized status list for consistent chart colors
    standard_statuses = ['pending', 'accepted', 'in_progress', 'completed', 'paid', 'cancelled']
    status_labels = [s.replace('_', ' ').title() for s in standard_statuses]
    status_values = [status_map.get(s, 0) for s in standard_statuses]

    # Calculate Avg Rating
    from django.db.models import Avg
    avg_rating = worker.reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    avg_rating = round(avg_rating, 1)

    # Convert to JSON for safe JS usage
    import json
    return render(request, 'worker_dashboard.html', {
        'worker': worker,
        'bookings': bookings,
        'requested_count': requested_count,
        'ongoing_count': ongoing_count,
        'done_count': done_count,
        'total_earnings': total_earnings,
        'pending_earnings': pending_earnings,
        'earnings_labels_json': json.dumps(earnings_labels),
        'earnings_data_json': json.dumps(earnings_data),
        'status_labels_json': json.dumps(status_labels),
        'status_values_json': json.dumps(status_values),
        'avg_rating': avg_rating,
    })

@never_cache
@login_required
@worker_required
def worker_earnings(request):
    worker = get_object_or_404(WorkerProfile, user=request.user)
    paid_bookings = Booking.objects.filter(worker=worker, status='paid').order_by('-completed_at')
    
    total_earnings = paid_bookings.aggregate(Sum('total_price'))['total_price__sum'] or 0
    pending_earnings = Booking.objects.filter(worker=worker, status__in=['accepted', 'in_progress', 'completed']).aggregate(Sum('total_price'))['total_price__sum'] or 0
    
    return render(request, 'worker_earnings.html', {
        'worker': worker,
        'paid_bookings': paid_bookings,
        'total_earnings': total_earnings,
        'pending_earnings': pending_earnings
    })

@never_cache
@login_required
@worker_required
def worker_jobs(request):
    worker = get_object_or_404(WorkerProfile, user=request.user)
    bookings = Booking.objects.filter(worker=worker).order_by('-created_at')
    
    # Filters
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
        
    date_filter = request.GET.get('date')
    if date_filter:
        bookings = bookings.filter(booking_date=date_filter)
        
    client_name = request.GET.get('client_name', '').strip()
    if client_name:
        bookings = bookings.filter(user__first_name__icontains=client_name) | bookings.filter(user__last_name__icontains=client_name)
        
    return render(request, 'worker_jobs.html', {
        'worker': worker,
        'bookings': bookings,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'client_name': client_name
    })

# =========================
# WORKER LIST & DETAIL
# =========================

def worker_list(request):
    # Show all verified + approved workers (regardless of availability so user can still view profile)
    workers = WorkerProfile.objects.filter(kyc_status='approved', is_verified=True)
    
    # Category Filter (Supports both ID from dropdown and Name from links)
    cat_query = request.GET.get('category')
    if cat_query:
        if cat_query.isdigit():
            workers = workers.filter(categories__id=cat_query)
        else:
            workers = workers.filter(categories__name__icontains=cat_query)
    
    # Location Filter
    city = request.GET.get('city')
    if city: workers = workers.filter(city__icontains=city)
    
    pincode = request.GET.get('pincode')
    if pincode: workers = workers.filter(pincode=pincode)
    
    # Search
    search = request.GET.get('search') or request.GET.get('q')
    if search:
        workers = workers.filter(
            Q(skills__icontains=search) | 
            Q(user__first_name__icontains=search) | 
            Q(user__last_name__icontains=search) |
            Q(categories__name__icontains=search)
        ).distinct()
    
    # Get distinct cities for filter dropdown
    cities = WorkerProfile.objects.values_list('city', flat=True).distinct()
    
    # Encode IDs for the template
    for w in workers:
        w.encoded_id = base64.urlsafe_b64encode(str(w.id).encode()).decode()
    
    # Fetch recent top reviews for dynamic testimonial section
    recent_reviews = Review.objects.filter(rating__gte=4).select_related('user', 'worker__user').order_by('-created_at')[:5]
    
    return render(request, 'worker_list.html', {
        'workers': workers, 
        'categories': Category.objects.all(),
        'selected_category': cat_query,
        'selected_city': city,
        'selected_pincode': pincode,
        'cities': cities,
        'reviews': recent_reviews,
    })

def worker_detail(request, worker_id):
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    worker.encoded_id = base64.urlsafe_b64encode(str(worker.id).encode()).decode()
    return render(request, 'worker_detail.html', {'worker': worker})

# =========================
# BOOKING SYSTEM
# =========================

_LOGIN_OFFER_WINDOW = 600  # 10 minutes in seconds
_LOGIN_OFFER_DISCOUNT = 10  # percent

def _get_login_offer_secs(request):
    """
    Returns remaining seconds for the personalized promotional window.
    Supports dynamic durations per offer.
    """
    login_time_str = request.session.get('login_time')
    duration_mins = request.session.get('offer_duration', 10) # Default 10 mins
    
    if not login_time_str:
        return 0
        
    try:
        from datetime import datetime
        login_time = datetime.fromisoformat(login_time_str)
        if login_time.tzinfo is None:
            login_time = timezone.make_aware(login_time)
            
        now = timezone.now()
        elapsed = (now - login_time).total_seconds()
        remaining = int((duration_mins * 60) - elapsed)
        return max(0, remaining)
    except Exception as e:
        return 0

def _activate_smart_offer(request):
    """Helper to check/activate smart offer for a user session."""
    now = timezone.now()
    today = timezone.localtime(now).date()
    
    used_booking = Booking.objects.filter(
        user=request.user,
        created_at__date=today,
        offer_applied=True,
        status__in=['completed', 'paid', 'accepted']
    ).exists()
    
    if used_booking:
        return False, 0, None

    settings = SmartOfferSettings.objects.first() or SmartOfferSettings.objects.create()
    if not settings.is_enabled:
        return False, 0, None

    login_offer_secs = _get_login_offer_secs(request)
    if login_offer_secs <= 0:
        # Clear stale session data to allow fresh activation
        keys_to_clear = ['login_time', 'offer_active', 'offer_id', 'offer_duration', 'offer_pct', 'offer_label', 'offer_popup_shown']
        for key in keys_to_clear:
            if key in request.session: del request.session[key]
        
        segment = get_user_segment(request.user)
        offer = get_active_smart_offer(request.user)
        if offer:
            request.session['login_time'] = now.isoformat()
            request.session['offer_active'] = True
            request.session['offer_id'] = offer.id
            request.session['offer_duration'] = offer.duration_minutes
            request.session['offer_pct'] = offer.discount
            request.session['offer_type'] = segment # Store segment/type in session
            
            # Map labels
            labels = {'new': 'Welcome Offer', 'regular': 'Special Offer', 'inactive': 'We Miss You'}
            request.session['offer_label'] = labels.get(segment, 'Exclusive Offer')
            
            request.session.modified = True
            return True, _get_login_offer_secs(request), offer
    
    # Check if already active
    if request.session.get('offer_active') and login_offer_secs > 0:
        offer_id = request.session.get('offer_id')
        offer = Offer.objects.filter(id=offer_id).first() if offer_id else None
        return True, login_offer_secs, offer

    return False, 0, None

@login_required
def booking_config(request, worker_id):
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    
    offer_applied, login_offer_secs, active_offer = _activate_smart_offer(request)
    
    today = timezone.localtime(timezone.now()).date()
    used_booking = Booking.objects.filter(
        user=request.user,
        created_at__date=today,
        offer_applied=True,
        status__in=['completed', 'paid', 'accepted']
    ).exists()

    return render(request, 'booking_config.html', {
        'worker': worker,
        'today': today,
        'login_offer_secs': login_offer_secs,
        'offer_used_today': used_booking,
        'offer_applied': offer_applied,
        'active_offer': active_offer,
    })

@csrf_exempt
@login_required
def book_service(request):
    # Always return JSON — never redirect for this API endpoint
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'You must be logged in to book a service.'}, status=401)
    
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
    
    try:
        w_id = request.POST.get('worker_id')
        service_type = request.POST.get('service_type')
        address = request.POST.get('address')
        booking_date = request.POST.get('date')
        start_time = request.POST.get('time')

        # Validate required fields
        if not w_id:
            return JsonResponse({'status': 'error', 'message': 'Worker ID is missing.'}, status=400)
        if not service_type:
            return JsonResponse({'status': 'error', 'message': 'Please select a service type.'}, status=400)
        if not address:
            return JsonResponse({'status': 'error', 'message': 'Service address is required.'}, status=400)
        if not booking_date:
            return JsonResponse({'status': 'error', 'message': 'Booking date is required.'}, status=400)
        if not start_time:
            return JsonResponse({'status': 'error', 'message': 'Start time is required.'}, status=400)

        worker = get_object_or_404(WorkerProfile, id=w_id)
        
        # Security Check: Ensure worker is not already busy
        if worker.status == 'busy':
            return JsonResponse({'status': 'error', 'message': 'This worker is currently busy. Please select another.'}, status=400)
        
        # ── Offer Processing Logic ──
        offer_id = request.POST.get('offer_id')
        apply_login_offer = request.POST.get('apply_login_offer') == 'true'
        total_price = worker.price_per_day
        applied_offer = None
        discount_label = None

        today = timezone.localtime(timezone.now()).date()

        # Enforce "one offer per day" rule across all offers
        if apply_login_offer or offer_id:
            used_booking = Booking.objects.filter(
                user=request.user,
                created_at__date=today,
                offer_applied=True,
                status__in=['completed', 'paid', 'accepted']
            ).exists()
            
            if used_booking:
                return JsonResponse({'status': 'error', 'message': "Today's offer already used."}, status=400)

        # 1. Smart Offer / Login Offer (session-activated)
        if apply_login_offer:
            login_secs = _get_login_offer_secs(request)
            if login_secs > 0:
                pct = request.session.get('offer_pct', 10)
                db_offer_id = request.session.get('offer_id')
                
                discount = (total_price * pct) / 100
                total_price -= discount
                discount_label = f'Special Offer ({pct}% off)'
                
                # Update DB if it was a tracked smart offer
                if db_offer_id:
                    try:
                        off = Offer.objects.get(id=db_offer_id)
                        off.usage_count += 1
                        off.save()
                        applied_offer = off
                    except Offer.DoesNotExist:
                        pass

                # Clear session state
                request.session.pop('login_time', None)
                request.session.pop('offer_id', None)
                request.session['offer_active'] = False
                request.session.modified = True

        # 2. Manual/Regular DB offer (if any, e.g. from a list)
        elif offer_id:
            try:
                offer = Offer.objects.get(id=offer_id, is_active=True)
                now = timezone.now()
                
                if (not offer.valid_from or now >= offer.valid_from) and \
                   (not offer.valid_to or now <= offer.valid_to) and \
                   (not offer.usage_limit or offer.usage_count < offer.usage_limit) and \
                   (not offer.min_order_amount or total_price >= offer.min_order_amount):
                    
                    discount = (total_price * offer.discount) / 100
                    if offer.max_discount_amount and discount > offer.max_discount_amount:
                        discount = offer.max_discount_amount
                    
                    total_price -= discount
                    offer.usage_count += 1
                    offer.save()
                    applied_offer = offer
            except Offer.DoesNotExist:
                pass

        booking = Booking.objects.create(
            user=request.user,
            worker=worker,
            service_type=service_type,
            service_address=address,
            start_time=start_time,
            booking_date=booking_date,
            total_price=total_price,
            status='pending',
            offer_applied=bool(discount_label or applied_offer)
        )
        
        # Mark offer as used only AFTER successful booking
        if discount_label or applied_offer:
            request.user.last_offer_date = today
            request.user.save()

        # Update worker availability
        worker.status = 'busy'
        worker.save()

        # Notify worker
        create_notification(worker.user, f"New booking request from {request.user.first_name}! Check your dashboard.")
        
        try:
            from maidapp.utils import broadcast_status_update
            broadcast_status_update({
                'event': 'booking_created',
                'booking_id': booking.id,
                'status': 'pending',
                'user_id': request.user.id,
                'worker_id': worker.id
            })
        except Exception:
            pass  # Don't fail booking if WebSocket broadcast fails

        return JsonResponse({
            'status': 'success',
            'booking_id': booking.booking_id_str,
            'message': 'Booking created successfully!'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Booking failed: {str(e)}'}, status=500)

@login_required
@worker_required
def worker_home(request):
    """Landing page for workers."""
    worker = get_object_or_404(WorkerProfile, user=request.user)
    today = timezone.now().date()
    todays_bookings = Booking.objects.filter(worker=worker, booking_date__date=today)
    
    # For timeline, we want today's bookings PLUS any active future bookings
    from django.db.models import Q
    timeline_bookings = Booking.objects.filter(
        Q(worker=worker) & 
        (Q(booking_date__date=today) | Q(status__in=['pending', 'accepted', 'in_progress']))
    ).order_by('booking_date', 'start_time')
    
    # Calculate Today's Earnings
    todays_earned = todays_bookings.filter(
        status__in=['completed', 'paid']
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    daily_target = worker.price_per_day
    
    # Recent Feedback
    recent_reviews = Review.objects.filter(worker=worker).order_by('-created_at')[:3]
    
    return render(request, 'worker_home.html', {
        'worker': worker,
        'todays_bookings': timeline_bookings,
        'todays_earned': todays_earned,
        'daily_target': daily_target,
        'recent_reviews': recent_reviews,
        'today_date': today
    })

@login_required
@worker_required
def accept_booking(request, booking_id):
    """Worker accepts a pending booking."""
    booking = get_object_or_404(Booking, id=booking_id)
    worker = get_object_or_404(WorkerProfile, user=request.user)
    
    if booking.worker != worker:
        messages.error(request, "Unauthorized access.")
        return redirect('worker_home')

    booking.status = "accepted"
    booking.accepted_at = timezone.now()
    booking.save()
    
    messages.success(request, "Booking accepted! Check your schedule.")
    return redirect('worker_home')

@login_required
@worker_required
def reject_booking(request, booking_id):
    """Worker rejects a pending booking."""
    booking = get_object_or_404(Booking, id=booking_id)
    worker = get_object_or_404(WorkerProfile, user=request.user)
    
    if booking.worker != worker:
        messages.error(request, "Unauthorized access.")
        return redirect('worker_home')

    booking.status = "rejected"
    booking.save()
    
    # Re-enable worker availability if they were busy
    worker.status = "available"
    worker.save()
    
    messages.warning(request, "Booking rejected.")
    return redirect('worker_home')

@login_required
@worker_required
def start_job(request, booking_id):
    """Worker starts an accepted job."""
    booking = get_object_or_404(Booking, id=booking_id)
    worker = get_object_or_404(WorkerProfile, user=request.user)
    
    if booking.worker != worker:
        messages.error(request, "Unauthorized access.")
        return redirect('worker_home')

    if booking.status != 'accepted':
        messages.error(request, "Only accepted bookings can be started.")
        return redirect('worker_home')

    booking.status = "in_progress"
    booking.save()
    
    messages.success(request, "Job started! Good luck.")
    return redirect('worker_home')

@login_required
@worker_required
def complete_job(request, booking_id):
    """Worker completes an in-progress job."""
    booking = get_object_or_404(Booking, id=booking_id)
    worker = get_object_or_404(WorkerProfile, user=request.user)
    
    if booking.worker != worker:
        messages.error(request, "Unauthorized access.")
        return redirect('worker_home')

    if booking.status != 'in_progress':
        messages.error(request, "Only in-progress bookings can be completed.")
        return redirect('worker_home')

    booking.status = "completed"
    booking.completed_at = timezone.now()
    booking.save()
    
    # Free up the worker
    worker.status = "available"
    worker.save()
    
    messages.success(request, "Great job! Booking marked as completed.")
    return redirect('worker_home')

@login_required
@worker_required
def toggle_availability(request):
    """Toggle worker's online/offline status."""
    worker = get_object_or_404(WorkerProfile, user=request.user)
    worker.is_online = not worker.is_online
    worker.save()
    
    status_text = "online" if worker.is_online else "offline"
    return JsonResponse({"status": status_text, "is_online": worker.is_online})

@login_required
@worker_required
def api_worker_bookings(request):
    """API endpoint for fetching today's bookings + summary stats."""
    worker = get_object_or_404(WorkerProfile, user=request.user)
    today = timezone.now().date()
    
    from django.db.models import Q
    todays_bookings = Booking.objects.filter(worker=worker, booking_date__date=today)
    timeline_bookings = Booking.objects.filter(
        Q(worker=worker) & 
        (Q(booking_date__date=today) | Q(status__in=['pending', 'accepted', 'in_progress']))
    ).order_by('booking_date', 'start_time')

    data = []
    for b in timeline_bookings:
        time_str = b.start_time.strftime("%I:%M %p") if b.start_time else '--:--'
        if b.booking_date.date() != today:
            time_str = f"{b.booking_date.strftime('%b %d')} {time_str}"
            
        data.append({
            'id': b.id,
            'customer': b.user.get_full_name() or b.user.username,
            'time': time_str,
            'service': b.service_type,
            'status': b.status,
        })

    # Summary stats for dynamic cards
    earned = todays_bookings.filter(status__in=['completed', 'paid']).aggregate(
        total=Sum('total_price'))['total'] or 0
        
    active_count = timeline_bookings.filter(status__in=['pending', 'accepted', 'in_progress']).count()
    
    next_booking = timeline_bookings.filter(
        status__in=['pending', 'accepted', 'in_progress']
    ).first()
    next_slot = next_booking.start_time.strftime("%I:%M %p") if (next_booking and next_booking.start_time) else '--:--'
    if next_booking and next_booking.booking_date.date() != today:
        next_slot = f"{next_booking.booking_date.strftime('%b %d')} {next_slot}"

    daily_target = worker.price_per_day
    progress = 0
    if daily_target > 0:
        progress = (float(earned) / daily_target) * 100
        if progress > 100: progress = 100

    return JsonResponse({
        'bookings': data,
        'summary': {
            'earned': float(earned),
            'active_count': active_count,
            'next_slot': next_slot,
            'daily_target': daily_target,
            'progress': progress,
        }
    })

@login_required
@worker_required
def api_worker_jobs_list(request):
    """API endpoint for fetching all bookings for the worker."""
    worker = get_object_or_404(WorkerProfile, user=request.user)
    bookings = Booking.objects.filter(worker=worker).order_by('-booking_date', '-start_time')
    
    data = []
    now = timezone.now()
    for b in bookings:
        # Urgency Check (within 1 hour of start time)
        is_urgent = False
        if b.start_time and b.booking_date.date() == now.date():
            from datetime import datetime, time, combine
            job_time = combine(now.date(), b.start_time)
            # Use timezone aware comparison
            job_time = timezone.make_aware(job_time, timezone.get_current_timezone())
            time_diff = (job_time - now).total_seconds()
            if 0 < time_diff < 3600:
                is_urgent = True

        data.append({
            'id': b.id,
            'booking_id_str': b.booking_id_str,
            'customer': b.user.get_full_name() or b.user.username,
            'address': b.service_address,
            'price': str(b.total_price),
            'time': b.start_time.strftime("%I:%M %p") if b.start_time else "N/A",
            'date': b.booking_date.strftime("%Y-%m-%d"),
            'service': b.service_type,
            'status': b.status,
            'is_new': b.status == 'pending',
            'is_urgent': is_urgent
        })
    return JsonResponse({'jobs': data})

@login_required
@user_required
def instant_book(request):
    """One-click instant booking logic."""
    worker_id = request.GET.get('worker_id')
    if not worker_id:
        messages.error(request, "Worker selection is required for instant booking.")
        return redirect('worker_list')
        
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    
    # Critical Availability Check
    if worker.status == 'busy':
        messages.warning(request, f"Sorry, {worker.user.first_name} just became busy. Please try another professional.")
        return redirect('worker_list')
        
    try:
        # Default category from worker
        service_type = worker.categories.first().name if worker.categories.exists() else "General Service"
        
        # Create confirmed booking
        booking = Booking.objects.create(
            user=request.user,
            worker=worker,
            service_type=service_type,
            service_address=request.user.userprofile.address if hasattr(request.user, 'userprofile') else "Address on file",
            start_time="09:00:00", # Default morning slot
            booking_date=timezone.now().date(),
            total_price=worker.price_per_day,
            status='accepted' # Instant book bypasses 'pending'
        )
        
        # Mark worker as busy immediately
        worker.status = 'busy'
        worker.save()
        
        # Notify
        create_notification(worker.user, f"⚡ INSTANT BOOK! You have a new confirmed booking from {request.user.first_name}.")
        
        # Instead of a blind redirect, show the success page with details
        return render(request, 'instant_success.html', {'booking': booking})
        
    except Exception as e:
        messages.error(request, f"Instant booking failed: {str(e)}")
        return redirect('worker_list')

@login_required
@user_required
def booking_new(request):
    workers = WorkerProfile.objects.filter(kyc_status='approved', is_verified=True, availability='available')
    preselected_worker = None
    
    worker_id_param = request.GET.get('worker_id')
    if worker_id_param:
        try:
            # Try parsing as a raw integer first (from new UI)
            worker_id = int(worker_id_param)
            preselected_worker = WorkerProfile.objects.filter(id=worker_id, kyc_status='approved', is_verified=True, status='available').first()
        except (ValueError, TypeError):
            # Fallback for older base64 encoded URLs
            try:
                worker_id = int(base64.urlsafe_b64decode(worker_id_param).decode())
                preselected_worker = WorkerProfile.objects.filter(id=worker_id, kyc_status='approved', is_verified=True, status='available').first()
            except Exception:
                preselected_worker = None
        
    now = timezone.now()
    active_offers = Offer.objects.filter(
        is_active=True,
        valid_from__lte=now,
        valid_to__gte=now
    )

    # ── Login Offer window ──
    today = timezone.localtime(timezone.now()).date()
    used_booking = Booking.objects.filter(
        user=request.user,
        created_at__date=today,
        offer_applied=True,
        status__in=['completed', 'paid', 'accepted']
    ).first()
    
    offer_used_today = used_booking is not None
    if offer_used_today:
        import logging
        logger = logging.getLogger('maidapp')
        logger.debug(f"Offer blocked for {request.user.username}: Triggered by Booking {used_booking.id}")

    # 🚀 AUTO-START OFFER TIMER: If not used today and (not set or expired)
    login_offer_secs = _get_login_offer_secs(request)
    if not offer_used_today and login_offer_secs <= 0:
        request.session['login_time'] = timezone.now().isoformat()
        request.session['offer_active'] = True
        request.session.modified = True
        login_offer_secs = _get_login_offer_secs(request)

    offer_applied = request.session.get('offer_active', False) and login_offer_secs > 0 and not offer_used_today
    
    return render(request, 'booking_new.html', {
        'workers': workers,
        'preselected_worker': preselected_worker,
        'selected_worker': preselected_worker,
        'offers': active_offers,
        'today': date.today(),
        'login_offer_secs': login_offer_secs,
        'offer_used_today': offer_used_today,
        'offer_applied': offer_applied,
    })

@login_required
@user_required
def edit_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if booking.status not in ['pending', 'accepted']:
        messages.error(request, 'This booking cannot be edited at this stage.')
        return redirect('user_dashboard')
        
    if request.method == 'POST':
        booking.service_type = request.POST.get('service_type')
        booking.booking_date = request.POST.get('date')
        booking.start_time = request.POST.get('time')
        booking.service_address = request.POST.get('address')
        booking.save()
        
        messages.success(request, f'Booking #{booking.booking_id_str} updated successfully!')
        return redirect('user_dashboard')
        
    return render(request, 'edit_booking.html', {'booking': booking, 'today': date.today()})

@login_required
@user_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if booking.status in ['pending', 'accepted']:
        booking.status = 'cancelled'
        booking.save()
        create_notification(booking.worker.user, f"Booking {booking.booking_id_str} was cancelled by the customer.")
        messages.success(request, f'Booking {booking.booking_id_str} has been cancelled.')
    else:
        messages.error(request, 'This booking cannot be cancelled.')
    return redirect('user_dashboard')


# =========================
# KYC / MANAGEMENT / ERROR
# =========================

@login_required
@worker_required
def submit_kyc(request):
    worker = get_object_or_404(WorkerProfile, user=request.user)
    if request.method == "POST":
        worker.aadhar_no = request.POST.get('aadhar_no')
        worker.pan_no = request.POST.get('pan_no')
        for f in ['aadhar_front', 'aadhar_back', 'pan_photo', 'selfie']:
            if request.FILES.get(f): setattr(worker, f, request.FILES.get(f))
        worker.kyc_status = 'pending'
        worker.kyc_submitted_at = timezone.now()
        worker.save()
        messages.success(request, "KYC documents submitted for verification.")
        return redirect('worker_dashboard')
    return render(request, 'worker_kyc.html', {'worker': worker})

@login_required
@admin_required
def manage_kyc(request):
    return render(request, 'admin/manage_kyc.html', {
        'pending_kyc': WorkerProfile.objects.filter(kyc_status='pending').order_by('-kyc_submitted_at'),
        'approved_kyc': WorkerProfile.objects.filter(kyc_status='approved').order_by('-kyc_verified_at'),
        'rejected_kyc': WorkerProfile.objects.filter(kyc_status='rejected'),
    })

@login_required
def approve_kyc(request, worker_id):
    try:
        if not request.user.is_superuser and request.user.role != 'admin':
            return JsonResponse({'status': 'error', 'message': 'Admin privileges required.'}, status=403)
            
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'Only POST requests are allowed.'}, status=405)
            
        worker = get_object_or_404(WorkerProfile, id=worker_id)
        worker.kyc_status = 'approved'
        worker.is_verified = True
        worker.verified = True
        worker.kyc_verified_at = timezone.now()
        worker.save()
        
        return JsonResponse({
            'status': 'success', 
            'message': f"KYC for {worker.user.username} approved successfully."
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f"Internal Error: {str(e)}"}, status=400)

@login_required
def reject_kyc(request, worker_id):
    try:
        if not request.user.is_superuser and request.user.role != 'admin':
            return JsonResponse({'status': 'error', 'message': 'Admin privileges required.'}, status=403)
            
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'Only POST requests are allowed.'}, status=405)
            
        worker = get_object_or_404(WorkerProfile, id=worker_id)
        
        # Parse reason from POST or JSON
        reason = request.POST.get('reason')
        if not reason and request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            reason = data.get('reason')
            
        if not reason:
            return JsonResponse({'status': 'error', 'message': 'Rejection reason is required.'}, status=400)
            
        worker.kyc_status = 'rejected'
        worker.is_verified = False
        worker.verified = False
        worker.rejection_reason = reason
        worker.save()
        
        return JsonResponse({
            'status': 'success', 
            'message': f"KYC for {worker.user.username} rejected."
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@admin_required
def block_worker(request, worker_id):
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    worker.user.is_blocked = True
    worker.user.save()
    messages.error(request, f"Worker {worker.user.username} has been blocked.")
    return redirect('manage_workers')
    
@login_required
def profile_view(request):
    """
    Unified route to show the user's profile summary based on their role.
    """
    if request.user.role == 'worker':
        worker = get_object_or_404(WorkerProfile, user=request.user)
        # Calculate earnings summary
        total_earnings = Booking.objects.filter(worker=worker, status='paid').aggregate(Sum('total_price'))['total_price__sum'] or 0
        pending_earnings = Booking.objects.filter(worker=worker, status__in=['accepted', 'in_progress', 'completed']).aggregate(Sum('total_price'))['total_price__sum'] or 0
        
        return render(request, 'worker_profile.html', {
            'worker': worker,
            'total_earnings': total_earnings,
            'pending_earnings': pending_earnings,
            'jobs_completed': worker.jobs_completed
        })
    elif request.user.role == 'user':
        # Calculate total bookings for user
        booking_count = Booking.objects.filter(user=request.user).count()
        return render(request, 'user_profile.html', {
            'booking_count': booking_count
        })
    elif request.user.is_superuser:
        return redirect('admin_dashboard')
    return redirect('home')

@login_required
@user_required
def user_profile_update(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            request.user.first_name = form.cleaned_data.get('first_name', request.user.first_name)
            request.user.last_name = form.cleaned_data.get('last_name', request.user.last_name)
            request.user.save()
            messages.success(request, "Profile updated.")
            return redirect('user_dashboard')
    else:
        form = UserProfileUpdateForm(instance=profile, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        })
    return render(request, 'profile_update.html', {'form': form, 'role': 'user'})

@login_required
@worker_required
def worker_profile_update(request):
    worker = get_object_or_404(WorkerProfile, user=request.user)
    if request.method == 'POST':
        form = WorkerProfileUpdateForm(request.POST, request.FILES, instance=worker)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect('worker_dashboard')
    else:
        form = WorkerProfileUpdateForm(instance=worker)
    return render(request, 'profile_update.html', {'form': form, 'role': 'worker'})

@login_required
@admin_required
def manage_workers(request):
    workers = WorkerProfile.objects.all().order_by('-id')
    return render(request, 'manage_workers.html', {'workers': workers})

@login_required
@admin_required
def toggle_worker_verification(request, worker_id):
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    worker.is_verified = not worker.is_verified
    worker.verified = worker.is_verified  # Sync
    if worker.is_verified:
        worker.kyc_status = 'approved'
    worker.save()
    
    status_text = "authorized" if worker.is_verified else "suspended"
    messages.success(request, f"Worker {worker.user.username} has been {status_text}.")
    
    return JsonResponse({'status': 'success', 'verified': worker.is_verified})

@login_required
@admin_required
def admin_dashboard(request):
    # KPI Statistics
    total_users = CustomUser.objects.filter(role='user').count()
    total_workers = CustomUser.objects.filter(role='worker').count()
    total_bookings = Booking.objects.count()
    
    # Revenue Calculation (Sum of all successful payments)
    from django.db.models import Sum
    total_revenue = Payment.objects.filter(status='successful').aggregate(Sum('amount'))['amount__sum'] or 0

    # Chart Data: Bookings per day (Last 7 Days)
    from datetime import timedelta
    from django.utils import timezone
    from django.db.models import Sum, Count
    seven_days_ago = timezone.now().date() - timedelta(days=6)
    daily_stats = Booking.objects.filter(created_at__date__gte=seven_days_ago)\
        .values('created_at__date')\
        .annotate(count=Count('id'))\
        .order_by('created_at__date')

    # Chart Data: Category Distribution
    categories = Category.objects.all()
    colors = ['var(--v-blue)', 'var(--v-pink)', 'var(--v-yellow)', '#6f42c1', '#20c997', '#fd7e14', '#0dcaf0', '#6610f2', '#e83e8c']
    category_data = []
    for i, cat in enumerate(categories):
        count = Booking.objects.filter(worker__categories=cat).count()
        color = colors[i % len(colors)]
        category_data.append({'name': cat.name, 'count': count, 'color': color})

    # Top Workers (by booking count)
    top_workers = WorkerProfile.objects.annotate(job_count=Count('bookings'))\
        .order_by('-job_count')[:5]

    context = {
        'total_users': total_users,
        'total_workers': total_workers,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'daily_stats': list(daily_stats),
        'category_data': category_data,
        'top_workers': top_workers,
        'user_count': total_users,
        'worker_count': total_workers,
        'booking_count': total_bookings,
        'revenue_total': total_revenue,
        'kyc_pending_count': WorkerProfile.objects.filter(kyc_status='pending').count(),
        'pending_complaints': Complaint.objects.filter(status='open').count(),
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
@admin_required
def manage_worker_detail(request, worker_id):
    worker = get_object_or_404(WorkerProfile, id=worker_id)
    bookings = Booking.objects.filter(worker=worker).order_by('-booking_date')
    return render(request, 'admin/worker_manage_detail.html', {
        'worker': worker,
        'bookings': bookings
    })

@login_required
@admin_required
def manage_user_detail(request, user_id):
    target_user = get_object_or_404(CustomUser, id=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    bookings = Booking.objects.filter(user=target_user).order_by('-booking_date')
    return render(request, 'admin/user_manage_detail.html', {
        'target_user': target_user,
        'profile': profile,
        'bookings': bookings
    })

@login_required
@admin_required
def offer_management(request):
    offers = Offer.objects.all().order_by('-id')
    settings = SmartOfferSettings.objects.first() or SmartOfferSettings.objects.create()
    
    # Analytics
    total_offers = offers.count()
    total_usage = Offer.objects.aggregate(Sum('usage_count'))['usage_count__sum'] or 0
    most_used_offer = Offer.objects.order_by('-usage_count').first()
    
    # Smart Offer Stats
    smart_offers_count = offers.filter(offer_type='smart').count()
    
    if request.method == 'POST':
        form = SmartOfferSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Smart Offer Settings updated successfully.")
            return redirect('offer_management')
    else:
        form = SmartOfferSettingsForm(instance=settings)
        
    return render(request, 'offer_management.html', {
        'offers': offers,
        'settings_form': form,
        'total_offers': total_offers,
        'total_usage': total_usage,
        'most_used_offer': most_used_offer,
        'smart_offers_count': smart_offers_count,
    })

@login_required
@admin_required
def create_offer(request):
    if request.method == 'POST':
        form = OfferForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "New offer created successfully.")
            return redirect('offer_management')
    else:
        form = OfferForm()
    return render(request, 'offer_form.html', {'form': form, 'title': 'Create New Offer'})

@login_required
@admin_required
def edit_offer(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)
    if request.method == 'POST':
        form = OfferForm(request.POST, instance=offer)
        if form.is_valid():
            form.save()
            messages.success(request, f"Offer '{offer.name}' updated successfully.")
            return redirect('offer_management')
    else:
        form = OfferForm(instance=offer)
    return render(request, 'offer_form.html', {'form': form, 'title': f'Edit Offer: {offer.name}'})

@login_required
@admin_required
def delete_offer(request, offer_id):
    offer = get_object_or_404(Offer, id=offer_id)
    name = offer.name
    offer.delete()
    messages.success(request, f"Offer '{name}' deleted successfully.")
    return redirect('offer_management')

@login_required
@admin_required
def manage_users(request):
    from django.db.models import Count, Q
    users = CustomUser.objects.filter(role='user').annotate(
        cancellation_count=Count('booking', filter=Q(booking__status='cancelled')),
        complaint_count=Count('complaint')
    ).order_by('-date_joined')
    return render(request, 'manage_users.html', {'users': users})

@login_required
@admin_required
def manage_workers(request):
    from django.db.models import Count, Q
    workers = WorkerProfile.objects.annotate(
        cancellation_count=Count('bookings', filter=Q(bookings__status='cancelled')),
        complaint_count=Count('bookings__complaint')
    ).all()
    return render(request, 'manage_workers.html', {'workers': workers})

@login_required
@admin_required
def admin_complaints(request):
    if request.method == "POST":
        complaint_id = request.POST.get('complaint_id')
        complaint = get_object_or_404(Complaint, id=complaint_id)
        complaint.status = 'resolved'
        complaint.save()
        messages.success(request, f"Complaint from @{complaint.user.username} marked as resolved.")
        return redirect('admin_complaints')
        
    complaints = Complaint.objects.all().order_by('-created_at')
    open_count = complaints.filter(status='open').count()
    return render(request, 'manage_complaints.html', {
        'complaints': complaints,
        'open_count': open_count
    })

@login_required
@admin_required
def admin_bookings(request):
    """View all bookings in the system."""
    bookings = Booking.objects.all().order_by('-booking_date')
    ongoing_bookings = bookings.filter(status__in=['pending', 'accepted', 'in_progress'])
    completed_bookings = bookings.filter(status__in=['completed', 'paid'])
    
    total_revenue = Payment.objects.filter(status='successful').aggregate(Sum('amount'))['amount__sum'] or 0
    
    return render(request, 'admin/manage_bookings.html', {
        'bookings': bookings,
        'ongoing_count': ongoing_bookings.count(),
        'completed_count': completed_bookings.count(),
        'total_revenue': total_revenue
    })

@login_required
def submit_complaint(request):
    booking_id = request.GET.get('booking_id') or request.POST.get('booking_id')
    booking = Booking.objects.filter(id=booking_id).first() if booking_id else None
    
    if request.method == 'POST':
        Complaint.objects.create(
            user=request.user,
            booking=booking,
            message=request.POST.get('message')
        )
        messages.success(request, "Complaint submitted successfully.")
        return redirect('user_dashboard' if request.user.role == 'user' else 'worker_dashboard')
    bookings = []
    if request.user.is_authenticated:
        if request.user.role == 'user':
            bookings = Booking.objects.filter(user=request.user).order_by('-booking_date')
        else:
            bookings = Booking.objects.filter(worker__user=request.user).order_by('-booking_date')
            
    return render(request, 'submit_complaint.html', {'booking': booking, 'bookings': bookings})

@login_required
def view_receipt(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if request.user != booking.user and request.user != booking.worker.user and request.user.role != 'admin':
        messages.error(request, "Access denied.")
        return redirect('home')
    payment = Payment.objects.filter(booking=booking, status='successful').first()
    return render(request, 'receipt.html', {'booking': booking, 'payment': payment})

@login_required
@worker_required
def check_new_jobs(request):
    worker = get_object_or_404(WorkerProfile, user=request.user)
    count = Booking.objects.filter(worker=worker, status='pending').count()
    return JsonResponse({'count': count})

@csrf_exempt
def api_worker_status(request):
    worker_id = request.GET.get('worker_id')
    if not worker_id:
        return JsonResponse({'error': 'worker_id parameter is required'}, status=400)
        
    worker = WorkerProfile.objects.filter(id=worker_id).first()
    if worker:
        return JsonResponse({
            'worker_id': worker.id,
            'status': worker.status
        })
        
    return JsonResponse({'error': 'Worker not found'}, status=404)

@login_required
@user_required
def api_bookings_list(request):
    # Fetch the latest 10 bookings for the logged-in user
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    data = []
    for b in bookings:
        data.append({
            'booking_id': b.id,
            'service_type': b.service_type,
            'worker_name': b.worker.user.get_full_name() or b.worker.user.username,
            'status': b.status,
            'booking_date': b.booking_date.strftime('%Y-%m-%d') if b.booking_date else None,
            'total_price': str(b.total_price)
        })
        
    return JsonResponse({'status': 'success', 'bookings': data})

def api_get_locations(request):
    locs = WorkerProfile.objects.values_list('district', flat=True).distinct()
    return JsonResponse({'locations': list(filter(None, locs))})

# =========================
# KYC DUMMY GENERATOR
# =========================

def generate_dummy_aadhar():
    return "".join([str(random.randint(0, 9)) for _ in range(12)])

def generate_dummy_pan():
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    prefix = "".join(random.choice(letters) for _ in range(5))
    middle = "".join(str(random.randint(0, 9)) for _ in range(4))
    suffix = random.choice(letters)
    return prefix + middle + suffix

@login_required
@admin_required
def create_dummy_workers(request):
    """Admin-only endpoint to seed dummy workers for testing."""
    categories = list(Category.objects.all())
    if not categories:
        return JsonResponse({"error": "No categories found. Run migrations/seed first."})
    
    first_names = ["Rahul", "Priya", "Ankit", "Sowmya", "Arun"]
    last_names = ["Sharma", "Nair", "Patel", "Reddy", "Verma"]
    
    created_count = 0
    for i in range(5):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        uname = f"testworker_{random.randint(1000, 9999)}"
        email = f"{uname}@example.com"
        
        user = CustomUser.objects.create_user(
            username=uname, email=email, password="password123",
            first_name=fname, last_name=lname, role='worker'
        )
        
        worker = WorkerProfile.objects.create(
            user=user,
            aadhar_no=generate_dummy_aadhar(),
            pan_no=generate_dummy_pan(),
            kyc_status='approved',
            is_verified=True,
            verified=True,
            price_per_day=random.randint(500, 1200),
            experience=random.randint(2, 10),
            location="Tirupur",
            availability='available'
        )
        worker.categories.add(random.choice(categories))
        created_count += 1
    
    messages.success(request, f"Successfully created {created_count} dummy workers.")
    return redirect('manage_workers')

def custom_403_view(request, e=None): return render(request, '403.html', status=403)
def custom_404_view(request, e=None): return render(request, '404.html', status=404)

@login_required
@worker_required
def kyc_status_api(request):
    worker = get_object_or_404(WorkerProfile, user=request.user)
    return JsonResponse({
        "status": worker.kyc_status
    })

@login_required
@worker_required
def update_booking_status(request, booking_id, action):
    from maidapp.utils import broadcast_status_update
    booking = get_object_or_404(Booking, id=booking_id, worker__user=request.user)
    worker = booking.worker
    
    if action == 'accept' and booking.status == 'pending':
        booking.status = 'accepted'
        booking.accepted_at = timezone.now()
        worker.availability = 'busy'
        worker.save()
        create_notification(booking.user, f"Good news! Your booking #{booking.booking_id_str} with {booking.worker.user.first_name} has been accepted.")
        messages.success(request, f"Booking #{booking.booking_id_str} accepted!")
    
    elif action == 'reject' and booking.status == 'pending':
        booking.status = 'rejected'
        create_notification(booking.user, f"We're sorry, your booking #{booking.booking_id_str} was declined by the partner.")
        messages.warning(request, f"Booking #{booking.booking_id_str} rejected.")
    
    elif action == 'start' and booking.status == 'accepted':
        booking.status = 'in_progress'
        worker.availability = 'busy'
        worker.save()
        create_notification(booking.user, f"Work has started for your booking #{booking.booking_id_str}. {booking.worker.user.first_name} is on it!")
        messages.info(request, "Work started! Focus on quality.")
    
    elif action == 'complete' and booking.status == 'in_progress':
        booking.status = 'completed'
        booking.completed_at = timezone.now()
        worker.availability = 'available'
        worker.status = 'available'
        worker.save()
        create_notification(booking.user, f"Service completed for #{booking.booking_id_str}! Please rate your experience.")
        messages.success(request, "Job well done! Earnings updated.")
        
        # ══ AUTO-MOVE TO NEXT JOB ══
        next_job = Booking.objects.filter(worker=worker, status='accepted').order_by('created_at').first()
        if next_job:
            next_job.status = 'in_progress'
            next_job.save()
            worker.availability = 'busy'
            worker.status = 'busy'
            worker.save()
            create_notification(next_job.user, f"{worker.user.first_name} has started your service! Stay updated.")
    
    
    else:
        messages.error(request, "Invalid action or state transition.")
        
    booking.save()
    
    # Real-time broadcast
    broadcast_status_update({
        'event': 'booking_updated',
        'booking_id': booking.id,
        'status': booking.status,
        'worker_status': worker.availability,
        'user_id': booking.user.id,
        'worker_id': worker.id
    })
    
    return redirect('worker_dashboard')

from maidapp.forms import ReviewForm

@login_required
def submit_review(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user, status__in=['completed', 'paid'])
    
    # Check if review already exists
    if hasattr(booking, 'review'):
        messages.error(request, "You have already reviewed this service.")
        return redirect('user_dashboard')

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.worker = booking.worker
            review.booking = booking
            review.save()
            
            # Update Worker Average Rating
            reviews = booking.worker.reviews.all()
            if reviews.exists():
                avg = sum([r.rating for r in reviews]) / reviews.count()
                booking.worker.rating_avg = round(avg, 1)
                booking.worker.save()
            
            messages.success(request, "Thank you for your feedback!")
            return redirect('user_dashboard')
    else:
        form = ReviewForm()
        
    return render(request, 'submit_review.html', {'form': form, 'booking': booking})

@login_required
@worker_required
def accept_booking_ajax(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, worker__user=request.user)
    if booking.status == 'pending':
        booking.status = 'accepted'
        booking.accepted_at = timezone.now()
        booking.save()
        create_notification(booking.user, f"Your booking #{booking.booking_id_str} has been accepted by {booking.worker.user.first_name}.")
        return JsonResponse({"status": "accepted"})
    return JsonResponse({"status": "error", "message": "Invalid state"}, status=400)

@login_required
@worker_required
def complete_booking_ajax(request, booking_id):
    from maidapp.utils import broadcast_status_update
    booking = get_object_or_404(Booking, id=booking_id, worker__user=request.user)
    worker = booking.worker
    if booking.status in ['accepted', 'in_progress']:
        booking.status = 'completed'
        booking.completed_at = timezone.now()
        worker.availability = 'available'
        worker.status = 'available'
        worker.save()
        booking.save()

        # ══ AUTO-MOVE TO NEXT JOB ══
        next_job = Booking.objects.filter(worker=worker, status='accepted').order_by('created_at').first()
        if next_job:
            next_job.status = 'in_progress'
            next_job.save()
            worker.availability = 'busy'
            worker.status = 'busy'
            worker.save()
            create_notification(next_job.user, f"{worker.user.first_name} has started your service! Stay updated.")
    
        
        broadcast_status_update({
            'event': 'booking_updated',
            'booking_id': booking.id,
            'status': booking.status,
            'worker_status': worker.availability,
            'user_id': booking.user.id,
            'worker_id': worker.id
        })
        create_notification(booking.user, f"Your service has been completed by {worker.user.first_name} {worker.user.last_name}.")
        return JsonResponse({"success": True, "status": "completed"})
    return JsonResponse({"success": False, "status": "error", "message": "Invalid state"}, status=400)

@login_required
@worker_required
def worker_live_updates(request):
    worker = get_object_or_404(WorkerProfile, user=request.user)
    
    from datetime import timedelta
    seven_days_ago = timezone.now() - timedelta(days=7)
    
    weekly_earnings = Booking.objects.filter(worker=worker, status='paid', completed_at__gte=seven_days_ago).aggregate(total=Sum('total_price'))['total'] or 0
    today_earnings = Booking.objects.filter(worker=worker, status='paid', completed_at__date=timezone.now().date()).aggregate(total=Sum('total_price'))['total'] or 0
    completed_jobs = Booking.objects.filter(worker=worker, status__in=['completed', 'paid']).count()
    ongoing_jobs = Booking.objects.filter(worker=worker, status__in=['accepted', 'in_progress']).count()
    total_earnings = Booking.objects.filter(worker=worker, status="paid").aggregate(total=Sum('total_price'))['total'] or 0
    pending_earnings = Booking.objects.filter(worker=worker, status__in=['accepted', 'in_progress', 'completed']).aggregate(total=Sum('total_price'))['total'] or 0

    return JsonResponse({
        "weekly_earnings": str(weekly_earnings),
        "today_earnings": str(today_earnings),
        "completed_jobs": completed_jobs,
        "ongoing_jobs": ongoing_jobs,
        "total_earnings": str(total_earnings),
        "pending_earnings": str(pending_earnings)
    })

@login_required
@worker_required
def request_payout(request):
    if request.method == "POST":
        worker = get_object_or_404(WorkerProfile, user=request.user)
        total_earnings = Booking.objects.filter(worker=worker, status="paid").aggregate(total=Sum('total_price'))['total'] or 0
        
        if total_earnings <= 0:
            return JsonResponse({"status": "error", "message": "No available balance to withdraw."}, status=400)
            
        # Notify admin (Assuming superusers are admins)
        admins = CustomUser.objects.filter(is_superuser=True)
        for admin in admins:
            create_notification(admin, f"Payout Request: {worker.user.username} requested withdrawal of ₹{total_earnings}.")
            
        return JsonResponse({
            "status": "success", 
            "message": "Payout request submitted successfully! Funds will be transferred to your registered bank account within 3-5 business days."
        })
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=405)

@login_required
def complete_booking(request, id):
    if request.method == "POST":
        try:
            booking = Booking.objects.get(id=id, worker__user=request.user)
            booking.status = "completed"
            booking.worker.status = "available"
            booking.worker.availability = "available"
            booking.worker.save()
            booking.save()
            return JsonResponse({"success": True})
        except:
            return JsonResponse({"success": False})

@login_required
@user_required
def make_payment(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    if booking.status != 'completed':
        messages.error(request, "This booking is not ready for payment yet.")
        return redirect('user_dashboard')
        
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
    payment = None
    try:
        payment = Payment.objects.get(booking=booking)
    except Payment.DoesNotExist:
        payment = Payment.objects.create(
            booking=booking,
            user=request.user,
            amount=booking.total_price
        )

    # Razorpay amount is in paise
    amount_in_paise = int(payment.amount * 100)
    
    if not payment.razorpay_order_id:
        try:
            razorpay_order = client.order.create(dict(amount=amount_in_paise, currency='INR', payment_capture='1'))
            payment.razorpay_order_id = razorpay_order['id']
        except Exception as e:
            # Handle dummy key case safely
            import secrets
            payment.razorpay_order_id = f"dummy_order_{payment.id}_{secrets.token_hex(4)}"
            
        payment.save()
        
    return render(request, 'make_payment.html', {
        'payment': payment, 
        'booking': booking,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'amount_in_paise': amount_in_paise
    })

@csrf_exempt
def payment_success(request):
    if request.method == "POST":
        razorpay_payment_id = request.POST.get('razorpay_payment_id')
        razorpay_order_id = request.POST.get('razorpay_order_id')
        razorpay_signature = request.POST.get('razorpay_signature')
        
        try:
            payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
            
            if not str(razorpay_order_id).startswith('dummy_order'):
                client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
                
                params_dict = {
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id,
                    'razorpay_signature': razorpay_signature
                }
                
                client.utility.verify_payment_signature(params_dict)
            
            payment.status = 'successful'
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.save()
            
            booking = payment.booking
            booking.status = 'paid'
            booking.save()
            
            from maidapp.utils import broadcast_status_update
            broadcast_status_update({
                'event': 'booking_updated',
                'booking_id': booking.id,
                'status': booking.status,
                'user_id': booking.user.id,
                'worker_id': booking.worker.id
            })
            
            create_notification(booking.worker.user, f"Payment of ₹{payment.amount} for your completed service (#{booking.booking_id_str}) has been received successfully.")
            messages.success(request, f"Payment successful for booking #{booking.booking_id_str}")
            
        except Exception as e:
            messages.error(request, f"Payment verification failed: {str(e)}")
            
    return redirect('user_dashboard')

@csrf_exempt
@login_required
@worker_required
def toggle_availability(request):
    if request.method == "POST":
        worker = get_object_or_404(WorkerProfile, user=request.user)
        worker.availability = 'busy' if worker.availability == 'available' else 'available'
        worker.save()
        return JsonResponse({'status': 'success', 'new_state': worker.availability})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def get_booking_status(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    # Check permission
    if request.user != booking.user and request.user != booking.worker.user and request.user.role != 'admin':
        return JsonResponse({'status': 'error', 'message': 'Permission denied'}, status=403)
        
    return JsonResponse({
        'status': booking.status,
        'booking_id': booking.booking_id_str,
        'is_completed': booking.status == 'completed',
        'is_cancelled': booking.status == 'cancelled' or booking.status == 'rejected'
    })

@login_required
def get_notifications(request):
    notifications = request.user.notifications.all()[:5]
    unread_count = request.user.notifications.filter(is_read=False).count()
    
    data = {
        'unread_count': unread_count,
        'notifications': [
            {
                'id': n.id,
                'message': n.message,
                'created_at': n.created_at.strftime("%b %d, %H:%M"),
                'is_read': n.is_read
            } for n in notifications
        ]
    }
    return JsonResponse(data)

@login_required
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({'status': 'success'})

@login_required
@admin_required
def admin_live_updates(request):
    from django.db.models import Sum
    return JsonResponse({
        'user_count': CustomUser.objects.filter(role='user').count(),
        'worker_count': CustomUser.objects.filter(role='worker').count(),
        'booking_count': Booking.objects.count(),
        'revenue_total': str(Payment.objects.filter(status='successful').aggregate(Sum('amount'))['amount__sum'] or 0),
        'kyc_pending_count': WorkerProfile.objects.filter(kyc_status='pending').count(),
    })

@login_required
@admin_required
def export_report(request):
    from django.http import HttpResponse
    
    html = """
    <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
        <style>
            table { border-collapse: collapse; font-family: Arial, sans-serif; }
            th { background-color: #3F4FCF; color: white; font-weight: bold; padding: 10px; border: 1px solid #dddddd; }
            td { padding: 8px; border: 1px solid #dddddd; }
            .status-completed { color: green; font-weight: bold; }
            .status-paid { color: blue; font-weight: bold; }
            .status-pending { color: orange; }
        </style>
    </head>
    <body>
        <h2>MaidConnect - Official Platform Report</h2>
        <table>
            <thead>
                <tr>
                    <th>Booking ID</th>
                    <th>Customer Name</th>
                    <th>Professional</th>
                    <th>Service Type</th>
                    <th>Status</th>
                    <th>Total Amount (INR)</th>
                    <th>Booking Date</th>
                </tr>
            </thead>
            <tbody>
    """
    
    bookings = Booking.objects.all().order_by('-created_at')
    for b in bookings:
        status_class = f"status-{b.status.lower()}"
        date_str = b.created_at.strftime("%B %d, %Y - %H:%M") if b.created_at else ''
        worker_name = f"{b.worker.user.first_name} {b.worker.user.last_name}" if b.worker else "N/A"
        customer_name = f"{b.user.first_name} {b.user.last_name}"
        
        html += f"""
            <tr>
                <td style="font-weight:bold;">{b.booking_id_str}</td>
                <td>{customer_name}</td>
                <td>{worker_name}</td>
                <td style="text-transform: capitalize;">{b.service_type}</td>
                <td class="{status_class}">{b.status.upper()}</td>
                <td>{b.total_price}</td>
                <td>{date_str}</td>
            </tr>
        """
        
    html += """
            </tbody>
        </table>
    </body>
    </html>
    """
    
    response = HttpResponse(html, content_type="application/vnd.ms-excel")
    response['Content-Disposition'] = 'attachment; filename="MaidConnect_Platform_Report.xls"'
    return response

@login_required
@admin_required
def toggle_user_status(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if user == request.user:
        return JsonResponse({'status': 'error', 'message': 'You cannot deactivate yourself.'}, status=400)
    
    user.is_active = not user.is_active
    user.save()
    return JsonResponse({
        'status': 'success', 
        'is_active': user.is_active,
        'message': f"User {user.username} is now {'Connected' if user.is_active else 'Isolated'}."
    })

@login_required
@admin_required
def api_complaints_list(request):
    complaints = Complaint.objects.all().order_by('-created_at')
    data = []
    for c in complaints:
        data.append({
            'id': c.id,
            'user': c.user.username,
            'booking_id': c.booking.booking_id_str if (c.booking and hasattr(c.booking, 'booking_id_str')) else 'GENERAL',
            'message': c.message,
            'status': c.status,
            'created_at': c.created_at.strftime("%B %d, %Y")
        })
    return JsonResponse({'complaints': data})


# =========================
# WORKER AVAILABILITY TOGGLE
# =========================

@login_required
@worker_required
def toggle_availability(request):
    """
    Toggle the worker's online/offline status.
    Called via GET from the worker dashboard/home JS.
    Returns JSON: {"is_online": true/false, "status": "success"}
    """
    worker = get_object_or_404(WorkerProfile, user=request.user)
    worker.is_online = not worker.is_online
    worker.save(update_fields=['is_online'])
    return JsonResponse({
        'status': 'success',
        'is_online': worker.is_online,
        'message': 'You are now Online' if worker.is_online else 'You are now Offline',
    })