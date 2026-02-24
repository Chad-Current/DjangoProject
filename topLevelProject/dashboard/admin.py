# dashboard/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Count
from .models import (
    Profile,
    Contact,
    Account,
    Device,
    DigitalEstateDocument,
    ImportantDocument,
    FamilyNeedsToKnowSection,
    FuneralPlan,
    RelevanceReview,
)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'user', 'email', 'created_at')
    list_filter = ('email', 'created_at')
    search_fields = ('first_name', 'last_name', 'user__username', 'email')
    readonly_fields = ('user', 'created_at', 'updated_at')

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'first_name', 'last_name', 'date_of_birth', 'email', 'phone')
        }),
        ('Address', {
            'fields': ('address_1', 'address_2', 'city', 'state', 'zipcode')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        'first_name',
        'last_name',
        'contact_relation',
        'email',
        'phone',
        'city',
        'state',
        'is_emergency_contact',
        'is_digital_executor',
        'is_caregiver',
        'is_legal_executor',
        'is_trustee',
        'is_financial_agent',
        'is_healthcare_proxy',
        'is_guardian_for_dependents',
        'is_pet_caregiver',
        'is_memorial_contact',
        'is_legacy_contact',
        'is_professional_advisor',
        'is_notification_only',
        'is_knowledge_contact',
    )
    list_filter = (
        'contact_relation',
        'is_emergency_contact',
        'is_digital_executor',
        'is_caregiver',
        'is_legal_executor',
        'is_trustee',
        'is_financial_agent',
        'is_healthcare_proxy',
        'is_guardian_for_dependents',
        'is_pet_caregiver',
        'is_memorial_contact',
        'is_legacy_contact',
        'is_professional_advisor',
        'is_notification_only',
        'is_knowledge_contact',
        'created_at',
    )
    search_fields = (
        'first_name', 'last_name', 'email', 'phone',
        'address_1', 'address_2', 'city', 'state',
        'profile__first_name', 'profile__last_name',
    )
    readonly_fields = ('profile', 'created_at', 'updated_at', 'documents_count_display')

    fieldsets = (
        ('Contact Information', {
            'fields': ('profile', 'first_name', 'last_name', 'contact_relation', 'email', 'phone')
        }),
        ('Address', {
            'fields': ('address_1', 'address_2', 'city', 'state', 'zipcode')
        }),
        ('Roles', {
            'fields': (
                'is_emergency_contact',
                'is_digital_executor',
                'is_caregiver',
                'is_legal_executor',
                'is_trustee',
                'is_financial_agent',
                'is_healthcare_proxy',
                'is_guardian_for_dependents',
                'is_pet_caregiver',
                'is_memorial_contact',
                'is_legacy_contact',
                'is_professional_advisor',
                'is_notification_only',
                'is_knowledge_contact',
            )
        }),
        ('Document Assignment', {
            'fields': ('documents_count_display',),
            'description': 'Number of items assigned to this contact.'
        }),
        ('Message', {
            'fields': ('body',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            estate_count=Count('delegated_estate_documents'),
            important_count=Count('delegated_important_documents'),
            device_count=Count('delegated_devices'),
            account_count=Count('delegated_accounts'),
        )

    def documents_count(self, obj):
        estate = getattr(obj, 'estate_count', 0)
        important = getattr(obj, 'important_count', 0)
        device = getattr(obj, 'device_count', 0)
        account = getattr(obj, 'account_count', 0)
        total = estate + important + device + account
        return f"{total} total (E:{estate} I:{important} D:{device} A:{account})"
    documents_count.short_description = 'Assigned Items'
    documents_count.admin_order_field = 'estate_count'

    def documents_count_display(self, obj):
        if obj.pk:
            estate = obj.delegated_estate_documents.count()
            important = obj.delegated_important_documents.count()
            device = obj.delegated_devices.count()
            account = obj.delegated_accounts.count()
            total = estate + important + device + account
            return (
                f"{total} total "
                f"({estate} estate docs, {important} important docs, "
                f"{device} devices, {account} accounts)"
            )
        return "Save contact first to see item counts"
    documents_count_display.short_description = 'Items Assigned'


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        'account_name_or_provider', 'account_category',
        'delegated_account_to', 'review_time', 'created_at',
    )
    list_filter = ('account_category', 'keep_or_close_instruction', 'review_time', 'created_at')
    search_fields = (
        'account_name_or_provider', 'username_or_email',
        'profile__first_name', 'profile__last_name',
        'delegated_account_to__first_name', 'delegated_account_to__last_name',
    )
    readonly_fields = ('profile', 'created_at', 'updated_at')

    fieldsets = (
        ('Account Information', {
            'fields': ('profile', 'account_name_or_provider', 'account_category', 'website_url', 'delegated_account_to')
        }),
        ('Credentials', {
            'fields': ('username_or_email', 'credential_storage_location')
        }),
        ('Status & Instructions', {
            'fields': ('review_time', 'keep_or_close_instruction', 'notes_for_family')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile', 'delegated_account_to')


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        'device_name', 'device_type', 'owner_label',
        'used_for_2fa', 'delegated_device_to', 'review_time', 'created_at',
    )
    list_filter = ('device_type', 'used_for_2fa', 'review_time', 'created_at')
    search_fields = (
        'device_name', 'owner_label',
        'profile__first_name', 'profile__last_name',
        'delegated_device_to__first_name', 'delegated_device_to__last_name',
    )
    readonly_fields = ('profile', 'created_at', 'updated_at')

    fieldsets = (
        ('Device Information', {
            'fields': (
                'profile', 'device_type', 'device_name', 'owner_label',
                'location_description', 'delegated_device_to', 'review_time',
            )
        }),
        ('Security', {
            'fields': ('unlock_method_description', 'used_for_2fa', 'decommission_instruction')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile', 'delegated_device_to')


@admin.register(DigitalEstateDocument)
class DigitalEstateDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'name_or_title', 'estate_category',
        'delegated_estate_to', 'profile', 'review_time', 'created_at',
    )
    list_filter = (
        'estate_category',
        'applies_on_death', 'applies_on_incapacity', 'applies_immediately',
        'review_time', 'created_at',
    )
    search_fields = (
        'name_or_title',
        'profile__first_name', 'profile__last_name',
        'estate_overall_instructions',
        'delegated_estate_to__first_name', 'delegated_estate_to__last_name',
    )
    readonly_fields = ('profile', 'created_at', 'updated_at')

    fieldsets = (
        ('Assignment', {
            'fields': ('profile', 'delegated_estate_to'),
            'description': 'Document must be assigned to a contact.'
        }),
        ('Document Information', {
            'fields': ('estate_category', 'name_or_title', 'estate_file', 'review_time')
        }),
        ('Locations', {
            'fields': ('estate_physical_location', 'estate_digital_location')
        }),
        ('Instructions', {
            'fields': ('estate_overall_instructions',)
        }),
        ('Applicability', {
            'fields': ('applies_on_death', 'applies_on_incapacity', 'applies_immediately')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile', 'delegated_estate_to')


@admin.register(ImportantDocument)
class ImportantDocumentAdmin(admin.ModelAdmin):
    list_display = (
        'name_or_title', 'document_category',
        'delegated_important_document_to', 'requires_legal_review',
        'review_time', 'created_at',
    )
    list_filter = (
        'document_category', 'requires_legal_review',
        'applies_on_death', 'applies_on_incapacity', 'applies_immediately',
        'review_time', 'created_at',
    )
    search_fields = (
        'name_or_title', 'description',
        'profile__first_name', 'profile__last_name',
        'delegated_important_document_to__first_name',
        'delegated_important_document_to__last_name',
    )
    readonly_fields = ('profile', 'created_at', 'updated_at')

    fieldsets = (
        ('Assignment', {
            'fields': ('profile', 'delegated_important_document_to'),
            'description': 'Document must be assigned to a contact.'
        }),
        ('Document Information', {
            'fields': ('name_or_title', 'document_category', 'description', 'requires_legal_review', 'review_time')
        }),
        ('Locations', {
            'fields': ('physical_location', 'digital_location', 'important_file')
        }),
        ('Applicability', {
            'fields': ('applies_on_death', 'applies_on_incapacity', 'applies_immediately')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('profile', 'delegated_important_document_to')


@admin.register(FamilyNeedsToKnowSection)
class FamilyNeedsToKnowSectionAdmin(admin.ModelAdmin):
    list_display = (
        'relation', 'content_preview',
        'is_location_of_legal_will', 'is_password_manager', 'created_at',
    )
    list_filter = (
        'is_location_of_legal_will',
        'is_password_manager',
        'is_social_media',
        'is_photos_or_files',
        'is_data_retention_preferences',
        'created_at',
    )
    search_fields = ('relation__first_name', 'relation__last_name', 'content')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Family Information', {
            'fields': ('relation', 'content')
        }),
        ('Categories', {
            'fields': (
                'is_location_of_legal_will',
                'is_password_manager',
                'is_social_media',
                'is_photos_or_files',
                'is_data_retention_preferences',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(FuneralPlan)
class FuneralPlanAdmin(admin.ModelAdmin):
    """
    Admin interface for FuneralPlan.
    Organised into the same 8 sections as the onboarding wizard.
    Plans are created exclusively through the user-facing wizard
    (get_or_create on first step visit) — add permission is disabled.
    Only superusers may hard-delete.
    """

    # ── List display ──────────────────────────────────────────────────────────

    list_display = (
        'profile_full_name',
        'disposition_method',
        'service_type',
        'is_veteran',
        'burial_plot_or_niche_purchased',
        'reception_desired',
        'sections_complete',
        'completeness_badge',
        'review_time',
        'updated_at',
    )

    list_filter = (
        'disposition_method',
        'service_type',
        'marital_status',
        'is_veteran',
        'open_casket_viewing',
        'burial_plot_or_niche_purchased',
        'reception_desired',
        'review_time',
    )

    search_fields = (
        'profile__first_name',
        'profile__last_name',
        'profile__user__email',
        'preferred_name',
        'occupation',
        'preferred_funeral_home',
        'burial_or_interment_location',
        'funeral_insurance_policy_number',
    )

    ordering = ('-updated_at',)
    date_hierarchy = 'created_at'

    readonly_fields = (
        'profile_link',
        'officiant_link',
        'created_at',
        'updated_at',
        'completeness_badge',
        'sections_complete',
        'section_progress_display',
    )

    autocomplete_fields = ['officiant_contact']

    # ── Fieldsets ─────────────────────────────────────────────────────────────

    fieldsets = (
        (
            'Record',
            {
                'fields': (
                    'profile_link',
                    'section_progress_display',
                    'completeness_badge',
                    'created_at',
                    'updated_at',
                    'review_time',
                ),
                'classes': ('wide',),
            },
        ),
        (
            '1 · Personal Information',
            {
                'fields': (
                    'preferred_name',
                    'occupation',
                    'marital_status',
                    'religion_or_spiritual_affiliation',
                    ('is_veteran', 'veteran_branch'),
                ),
                'classes': ('wide',),
            },
        ),
        (
            '2 · Service Preferences',
            {
                'fields': (
                    'service_type',
                    'preferred_funeral_home',
                    ('funeral_home_phone', 'funeral_home_address'),
                    'preferred_venue',
                    ('officiant_contact', 'officiant_link'),
                    'officiant_name_freetext',
                    ('desired_timing', 'open_casket_viewing'),
                ),
                'classes': ('wide',),
            },
        ),
        (
            '3 · Final Disposition',
            {
                'fields': (
                    'disposition_method',
                    'burial_or_interment_location',
                    'burial_plot_or_niche_purchased',
                    'casket_type_preference',
                    'urn_type_preference',
                    'headstone_or_marker_inscription',
                ),
                'classes': ('wide',),
            },
        ),
        (
            '4 · Ceremony Personalization',
            {
                'fields': (
                    'music_choices',
                    'flowers_or_colors',
                    'readings_poems_or_scriptures',
                    'eulogists_notes',
                    'pallbearers_notes',
                    'clothing_or_jewelry_description',
                    'religious_cultural_customs',
                    'items_to_display',
                ),
                'classes': ('wide', 'collapse'),
            },
        ),
        (
            '5 · Reception / Gathering',
            {
                'fields': (
                    'reception_desired',
                    'reception_location',
                    'reception_food_preferences',
                    'reception_atmosphere_notes',
                    'reception_guest_list_notes',
                ),
                'classes': ('wide', 'collapse'),
            },
        ),
        (
            '6 · Obituary & Memorial',
            {
                'fields': (
                    'obituary_photo_description',
                    'obituary_key_achievements',
                    'obituary_publications',
                    'charitable_donations_in_lieu',
                ),
                'classes': ('wide', 'collapse'),
            },
        ),
        (
            '7 · Administrative & Financial',
            {
                'fields': (
                    'funeral_insurance_policy_number',
                    'death_certificates_requested',
                    'payment_arrangements',
                ),
                'classes': ('wide', 'collapse'),
            },
        ),
        (
            '8 · Additional Instructions',
            {
                'fields': ('additional_instructions',),
                'classes': ('wide', 'collapse'),
            },
        ),
    )

    # ── Section progress helper (mirrors get_plan_progress() in views) ────────

    def _get_progress(self, obj):
        """
        Mirrors FuneralPlanMixin.get_plan_progress() so the admin
        shows the same completion logic as the user-facing wizard.
        """
        return {
            'personal_info': any([
                obj.preferred_name, obj.occupation, obj.marital_status,
                obj.religion_or_spiritual_affiliation, obj.is_veteran,
            ]),
            'service': any([
                obj.service_type, obj.preferred_funeral_home,
                obj.preferred_venue, obj.desired_timing,
            ]),
            'disposition': any([
                obj.disposition_method, obj.burial_or_interment_location,
                obj.casket_type_preference, obj.urn_type_preference,
            ]),
            'ceremony': any([
                obj.music_choices, obj.flowers_or_colors,
                obj.readings_poems_or_scriptures, obj.eulogists_notes,
                obj.clothing_or_jewelry_description,
            ]),
            'reception': obj.reception_desired is not None,
            'obituary': any([
                obj.obituary_photo_description, obj.obituary_key_achievements,
                obj.obituary_publications, obj.charitable_donations_in_lieu,
            ]),
            'admin': any([
                obj.funeral_insurance_policy_number,
                obj.death_certificates_requested,
                obj.payment_arrangements,
            ]),
            'instructions': bool(obj.additional_instructions),
        }

    # ── Custom list-display helpers ───────────────────────────────────────────

    @admin.display(description='Profile', ordering='profile__last_name')
    def profile_full_name(self, obj):
        return f"{obj.profile.first_name} {obj.profile.last_name}"

    @admin.display(description='Sections')
    def sections_complete(self, obj):
        progress = self._get_progress(obj)
        done = sum(progress.values())
        return f"{done} / 8"

    @admin.display(description='Complete?')
    def completeness_badge(self, obj):
        progress = self._get_progress(obj)
        done = sum(progress.values())
        if done == 8:
            return format_html(
                '<span style="color:#2e7d32; font-weight:bold;">&#10003; Complete</span>'
            )
        if done == 0:
            return format_html(
                '<span style="color:#9e9e9e;">&#9675; Empty</span>'
            )
        return format_html(
            '<span style="color:#e65100; font-weight:bold;">&#9679; {}/8 sections</span>',
            done,
        )

    @admin.display(description='Section Progress')
    def section_progress_display(self, obj):
        if not obj.pk:
            return '—'
        progress = self._get_progress(obj)
        labels = {
            'personal_info': '1 · Personal Info',
            'service':       '2 · Service Prefs',
            'disposition':   '3 · Disposition',
            'ceremony':      '4 · Ceremony',
            'reception':     '5 · Reception',
            'obituary':      '6 · Obituary',
            'admin':         '7 · Admin',
            'instructions':  '8 · Instructions',
        }
        rows = []
        for key, label in labels.items():
            done = progress[key]
            icon  = '&#10003;' if done else '&#10007;'
            color = '#2e7d32' if done else '#c62828'
            rows.append(
                f'<span style="display:inline-block; min-width:200px; '
                f'color:{color}; margin-right:1rem;">{icon} {label}</span>'
            )
        # Two columns
        pairs = [
            rows[i] + (rows[i + 1] if i + 1 < len(rows) else '')
            for i in range(0, len(rows), 2)
        ]
        inner = ''.join(f'<div>{p}</div>' for p in pairs)
        return mark_safe(f'<div style="line-height:1.9;">{inner}</div>')

    # ── Readonly link helpers ─────────────────────────────────────────────────

    @admin.display(description='Profile (link)')
    def profile_link(self, obj):
        if not obj.pk:
            return '—'
        try:
            url = reverse('admin:dashboard_profile_change', args=[obj.profile.pk])
            return format_html(
                '<a href="{}">{} {}</a>',
                url,
                obj.profile.first_name,
                obj.profile.last_name,
            )
        except Exception:
            return str(obj.profile)

    @admin.display(description='Officiant (link)')
    def officiant_link(self, obj):
        if not obj.officiant_contact_id:
            return '—'
        try:
            url = reverse('admin:dashboard_contact_change', args=[obj.officiant_contact.pk])
            return format_html('<a href="{}">{}</a>', url, obj.officiant_contact)
        except Exception:
            return str(obj.officiant_contact)

    # ── Queryset optimisation ─────────────────────────────────────────────────

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related('profile', 'profile__user', 'officiant_contact')
        )

    # ── Permissions ───────────────────────────────────────────────────────────

    def has_add_permission(self, request):
        """
        FuneralPlans are created exclusively through the user-facing
        onboarding wizard via get_or_create — never directly in admin.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """Only superusers may hard-delete a funeral plan."""
        return request.user.is_superuser


@admin.register(RelevanceReview)
class RelevanceReviewAdmin(admin.ModelAdmin):
    list_display = (
        'get_item_name', 'get_item_type',
        'reviewer', 'matters', 'review_date', 'next_review_due',
    )
    list_filter = ('matters', 'review_date', 'next_review_due')
    search_fields = (
        'account_review__account_name_or_provider',
        'device_review__device_name',
        'estate_review__name_or_title',
        'important_document_review__name_or_title',
        'reviewer__username',
        'reasoning',
    )
    readonly_fields = ('reviewer', 'review_date', 'created_at', 'updated_at')

    fieldsets = (
        ('Review Target', {
            'fields': ('account_review', 'device_review', 'estate_review', 'important_document_review'),
            'description': 'Select exactly ONE item to review.'
        }),
        ('Review Information', {
            'fields': ('reviewer', 'matters', 'review_date', 'next_review_due')
        }),
        ('Details', {
            'fields': ('reasoning',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_item_name(self, obj):
        return obj.get_item_name()
    get_item_name.short_description = 'Item'

    def get_item_type(self, obj):
        return obj.get_item_type()
    get_item_type.short_description = 'Type'


# ── Site customisation ────────────────────────────────────────────────────────

admin.site.site_header = "Digital Estate Planning Administration"
admin.site.site_title = "Digital Estate Admin"
admin.site.index_title = "Welcome to Digital Estate Planning Administration"