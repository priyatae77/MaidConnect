from django.contrib import admin
from .models import *

# USER ADMIN
class UserAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'role', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('name', 'email')

# admin.site.register(User, UserAdmin)


# WORKER ADMIN
class WorkerAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'availability', 'verified', 'price_per_day')
    list_filter = ('availability', 'verified')
    search_fields = ('user__name', 'location')
    list_editable = ('verified', 'availability')  # 🔥 direct edit option

admin.site.register(WorkerProfile, WorkerAdmin)


# DOCUMENT ADMIN
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('worker', 'document_type', 'status', 'uploaded_at')
    list_filter = ('status',)
    list_editable = ('status',)  # 🔥 approve/reject directly

admin.site.register(Document, DocumentAdmin)


admin.site.register(Booking)
admin.site.register(Review)
admin.site.register(Complaint)