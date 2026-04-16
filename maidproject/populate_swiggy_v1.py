"""
populate_swiggy_v1.py
─────────────────────
MaidConnect — Swiggy/Zomato style data seed.
Run AFTER purge_data.py:

  cd maidproject
  python purge_data.py
  python populate_swiggy_v1.py

Creates:
  • 8 service categories (with Unsplash image URLs stored as paths to note)
  • 20 realistic worker profiles spread across the categories
  • 30+ reviews to populate ratings
"""

import os
import sys
import django
import random
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maidproject.settings')
django.setup()

from maidapp.models import CustomUser, WorkerProfile, Category, Review

# ─── CATEGORIES ───────────────────────────────────────────────────────────────
CATEGORIES = [
    {"name": "House Cleaning",  "description": "Deep cleaning, mopping, dusting, kitchen & bathroom scrubbing."},
    {"name": "Cooking",         "description": "Home-cooked South/North Indian meals, tiffin prep, diet cooking."},
    {"name": "Baby Care",       "description": "Infant feeding, bathing, sleeping routines, activity support."},
    {"name": "Elder Care",      "description": "Companionship, medication reminders, physiotherapy assistance."},
    {"name": "Laundry & Iron",  "description": "Washing, drying, pressing and folding clothes and linen."},
    {"name": "Grocery & Errands","description": "Daily grocery runs, bill payments, pharmacy pickups."},
    {"name": "Driver",          "description": "Daily drop & pickup, school runs, airport transfers."},
    {"name": "Security Guard",  "description": "24-hr building security, gate management, CCTV monitoring."},
]

