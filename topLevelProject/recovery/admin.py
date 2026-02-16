from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import RecoveryRequest


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
    
    actions = ['mark_as_verified', 'mark_as_in_progress', 'mark_as_completed', 'mark_as_denied']
    
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