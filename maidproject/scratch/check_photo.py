import os
import sys
import django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maidproject.settings')
django.setup()

from maidapp.models import UserProfile
from django.contrib.auth import get_user_model

User = get_user_model()
users = User.objects.filter(role='user')
print(f"Found {users.count()} users with role 'user'.")

for user in users:
    print(f"\nChecking User: {user.username} ({user.get_full_name()})")
    try:
        profile = user.userprofile
        print(f"  - Profile exists.")
        print(f"  - Photo Field: {profile.photo}")
        if profile.photo:
            try:
                print(f"  - Photo URL: {profile.photo.url}")
                print(f"  - File Path: {profile.photo.path}")
                if os.path.exists(profile.photo.path):
                    print("  - [SUCCESS] File EXISTS on disk.")
                else:
                    print("  - [FAIL] File DOES NOT exist on disk.")
            except ValueError:
                print("  - [FAIL] Photo field has no associated file.")
        else:
            print("  - No photo set in database.")
    except Exception as e:
        print(f"  - Error: {e}")