# ─── WORKERS ─────────────────────────────────────────────────────────────────
WORKERS = [
    # (username, first, last, gender, age, city, experience, price, skills, languages, timings, rating, categories_indices)
    ("priya_maid",    "Priya",     "Sharma",    "Female", 34, "Chennai",   6,  550,  "Deep cleaning Mopping Utensil washing Bathroom scrubbing", "Tamil Hindi", "6 AM – 2 PM", 4.8, [0]),
    ("anitha_cook",   "Anitha",    "Krishnan",  "Female", 42, "Bangalore", 10, 650,  "South Indian cooking Tiffin prep Filter coffee Lunch box", "Tamil Kannada English", "7 AM – 12 PM", 4.9, [1]),
    ("kavitha_care",  "Kavitha",   "Raju",      "Female", 38, "Chennai",   8,  700,  "Baby bathing Feeding Infant sleep routine Activity play", "Tamil English", "Full Day", 4.7, [2]),
    ("meena_elder",   "Meena",     "Nair",      "Female", 45, "Kochi",     12, 800,  "Elder care Medication reminders Physiotherapy assist Companionship", "Malayalam Hindi English", "Full Day", 4.9, [3]),
    ("ravi_laundry",  "Ravi",      "Kumar",     "Male",   28, "Hyderabad", 4,  350,  "Washing Ironing Folding Dry cleaning handover Linen care", "Telugu Hindi", "7 AM – 4 PM", 4.5, [4]),
    ("suresh_driver", "Suresh",    "Patel",     "Male",   36, "Mumbai",    9,  900,  "City driving Airport transfer School runs Intercity trips", "Hindi Marathi English", "24/7 on call", 4.8, [6]),
    ("raja_security", "Raja",      "Murugan",   "Male",   40, "Chennai",   15, 950,  "Gate management CCTV patrolling Visitor log Night duty", "Tamil Hindi", "Night shift 8 PM–8 AM", 4.7, [7]),
    ("divya_clean",   "Divya",     "Venkat",    "Female", 29, "Coimbatore",3,  450,  "Quick clean Dusting Wiping Kitchen hygiene Pest prevention", "Tamil English", "Morning 6–10 AM", 4.4, [0]),
    ("lakshmi_cook",  "Lakshmi",   "Iyer",      "Female", 50, "Chennai",   18, 750,  "Brahmin cooking Sweets Festival food Tiffin North+South", "Tamil Hindi Sanskrit", "6 AM – 1 PM", 5.0, [1]),
    ("suma_baby",     "Suma",      "Devi",      "Female", 33, "Bangalore", 7,  720,  "Newborn care Toddler activity Story telling Homework help", "Kannada Tamil English", "Full Day", 4.8, [2]),
    ("thomas_elder",  "Thomas",    "Mathew",    "Male",   48, "Kochi",     13, 850,  "Male elder care Walker assist Hospital escort Bed care", "Malayalam English Hindi", "Full Day", 4.6, [3]),
    ("pooja_laundry", "Pooja",     "Singh",     "Female", 27, "Delhi",     3,  380,  "Laundry Machine+hand Iron Steam press Wardrobe sorting", "Hindi Punjabi English", "9 AM – 5 PM", 4.3, [4]),
    ("arjun_errand",  "Arjun",     "Mehta",     "Male",   24, "Mumbai",    2,  420,  "Grocery pickup Bill payments Pharmacy courier Parcel handover", "Hindi Marathi Gujarati", "8 AM – 8 PM", 4.4, [5]),
    ("sunita_multi",  "Sunita",    "Rao",       "Female", 39, "Hyderabad", 11, 800,  "Cooking Cleaning Babysitting All-rounder Full home management", "Telugu Hindi English", "Full Day", 4.9, [0, 1, 2]),
    ("mahesh_drv",    "Mahesh",    "Verma",     "Male",   44, "Delhi",     16, 1000, "Long distance driving Night driving GPS navigation Car care", "Hindi English", "On call 24/7", 4.7, [6]),
    ("kamla_clean",   "Kamla",     "Bai",       "Female", 43, "Pune",      14, 480,  "Deep cleaning Carpet washing Sofa cleaning Window wiping Garbage", "Hindi Marathi", "7 AM – 2 PM", 4.6, [0]),
    ("geetha_cook",   "Geetha",    "Pillai",    "Female", 46, "Trivandrum", 17, 700, "Kerala meals Fish curry Sadya Rice porridge Health cooking", "Malayalam Tamil", "6 AM – 12 PM", 4.8, [1]),
    ("vikram_guard",  "Vikram",    "Reddy",     "Male",   35, "Hyderabad", 8,  880,  "Armed guard Parking management Access control Society patrol", "Telugu Hindi", "Day shift 8 AM–8 PM", 4.5, [7]),
    ("nirmala_elder", "Nirmala",   "Das",       "Female", 52, "Kolkata",   20, 900,  "Bengali elder care Diabetic diet Mobility assist Emotional support", "Bengali Hindi English", "Full Day", 5.0, [3]),
    ("hari_all",      "Hari",      "Prasad",    "Male",   32, "Bangalore", 5,  650,  "Cleaning Cooking Errands Driver Versatile all-purpose home help", "Kannada Telugu Hindi", "Full Day", 4.6, [0, 1, 5, 6]),
]

# ─── REVIEW TEMPLATES ─────────────────────────────────────────────────────────
REVIEWS = [
    (5, "Absolutely brilliant! My house has never looked so clean. Will book again every month."),
    (5, "Amazing cook! The food tasted exactly like home. The whole family loved it."),
    (5, "So gentle with my baby. I felt completely at ease leaving the little one with her."),
    (4, "Very hardworking and reliable. Arrived on time and did everything without any supervision."),
    (5, "My elderly mother loves her. She's patient, kind, and always cheerful."),
    (4, "Good work overall. The cleaning was thorough. Minor issues with the stove but sorted quickly."),
    (5, "Excellent driver — safe, punctual, and knows all the shortcuts in the city!"),
    (4, "Trustworthy security guard. Very alert and keeps a good visitor log."),
    (5, "The best cook we've ever had. Healthy meals every day, zero complaints."),
    (3, "Decent work but needed a few reminders. Eventually got everything done."),
    (5, "Outstanding! She managed the baby, cooked lunch and cleaned the kitchen — all before noon!"),
    (4, "Very polite and professional. Will highly recommend to friends."),
    (5, "Nirmala is an absolute gem. My parents adore her. She treats them like family."),
    (5, "Lakshmi's cooking is next level. Festival sweets were outstanding!"),
    (4, "Hari did everything we asked without a single complaint. Great all-rounder."),
]


