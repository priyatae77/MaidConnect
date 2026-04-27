from django.contrib import admin
from maidapp.models import CustomUser, UserProfile, Category, Payment, WorkerProfile, Document, Booking, Review, Complaint

# USER ADMIN
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserProfile)
admin.site.register(Category)
admin.site.register(Payment)


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