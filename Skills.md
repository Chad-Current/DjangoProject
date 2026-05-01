# Skills & Technologies

A reference of the technical skills and tools applied in this project.

---

## Backend

| Skill | Detail |
|-------|--------|
| Python | Primary language |
| Django 5.2 | Full-stack web framework; models, views, URLs, admin, middleware |
| Class-Based Views (CBVs) | CreateView, UpdateView, DetailView, ListView, DeleteView with custom mixins |
| Django ORM | Queryset scoping, FK relationships, model lifecycle hooks |
| Custom User Model | Extended `AbstractUser`; subscription tier logic on the model |
| Session Management | 1-hour timeout, HttpOnly + SameSite cookie hardening |
| Django REST Framework | API layer for OAuth2-protected endpoints |
| OAuth2 (django-oauth-toolkit) | Token issuance, rotation, and expiry for API clients |
| django-axes | Brute-force lockout, Redis-backed for multi-instance deployments |

---

## Security & Encryption

| Skill | Detail |
|-------|--------|
| Fernet (cryptography) | Symmetric encryption for vault credential storage |
| Environment-based secrets | Keys loaded from environment variables via python-decouple; never hardcoded |
| CSRF / XSS / Clickjacking | Enabled globally via Django middleware |
| Audit logging | `VaultAccessLog` records every credential access with user and timestamp |
| Access control mixins | `ViewAccessMixin` / `FullAccessMixin` enforce subscription tier on every view |

---

## Frontend Design

| Skill | Detail |
|-------|--------|
| CSS Design Tokens | Custom properties (`:root`) for a consistent color palette, fluid type scale, and font families across the entire application |
| Fluid Typography | `clamp()`-based type scale (xs → title) that scales smoothly between viewport widths without breakpoint jumps |
| Color System | Structured palette using a blue-grey primary ramp (10–70%), accent amber, and semantic dark/light text tokens |
| Google Fonts | Crimson Text (titles), Nunito (body), Inter (paragraphs), Lobster Two + Ultra (accents) loaded via CSS `@import` |
| Font Awesome | Icon library via CDN (kit `ea6a27c21b`) |
| Responsive Layout | Bootstrap 5 grid + custom CSS; mobile-first with `max-width` containers up to 1400px |
| Per-app Stylesheets | Each Django app owns its CSS under `app/static/app/css/`; base tokens declared once in `stylesheet.css` and consumed everywhere |
| Custom Scrollbar | Webkit scrollbar styling matching the brand palette |
| Print Stylesheets | Dedicated print CSS for accounts, devices, estate documents, important documents, funeral plan, and family awareness sections |
| Sticky Subnav | Dashboard section nav fixed at top (`position: sticky; z-index: 40`) with gradient background and subtle box shadow |
| Collapsible Sections | Accordion/collapse CSS for long-form dashboard content |
| Contact Node Tree | Visual tree layout CSS for contact relationship hierarchy |
| Onboarding Tooltips | Tooltip and overlay CSS for guided first-run UX |
| Progress Indicators | Progress bar CSS for dashboard completion tracking |
| Detail & Delete Views | Dedicated stylesheets for consistent detail-page and confirmation-dialog presentation |
| Vault UI | Separate stylesheet for the encrypted credential vault interface |
| Django Crispy Forms | Form rendering wired to Bootstrap5 template pack via `crispy_bootstrap5` |
| Django Template Language | Jinja-style template inheritance (`{% block %}`, `{% include %}`), static tag, and message framework integration |

---

## Payments

| Skill | Detail |
|-------|--------|
| Stripe | Recurring subscription billing (monthly and annual intervals); Essentials ($5.99/mo · $59.99/yr) and Legacy ($9.99/mo · $99.99/yr) tiers; webhook-driven status sync; view-only access retained permanently after cancellation |

---

## Infrastructure & DevOps

| Skill | Detail |
|-------|--------|
| AWS S3 (django-storages) | Media uploads and static file hosting |
| AWS SES (django-ses) | Transactional email delivery |
| AWS RDS (PostgreSQL) | Production database via psycopg2 |
| AWS ElastiCache (Redis) | Session cache and django-axes lockout state |
| AWS Secrets Manager (boto3) | Runtime secret retrieval |
| Gunicorn | WSGI production server |
| SQLite3 | Development database |

---

## Auth & Identity

| Skill | Detail |
|-------|--------|
| Custom auth backend | `EmailOrUsernameBackend` — login with email or username |
| Password policy | 12-char minimum, not all-numeric, not common |
| Recovery system | Family-initiated requests with admin review and time-limited tokens |
