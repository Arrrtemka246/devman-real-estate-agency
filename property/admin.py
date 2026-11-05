from django.contrib import admin

from .models import Complaint, Flat, Owner


class OwnershipInline(admin.TabularInline):
    model = Owner.flats.through
    raw_id_fields = ("owner",)
    extra = 0


@admin.register(Flat)
class FlatAdmin(admin.ModelAdmin):
    search_fields = (
        "town",
        "address",
        "owned_by__name",
        "owned_by__phonenumber",
        "owned_by__source_phone",
    )
    readonly_fields = ("created_at",)
    list_display = (
        "address",
        "price",
        "new_building",
        "construction_year",
        "town",
        "owner_phones",
    )
    list_editable = ("new_building",)
    list_filter = ("new_building", "town", "has_balcony", "active")
    raw_id_fields = ("liked_by",)
    inlines = (OwnershipInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("owned_by")

    @admin.display(description="Телефоны собственников")
    def owner_phones(self, flat):
        return ", ".join(
            str(owner.phonenumber or owner.source_phone)
            for owner in flat.owned_by.all()
        )


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    raw_id_fields = ("flat", "user")
    list_display = ("id", "flat", "user", "created_at")
    readonly_fields = ("created_at",)
    search_fields = ("text", "flat__address", "user__username")


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    raw_id_fields = ("flats",)
    list_display = ("name", "phonenumber", "source_phone")
    search_fields = ("name", "phonenumber", "source_phone")
