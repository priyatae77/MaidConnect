from django.urls import path
from maidapp import views  

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('services/', views.services, name='services'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),

    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('send-otp/', views.send_otp, name='send_otp'),
    path('send-otp-api/', views.send_otp, name='send_otp_api'),  # API alias
    path('verify-otp-api/', views.verify_otp_api, name='verify_otp_api'),
    path('resend-otp-api/', views.resend_otp, name='resend_otp_api'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-reset-otp/', views.verify_reset_otp, name='verify_reset_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),

    # Register
    path('register/', views.register_choice, name='register_choice'),
    path('register/worker/', views.worker_register, name='worker_register'),
    path('register/user/', views.user_register, name='user_register'),

    # KYC
    path('worker/kyc/', views.submit_kyc, name='submit_kyc'),
    path('manage/kyc/', views.manage_kyc, name='manage_kyc'),
    path('manage/kyc/approve/<int:worker_id>/', views.approve_kyc, name='approve_kyc'),
    path('manage/kyc/reject/<int:worker_id>/', views.reject_kyc, name='reject_kyc'),
    path('manage/worker/block/<int:worker_id>/', views.block_worker, name='block_worker'),

    # Dashboards
    path('home/user/', views.user_home, name='user_home'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/user/', views.user_dashboard, name='user_dashboard'),
    path('home/worker/', views.worker_home, name='worker_home'),
    path('dashboard/worker/', views.worker_dashboard, name='worker_dashboard'),
    path('dashboard/worker/jobs/', views.worker_jobs, name='worker_jobs'),
    path('dashboard/worker/earnings/', views.worker_earnings, name='worker_earnings'),
    
    # Profile Update
    path('profile/', views.profile_view, name='profile_view'),
    path('profile/update/user/', views.user_profile_update, name='user_profile_update'),
    path('profile/update/worker/', views.worker_profile_update, name='worker_profile_update'),

    # Workers
    path('workers/', views.worker_list, name='worker_list'),
    path('worker/<int:worker_id>/', views.worker_detail, name='worker_detail'),

    # Receipt
    path('receipt/<int:booking_id>/', views.view_receipt, name='view_receipt'),
    
    # Admin Management
    path('manage/workers/', views.manage_workers, name='manage_workers'),
    path('manage/workers/<int:worker_id>/', views.manage_worker_detail, name='manage_worker_detail'),
    path('manage/workers/verify/<int:worker_id>/', views.toggle_worker_verification, name='toggle_worker_verification'),
    path('manage/users/', views.manage_users, name='manage_users'),
    path('manage/users/<int:user_id>/', views.manage_user_detail, name='manage_user_detail'),
    path('manage/complaints/', views.admin_complaints, name='admin_complaints'),
    path('manage/bookings/', views.admin_bookings, name='admin_bookings'),
    
    # Offer Management
    path('manage/offers/', views.offer_management, name='offer_management'),
    path('manage/offers/create/', views.create_offer, name='create_offer'),
    path('manage/offers/edit/<int:offer_id>/', views.edit_offer, name='edit_offer'),
    path('manage/offers/delete/<int:offer_id>/', views.delete_offer, name='delete_offer'),

    # Support / Complaint
    path('support/submit/', views.submit_complaint, name='submit_complaint'),

    # Booking Flow
    path('book/new/', views.booking_new, name='booking_new'),
    path('book/instant/', views.instant_book, name='instant_book'),
    path('book/<int:worker_id>/', views.booking_config, name='booking_config'),
    path('book/submit/', views.book_service, name='book_service'),
    path('booking/<int:booking_id>/edit/', views.edit_booking, name='edit_booking'),
    path('booking/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('booking/<int:booking_id>/<str:action>/', views.update_booking_status, name='update_booking_status'),
    path('booking/review/<int:booking_id>/', views.submit_review, name='submit_review'),
    path('booking/payment/<int:booking_id>/', views.make_payment, name='make_payment'),
    path('payment/success/', views.payment_success, name='payment_success'),

    # APIs
    path('api/worker/new-jobs/', views.check_new_jobs, name='check_new_jobs'),
    path('api/locations/', views.api_get_locations, name='api_get_locations'),
    path('api/kyc-status/', views.kyc_status_api, name='kyc_status_api'),
    path('api/booking-status/<int:booking_id>/', views.get_booking_status, name='get_booking_status'),
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('manage/seed-workers/', views.create_dummy_workers, name='seed_workers'),
    # AJAX Worker Actions
    path('worker/accept-booking/<int:booking_id>/', views.accept_booking_ajax, name='accept_booking_ajax'),
    path('worker/complete-booking/<int:booking_id>/', views.complete_booking_ajax, name='complete_booking_ajax'),
    path('worker/complete-booking/<int:id>/', views.complete_booking),
    path('worker/live-updates/', views.worker_live_updates, name='worker_live_updates'),
    path('worker/request-payout/', views.request_payout, name='request_payout'),
    path('manage/live-updates/', views.admin_live_updates, name='admin_live_updates'),
    path('manage/export-report/', views.export_report, name='export_report'),
    path('manage/user/toggle/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),
    path('api/complaints/', views.api_complaints_list, name='api_complaints_list'),
    path('api/worker-status/', views.api_worker_status, name='api_worker_status'),
    path('api/worker/bookings/', views.api_worker_bookings, name='api_worker_bookings'),
    path('api/worker/toggle-availability/', views.toggle_availability, name='toggle_availability'),
    path('api/worker-jobs/', views.api_worker_jobs_list, name='api_worker_jobs_list'),
    path('booking/accept/<int:booking_id>/', views.accept_booking, name='accept_booking'),
    path('booking/reject/<int:booking_id>/', views.reject_booking, name='reject_booking'),
    path('booking/start/<int:booking_id>/', views.start_job, name='start_job'),
    path('booking/complete/<int:booking_id>/', views.complete_job, name='complete_job'),
    path('api/bookings/', views.api_bookings_list, name='api_bookings_list'),
]