import os
import django
import random
from django.core.files.base import ContentFile
import requests

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maidproject.settings')
django.setup()

from maidapp.models import CustomUser, WorkerProfile

def populate():
    workers_data = [
        {
            'username': 'anita_cleaner',
            'first_name': 'Anita',
            'last_name': 'Sharma',
            'skills': 'Expert House Cleaning, Deep Cleaning, Organizing',
            'location': 'Chennai, Tamil Nadu',
            'price': 500,
            'exp': 8,
            'gender': 'Female',
            'age': 34,
            'image_url': 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?q=80&w=800'
        },
        {
            'username': 'chef_rahul',
            'first_name': 'Rahul',
            'last_name': 'Verma',
            'skills': 'Professional Indian & Continental Cooking, Meal Prep',
            'location': 'Coimbatore, Tamil Nadu',
            'price': 800,
            'exp': 12,
            'gender': 'Male',
            'age': 40,
            'image_url': 'https://images.unsplash.com/photo-1556910103-1c02745aae4d?q=80&w=800'
        },
        {
            'username': 'priya_nanny',
            'first_name': 'Priya',
            'last_name': 'Das',
            'skills': 'Child Care, Newborn Specialty, Early Education',
            'location': 'Madurai, Tamil Nadu',
            'price': 1200,
            'exp': 6,
            'gender': 'Female',
            'age': 28,
            'image_url': 'https://images.unsplash.com/photo-1510154221590-ff63e90a136f?q=80&w=800'
        },
        {
            'username': 'samuel_care',
            'first_name': 'Samuel',
            'last_name': 'John',
            'skills': 'Elderly Care, Nursing Assistant, Physiotherapy Aid',
            'location': 'Trichy, Tamil Nadu',
            'price': 1500,
            'exp': 10,
            'gender': 'Male',
            'age': 45,
            'image_url': 'https://images.unsplash.com/photo-1581579438747-1dc8d17bbce4?q=80&w=800'
        },
        {
            'username': 'maya_housekeeper',
            'first_name': 'Maya',
            'last_name': 'Reddy',
            'skills': 'Full-time Housekeeping, Laundry, Grocery Management',
            'location': 'Salem, Tamil Nadu',
            'price': 600,
            'exp': 5,
            'gender': 'Female',
            'age': 30,
            'image_url': 'https://images.unsplash.com/photo-1528740561666-dc2479dc08ab?q=80&w=800'
        },
        {
            'username': 'david_driver',
            'first_name': 'David',
            'last_name': 'Wilson',
            'skills': 'Professional Driving, Valet, Car Maintenance',
            'location': 'Tirunelveli, Tamil Nadu',
            'price': 900,
            'exp': 15,
            'gender': 'Male',
            'age': 50,
            'image_url': 'https://images.unsplash.com/photo-1449965408869-eaa3f722e40d?q=80&w=800'
        }
    ]

    print("Starting population...")

    for data in workers_data:
        # Create or update user
        user, created = CustomUser.objects.get_or_create(
            username=data['username'],
            defaults={
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'role': 'worker',
                'email': f"{data['username']}@example.com"
            }
        )
        if created:
            user.set_password('password123')
            user.save()

        # Create or update profile
        profile, p_created = WorkerProfile.objects.get_or_create(
            user=user,
            defaults={
                'address': f"Central {data['location']}",
                'location': data['location'],
                'skills': data['skills'],
                'experience': data['exp'],
                'price_per_day': data['price'],
                'age': data['age'],
                'gender': data['gender'],
                'availability': 'available',
                'verified': True,
                'rating_avg': round(random.uniform(4.2, 5.0), 1)
            }
        )

        if p_created:
            # Download and save image
            print(f"Downloading image for {data['username']}...")
            try:
                response = requests.get(data['image_url'])
                if response.status_code == 200:
                    profile.photo.save(f"{data['username']}.jpg", ContentFile(response.content), save=True)
            except Exception as e:
                print(f"Failed to download image: {e}")

    print("Population complete!")

if __name__ == '__main__':
    populate()
