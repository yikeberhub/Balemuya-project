from django.contrib import admin
from django.utils.html import mark_safe
from .models import User, Admin, Customer, Professional, Education, Portfolio, Certificate, Address, Skill, Payment, SubscriptionPlan,\
    VerificationRequest
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class AddressInline(admin.StackedInline):
    model = Address
    extra = 1 

class EducationInline(admin.StackedInline):
    model = Education
    extra = 1

class SkillsInline(admin.StackedInline):
    model = Professional.skills.through
    extra = 1

class PortfolioInline(admin.StackedInline):
    model = Portfolio
    extra = 1

class CertificateInline(admin.StackedInline):
    model = Certificate
    extra = 1

# Custom User Admin
class CustomUserAdmin(admin.ModelAdmin):
    model = User
    list_display = ('email', 'first_name', 'middle_name', 'last_name','profile_image_preview', 'phone_number', 'gender', 'user_type', 'is_active', 'is_staff', 'is_superuser')
    list_filter = ('user_type', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('email', 'first_name', 'middle_name', 'last_name', 'phone_number')
    ordering = ('email',)
    
    inlines = [AddressInline]
    
    def profile_image_preview(self, obj):
            return mark_safe(f'<img src="{settings.MEDIA_URL}{obj.profile_image}" width="50" height="50" />')
    profile_image_preview.allow_tags = True
    profile_image_preview.short_description = 'Profile Image'

# Admin Admin
class AdminAdmin(admin.ModelAdmin):
    list_display = ('user', 'admin_level')
    search_fields = ('user__email', 'admin_level')
    list_filter = ('admin_level',)

# Customer Admin
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating')
    search_fields = ('user__email', 'rating')
    list_filter = ('rating',)

# Professional Admin
class ProfessionalAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_verified', 'kebele_id_image_front_preview', 'kebele_id_image_back_preview', 'rating', 'years_of_experience', 'is_available')
    search_fields = ('user__email',)
    list_filter = ('is_verified', 'is_available', 'rating')

    def kebele_id_image_front_preview(self, obj):
            return mark_safe(f'<img src="{settings.MEDIA_URL}{obj.kebele_id_front_image}" width="50" height="50" />')
    kebele_id_image_front_preview.allow_tags = True
    kebele_id_image_front_preview.short_description = 'Id front Image'

    def kebele_id_image_back_preview(self, obj):
            return mark_safe(f'<img src="{settings.MEDIA_URL}{obj.kebele_id_back_image}" width="50" height="50" />')
    kebele_id_image_back_preview.allow_tags = True
    kebele_id_image_back_preview.short_description = 'Id back Image'
    inlines = [EducationInline, SkillsInline, PortfolioInline, CertificateInline]  

class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('professional', 'plan_type', 'duration', 'cost', 'start_date', 'end_date', 'is_expired')
    list_filter = ('plan_type', 'duration')
    search_fields = ('professional__name', 'plan_type')
    readonly_fields = ('start_date', 'end_date', 'is_expired')
    
    def is_expired(self, obj):
        return obj.is_expired()
    is_expired.boolean = True
    is_expired.short_description = 'Expired'

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('professional', 'subscription_plan', 'amount', 'payment_status', 'payment_method', 'payment_date')
    list_filter = ('payment_status', 'payment_method')
    search_fields = ('professional__name', 'payment_status', 'subscription__plan_type')
    readonly_fields = ('payment_date',)
    

@admin.register(VerificationRequest)
class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ('professional', 'status', 'verified_by', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('professional__name', 'verified_by__name')
    


# Register the models with the custom admin classes
admin.site.register(User, CustomUserAdmin)
admin.site.register(Admin, AdminAdmin)
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Professional, ProfessionalAdmin)
admin.site.register(Education) 
admin.site.register(Skill)
admin.site.register(Portfolio)
admin.site.register(Certificate) 
admin.site.register(Address)
admin.site.register(SubscriptionPlan, SubscriptionPlanAdmin)
admin.site.register(Payment, PaymentAdmin)
