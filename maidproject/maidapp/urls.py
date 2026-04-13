from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    path('worker/register/', views.worker_register, name='worker_register'),
    path('user/register/', views.user_register, name='user_register'),
    path('workers/', views.worker_list, name='worker_list'),

    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('worker-dashboard/', views.worker_dashboard, name='worker_dashboard'),

    path('book/<int:worker_id>/', views.book_worker, name='book_worker'),
    path('booking/<int:booking_id>/<str:action>/', views.update_booking_status, name='update_booking_status'),

    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('payment/initiate/<int:booking_id>/', views.initiate_payment, name='initiate_payment'),
    path('payment/success/', views.payment_success, name='payment_success'),
]