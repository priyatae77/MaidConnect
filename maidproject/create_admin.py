import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'maidproject.settings')
django.setup()

from maidapp.models import CustomUser

def create_precise_admin():
    print("\n" + "="*50)
    print("  MaidConnect - Custom Admin Creator")
    print("="*50)
    
    username = input("Enter Admin Username: ")
    email = input("Enter Admin Email: ")
    password = input("Enter Password: ")
    
    if CustomUser.objects.filter(username=username).exists():
        print(f"Error: User '{username}' already exists.")
        return

    # Create Superuser
    user = CustomUser.objects.create_superuser(
        username=username, 
        email=email, 
        password=password
    )
    
    # Force the 'admin' role for redirection logic
    user.role = 'admin'
    user.save()
    
    print(f"\nSUCCESS: Admin '{username}' created with role 'admin'.")
    print("Login at /login/ to access the Admin Dashboard.")
    print("="*50 + "\n")

if __name__ == "__main__":
    create_precise_admin()
