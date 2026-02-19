from datetime import timedelta
from django.contrib import admin
from django.utils import timezone
from .models import ChecklistEmailLog


@admin.register(ChecklistEmailLog)
class ChecklistEmailLogAdmin(admin.ModelAdmin):
    list_display = (
        'email',
        'first_name',
        'sent_at',
        'ip_address',
        'converted',
        'has_notes',
    )
    list_filter = (
        'converted',
        ('sent_at', admin.DateFieldListFilter),
    )
    search_fields = ('email', 'first_name', 'ip_address', 'notes')
    readonly_fields = ('email', 'first_name', 'sent_at', 'ip_address')
    ordering = ('-sent_at',)
    list_per_page = 50
    date_hierarchy = 'sent_at'

    # Points at our custom template so checklist_stats is actually rendered.
    change_list_template = 'admin/baseapp/checklistemaillog/change_list.html'

    fieldsets = (
        ('Requester', {
            'fields': ('email', 'first_name', 'ip_address', 'sent_at'),
        }),
        ('Lead Status', {
            'fields': ('converted', 'notes'),
            'description': (
                'Mark "converted" once this lead creates an account. '
                'Use notes to track follow-up activity.'
            ),
        }),
    )

    # ── custom columns ───────────────────────────────────────────────────────

    @admin.display(boolean=True, description='Notes?')
    def has_notes(self, obj):
        return bool(obj.notes)

    # ── actions ──────────────────────────────────────────────────────────────

    actions = ['mark_converted', 'mark_not_converted']

    @admin.action(description='Mark selected as converted')
    def mark_converted(self, request, queryset):
        updated = queryset.update(converted=True)
        self.message_user(request, f'{updated} record(s) marked as converted.')

    @admin.action(description='Mark selected as not converted')
    def mark_not_converted(self, request, queryset):
        updated = queryset.update(converted=False)
        self.message_user(request, f'{updated} record(s) marked as not converted.')

    # ── summary panel ────────────────────────────────────────────────────────

    def changelist_view(self, request, extra_context=None):
        """Inject quick stats that the custom template will render."""
        now = timezone.now()
        extra_context = extra_context or {}
        extra_context['checklist_stats'] = {
            'total':        ChecklistEmailLog.objects.count(),
            'last_30_days': ChecklistEmailLog.objects.filter(sent_at__gte=now - timedelta(days=30)).count(),
            'last_7_days':  ChecklistEmailLog.objects.filter(sent_at__gte=now - timedelta(days=7)).count(),
            'converted':    ChecklistEmailLog.objects.filter(converted=True).count(),
        }
        return super().changelist_view(request, extra_context=extra_context)