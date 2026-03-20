# CLAUDE.md — DjangoProject

## Project Purpose

A **digital estate planning and account management** SaaS application. Users document their digital accounts, physical devices, credentials, estate/legal documents, important personal documents, and funeral preferences so that family members or designated contacts can access and act on this information when needed.

Core value proposition: guided, organized digital legacy planning with secure credential storage, delegation to trusted contacts, and a family-access recovery system.

**Subscription tiers:**
- `none` — Read-only or restricted access
- `essentials` — Full edit access for 1 year from payment date
- `legacy` — Lifetime full edit access

---

## Project Structure

```
DjangoProject/
└── topLevelProject/
    ├── topLevelProject/    # Project config (settings.py, urls.py, wsgi/asgi)
    ├── accounts/           # Auth, CustomUser, subscriptions, OAuth2
    ├── baseapp/            # Public landing page, legal pages, checklist download
    ├── dashboard/          # Core app — all user data models and CRUD views
    ├── faqs/               # Single FAQ page
    ├── recovery/           # External recovery requests (deceased/incapacitated users)
    ├── infrapps/           # Encrypted vault for credentials (Fernet)
    ├── templates/          # Global base templates
    ├── static/             # Global static assets
    ├── media/              # User-uploaded files
    ├── db.sqlite3          # Dev database
    └── manage.py
```

---

## Key Architecture Decisions

### Apps & Responsibilities

| App | Responsibility |
|-----|---------------|
| `accounts` | `CustomUser` model, subscription logic, login/registration, password reset, OAuth2 provider |
| `baseapp` | Public pages: home, checklist PDF download/email, privacy/terms/cookies/accessibility |
| `dashboard` | All user data: Profile, Account, Contact, Device, DigitalEstateDocument, ImportantDocument, FuneralPlan, FamilyNeedsToKnowSection, RelevanceReview |
| `faqs` | FAQ page only |
| `recovery` | Family-initiated recovery requests with verification tokens; admin review workflow |
| `infrapps` | Fernet-encrypted vault entries linked to accounts/devices; VaultAccessLog audit trail |

### Auth

- Custom backend: `EmailOrUsernameBackend` — users can log in with email or username
- Session-based auth for web; OAuth2 (django-oauth-toolkit) for API access
- Session timeout: 1 hour
- Account lockout after repeated failed login attempts

### Subscription Access Control

Access is enforced via CBV mixins in `dashboard/views.py`:
- `ViewAccessMixin` — allows read access based on `user.can_view_data()`
- `FullAccessMixin` — allows write/edit access based on `user.can_modify_data()`

Both methods live on `CustomUser` in `accounts/models.py`. Never bypass these mixins.

### Encryption (Vault)

- `infrapps` uses Fernet symmetric encryption for all stored credentials
- Fernet key is stored in environment variables — never hardcoded
- All vault access is logged to `VaultAccessLog`

### Database

- **Dev:** SQLite3 (`db.sqlite3`)
- **Prod:** PostgreSQL or MySQL, configured via environment variables in `settings.py`

---

## Coding Conventions

### Models

- Every model gets `created_at = DateTimeField(auto_now_add=True)` and `updated_at = DateTimeField(auto_now=True)`
- Slugs are auto-generated on save using a UUID suffix (8-char hex) to prevent collisions
- All fields include `help_text`
- Choice fields use descriptive string labels
- `__str__` returns a human-readable string
- Foreign keys to Profile use `CASCADE`; to Contact/Account/Device use `SET_NULL`

### Views

- Always use **class-based views** (CBVs): `CreateView`, `UpdateView`, `DetailView`, `ListView`, `DeleteView`
- Always apply `LoginRequiredMixin` plus the appropriate access mixin
- Use `SlugLookupMixin` for slug-based `get_object()` lookups
- Override `get_queryset()` to scope data to `request.user`

### Forms

- Use **Django Crispy Forms** with the Bootstrap5 template pack
- One form class per model in `app/forms.py`
- Customize widgets in the form's `Meta.widgets` or `__init__`

### URLs

- Slug-based URLs for all user-owned objects: `<slug:slug>/`
- App namespaces match app directory names
- Include app URLs in `topLevelProject/urls.py`

### Templates & Static Files

- Each app owns its templates at `app/templates/app/` and static files at `app/static/app/`
- Global base templates live in `topLevelProject/templates/`
- Extend a base template; use `{% block content %}` and `{% block title %}`
- Icons: Font Awesome via CDN

### Security

- Never store plaintext credentials — always encrypt via Fernet in `infrapps`
- Never log or print decrypted vault contents
- Password requirements: 12-char min, not all-numeric, not common
- XSS, CSRF, clickjacking, and content-type sniffing protections are enabled globally

---

## Common Tasks

### Debugging

1. Run `python manage.py check` first — catches config and model issues
2. After any model change: `python manage.py makemigrations && python manage.py migrate`
3. Inspect data in Django shell: `python manage.py shell`
4. Subscription/access bugs: check `user.can_view_data()` and `user.can_modify_data()` on `CustomUser`
5. Vault bugs: verify Fernet key env var is set; check `VaultAccessLog` for access history

### Adding a Feature to the Dashboard

1. Add model to `dashboard/models.py` — follow timestamp + slug pattern
2. `python manage.py makemigrations dashboard && python manage.py migrate`
3. Add form class in `dashboard/forms.py` using crispy forms
4. Add CBV in `dashboard/views.py` with `LoginRequiredMixin` + appropriate access mixin
5. Wire URL in `dashboard/urls.py` with slug pattern
6. Create templates under `dashboard/templates/dashboard/`
7. Link the new section from the dashboard home or relevant navigation

### Adding a New App

1. `python manage.py startapp <name>` inside `topLevelProject/`
2. Add to `INSTALLED_APPS` in `settings.py`
3. Create `<name>/urls.py` and include in `topLevelProject/urls.py`
4. Follow existing app structure: `models.py`, `views.py`, `forms.py`, `urls.py`, `templates/<name>/`, `static/<name>/`

### Working with Subscriptions

- Business logic for tiers lives in `accounts/models.py` (`CustomUser`)
- `essentials_expires` tracks when Essentials edit access ends
- `addon_active` / `addon_expires` for add-on features
- Enforcement is in CBV mixins in `dashboard/views.py` — always use them for new views

### Working with the Vault (infrapps)

- Entries link optionally to an `Account` or `Device`
- Encrypt before save, decrypt only on explicit user request
- Log every access in `VaultAccessLog` with user and timestamp
- Fernet key must be in environment — check `.env` or system env vars if vault breaks

### Recovery System

- External users (family) submit a `RecoveryRequest` with verification documents
- Requests go through admin review before granting access
- Verification tokens are time-limited — check expiry logic in `recovery/models.py`
