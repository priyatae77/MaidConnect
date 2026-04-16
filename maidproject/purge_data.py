import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maidproject.settings')
django.setup()

from maidapp.models import WorkerProfile, Category, Booking, Payment, CustomUser, UserProfile

def purge_all_data():
    print("Initiating system purge...")
    
    # 1. Clear Bookings and Payments first due to FKs
    print("Deleting Bookings and Payments...")
    Booking.objects.all().delete()
    Payment.objects.all().delete()
    
    # 2. Clear Workers, Profiles, and Reviews
    print("Deleting Profiles and Reviews...")
    WorkerProfile.objects.all().delete()
    UserProfile.objects.all().delete()
    from maidapp.models import Review, Complaint
    Review.objects.all().delete()
    Complaint.objects.all().delete()
    
    # 3. Clear non-admin users
    print("Deleting all non-superuser accounts...")
    CustomUser.objects.filter(is_superuser=False).delete()
    
    # 4. Clear Categories
    print("Deleting Categories...")
    Category.objects.all().delete()
    
    print("System purge complete. Database is clean.")

if __name__ == "__main__":
    purge_all_data()
