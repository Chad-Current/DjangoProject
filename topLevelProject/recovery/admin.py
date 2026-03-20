from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from .models import RecoveryRequest, ProfileAccessGrant


@admin.register(RecoveryRequest)
class RecoveryRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'requester_display',
        'profile_link',
        'reason',
        'status',
        'verification_status',
        'created_at',
        'reviewed_by',
    ]
    
    list_filter = [
        'status',
        'reason',
        'verified_at',
        'created_at',
    ]
    
    search_fields = [
        'requester_first_name',
        'requester_last_name',
        'requester_email',
        'target_description',
        'profile__first_name',
        'profile__last_name',
        'requested_by_user__username',
        'requested_by_user__email',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'verified_at',
        'verification_token',
        'verification_attempts',
        'completed_at',
        'requester_info_display',
        'documents_display',
    ]
    
    fieldsets = (
        ('Request Information', {
            'fields': (
                'profile',
                'reason',
                'target_account',
                'target_description',
                'status',
            )
        }),
        ('Requester Details', {
            'fields': (
                'requester_info_display',
                'requested_by_user',
                'requester_first_name',
                'requester_last_name',
                'requester_email',
                'requester_phone',
                'requester_relationship',
            )
        }),
        ('Verification', {
            'fields': (
                'verification_token',
                'verified_at',
                'verification_attempts',
            )
        }),
        ('Supporting Documentation', {
            'fields': (
                'documents_display',
                'death_certificate',
                'proof_of_relationship',
                'legal_authorization',
                'additional_notes',
            )
        }),
        ('Processing', {
            'fields': (
                'reviewed_by',
                'reviewed_at',
                'provider_ticket_number',
                'steps_taken',
                'outcome_notes',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
                'completed_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def requester_display(self, obj):
        """Display requester name with type indicator"""
        name = obj.get_requester_name()
        if obj.is_external_request():
            return format_html('<span style="color: #0066cc;">🔓 {}</span>', name)
        return format_html('<span style="color: #009900;">🔒 {}</span>', name)
    requester_display.short_description = 'Requester'
    
    def profile_link(self, obj):
        """Link to the profile being accessed"""
        url = reverse('admin:dashboard_profile_change', args=[obj.profile.pk])
        return format_html('<a href="{}">{}</a>', url, obj.profile)
    profile_link.short_description = 'Profile'
    
    def verification_status(self, obj):
        """Show verification status with visual indicator"""
        if obj.is_verified():
            return format_html('<span style="color: green;">✓ Verified</span>')
        return format_html('<span style="color: orange;">⏳ Pending</span>')
    verification_status.short_description = 'Verification'
    
    def requester_info_display(self, obj):
        """Formatted display of requester information"""
        if obj.requested_by_user:
            return format_html(
                '<strong>Authenticated User:</strong> {}<br>'
                '<strong>Email:</strong> {}',
                obj.requested_by_user,
                obj.requested_by_user.email
            )
        else:
            return format_html(
                '<strong>External Requester</strong><br>'
                '<strong>Name:</strong> {} {}<br>'
                '<strong>Email:</strong> {}<br>'
                '<strong>Phone:</strong> {}<br>'
                '<strong>Relationship:</strong> {}',
                obj.requester_first_name,
                obj.requester_last_name,
                obj.requester_email,
                obj.requester_phone or 'N/A',
                obj.requester_relationship or 'N/A'
            )
    requester_info_display.short_description = 'Requester Information'
    
    def documents_display(self, obj):
        """Show uploaded documents"""
        docs = []
        if obj.death_certificate:
            docs.append(f'✓ Death Certificate: <a href="{obj.death_certificate.url}" target="_blank">View</a>')
        if obj.proof_of_relationship:
            docs.append(f'✓ Proof of Relationship: <a href="{obj.proof_of_relationship.url}" target="_blank">View</a>')
        if obj.legal_authorization:
            docs.append(f'✓ Legal Authorization: <a href="{obj.legal_authorization.url}" target="_blank">View</a>')
        
        if docs:
            return format_html('<br>'.join(docs))
        return 'No documents uploaded'
    documents_display.short_description = 'Uploaded Documents'
    
    actions = [
        'mark_as_verified', 'mark_as_in_progress',
        'mark_as_completed', 'mark_as_denied',
        'grant_profile_access',
    ]

    def mark_as_verified(self, request, queryset):
        updated = queryset.update(status='Verified', verified_at=timezone.now())
        self.message_user(request, f'{updated} request(s) marked as verified.')
    mark_as_verified.short_description = 'Mark selected as Verified'

    def mark_as_in_progress(self, request, queryset):
        updated = queryset.update(status='In Progress')
        self.message_user(request, f'{updated} request(s) marked as in progress.')
    mark_as_in_progress.short_description = 'Mark selected as In Progress'

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='Completed', completed_at=timezone.now())
        self.message_user(request, f'{updated} request(s) marked as completed.')
    mark_as_completed.short_description = 'Mark selected as Completed'

    def mark_as_denied(self, request, queryset):
        updated = queryset.update(status='Denied')
        self.message_user(request, f'{updated} request(s) marked as denied.')
    mark_as_denied.short_description = 'Mark selected as Denied'

    def grant_profile_access(self, request, queryset):
        """
        Grant the authenticated requester read-only access to the profile.

        Rules enforced here:
        - Only works on requests where requested_by_user is set (authenticated
          requester with a site account).  External requesters must be given an
          account first.
        - Only Completed or Verified requests are eligible.
        - Skips and warns if a grant already exists for that profile+user pair.
        """
        created = 0
        skipped = 0

        for rr in queryset.select_related('profile', 'requested_by_user'):
            if not rr.requested_by_user:
                self.message_user(
                    request,
                    f'Request #{rr.pk}: requester has no site account — '
                    'create one for them first, then run this action again.',
                    level=messages.WARNING,
                )
                skipped += 1
                continue

            if rr.status not in ('Verified', 'Completed'):
                self.message_user(
                    request,
                    f'Request #{rr.pk}: status is "{rr.status}" — '
                    'only Verified or Completed requests can be granted access.',
                    level=messages.WARNING,
                )
                skipped += 1
                continue

            grant, new = ProfileAccessGrant.objects.get_or_create(
                profile=rr.profile,
                granted_to=rr.requested_by_user,
                defaults={
                    'recovery_request': rr,
                    'granted_by': request.user,
                    'notes': f'Auto-created from recovery request #{rr.pk}.',
                },
            )

            if new:
                created += 1
                # Mark request completed if it isn't already
                if rr.status != 'Completed':
                    rr.status = 'Completed'
                    rr.completed_at = timezone.now()
                    rr.save(update_fields=['status', 'completed_at'])
            else:
                if not grant.is_active:
                    grant.is_active = True
                    grant.save(update_fields=['is_active'])
                    created += 1
                else:
                    skipped += 1
                    self.message_user(
                        request,
                        f'Request #{rr.pk}: {rr.requested_by_user} already has '
                        'an active grant for this profile.',
                        level=messages.INFO,
                    )

        if created:
            self.message_user(
                request,
                f'{created} access grant(s) created successfully.',
                level=messages.SUCCESS,
            )

    grant_profile_access.short_description = 'Grant profile access to requester'


# =============================================================================
# PROFILE ACCESS GRANT ADMIN
# =============================================================================

@admin.register(ProfileAccessGrant)
class ProfileAccessGrantAdmin(admin.ModelAdmin):
    list_display = (
        'granted_to',
        'profile_link',
        'recovery_request_link',
        'granted_by',
        'granted_at',
        'expires_at',
        'is_active',
        'validity_display',
    )
    list_filter = ('is_active', 'granted_at', 'expires_at')
    search_fields = (
        'granted_to__username',
        'granted_to__email',
        'profile__first_name',
        'profile__last_name',
        'granted_by__username',
    )
    readonly_fields = ('granted_at', 'granted_by', 'validity_display')
    ordering = ('-granted_at',)

    fieldsets = (
        ('Grant', {
            'fields': ('profile', 'granted_to', 'is_active', 'expires_at'),
        }),
        ('Audit', {
            'fields': ('granted_by', 'granted_at', 'recovery_request', 'notes', 'validity_display'),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.granted_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description='Profile')
    def profile_link(self, obj):
        url = reverse('admin:dashboard_profile_change', args=[obj.profile.pk])
        return format_html(
            '<a href="{}">{} {}</a>',
            url, obj.profile.first_name, obj.profile.last_name,
        )

    @admin.display(description='Recovery Request')
    def recovery_request_link(self, obj):
        if not obj.recovery_request_id:
            return '—'
        url = reverse('admin:recovery_recoveryrequest_change', args=[obj.recovery_request_id])
        return format_html('<a href="{}">Request #{}</a>', url, obj.recovery_request_id)

    @admin.display(description='Valid?')
    def validity_display(self, obj):
        if not obj.pk:
            return '—'
        if not obj.is_active:
            return format_html('<span style="color:#b91c1c;font-weight:600;">✘ Revoked</span>')
        if obj.is_expired():
            return format_html('<span style="color:#b45309;font-weight:600;">⏰ Expired</span>')
        return format_html('<span style="color:#15803d;font-weight:600;">✔ Active</span>')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'profile', 'granted_to', 'granted_by', 'recovery_request'
        )