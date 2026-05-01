from django import template
import base64

register = template.Library()

@register.filter(name='split')
def split(value, arg):
    if not value:
        return []
    return value.split(arg)

@register.filter(name='multiply')
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter(name='percentage')
def percentage(value, arg):
    try:
        if float(arg) == 0: return 0
        p = (float(value) / float(arg)) * 100
        return min(p, 100) # Cap at 100
    except (ValueError, TypeError):
        return 0

@register.simple_tag
def define_services():
    return [
        {'name': 'Professional Cleaning', 'slug': 'cleaning', 'icon': 'fa-broom', 'color': 'var(--v-blue)', 'desc': 'Deep home & office sanitization.'},
        {'name': 'Expert Cooking', 'slug': 'cooking', 'icon': 'fa-utensils', 'color': 'var(--v-pink)', 'desc': 'Nutritious & gourmet meals.'},
        {'name': 'Elite Babysitting', 'slug': 'babycare', 'icon': 'fa-baby-carriage', 'color': 'var(--v-yellow)', 'desc': 'Gentle care for your little ones.'},
        {'name': 'Elderly Support', 'slug': 'eldercare', 'icon': 'fa-heart-pulse', 'color': '#6f42c1', 'desc': 'Compassionate senior assistance.'},
        {'name': 'Housekeeping', 'slug': 'housekeeping', 'icon': 'fa-house-chimney-window', 'color': '#20c997', 'desc': 'Daily chores & organization.'},
        {'name': 'Professional Driver', 'slug': 'driver', 'icon': 'fa-car-side', 'color': '#fd7e14', 'desc': 'Safe & reliable city navigation.'},
        {'name': 'Patient Care', 'slug': 'patientcare', 'icon': 'fa-user-nurse', 'color': '#0dcaf0', 'desc': 'Dedicated post-op & health care.'},
        {'name': 'Laundry Service', 'slug': 'laundry', 'icon': 'fa-shirt', 'color': '#6610f2', 'desc': 'Pristine wash & fold services.'},
    ]

@register.filter(name='get_unread_count')
def get_unread_count(user):
    if user.is_authenticated:
        return user.notifications.filter(is_read=False).count()
    return 0

@register.filter(name='encoded_id')
def encoded_id(value):
    try:
        return base64.urlsafe_b64encode(str(value).encode()).decode().replace('=', '')
    except (ValueError, TypeError, AttributeError):
        return value
