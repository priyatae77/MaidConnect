"""
populate_tamilnadu_market.py
────────────────────────────
MaidConnect — Premium Tamil Nadu Marketplace Data Seed.
Focus: Tirupur, Coimbatore, Chennai, Trichy, etc.
"""

import os
import django
import random
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maidproject.settings')
django.setup()

from maidapp.models import CustomUser, WorkerProfile, Category, Review

# ─── CATEGORIES ───────────────────────────────────────────────────────────────
CATEGORIES = [
    {"name": "Master Chef",   "description": "Traditional South Indian meals, Tiffin, and Feast catering."},
    {"name": "Deep Cleaning", "description": "Full home sanitation, kitchen scrubbing, and floor polishing."},
    {"name": "Baby Care",     "description": "Certified infant care, feeding, and toddler engagement."},
    {"name": "Elder Care",    "description": "Medical assistance, medication reminders, and companionship."},
    {"name": "Laundry Pro",   "description": "Washing, drying, and premium steam ironing."},
    {"name": "Pro Driver",    "description": "Local and outstation travel, safe and punctual."},
    {"name": "Guardians",     "description": "24/7 Security, gate management, and CCTV monitoring."},
    {"name": "Errands",       "description": "Grocery, bills, and pharmacy support."},
]

# ─── DISTRICTS & AREAS ───────────────────────────────────────────────────────
DISTRICTS = ["Tirupur", "Coimbatore", "Chennai", "Trichy", "Salem", "Karur", "Tuticorin", "Pondicherry"]

AREA_MAPPING = {
    "Tirupur": ["Avinashi Road", "Kangayam Road", "Rayapuram", "Palladam", "Tirupur Central", "Dharapuram Road", "Palladam Road"],
    "Coimbatore": ["Gandhipuram", "RS Puram", "Peelamedu", "Saravanampatti", "Race Course"],
    "Chennai": ["T Nagar", "Adyar", "Velachery", "Anna Nagar", "Mylapore"],
    "Trichy": ["Thillai Nagar", "Srirangam", "Cantonment", "Woraiur", "KK Nagar"],
    "Salem": ["Shevapet", "Suramangalam", "Hasthampatti", "Fairlands", "Gugai"],
    "Karur": ["Gandhigramam", "Jawahar Bazaar", "Thanthonimalai", "Pasupathipalayam"],
    "Tuticorin": ["Palayamkottai Road", "Bryant Nagar", "Meelavittan", "Thoothukudi Central"],
    "Pondicherry": ["White Town", "Heritage Town", "Mission Street", "Nellitope", "Saram"]
}

# ─── WORKER DATA ─────────────────────────────────────────────────────────────
WORKER_DATA = [
    ("selvam_tirupur", "Selvam", "Murugan", "Male", "Tirupur", 12, 600, "South Indian feast, Tiffin Master", "Tamil, English"),
    ("priya_cbe", "Priya", "Dharshini", "Female", "Coimbatore", 8, 550, "Full Home Cleaning, Kitchen Scrub", "Tamil, Telugu"),
    ("aruna_chennai", "Aruna", "Devi", "Female", "Chennai", 15, 800, "Newborn Care, Pediatric Support", "Tamil, Hindi, English"),
    ("ravi_trichy", "Ravi", "Chandran", "Male", "Trichy", 10, 950, "Safe Driver, Outstation Specialist", "Tamil, Malayalam"),
    ("karthik_salem", "Karthik", "Raja", "Male", "Salem", 6, 700, "Industrial Cleaning, Floor Polishing", "Tamil"),
    ("meena_karur", "Meena", "Kumari", "Female", "Karur", 5, 500, "Elderly Companionship, Medication", "Tamil"),
    ("john_tuticorin", "John", "Victor", "Male", "Tuticorin", 20, 1000, "Ex-Service Security, Gate Pro", "Tamil, English"),
    ("ramya_pondy", "Ramya", "Sundar", "Female", "Pondicherry", 7, 650, "French Cuisine, Tiffin, Baking", "Tamil, French, English"),
    ("velu_tirupur", "Velu", "Swaminathan", "Male", "Tirupur", 14, 580, "Expert Laundry, Steam Ironing", "Tamil"),
    ("deepa_cbe", "Deepa", "Venkatesh", "Female", "Coimbatore", 9, 720, "Certified Baby Care, Education Play", "Tamil, English"),
    ("suresh_chennai", "Suresh", "Kumar", "Male", "Chennai", 11, 450, "Quick Errand Runner, Bill Payments", "Tamil, Hindi"),
    ("lakshmi_trichy", "Lakshmi", "Bhai", "Female", "Trichy", 18, 750, "Traditional Veg Cooking, Sweets", "Tamil, Kannada"),
    ("raja_salem", "Raja", "Sekar", "Male", "Salem", 13, 850, "Bodyguard, Security Management", "Tamil, Hindi"),
    ("anitha_karur", "Anitha", "Priya", "Female", "Karur", 6, 520, "Daily Housekeep, Dish Washing", "Tamil"),
    ("mani_tuticorin", "Mani", "Kandan", "Male", "Tuticorin", 9, 680, "Professional Driver, Parcel Pickup", "Tamil"),
    ("saranya_pondy", "Saranya", "M", "Female", "Pondicherry", 10, 820, "Specialized Elder Care, Nursing Assist", "Tamil, English"),
    ("ganesh_tirupur", "Ganesh", "S", "Male", "Tirupur", 11, 620, "Deep Sanitization, Pest Control Support", "Tamil"),
    ("kavitha_cbe", "Kavitha", "S", "Female", "Coimbatore", 7, 580, "Laundry Pro, Saree Draping, Ironing", "Tamil"),
    ("vimal_chennai", "Vimal", "N", "Male", "Chennai", 5, 900, "Luxury Car Driver, Valet Expert", "Tamil, English"),
    ("uma_trichy", "Uma", "Maheshwari", "Female", "Trichy", 12, 700, "All-rounder Home Management", "Tamil, Telugu"),
]

