import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maidproject.settings')
django.setup()

from maidapp.models import Category

def seed_categories():
    categories = [
        {
            'name': 'Elderly Care',
            'description': 'Professional and compassionate care for seniors, including medical assistance and companionship.',
            'image_url': 'https://images.unsplash.com/photo-1581579438747-1dc8d17bbce4?q=80&w=800'
        },
        {
            'name': 'Baby Care',
            'description': 'Trusted nannies and babysitters for your little ones, ensuring safety and early development.',
            'image_url': 'https://images.unsplash.com/photo-1510154221590-ff63e90a136f?q=80&w=800'
        },
        {
            'name': 'Professional Cooking',
            'description': 'Expert chefs for daily meals or special occasions, specialized in various cuisines.',
            'image_url': 'https://images.unsplash.com/photo-1556910103-1c02745aae4d?q=80&w=800'
        },
        {
            'name': 'Home Cleaning',
            'description': 'Deep cleaning, organizing, and regular maintenance for a pristine living environment.',
            'image_url': 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?q=80&w=800'
        }
    ]

    for cat_data in categories:
        cat, created = Category.objects.get_or_create(
            name=cat_data['name'],
            defaults={'description': cat_data['description']}
        )
        if not created:
            cat.description = cat_data['description']
        
        # In a real scenario, we'd download the image. For now, we'll store the URL or use a placeholder logic.
        # Since 'image' is an ImageField, we should ideally download it.
        # But for this rapid upgrade, I'll update the model to allow URL if needed, OR just download it now.
        print(f"Propagating category: {cat.name}")
        cat.save()

if __name__ == '__main__':
    seed_categories()
