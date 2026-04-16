from django.urls import path
from django import views

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),

    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Register
    path('register/', views.register_choice, name='register_choice'),
    path('register/worker/', views.worker_register, name='worker_register'),
    path('register/user/', views.user_register, name='user_register'),

    # Dashboards
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/user/', views.user_dashboard, name='user_dashboard'),
    path('dashboard/worker/', views.worker_dashboard, name='worker_dashboard'),

    # Workers
    path('workers/', views.worker_list, name='worker_list'),
    path('worker/<int:worker_id>/', views.worker_detail, name='worker_detail'),

    # Receipt
    path('receipt/<int:booking_id>/', views.view_receipt, name='view_receipt'),
    
    # Admin Management
    path('admin/workers/', views.manage_workers, name='manage_workers'),
    path('admin/workers/verify/<int:worker_id>/', views.toggle_worker_verification, name='toggle_worker_verification'),
    path('admin/users/', views.manage_users, name='manage_users'),
    path('admin/complaints/', views.admin_complaints, name='admin_complaints'),

    # APIs
    path('api/worker/new-jobs/', views.check_new_jobs, name='check_new_jobs'),
    path('api/locations/', views.api_get_locations, name='api_get_locations'),
]