def create_categories():
    print("\n[1/3] Creating categories...")
    cats = []
    for c in CATEGORIES:
        cat, created = Category.objects.get_or_create(
            name=c["name"],
            defaults={"description": c["description"]}
        )
        status = "[+] Created" if created else "[=] Exists"
        print(f"   {status}: {cat.name}")
        cats.append(cat)
    return cats


def create_workers(cats):
    print("\n[2/3] Creating workers...")
    created_workers = []

    for idx, w in enumerate(WORKERS):
        (uname, first, last, gender, age, city, exp, price,
         skills, langs, timings, rating, cat_indices) = w

        # Create or get user
        user, user_created = CustomUser.objects.get_or_create(
            username=uname,
            defaults={
                "first_name": first,
                "last_name":  last,
                "email":      f"{uname}@maidconnect.in",
                "role":       "worker",
            }
        )
        if user_created:
            user.set_password("Worker@123")
            user.save()

        # Create or get worker profile
        wp, wp_created = WorkerProfile.objects.get_or_create(
            user=user,
            defaults={
                "address":      f"{city}, India",
                "location":     city,
                "skills":       skills,
                "languages":    langs,
                "work_timings": timings,
                "age":          age,
                "gender":       gender,
                "experience":   exp,
                "price_per_day":price,
                "availability": "available",
                "verified":     True,
                "rating_avg":   rating,
            }
        )

        if wp_created:
            # Assign categories
            for ci in cat_indices:
                if ci < len(cats):
                    wp.categories.add(cats[ci])
            wp.save()
            print(f"   [+] Worker: {first} {last} ({city})")
        else:
            print(f"   [=] Exists: {uname}")

        created_workers.append(wp)

    return created_workers


def create_reviews(workers):
    print("\n[3/3] Adding reviews...")

    # Create a few generic reviewer accounts
    reviewers = []
    reviewer_names = ["rahul", "preethi", "anand", "sneha", "kartik", "meera", "arjun_user", "deepa_user"]
    for rname in reviewer_names:
        u, _ = CustomUser.objects.get_or_create(
            username=rname,
            defaults={"email": f"{rname}@gmail.com", "role": "user"}
        )
        if _:
            u.set_password("User@123")
            u.save()
        reviewers.append(u)

    review_count = 0
    for wp in workers:
        # Give each worker 1-3 reviews
        num_reviews = random.randint(1, 3)
        used_reviewers = random.sample(reviewers, min(num_reviews, len(reviewers)))
        for reviewer in used_reviewers:
            rev_template = random.choice(REVIEWS)
            r, created = Review.objects.get_or_create(
                user=reviewer,
                worker=wp,
                defaults={
                    "rating":  rev_template[0],
                    "comment": rev_template[1],
                }
            )
            if created:
                review_count += 1

        # Recalculate avg rating from reviews
        reviews = Review.objects.filter(worker=wp)
        if reviews.exists():
            wp.rating_avg = round(sum(r.rating for r in reviews) / reviews.count(), 1)
            wp.save(update_fields=["rating_avg"])

    print(f"   [+] Created {review_count} reviews")


def main():
    print("=" * 55)
    print("  MaidConnect - Swiggy/Zomato Database Seed v1")
    print("=" * 55)

    cats    = create_categories()
    workers = create_workers(cats)
    create_reviews(workers)

    print("\n" + "=" * 55)
    print(f"  DONE! Seeding complete!")
    print(f"     Categories : {Category.objects.count()}")
    print(f"     Workers    : {WorkerProfile.objects.count()}")
    print(f"     Reviews    : {Review.objects.count()}")
    print("=" * 55)
    print("\n  Default password for all workers : Worker@123")
    print("  Default password for reviewers   : User@123")
    print("  Run: python manage.py runserver\n")


if __name__ == "__main__":
    main()
