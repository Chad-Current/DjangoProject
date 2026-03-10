# vault/views.py
import json 
import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
)

from dashboard.models import Profile, Account, Device
from .models import VaultEntry, VaultAccessLog

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Guard mixin — replaces AddonRequiredMixin inline for the vault app
# so this file stays self-contained. Uses the same can_access_addon()
# method defined on CustomUser in the previous implementation.
# ---------------------------------------------------------------------------

class VaultAccessMixin(LoginRequiredMixin):
    """
    Requires:
      1. User is authenticated.
      2. User has a paid subscription tier (has_paid=True).
      3. User has an active add-on (can_access_addon()).

    Non-paying users  → /accounts/payment/
    Paying, no add-on → /accounts/addon/
    """
    login_url = '/accounts/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not getattr(request.user, 'has_paid', False):
            messages.warning(
                request,
                'You need an active subscription to use the Vault.'
            )
            return redirect('accounts:payment')

        if not request.user.can_access_addon():
            messages.warning(
                request,
                'The Password Vault is part of the add-on subscription.'
            )
            return redirect('accounts:addon')

        return super().dispatch(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_profile_or_403(user):
    """Return the user's Profile or raise PermissionDenied."""
    try:
        return Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        raise PermissionDenied("Profile not found.")


def _get_client_ip(request) -> str:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------

class VaultListView(VaultAccessMixin, ListView):
    model               = VaultEntry
    template_name       = 'infrapps/infrapps_list.html'
    context_object_name = 'entries'
    paginate_by         = 20

    def get_queryset(self):
        profile = _get_profile_or_403(self.request.user)
        qs = VaultEntry.objects.filter(profile=profile).select_related(
            'linked_account', 'linked_device'
        )

        # Optional filter by type
        entry_type = self.request.GET.get('type')
        if entry_type in ('account', 'device', 'other'):
            qs = qs.filter(entry_type=entry_type)

        return qs.order_by('-updated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = _get_profile_or_403(self.request.user)
        context['can_modify']    = self.request.user.can_modify_data()
        context['addon_active']  = self.request.user.can_access_addon()
        context['total_entries'] = VaultEntry.objects.filter(profile=profile).count()
        context['current_type']  = self.request.GET.get('type', '')
        return context


# ---------------------------------------------------------------------------
# DETAIL
# ---------------------------------------------------------------------------

class VaultDetailView(VaultAccessMixin, DetailView):
    model               = VaultEntry
    template_name       = 'infrapps/infrapps_detail.html'
    context_object_name = 'entry'
    slug_field          = 'slug'
    slug_url_kwarg      = 'slug'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        profile = _get_profile_or_403(self.request.user)
        if obj.profile != profile:
            raise PermissionDenied("You don't have permission to view this entry.")
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_modify'] = self.request.user.can_modify_data()
        # Password is NOT decrypted here — only via the reveal AJAX endpoint.
        return context


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

class VaultCreateView(VaultAccessMixin, CreateView):
    model         = VaultEntry
    template_name = 'infrapps/infrapps_form.html'
    # Fields handled manually — password goes through set_password(), not directly
    fields = [
        'entry_type',
        'label',
        'linked_account',
        'linked_device',
        'username_or_email',
        'notes',
    ]

    def get_success_url(self):
        return reverse('vault:vault_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        profile = _get_profile_or_403(self.request.user)

        # Scope FK dropdowns to the user's own data
        form.fields['linked_account'].queryset = Account.objects.filter(
            profile=profile
        ).order_by('account_name_or_provider')
        form.fields['linked_device'].queryset = Device.objects.filter(
            profile=profile
        ).order_by('device_name')

        form.fields['linked_account'].required = False
        form.fields['linked_device'].required  = False
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['addon_active'] = self.request.user.can_access_addon()
        context['page_title']   = 'Add Vault Entry'
        context['submit_label'] = 'Save Entry'
        return context

    def form_valid(self, form):
        if not self.request.user.can_modify_data():
            messages.error(self.request, "Your subscription does not allow adding entries.")
            return redirect('vault:vault_list')

        profile = _get_profile_or_403(self.request.user)
        entry   = form.save(commit=False)
        entry.profile = profile

        # Encrypt the raw password submitted in the extra field
        raw_password = self.request.POST.get('raw_password', '').strip()
        if not raw_password:
            form.add_error(None, "A password is required.")
            return self.form_invalid(form)

        entry.set_password(raw_password)

        # Auto-derive entry_type from which FK is set
        if entry.linked_account_id and not entry.linked_device_id:
            entry.entry_type = 'account'
        elif entry.linked_device_id and not entry.linked_account_id:
            entry.entry_type = 'device'

        entry.save()
        messages.success(self.request, f'"{entry.label}" saved to your vault.')
        logger.info("VaultEntry %s created by %s", entry.pk, self.request.user.email)
        return redirect(self.get_success_url())


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

class VaultUpdateView(VaultAccessMixin, UpdateView):
    model         = VaultEntry
    template_name = 'infrapps/infrapps_form.html'
    slug_field    = 'slug'
    slug_url_kwarg = 'slug'
    fields = [
        'entry_type',
        'label',
        'linked_account',
        'linked_device',
        'username_or_email',
        'notes',
    ]

    def get_success_url(self):
        return reverse('vault:vault_detail', kwargs={'slug': self.object.slug})

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        profile = _get_profile_or_403(self.request.user)
        if obj.profile != profile:
            raise PermissionDenied("You don't have permission to edit this entry.")
        return obj

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        profile = _get_profile_or_403(self.request.user)

        form.fields['linked_account'].queryset = Account.objects.filter(
            profile=profile
        ).order_by('account_name_or_provider')
        form.fields['linked_device'].queryset = Device.objects.filter(
            profile=profile
        ).order_by('device_name')

        form.fields['linked_account'].required = False
        form.fields['linked_device'].required  = False
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['addon_active']    = self.request.user.can_access_addon()
        context['page_title']      = f'Edit — {self.object.label}'
        context['submit_label']    = 'Update Entry'
        context['is_update']       = True
        # Tell the template whether the user left raw_password blank (= keep existing)
        context['password_optional'] = True
        return context

    def form_valid(self, form):
        if not self.request.user.can_modify_data():
            messages.error(self.request, "Your subscription does not allow editing entries.")
            return redirect('vault:vault_list')

        entry        = form.save(commit=False)
        raw_password = self.request.POST.get('raw_password', '').strip()

        # Only re-encrypt if a new password was supplied; otherwise keep the old token
        if raw_password:
            entry.set_password(raw_password)

        entry.save()
        messages.success(self.request, f'"{entry.label}" updated.')
        logger.info("VaultEntry %s updated by %s", entry.pk, self.request.user.email)
        return redirect(self.get_success_url())


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

class VaultDeleteView(VaultAccessMixin, DeleteView):
    model          = VaultEntry
    template_name  = 'infrapps/infrapps_confirm_delete.html'
    success_url    = reverse_lazy('vault:vault_list')
    slug_field     = 'slug'
    slug_url_kwarg = 'slug'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        profile = _get_profile_or_403(self.request.user)
        if obj.profile != profile:
            raise PermissionDenied("You don't have permission to delete this entry.")
        return obj

    def delete(self, request, *args, **kwargs):
        if not request.user.can_modify_data():
            messages.error(request, "Your subscription does not allow deleting entries.")
            return redirect('vault:vault_list')
        entry = self.get_object()
        label = entry.label
        entry.delete()
        messages.success(request, f'"{label}" removed from your vault.')
        logger.info("VaultEntry '%s' deleted by %s", label, request.user.email)
        return redirect(self.success_url)


# ---------------------------------------------------------------------------
# REVEAL PASSWORD  (AJAX POST — never GET)
# ---------------------------------------------------------------------------

class VaultRevealPasswordView(VaultAccessMixin, View):
    """
    POST /vault/<slug>/reveal/
    Returns the decrypted password as JSON and writes an audit log entry.
    The password is NEVER embedded in a page — only returned on explicit request.
    """

    def post(self, request, slug):
        if not request.user.can_access_addon():
            return JsonResponse({'success': False, 'error': 'Add-on required.'}, status=403)

        try:
            profile = _get_profile_or_403(request.user)
            entry   = VaultEntry.objects.get(slug=slug, profile=profile)
        except VaultEntry.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Entry not found.'}, status=404)
        except PermissionDenied as exc:
            return JsonResponse({'success': False, 'error': str(exc)}, status=403)

        plaintext = entry.get_password()

        # Write audit log
        VaultAccessLog.objects.create(
            entry       = entry,
            accessed_by = request.user,
            ip_address  = _get_client_ip(request),
        )
        logger.info(
            "VaultEntry %s revealed by %s from %s",
            entry.pk, request.user.email, _get_client_ip(request),
        )

        return JsonResponse({'success': True, 'password': plaintext})

    def get(self, request, slug):
        return JsonResponse(
            {'success': False, 'error': 'Use POST to reveal a password.'},
            status=405,
        )
        
        
class AWSArchitectureView(LoginRequiredMixin, View):
    """
    Renders the interactive AWS architecture diagram.
    Accessible only to authenticated users (staff or any logged-in user — adjust as needed).
    """
    template_name = 'infrapps/aws_architecture.html'
    login_url = '/accounts/login/'

    def get(self, request):
        context = {
            'page_title': 'AWS Architecture',
            'layers_json':   json.dumps(LAYERS),
            'bands_json':    json.dumps(BANDS),
            'pillars_json':  json.dumps(PILLARS),
            'vpc_meta_json': json.dumps(VPC_META),
            'cost_chips_json': json.dumps(COST_CHIPS),
            'scale_path_json': json.dumps(SCALE_PATH),
        }
        return render(request, self.template_name, context)


# ── Data definitions ──────────────────────────────────────────────────────────

COST_CHIPS = [
    {"label": "Year 1 / month", "val": "~$115", "color": "#10b981"},
    {"label": "Year 3 / month", "val": "~$280", "color": "#3b82f6"},
    {"label": "Primary Region",  "val": "us-east-1", "color": "#a855f7"},
    {"label": "Users Y1",        "val": "50",    "color": "#f59e0b"},
    {"label": "Users Y3",        "val": "500",   "color": "#f97316"},
    {"label": "Uptime SLA",      "val": "99.9%", "color": "#06b6d4"},
]

LAYERS = [
    {"key": "edge",    "label": "Edge",          "color": "#f97316"},
    {"key": "waf",     "label": "Security",      "color": "#ef4444"},
    {"key": "alb",     "label": "Load Balancer", "color": "#a855f7"},
    {"key": "app",     "label": "Application",   "color": "#3b82f6"},
    {"key": "data",    "label": "Data",          "color": "#10b981"},
    {"key": "storage", "label": "Storage",       "color": "#f59e0b"},
    {"key": "obs",     "label": "Observability", "color": "#06b6d4"},
    {"key": "cicd",    "label": "CI/CD",         "color": "#ec4899"},
]

BANDS = [
    {
        "key": "edge", "label": "// LAYER 1 — EDGE & DNS", "cost": "~$3/mo",
        "services": [
            {
                "id": "route53", "icon": "🌐", "name": "Route 53",
                "sub": "DNS + Health Checks", "tier": "Standard — $0.50/hosted zone",
                "tag": "DNS",
                "details": [
                    "Hosted zone: yourdomain.com",
                    "A record → ALB DNS name (alias)",
                    "www CNAME → yourdomain.com",
                    "SPF / DKIM / DMARC TXT records for SES",
                    "Health check: $0.50/check/month",
                    "Failover routing to DR region",
                ],
            },
            {
                "id": "cloudfront", "icon": "⚡", "name": "CloudFront",
                "sub": "CDN — Static assets", "tier": "Standard — $0.0085/10k req",
                "tag": "CDN",
                "details": [
                    "Origin: yourapp-static S3 bucket",
                    "Origin Access Control — direct S3 access blocked",
                    "Price class: North America + Europe",
                    "Compress objects: enabled",
                    "Cache policy: CachingOptimized",
                    "HTTPS only — HTTP redirected to HTTPS",
                    "Serves CSS, JS, images — approx $2/mo",
                ],
            },
        ],
    },
    {
        "key": "waf", "label": "// LAYER 2 — WEB APPLICATION FIREWALL", "cost": "~$8/mo",
        "services": [
            {
                "id": "waf", "icon": "🛡️", "name": "AWS WAF",
                "sub": "OWASP Top 10 + Rate Limit", "tier": "Standard — $5/ACL + $1/rule/mo",
                "tag": "SECURITY",
                "details": [
                    "Attached to ALB (regional)",
                    "Rule: AWSManagedRulesCommonRuleSet (XSS, SQLi)",
                    "Rule: AWSManagedRulesKnownBadInputsRuleSet",
                    "Rule: AWSManagedRulesAmazonIpReputationList",
                    "Rate limit: 2,000 req / 5 min per IP — Block",
                    "Restrict /admin/ to internal IP via WAF rule",
                    "WAF logs → CloudWatch for analysis",
                ],
            },
            {
                "id": "shield", "icon": "🔰", "name": "Shield Standard",
                "sub": "DDoS Protection", "tier": "Free — auto-enabled on ALB",
                "tag": "FREE",
                "details": [
                    "Automatically protects ALB and CloudFront",
                    "Layer 3/4 DDoS mitigation included free",
                    "Covers volumetric and state-exhaustion attacks",
                    "Upgrade to Shield Advanced only if targeted attacks occur",
                ],
            },
        ],
    },
    {
        "key": "alb", "label": "// LAYER 3 — LOAD BALANCER & TLS TERMINATION", "cost": "~$18/mo",
        "services": [
            {
                "id": "acm", "icon": "🔒", "name": "ACM Certificate",
                "sub": "SSL/TLS — free, auto-renews", "tier": "Free for ALB-attached certs",
                "tag": "FREE",
                "details": [
                    "Covers yourdomain.com + www.yourdomain.com",
                    "DNS validation via Route 53 CNAME (automatic)",
                    "Auto-renews 60 days before expiry",
                    "TLS 1.2+ policy: TLS13-1-2-2021-06",
                    "Zero manual renewal effort required",
                ],
            },
            {
                "id": "alb", "icon": "⚖️", "name": "App Load Balancer",
                "sub": "HTTP→HTTPS redirect + routing", "tier": "~$16/mo base + LCU",
                "tag": "ALB",
                "details": [
                    "Port 80 listener: 301 permanent redirect to HTTPS",
                    "Port 443 listener: forward to EC2 target group",
                    "Target group: yourapp-ec2-targets (port 8000)",
                    "Health check: GET /accounts/login/ — expects 200",
                    "Healthy threshold: 2, Unhealthy: 3, Interval: 30s",
                    "Spans public-1a + public-1b across 2 AZs",
                    "Sticky sessions: disabled — Redis handles state",
                ],
            },
        ],
    },
    {
        "key": "app", "label": "// LAYER 4 — APPLICATION TIER (PRIVATE SUBNET VIA NAT)", "cost": "~$50/mo",
        "services": [
            {
                "id": "ec2", "icon": "🖥️", "name": "EC2 Auto Scaling",
                "sub": "Django + Gunicorn", "tier": "t3.small ($15/mo) × 1–4 instances",
                "tag": "COMPUTE",
                "details": [
                    "AMI: Amazon Linux 2023",
                    "Year 1: t3.small (2vCPU, 2GB RAM)",
                    "Year 3: upgrade to t3.medium",
                    "Min: 1, Desired: 2, Max: 4 instances",
                    "CPU > 70% triggers scale-out event",
                    "ASG spans public-1a + public-1b",
                    "IAM role: yourapp-ec2-role (no stored credentials)",
                    "EBS: 20GB gp3 — KMS encrypted",
                ],
            },
            {
                "id": "gunicorn", "icon": "🐍", "name": "Django / Gunicorn",
                "sub": "Python WSGI — 3 workers", "tier": "App code running on EC2",
                "tag": "APP",
                "details": [
                    "Django — DEBUG=False in production",
                    "Gunicorn: 3 workers, port 8000, timeout 120s",
                    "Custom user model: Essentials + Legacy tiers",
                    "Subscription gate: PaidUserRequiredMixin",
                    "Slug-based URLs for all resources",
                    "Secrets loaded from Secrets Manager at startup",
                    "SECURE_SSL_REDIRECT = True, HSTS enabled",
                ],
            },
            {
                "id": "nat", "icon": "🔁", "name": "NAT Gateway",
                "sub": "Outbound internet — private subnets", "tier": "$0.045/hr — ~$33/mo",
                "tag": "NETWORK",
                "details": [
                    "Placed in public-1a subnet",
                    "Routes outbound traffic for EC2, RDS patching",
                    "LARGEST single cost item Year 1 (~$33/mo)",
                    "Year 1 saving: swap for NAT Instance (t3.nano) = ~$3/mo",
                    "S3 + SES VPC endpoints bypass NAT entirely (free)",
                    "Add second NAT Gateway in 1b for HA in Year 2",
                ],
            },
        ],
    },
    {
        "key": "data", "label": "// LAYER 5 — DATA TIER (PRIVATE SUBNET — ZERO INTERNET ACCESS)", "cost": "~$28/mo",
        "services": [
            {
                "id": "rds", "icon": "🗄️", "name": "RDS PostgreSQL",
                "sub": "db.t3.micro — KMS encrypted", "tier": "~$15/mo + $2.30 storage",
                "tag": "DATABASE",
                "details": [
                    "Engine: PostgreSQL 16.x (latest)",
                    "Year 1: db.t3.micro — Year 3: db.t3.small",
                    "Storage: 20GB gp3, autoscale to 100GB",
                    "Public Access: NO — private subnet only",
                    "Multi-AZ: disabled Year 1, enable Year 2",
                    "Backups: 7-day retention at 02:00 UTC",
                    "KMS encryption with CMK alias/yourapp-production",
                    "Django: sslmode=require for all connections",
                ],
            },
            {
                "id": "redis", "icon": "🔴", "name": "ElastiCache Redis",
                "sub": "Sessions + caching — private subnet", "tier": "cache.t3.micro — ~$13/mo",
                "tag": "CACHE",
                "details": [
                    "Replaces DB-backed Django sessions",
                    "SESSION_ENGINE = backends.cache",
                    "SESSION_COOKIE_AGE = 3600 (1 hour)",
                    "In-transit encryption: TLS required",
                    "At-rest encryption: enabled",
                    "Auth token: required for all connections",
                    "Private subnet only — security group sg-cache",
                ],
            },
        ],
    },
    {
        "key": "storage", "label": "// LAYER 6 — STORAGE, SECRETS & ENCRYPTION", "cost": "~$12/mo",
        "services": [
            {
                "id": "s3-media", "icon": "📁", "name": "S3 Media Bucket",
                "sub": "Estate docs — private + versioned", "tier": "$0.023/GB/mo",
                "tag": "PRIVATE",
                "details": [
                    "yourapp-media-production",
                    "All public access: BLOCKED",
                    "Encryption: SSE-KMS with CMK",
                    "Versioning: enabled (delete recovery)",
                    "Cross-region replication → us-west-2",
                    "Stores: estate_file, important_file uploads",
                    "Access: pre-signed URLs with 1-hour expiry",
                ],
            },
            {
                "id": "s3-static", "icon": "📦", "name": "S3 Static Bucket",
                "sub": "CSS, JS, images — public via CDN", "tier": "$0.023/GB/mo",
                "tag": "PUBLIC",
                "details": [
                    "yourapp-static-production",
                    "Served exclusively via CloudFront CDN",
                    "SSE-S3 encryption (public assets)",
                    "Django collectstatic → S3 on each deploy",
                    "Cache-Control: max-age=86400",
                ],
            },
            {
                "id": "secrets", "icon": "🔑", "name": "Secrets Manager",
                "sub": "All credentials — zero hardcoding", "tier": "$0.40/secret/mo",
                "tag": "SECRETS",
                "details": [
                    "Secret path: yourapp/production/config",
                    "Stores: DJANGO_SECRET_KEY, DB_PASSWORD",
                    "Stores: DB_HOST, REDIS_URL, KMS_KEY_ID",
                    "Stores: SES credentials, S3 bucket names",
                    "Loaded at Django startup via boto3",
                    "EC2 IAM role has read access — no disk credentials",
                ],
            },
            {
                "id": "kms", "icon": "🛡", "name": "KMS CMK",
                "sub": "Master encryption key", "tier": "$1/key/mo + $0.03/10k API",
                "tag": "ENCRYPT",
                "details": [
                    "Alias: alias/yourapp-production",
                    "Type: Symmetric AES-256",
                    "Encrypts: RDS database at rest",
                    "Encrypts: S3 media bucket (SSE-KMS)",
                    "Encrypts: EBS root volumes on EC2",
                    "Encrypts: Secrets Manager secrets",
                    "Key user: yourapp-ec2-role only",
                ],
            },
        ],
    },
    {
        "key": "obs", "label": "// LAYER 7 — OBSERVABILITY, LOGGING & EMAIL", "cost": "~$8/mo",
        "services": [
            {
                "id": "cloudwatch", "icon": "📊", "name": "CloudWatch",
                "sub": "Logs + Alarms + Metrics", "tier": "$0.50/GB ingested",
                "tag": "MONITORING",
                "details": [
                    "Log groups: /yourapp/production/django",
                    "Log groups: gunicorn, nginx, rds/postgresql",
                    "Alarm: ALB 5xx errors > 10/min",
                    "Alarm: EC2 CPU > 80% for 5 minutes",
                    "Alarm: RDS free storage < 2GB",
                    "Alarm: Failed logins > 50/hour (metric filter)",
                    "SNS topic → email for all alerts",
                ],
            },
            {
                "id": "cloudtrail", "icon": "📋", "name": "CloudTrail",
                "sub": "Full API audit — all regions", "tier": "~$2/mo after free tier",
                "tag": "AUDIT",
                "details": [
                    "Trail: production-audit-trail",
                    "All regions: enabled",
                    "Logs every AWS API call made in account",
                    "S3 bucket: yourapp-cloudtrail-logs",
                    "CloudWatch Logs integration enabled",
                    "Required for security incident investigation",
                ],
            },
            {
                "id": "ses", "icon": "📧", "name": "Amazon SES",
                "sub": "Transactional email", "tier": "Free < 62k emails/mo from EC2",
                "tag": "EMAIL",
                "details": [
                    "Domain verified: yourdomain.com",
                    "DKIM + SPF + DMARC records in Route 53",
                    "Replaces console EMAIL_BACKEND in production",
                    "Sends: Essentials expiry warnings at 30/7/1 days",
                    "Sends: tier upgrade confirmations",
                    "Sends: password reset emails",
                    "Sends: checklist PDF to prospects",
                    "Requires production access request (out of sandbox)",
                ],
            },
        ],
    },
    {
        "key": "cicd", "label": "// LAYER 8 — CI/CD & DEPLOYMENT PIPELINE", "cost": "~$2/mo",
        "services": [
            {
                "id": "codepipeline", "icon": "🔄", "name": "CodePipeline",
                "sub": "GitHub → auto-deploy on push", "tier": "$1/active pipeline/mo",
                "tag": "PIPELINE",
                "details": [
                    "Source: GitHub main branch trigger",
                    "Push to main → automatic deploy",
                    "Build: CodeBuild (optional — run tests)",
                    "Deploy: CodeDeploy to Auto Scaling Group",
                    "Zero-downtime: OneAtATime rolling config",
                    "appspec.yml in repository root",
                ],
            },
            {
                "id": "codedeploy", "icon": "🚀", "name": "CodeDeploy",
                "sub": "Rolling deploy to ASG", "tier": "Free for EC2",
                "tag": "DEPLOY",
                "details": [
                    "Application: yourapp-production",
                    "Deployment group: yourapp-production-group",
                    "Hooks: stop → install deps → migrate → collectstatic → start",
                    "Auto rollback on health check failure",
                    "Agent installed via EC2 User Data bootstrap",
                ],
            },
            {
                "id": "backup", "icon": "💾", "name": "AWS Backup",
                "sub": "RDS + EBS automated policy", "tier": "$0.05/GB/mo",
                "tag": "BACKUP",
                "details": [
                    "Daily backups: 7-day retention",
                    "Weekly backups: 1-month retention",
                    "Monthly backups: 1-year retention",
                    "Cross-region copy → us-west-2 for DR",
                    "Vault encrypted with KMS CMK",
                    "RDS PITR: restore to any second within 7 days",
                    "S3 versioning covers individual file recovery",
                ],
            },
        ],
    },
]

VPC_META = {
    "cidr": "10.0.0.0/16",
    "region_primary": "us-east-1",
    "azs": "us-east-1a + us-east-1b",
    "note": "Public subnets: EC2 + ALB  ·  Private subnets: RDS + Redis (zero internet inbound)",
    "region_dr": "us-west-2",
    "sgs": [
        "sg-alb: port 443 inbound from 0.0.0.0/0",
        "sg-app: port 8000 from sg-alb ONLY",
        "sg-db: port 5432 from sg-app ONLY",
        "sg-cache: port 6379 from sg-app ONLY",
    ],
}

PILLARS = [
    {"icon": "🔒", "label": "Encryption",     "value": "KMS CMK — RDS, S3, EBS, Redis, Secrets at rest + TLS in transit everywhere"},
    {"icon": "🛡️", "label": "Network",        "value": "VPC isolation — database and cache never reachable from internet, sg least-privilege"},
    {"icon": "🔑", "label": "Auth & Secrets", "value": "IAM roles on EC2, zero stored credentials on disk, Secrets Manager for all config"},
    {"icon": "📊", "label": "Observability",  "value": "CloudWatch logs and alarms, CloudTrail full API audit, failed-login metric filter"},
    {"icon": "♻️", "label": "Recovery",       "value": "RDS PITR 7 days, S3 versioning, cross-region backup to us-west-2, ASG auto-replace"},
]

SCALE_PATH = [
    {"year": "LAUNCH",  "users": "50 users",  "cost": "~$115/mo", "color": "#10b981"},
    {"year": "YEAR 1",  "users": "100 users", "cost": "~$140/mo", "color": "#3b82f6"},
    {"year": "YEAR 2",  "users": "250 users", "cost": "~$200/mo", "color": "#a855f7"},
    {"year": "YEAR 3",  "users": "500 users", "cost": "~$280/mo", "color": "#f97316"},
]