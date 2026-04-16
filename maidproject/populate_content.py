import os
import django
import requests
from django.core.files.base import ContentFile
from decimal import Decimal

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "maidproject.settings")
django.setup()

from maidapp.models import Category, WorkerProfile, CustomUser

def download_image(url):
    response = requests.get(url)
    if response.status_code == 200:
        return ContentFile(response.content)
    return None

def populate():
    print("Starting Intelligence Population...")
    
    # 1. Create Categories
    categories_data = [
        {"name": "Elderly Care", "desc": "Distinguished professionals dedicated to senior comfort and specialized medical support.", "id": "1581579438747-1dc8d17bbce4"},
        {"name": "Baby Care", "desc": "Nurturing specialists for infants and children, vetted for safety and early development mastery.", "id": "1510154221590-ff63e90a136f"},
        {"name": "Professional Cooking", "desc": "Master chefs and culinary experts capable of curating world-class nutritional experiences.", "id": "1556910103-1c02745aae4d"},
        {"name": "Home Cleaning", "desc": "Meticulous organization and sanitation specialists for high-end residential estates.", "id": "1581578731548-c64695cc6952"},
    ]
    
    cats = {}
    for data in categories_data:
        cat, created = Category.objects.get_or_create(name=data["name"])
        cat.description = data["desc"]
        img_content = download_image(f"https://images.unsplash.com/photo-{data['id']}?q=80&w=1000")
        if img_content:
            cat.image.save(f"{data['name'].lower().replace(' ', '_')}.jpg", img_content, save=True)
        cat.save()
        cats[data["name"]] = cat
        print(f"Category processed: {data['name']}")

    # 2. Create Multiple Workers
    workers_data = [
        # Elderly Care
        {"user": "Elena_Care", "cat": "Elderly Care", "img": "1544005313-94ddf0286df2", "loc": "Mumbai West", "rate": 1500, "exp": 8, "skills": "Dementia Care, Medical Support, Holistic Wellness"},
        {"user": "Ravi_Senior", "cat": "Elderly Care", "img": "1506794778202-cad84cf45f1d", "loc": "Delhi NCR", "rate": 1200, "exp": 12, "skills": "Post-Op Recovery, Physical Therapy Support"},
        
        # Baby Care
        {"user": "Sophia_Nanny", "cat": "Baby Care", "img": "1531123897727-8f129e1688ce", "loc": "Bangalore Central", "rate": 1800, "exp": 6, "skills": "Montessori Trained, Infant Nutrition"},
        {"user": "Mark_ChildCare", "cat": "Baby Care", "img": "1507003211169-0a1dd7228f2d", "loc": "Hyderabad Cyber", "rate": 1400, "exp": 10, "skills": "Behavioral Specialist, Multilingual"},
        
        # Culinary
        {"user": "Chef_Vikram", "cat": "Professional Cooking", "img": "1539578101404-f0f20ce0a66a", "loc": "Pune East", "rate": 2500, "exp": 15, "skills": "French Cuisine, Keto Expert, Fine Dining"},
        {"user": "Anita_Gourmet", "cat": "Professional Cooking", "img": "1581333142764-16f30a902df5", "loc": "Kolkata North", "rate": 2000, "exp": 9, "skills": "Authentic Indian, Pastry Specialist"},
        
        # Cleaning
        {"user": "Clara_Clean", "cat": "Home Cleaning", "img": "1594824472421-5a507873528b", "loc": "Chennai South", "rate": 800, "exp": 5, "skills": "Deep Sanitation, Antiques Care, Eco-Friendly"},
        {"user": "David_Estate", "cat": "Home Cleaning", "img": "1441777013400-24d9c813000e", "loc": "Goa North", "rate": 1100, "exp": 14, "skills": "Luxury Living Room, Team Lead"},
    ]

    for wd in workers_data:
        # Create User
        username = wd["user"]
        email = f"{username.lower()}@elitecare.com"
        user, created = CustomUser.objects.get_or_create(username=username, defaults={"email": email, "role": "worker"})
        if created:
            user.set_password("elite123")
            user.save()
        
        # Create/Update Profile
        profile, created = WorkerProfile.objects.get_or_create(user=user, defaults={"experience": wd["exp"], "price_per_day": wd["rate"]})
        profile.location = wd["loc"]
        profile.experience = wd["exp"]
        profile.price_per_day = wd["rate"]
        profile.skills = wd["skills"]
        profile.verified = True
        profile.rating_avg = 4.8
        
        # Assign Category
        profile.categories.add(cats[wd["cat"]])
        
        # Download Portrait
        img_content = download_image(f"https://images.unsplash.com/photo-{wd['img']}?q=80&w=800")
        if img_content:
            profile.photo.save(f"{username.lower()}.jpg", img_content, save=True)
        
        profile.save()
        print(f"Worker deployed: {username}")

    print("Population Sequence Complete.")

if __name__ == "__main__":
    populate()