def main():
    print("\n" + "="*60)
    print("  MaidConnect - Premium Tamil Nadu Marketplace Seed")
    print("="*60)

    # 1. Categories
    print("\n[1/3] Planting Categories...")
    cats = []
    for c in CATEGORIES:
        cat, _ = Category.objects.get_or_create(name=c["name"], defaults={"description": c["description"]})
        cats.append(cat)
        print(f"   [+] {cat.name}")

    # 2. Workers
    print("\n[2/3] Recruiting Top Professionals (OTP-Verified Profiles)...")
    for username, first, last, gender, district, exp, price, skills, langs in WORKER_DATA:
        # User account
        user, created = CustomUser.objects.get_or_create(
            username=username,
            defaults={
                "first_name": first,
                "last_name": last,
                "email": f"{username}@tnmaid.com",
                "role": "worker",
                "is_otp_verified": True,
                "is_doc_verified": True
            }
        )
        if created:
            user.set_password("Worker@123")
            user.save()

        # Worker Profile
        local_area = random.choice(AREA_MAPPING.get(district, [district]))
        wp, created = WorkerProfile.objects.get_or_create(
            user=user,
            defaults={
                "mobile": f"98765{random.randint(10000, 99999)}",
                "address": f"{random.randint(1,100)}, Market Street, {local_area}, {district}",
                "district": district,
                "pincode": f"6{random.randint(10000, 99999)}",
                "location": f"{local_area}, {district}",
                "skills": skills,
                "languages": langs,
                "experience": exp,
                "price_per_day": price,
                "verified": True,
                "rating_avg": random.choice([4.5, 4.6, 4.7, 4.8, 4.9, 5.0]),
                "availability": "available"
            }
        )
        if created:
            # Assign random relevant categories
            cat_list = random.sample(cats, k=random.randint(1, 2))
            for c in cat_list:
                wp.categories.add(c)
            print(f"   [+] Verified Partner: {first} {last} ({district})")

    # 3. Reviews
    print("\n[3/3] Generating Professional Feedback loop...")
    reviewers = []
    for i in range(5):
        uname = f"customer_{i}"
        u, c = CustomUser.objects.get_or_create(username=uname, defaults={"role": "user", "email": f"{uname}@mail.com"})
        if c: 
            u.set_password("User@123")
            u.save()
        reviewers.append(u)

    feedback_templates = [
        "Incredibly professional. The Aadhar verification gave us peace of mind.",
        "Excellent skills, arrived exactly on time in Tirupur. Highly recommended!",
        "Very clean and polite. Handled my baby with great care.",
        "Standard of service is very high. Best marketplace in Tamil Nadu.",
        "The cook is a Master Chef truly! Authentic Karur flavors."
    ]

    for wp in WorkerProfile.objects.all():
        Review.objects.create(
            user=random.choice(reviewers),
            worker=wp,
            rating=random.randint(4, 5),
            comment=random.choice(feedback_templates)
        )

    print("\n" + "="*60)
    print("  SUCCESS: Tamil Nadu Marketplace is LIVE with 20 Verified Partners.")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
