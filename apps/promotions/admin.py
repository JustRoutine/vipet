from django.contrib import admin

from .models import DynamicPricingRule, DynamicPricingTier, LoyaltyTier, Promotion


class DynamicPricingTierInline(admin.TabularInline):
    model = DynamicPricingTier
    extra = 1


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "discount_type",
        "discount_value",
        "start_date",
        "end_date",
        "is_active",
    ]
    list_filter = ["is_active", "discount_type"]
    search_fields = ["name"]
    ordering = ["-start_date"]


@admin.register(DynamicPricingRule)
class DynamicPricingRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    inlines = [DynamicPricingTierInline]


@admin.register(DynamicPricingTier)
class DynamicPricingTierAdmin(admin.ModelAdmin):
    list_display = ["rule", "min_days", "max_days", "discount_percentage"]
    list_filter = ["rule"]


@admin.register(LoyaltyTier)
class LoyaltyTierAdmin(admin.ModelAdmin):
    list_display = ["name", "min_bookings", "discount_percentage"]
    ordering = ["min_bookings"]
