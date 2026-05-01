# AWS Deployment Guide — Digital Estate Planning SaaS

**Target:** AWS (us-east-1 primary)
**Stack:** Django 5.2 · Gunicorn · RDS PostgreSQL · ElastiCache Redis · S3 · SES · EC2 Auto Scaling · ALB
**Timeline:** ~8 weeks to production

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Pre-Deployment Checklist](#2-pre-deployment-checklist)
3. [Phase 1 — AWS Account & IAM Setup](#3-phase-1--aws-account--iam-setup)
4. [Phase 2 — Network Infrastructure (VPC)](#4-phase-2--network-infrastructure-vpc)
5. [Phase 3 — Data Tier (RDS + ElastiCache)](#5-phase-3--data-tier-rds--elasticache)
6. [Phase 4 — Secrets Manager](#6-phase-4--secrets-manager)
7. [Phase 5 — S3 Buckets & CloudFront](#7-phase-5--s3-buckets--cloudfront)
8. [Phase 6 — Amazon SES (Email)](#8-phase-6--amazon-ses-email)
9. [Phase 6b — Stripe Webhook Configuration](#9-phase-6b--stripe-webhook-configuration)
10. [Phase 7 — EC2 & Application Setup](#10-phase-7--ec2--application-setup)
11. [Phase 8 — Load Balancer & HTTPS](#11-phase-8--load-balancer--https)
12. [Phase 9 — Production Settings](#12-phase-9--production-settings)
13. [Phase 10 — CI/CD Pipeline](#13-phase-10--cicd-pipeline)
14. [Phase 11 — WAF & Security](#14-phase-11--waf--security)
15. [Phase 12 — Monitoring & Alarms](#15-phase-12--monitoring--alarms)
16. [Go-Live Checklist](#16-go-live-checklist)
17. [Cost Estimate](#17-cost-estimate)
18. [Post-Launch Runbook](#18-post-launch-runbook)

---

## 1. Architecture Overview

```
Internet
    │
    ▼
Route 53 (DNS)
    │
    ▼
CloudFront (CDN — static assets only)
    │
    ▼
AWS WAF ──── blocks OWASP Top 10, rate limits
    │
    ▼
Application Load Balancer (HTTPS :443, HTTP :80 → redirect)
    │
    ├── EC2 Auto Scaling Group (Django + Gunicorn, private subnet)
    │       │
    │       ├── RDS PostgreSQL (private subnet, no internet access)
    │       ├── ElastiCache Redis (private subnet, sessions + cache)
    │       └── Secrets Manager (IAM role — no stored credentials)
    │
    └── S3 Media Bucket (estate docs, recovery files — private)
        S3 Static Bucket (CSS/JS/images — served via CloudFront)
```

**Why this architecture for your app specifically:**

- **Private subnets for RDS and Redis** — Your vault stores Fernet-encrypted credentials and your users store estate documents. The database must never be reachable from the internet. Private subnets enforce this at the network layer, not just via security groups.
- **ElastiCache Redis for sessions** — Your current DB-backed sessions won't work correctly across two EC2 instances. User A hits instance 1, logs in, session stored in DB. User A's next request goes to instance 2 — session lookup still works because DB is shared. But with Auto Scaling terminating instances, you need a dedicated session store. Redis is the right answer.
- **Secrets Manager for VAULT_ENCRYPTION_KEY** — This key protects every password in the vault. It must never be in an environment file, never in Git, never on disk. Secrets Manager + IAM role is the only correct approach.
- **S3 for media** — Recovery requests include file uploads (death certificates, legal authorization). These must be stored durably outside the EC2 instance, which can be terminated at any time.

---

## 2. Pre-Deployment Checklist

Complete these before touching AWS.

### 2a. Code Preparation

**Register a domain name** (you need this before requesting an SSL certificate)

**Option A — Register via Route 53 (recommended):**
1. Go to Route 53 → Registered Domains → Register Domain
2. Search for your desired name (e.g., `myestateplanning.com`) — prices start at ~$12/year for `.com`
3. Complete the registrant contact form and confirm the registration email
4. Route 53 automatically creates a **hosted zone** for your domain — you're done; no extra steps needed
5. Note the 4 nameserver (NS) records in the hosted zone — they already match your domain registration

**Option B — Use an existing registrar (GoDaddy, Namecheap, etc.):**
1. Purchase your domain from the registrar as normal
2. In AWS → Route 53 → Hosted Zones → Create Hosted Zone
   - Domain name: `yourdomain.com`
   - Type: Public hosted zone
3. After creation, Route 53 shows 4 NS records (e.g., `ns-123.awsdns-45.com`)
4. Log in to your registrar and replace the default nameservers with these 4 AWS nameservers
5. Propagation takes 24–48 hours — all DNS records you add to Route 53 will resolve once propagation completes

**Why Route 53 for DNS even if you bought the domain elsewhere:** SES, ACM, and CloudFront all integrate directly with Route 53 — you can add verification records with one click instead of copying values manually into a third-party registrar.

**Create a `.env.example` file** (document all required env vars):
```
DJANGO_SECRET_KEY=
DJANGO_SETTINGS_MODULE=topLevelProject.settings
DB_NAME=
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=5432
REDIS_URL=
VAULT_ENCRYPTION_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_MEDIA_BUCKET_NAME=
AWS_S3_REGION_NAME=us-east-1
AWS_CLOUDFRONT_DOMAIN=
SES_ACCESS_KEY_ID=
SES_SECRET_ACCESS_KEY=
DEFAULT_FROM_EMAIL=
SITE_URL=https://yourdomain.com
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_ESSENTIALS_MONTHLY_PRICE_ID=price_...
STRIPE_ESSENTIALS_ANNUAL_PRICE_ID=price_...
STRIPE_LEGACY_MONTHLY_PRICE_ID=price_...
STRIPE_LEGACY_ANNUAL_PRICE_ID=price_...
```

**Never commit `.env` to Git.** Verify your `.gitignore` contains:
```
.env
*.pyc
__pycache__/
db.sqlite3
/media/
/static/
```

**Generate your Fernet key now and store it somewhere safe** (you'll put it in Secrets Manager):
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
This is the `VAULT_ENCRYPTION_KEY`. Generate it exactly once. If you ever regenerate it, every vault entry becomes permanently unreadable.

**Generate a strong Django secret key:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 2b. Database Migration Plan

Your development database is SQLite. PostgreSQL handles most things the same way but there are a few differences to be aware of:

- `IntegerField` in SQLite accepts strings silently; PostgreSQL will reject them. Your `zipcode = models.IntegerField(blank=True, null=True)` on Contact is fine since it's nullable.
- All your `CharField` choices are validated at the form level, not the DB level in either engine — no changes needed.
- Run `python manage.py check --deploy` locally before deploying. It will surface any settings issues.

### 2c. Static Files Audit

Run this locally to confirm collectstatic works:
```bash
python manage.py collectstatic --dry-run
```
Fix any errors before deploying. Common issue: template references a static file that doesn't exist on disk.

### 2d. Python Version Compatibility Check

**Critical:** Your local environment runs Python 3.14 (confirmed by `__pycache__/cpython-314.pyc` files). Amazon Linux 2023 ships Python 3.11 via `dnf` and Python 3.14 is **not available** as a package. If your code uses any Python 3.12+ syntax or features, it will fail on the server.

**Test locally before deploying:**
```bash
# Create a 3.11 venv and test the app starts cleanly
python3.11 -m venv venv311
source venv311/bin/activate
pip install -r requirements.txt
python manage.py check
deactivate
rm -rf venv311
```
If `python3.11` is not installed locally on Windows, test via WSL or Docker:
```bash
docker run --rm -v "$(pwd):/app" -w /app python:3.11-slim \
  sh -c "pip install -r requirements.txt && python manage.py check"
```

**If the check passes on 3.11:** Use Python 3.11 on the server (Phase 7 uses 3.11). The `__pycache__` files will be regenerated automatically — no action needed.

**If you need Python 3.14 on the server** (e.g., you're using 3.12+ syntax like `type X = Y`), compile from source in Phase 7. Add these steps *before* the `pip install` step:
```bash
sudo dnf install -y gcc openssl-devel bzip2-devel libffi-devel zlib-devel wget make
cd /tmp
wget https://www.python.org/ftp/python/3.14.0/Python-3.14.0.tgz
tar -xzf Python-3.14.0.tgz
cd Python-3.14.0
./configure --enable-optimizations
make -j$(nproc)
sudo make altinstall   # installs as python3.14 — does NOT replace system python3
```
Then replace `python3.11` with `python3.14` everywhere in Phase 7.

---

## 3. Phase 1 — AWS Account & IAM Setup

**Time: ~2 hours**

### 3a. AWS Account

If using a personal account, enable MFA on the root account immediately and do not use the root account for anything else. Create an IAM admin user for all daily work.

### 3b. IAM Roles (not users)

EC2 instances authenticate to AWS services via IAM roles, not stored credentials. This is critical — never put AWS access keys on an EC2 instance or in your settings.

**Create role: `digitalEstate-ec2-role`**

Go to IAM → Roles → Create Role → EC2 use case.

Attach these policies (create them as inline or managed):

**Policy 1 — Secrets Manager (read only):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:YOUR_ACCOUNT_ID:secret:digitalEstate/production/*"
    }
  ]
}
```

**Policy 2 — S3 (media bucket full, static bucket read):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::digitalEstate-media-production",
        "arn:aws:s3:::digitalEstate-media-production/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::digitalEstate-static-production",
        "arn:aws:s3:::digitalEstate-static-production/*"
      ]
    }
  ]
}
```

**Policy 3 — SES (send email only):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ses:SendEmail", "ses:SendRawEmail"],
      "Resource": "*"
    }
  ]
}
```

**Policy 4 — CloudWatch Logs (application logging):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:us-east-1:YOUR_ACCOUNT_ID:log-group:/digitalEstate/*"
    }
  ]
}
```

**Why role-based instead of access keys:** If an EC2 instance is compromised and has stored access keys, an attacker exfiltrates the keys and retains access forever. With IAM roles, the temporary credentials rotate automatically every few hours and are only valid from that specific EC2 instance.

---

## 4. Phase 2 — Network Infrastructure (VPC)

**Time: ~1 hour**

### 4a. Create VPC

VPC → Create VPC

- **CIDR:** `10.0.0.0/16` (gives you 65,536 addresses — plenty of room)
- **Name:** `digitalEstate-vpc`
- Enable DNS hostnames: Yes
- Enable DNS resolution: Yes

### 4b. Subnets

Create 4 subnets across 2 Availability Zones. Using 2 AZs means if one AWS data center has an outage, your app stays up.

| Name | AZ | CIDR | Type |
|------|----|------|------|
| `public-1a` | us-east-1a | 10.0.1.0/24 | Public (ALB + NAT Gateway) |
| `public-1b` | us-east-1b | 10.0.2.0/24 | Public (ALB) |
| `private-1a` | us-east-1a | 10.0.11.0/24 | Private (EC2, RDS, Redis) |
| `private-1b` | us-east-1b | 10.0.12.0/24 | Private (EC2, RDS, Redis) |

**Why public/private split:** Your EC2 instances should not have public IP addresses. The ALB sits in the public subnets and forwards traffic to EC2 in private subnets. Your database and Redis have no path to the internet at all — even if someone found a vulnerability, they cannot exfiltrate data over the network.

### 4c. Internet Gateway

VPC → Internet Gateways → Create → attach to `digitalEstate-vpc`

### 4d. NAT Gateway

EC2 instances in private subnets need outbound internet access (to download packages, reach Secrets Manager, reach SES). NAT Gateway provides outbound-only internet.

- Create in `public-1a`
- Allocate an Elastic IP for it
- **Cost note:** NAT Gateway costs ~$0.045/hr (~$33/month). This is your largest single cost. At launch, consider a NAT Instance (t3.nano, ~$3/month) and upgrade later.

### 4e. Route Tables

**Public route table** (attach to public-1a, public-1b):
- `0.0.0.0/0` → Internet Gateway

**Private route table** (attach to private-1a, private-1b):
- `0.0.0.0/0` → NAT Gateway

### 4f. Security Groups

Security groups are stateful firewalls. Create these:

**`sg-alb` — Application Load Balancer:**
- Inbound: TCP 443 from `0.0.0.0/0`
- Inbound: TCP 80 from `0.0.0.0/0` (for HTTP→HTTPS redirect)
- Outbound: TCP 8000 to `sg-app`

**`sg-app` — EC2 Application Servers:**
- Inbound: TCP 8000 from `sg-alb` ONLY (never from the internet directly)
- Inbound: TCP 22 from your office IP only (for SSH during setup; remove later)
- Outbound: TCP 5432 to `sg-db`
- Outbound: TCP 6379 to `sg-cache`
- Outbound: TCP 443 to `0.0.0.0/0` (for Secrets Manager, SES, S3 via HTTPS)

**`sg-db` — RDS PostgreSQL:**
- Inbound: TCP 5432 from `sg-app` ONLY
- No outbound needed (RDS manages its own)

**`sg-cache` — ElastiCache Redis:**
- Inbound: TCP 6379 from `sg-app` ONLY
- No outbound needed

**Why this layered approach:** Even if your Django application had a critical vulnerability, an attacker who gained RCE on EC2 still cannot connect to your database from outside the VPC, cannot connect to Redis, and cannot reach the internet except through defined outbound rules.

---

## 5. Phase 3 — Data Tier (RDS + ElastiCache)

**Time: ~1 hour setup, ~10 minutes to provision**

### 5a. RDS PostgreSQL

RDS → Create Database

- **Engine:** PostgreSQL 16
- **Template:** Free Tier for testing, then Production
- **Instance:** `db.t3.micro` at launch (~$15/month)
- **Storage:** 20 GB gp3, enable autoscaling to 100 GB
- **Multi-AZ:** Disable at launch (enable in Year 2 when you have paying users; it doubles the cost)
- **VPC:** `digitalEstate-vpc`
- **Subnet group:** Create a DB subnet group using `private-1a` and `private-1b`
- **Security group:** `sg-db`
- **Public access:** NO — this is the most important setting
- **Database name:** `digitalEstate`
- **Master username:** `digitalEstate_admin`
- **Master password:** Generate a strong one and save it — you'll put it in Secrets Manager
- **Encryption:** Enable, use AWS managed key (no extra cost)
- **Backup:** 7-day retention, 02:00 UTC backup window
- **Parameter group:** Default is fine for launch

Note the **endpoint hostname** after creation (looks like `digitalEstate.abc123.us-east-1.rds.amazonaws.com`). You'll need this for Secrets Manager.

**Why PostgreSQL over SQLite:** SQLite is a single file on disk. When your EC2 instance is terminated by Auto Scaling (which will happen during deployments and scaling events), that file is gone. PostgreSQL on RDS is a managed service with automated backups, point-in-time recovery, and persistence completely independent of your application servers.

### 5b. Create the Database

After RDS is ready, SSH into your EC2 instance (set up in Phase 7) and create the application database:

```bash
psql -h YOUR_RDS_ENDPOINT -U digitalEstate_admin -d postgres
CREATE DATABASE digitalEstate_db;
\q
```

### 5c. ElastiCache Redis

ElastiCache → Create → Redis OSS

- **Cluster mode:** Disabled (simpler, sufficient for your scale)
- **Node type:** `cache.t3.micro` (~$13/month)
- **Replicas:** 0 at launch (add 1 replica in Year 2 for HA)
- **VPC:** `digitalEstate-vpc`
- **Subnet group:** Create using `private-1a` and `private-1b`
- **Security group:** `sg-cache`
- **Encryption at rest:** Enable
- **Encryption in transit:** Enable (requires `rediss://` URL prefix)
- **Auth token:** Enable and generate one — save it for Secrets Manager

Note the **Primary Endpoint** after creation (looks like `digitalEstate.abc123.cache.amazonaws.com:6379`).

**Why Redis for sessions:** Your current `SESSION_SAVE_EVERY_REQUEST = True` means every single page request updates the session. With DB-backed sessions and 2 EC2 instances, that's fine but adds load to RDS. Redis handles session reads/writes in microseconds vs. milliseconds for DB queries. More importantly, Redis has built-in TTL (time-to-live) — your 1-hour session timeout works correctly because Redis automatically expires the key. No cleanup cron job needed.

---

## 6. Phase 4 — Secrets Manager

**Time: ~30 minutes**

All sensitive configuration lives here. Your EC2 instances load these at startup via boto3.

### 6a. Store Your Secrets

Secrets Manager → Store a new secret → Other type of secret

**Secret name:** `digitalEstate/production/config`

Store as key/value pairs:
```
DJANGO_SECRET_KEY                  = <your generated secret key>
VAULT_ENCRYPTION_KEY               = <your generated Fernet key>
DB_NAME                            = digitalEstate_db
DB_USER                            = digitalEstate_admin
DB_PASSWORD                        = <your RDS master password>
DB_HOST                            = <your RDS endpoint>
DB_PORT                            = 5432
REDIS_URL                          = rediss://:<redis_auth_token>@<elasticache_endpoint>:6379/0
AWS_STORAGE_BUCKET_NAME            = digitalEstate-static-production
AWS_MEDIA_BUCKET_NAME              = digitalEstate-media-production
AWS_S3_REGION_NAME                 = us-east-1
AWS_CLOUDFRONT_DOMAIN              = <your CloudFront distribution domain, e.g. d1abc123xyz.cloudfront.net>
DEFAULT_FROM_EMAIL                 = noreply@yourdomain.com
SITE_URL                           = https://yourdomain.com
ALLOWED_HOSTS                      = yourdomain.com,www.yourdomain.com
STRIPE_PUBLISHABLE_KEY             = pk_live_...
STRIPE_SECRET_KEY                  = sk_live_...
STRIPE_WEBHOOK_SECRET              = whsec_...  (set AFTER Phase 6b)
STRIPE_ESSENTIALS_MONTHLY_PRICE_ID = price_...
STRIPE_ESSENTIALS_ANNUAL_PRICE_ID  = price_...
STRIPE_LEGACY_MONTHLY_PRICE_ID     = price_...
STRIPE_LEGACY_ANNUAL_PRICE_ID      = price_...
```

**Note on Stripe keys:** Get these from your Stripe Dashboard → Developers → API Keys (for publishable/secret keys) and Products → Pricing (for price IDs). Use **live** keys for production — never test keys in production.

**Note on `AWS_CLOUDFRONT_DOMAIN`:** This value is only available after you create the CloudFront distribution in Phase 5. Add it to Secrets Manager after Phase 5 completes.

**Enable automatic rotation:** For the DB password, enable rotation (RDS supports this natively). Secrets Manager will update the password in RDS and in the secret automatically on your schedule. This means even if someone saw the password once, it will be different within days.

**Why not use a `.env` file on EC2:** A `.env` file on disk means the secret is on the file system of every EC2 instance. It will end up in AMI snapshots, EBS snapshots, and potentially CloudTrail logs. More critically, when Auto Scaling launches a new instance, you'd need a mechanism to get the `.env` file onto it — which means either baking it into the AMI (terrible) or fetching it from somewhere (which is exactly what Secrets Manager does, but properly).

### 6b. Secrets Loader

Create `topLevelProject/topLevelProject/secrets.py`:

```python
import json
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

def load_secrets(secret_name: str, region: str = "us-east-1") -> dict:
    """
    Load secrets from AWS Secrets Manager.
    Returns empty dict on failure so settings.py can fall back to
    environment variables (for local development).
    """
    client = boto3.session.Session().client(
        service_name="secretsmanager",
        region_name=region,
    )
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except ClientError as e:
        logger.warning("Could not load secrets from Secrets Manager: %s", e)
        return {}
```

This is called at the top of `settings.py` in production. In local development, boto3 won't find the secret and returns an empty dict, so `python-decouple` falls back to your local `.env` file.

---

## 7. Phase 5 — S3 Buckets & CloudFront

**Time: ~45 minutes**

### 7a. Static Files Bucket

S3 → Create bucket

- **Name:** `digitalEstate-static-production`
- **Region:** us-east-1
- **Block all public access:** YES (CloudFront will access it via Origin Access Control)
- **Versioning:** Optional for static files
- **Encryption:** SSE-S3 (no extra cost)

### 7b. Media Files Bucket

S3 → Create bucket

- **Name:** `digitalEstate-media-production`
- **Region:** us-east-1
- **Block all public access:** YES
- **Versioning:** Enable (so accidentally deleted estate documents can be recovered)
- **Encryption:** SSE-KMS (use AWS managed key)
- **Lifecycle rule:** Move objects to S3-IA after 90 days (estate documents are rarely accessed after upload)

**Why strict access control on media:** Your recovery app accepts uploads of death certificates, legal authorization documents, and proof-of-relationship files. These are sensitive documents. They must never be publicly accessible via a guessable URL. All access must go through Django, which enforces authentication and ownership checks.

### 7c. CORS Configuration for Media Bucket

Add this CORS rule to the media bucket (required for direct browser uploads if you add that later):
```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT", "POST"],
    "AllowedOrigins": ["https://yourdomain.com"],
    "MaxAgeSeconds": 3000
  }
]
```

### 7d. CloudFront Distribution (Static Assets)

CloudFront → Create Distribution

- **Origin:** `digitalEstate-static-production.s3.us-east-1.amazonaws.com`
- **Origin Access Control:** Create new OAC (CloudFront signs requests to S3 — no public S3 access needed)
- **HTTPS only:** Yes, redirect HTTP to HTTPS
- **Cache policy:** CachingOptimized
- **Price class:** North America and Europe (cheapest; add more regions when you have international users)
- **Alternate domain names:** `static.yourdomain.com` (optional but clean)
- **SSL certificate:** Request one via ACM (see Phase 8)

After creating the distribution, CloudFront will give you a bucket policy to paste into the static bucket. Paste it — this is what allows CloudFront to read from S3 without making the bucket public.

**Why CloudFront instead of serving static files from EC2:** Every CSS, JS, and image file served by Django uses Gunicorn worker capacity. A single worker handling a CSS file request is a worker not handling a page request. CloudFront caches static files at edge locations globally and serves them without touching your servers at all.

---

## 8. Phase 6 — Amazon SES (Email)

**Time: ~1 hour (plus up to 24 hours for DNS propagation)**

Your app sends email for:
- Password resets
- Recovery request verification tokens
- Essentials tier expiry warnings
- Registration confirmation

### 8a. Verify Your Domain

SES → Verified Identities → Create Identity → Domain

- Enter `yourdomain.com`
- SES provides DNS records to add to Route 53

Add these records to Route 53 (SES provides exact values):
- 3× DKIM CNAME records
- 1× SPF TXT record (add to existing if you have one: `v=spf1 include:amazonses.com ~all`)
- 1× DMARC TXT record: `v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com`

Wait for SES to show "Verified" (usually minutes once DNS propagates).

### 8b. Request Production Access

By default, SES is in **sandbox mode** — you can only send to verified email addresses. You need to request production access before launch.

SES → Account Dashboard → Request Production Access

In your request, explain:
- You're sending transactional email (password resets, verification emails) — not marketing
- Estimated volume (likely <1,000/month at launch)
- Your bounce and complaint handling process

AWS typically approves within 24 hours for legitimate transactional use cases.

**Why SES over SendGrid/Mailgun:** Your EC2 instances have IAM roles that already authorize SES sending. No separate API key to manage, no third-party service dependency, and from EC2 in the same region, SES is essentially free (62,000 emails/month free from EC2).

---

## 9. Phase 6b — Stripe Webhook Configuration

**Time: ~30 minutes** | **Prerequisite: domain + HTTPS must be live (complete Phase 8 first, then return here)**

Your subscription system depends on Stripe webhooks. Without them, payments will succeed in Stripe but your database will never know — users will pay and remain locked out, or cancel and retain access indefinitely.

### 9a. Find Your Webhook URL

Your webhook endpoint is defined in `accounts/urls.py`. Locate the URL pattern for the Stripe webhook view (look for a view named something like `stripe_webhook`). The full production URL will be:
```
https://yourdomain.com/accounts/stripe/webhook/
```
Confirm this by running locally: `python manage.py show_urls | grep stripe` (requires `django-extensions`), or just inspect `accounts/urls.py` directly.

### 9b. Register the Webhook in Stripe Dashboard

1. Stripe Dashboard → **Developers** → **Webhooks** → **Add endpoint**
2. **Endpoint URL:** `https://yourdomain.com/accounts/stripe/webhook/`
3. **Listen to:** Select these events:
   - `checkout.session.completed` — user completes payment
   - `customer.subscription.updated` — subscription tier or interval changed
   - `customer.subscription.deleted` — subscription canceled
   - `invoice.payment_succeeded` — recurring payment processed
   - `invoice.payment_failed` — payment declined (moves user to `past_due`)
4. Click **Add endpoint**
5. On the webhook detail page, reveal the **Signing secret** (`whsec_...`)

### 9c. Store the Signing Secret

Add `STRIPE_WEBHOOK_SECRET` to your Secrets Manager secret (`digitalEstate/production/config`):
```
STRIPE_WEBHOOK_SECRET = whsec_...
```

Also add all Stripe keys if not already added in Phase 4:
```
STRIPE_PUBLISHABLE_KEY             = pk_live_...
STRIPE_SECRET_KEY                  = sk_live_...
STRIPE_ESSENTIALS_MONTHLY_PRICE_ID = price_...
STRIPE_ESSENTIALS_ANNUAL_PRICE_ID  = price_...
STRIPE_LEGACY_MONTHLY_PRICE_ID     = price_...
STRIPE_LEGACY_ANNUAL_PRICE_ID      = price_...
```

### 9d. Test the Webhook

Use the Stripe CLI to simulate events against your live endpoint:
```bash
# Install Stripe CLI locally: https://stripe.com/docs/stripe-cli
stripe login
stripe trigger checkout.session.completed --override checkout_session:metadata.user_id=1
```

Or use the Stripe Dashboard → Webhooks → your endpoint → **Send test webhook** → select an event type.

Verify in your application logs (`journalctl -u gunicorn`) that the webhook view received and processed the event without error.

**Why webhook signature verification matters:** Stripe signs every webhook with your `STRIPE_WEBHOOK_SECRET`. Your view must verify this signature — if it doesn't, anyone can POST fake payment events to grant themselves subscriptions. Check that `accounts/views.py` calls `stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)`.

---

## 10. Phase 7 — EC2 & Application Setup

**Time: ~3 hours**

### 9a. Create the EC2 Instance (Initial Setup)

Launch a single instance first — get the app working, then convert to Auto Scaling.

EC2 → Launch Instance

- **AMI:** Amazon Linux 2023 (has Python 3.11+ built in)
- **Instance type:** `t3.small` (2 vCPU, 2 GB RAM, ~$15/month)
- **IAM role:** `digitalEstate-ec2-role`
- **VPC:** `digitalEstate-vpc`
- **Subnet:** `private-1a`
- **Auto-assign public IP:** Disable (private subnet)
- **Security group:** `sg-app`
- **Storage:** 20 GB gp3, encrypted
- **Key pair:** Create one, download the `.pem` file

**To SSH into a private subnet instance**, use AWS Systems Manager Session Manager — it requires no open SSH port and leaves an audit trail in CloudTrail.

**Enable Session Manager:**
1. Ensure your EC2 role has `AmazonSSMManagedInstanceCore` policy attached (add it in IAM → Roles → `digitalEstate-ec2-role` → Add permissions)
2. Launch the EC2 instance and wait ~2 minutes for the SSM agent to register (AL2023 includes the agent pre-installed)
3. In the AWS console: EC2 → Instances → select your instance → **Connect** button → **Session Manager** tab → **Connect**

If the Session Manager tab is grayed out, the SSM agent hasn't registered yet. Check: the instance needs outbound HTTPS (port 443) to `ssm.us-east-1.amazonaws.com` — this is covered by the `sg-app` outbound rule you created in Phase 2. Wait another 2–3 minutes and refresh.

### 9b. Install Dependencies

Connect via Session Manager:

```bash
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-pip python3.11-devel gcc postgresql15-devel

# Create app user (never run Django as root)
sudo useradd -m -s /bin/bash appuser
sudo mkdir -p /opt/digitalEstate
sudo chown appuser:appuser /opt/digitalEstate
```

### 9c. Deploy Application Code

From your local machine, create a deployment package or use CodeDeploy (covered in Phase 10). For initial manual deployment:

```bash
# On your local machine
cd DjangoProject/topLevelProject
pip install build
tar --exclude='.git' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='db.sqlite3' \
    --exclude='.env' \
    -czf app.tar.gz .
```

Transfer via S3 (since EC2 is in a private subnet):
```bash
aws s3 cp app.tar.gz s3://digitalEstate-static-production/deployments/app.tar.gz
```

On EC2:
```bash
sudo -u appuser bash
cd /opt/digitalEstate
aws s3 cp s3://digitalEstate-static-production/deployments/app.tar.gz .
tar -xzf app.tar.gz
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 9d. Load Secrets and Run Migrations

```bash
# Test that Secrets Manager is reachable
python -c "
import boto3, json
client = boto3.client('secretsmanager', region_name='us-east-1')
secret = client.get_secret_value(SecretId='digitalEstate/production/config')
print('Secrets loaded:', list(json.loads(secret['SecretString']).keys()))
"
```

Run database migrations (this is the moment SQLite data does NOT transfer — start fresh in production or write a data migration script if needed):

```bash
DJANGO_SETTINGS_MODULE=topLevelProject.settings python manage.py migrate
python manage.py createsuperuser  # create your admin account
python manage.py collectstatic --noinput  # pushes to S3
```

### 9e. Gunicorn Configuration

Create `/etc/systemd/system/gunicorn.service`:

```ini
[Unit]
Description=Gunicorn daemon for Digital Estate Planning
After=network.target

[Service]
User=appuser
Group=appuser
WorkingDirectory=/opt/digitalEstate
ExecStart=/opt/digitalEstate/venv/bin/gunicorn \
    --workers 3 \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    topLevelProject.wsgi:application
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
sudo systemctl status gunicorn
```

**Why 3 workers:** The standard formula is `(2 × CPU cores) + 1`. A `t3.small` has 2 vCPUs, so 3 workers. Each worker handles one request at a time. If all 3 are busy, requests queue. Size up (more workers or a larger instance) if you consistently see queue depth.

**Why `--timeout 120`:** Your vault decrypt operations and file upload handling could take longer than Gunicorn's default 30-second timeout. 120 seconds is generous but appropriate for a file upload endpoint.

### 9f. Test the Application

From a machine that can reach the private subnet (your bastion or via Session Manager port forwarding):

```bash
curl http://10.0.11.XXX:8000/accounts/login/
# Should return HTML with status 200
```

### 9g. CloudWatch Logs Agent

Phase 12 configures CloudWatch alarms against log group `/digitalEstate/production/django`, but logs won't arrive there until you install and configure the CloudWatch agent. Without this, `journalctl` is the only way to see logs — which means you lose visibility the moment a session ends.

**Install the agent:**
```bash
sudo dnf install -y amazon-cloudwatch-agent
```

**Create config at `/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`:**
```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/messages",
            "log_group_name": "/digitalEstate/production/system",
            "log_stream_name": "{instance_id}"
          }
        ]
      },
      "journald": {
        "collect_list": [
          {
            "log_group_name": "/digitalEstate/production/django",
            "log_stream_name": "{instance_id}",
            "units": ["gunicorn.service"]
          }
        ]
      }
    }
  }
}
```

**Start the agent:**
```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

sudo systemctl enable amazon-cloudwatch-agent
sudo systemctl start amazon-cloudwatch-agent
```

Verify logs appear: CloudWatch → Log Groups → `/digitalEstate/production/django`. Generate a log entry by restarting gunicorn and checking within 60 seconds.

**Include in your Launch Template AMI:** When you convert to Auto Scaling in Phase 12, create the AMI *after* this step so every new instance launches with the agent pre-configured.

---

## 11. Phase 8 — Load Balancer & HTTPS

**Time: ~1 hour**

### 10a. Route 53 Hosted Zone (verify before proceeding)

Before requesting an SSL certificate, your hosted zone must exist and your domain must be pointed at Route 53 nameservers.

**If you registered via Route 53 (Section 2a, Option A):** Your hosted zone was created automatically. Verify: Route 53 → Hosted Zones → `yourdomain.com` should exist with an NS record and an SOA record. You're ready.

**If you used a third-party registrar (Section 2a, Option B):**
1. Route 53 → Hosted Zones → Create Hosted Zone → enter `yourdomain.com` → Public
2. Copy the 4 NS record values shown (e.g., `ns-123.awsdns-45.com`)
3. Log in to your registrar and replace its default nameservers with these 4 values
4. Wait for propagation: `nslookup -type=NS yourdomain.com 8.8.8.8` — when it returns the AWS nameservers, propagation is done (can take minutes to 48 hours)

**Do not proceed to SSL until the hosted zone is set up** — ACM DNS validation requires you to add a CNAME to this hosted zone.

### 10b. SSL Certificate

ACM → Request Certificate → Public Certificate

- Add domains: `yourdomain.com` and `*.yourdomain.com`
- Validation: DNS validation (add the CNAME records ACM provides to Route 53)
- Certificate is free and auto-renews

**Why wildcard:** Covers `www.yourdomain.com`, `static.yourdomain.com`, and any subdomains you add later without requesting a new certificate.

### 10c. Target Group

EC2 → Target Groups → Create

- **Type:** Instances
- **Protocol:** HTTP, Port 8000
- **VPC:** `digitalEstate-vpc`
- **Health check:** GET `/accounts/login/`
- **Healthy threshold:** 2 consecutive successes
- **Unhealthy threshold:** 3 consecutive failures
- **Interval:** 30 seconds

Register your EC2 instance as a target.

**Why `/accounts/login/` for health check:** It's a lightweight page that exercises the Django stack (URL routing, template rendering, DB connection via session middleware). If this returns 200, your app is working. Avoid using `/` if it requires a database query that could fail during startup.

### 10d. Application Load Balancer

EC2 → Load Balancers → Create → Application Load Balancer

- **Scheme:** Internet-facing
- **Subnets:** `public-1a` and `public-1b` (must be public subnets)
- **Security group:** `sg-alb`

**Listeners:**
- HTTP :80 → Redirect to HTTPS :443 (301 permanent)
- HTTPS :443 → Forward to your target group, using your ACM certificate

### 10e. Route 53 DNS

Route 53 → Your hosted zone → Create record

- **Name:** `yourdomain.com` (A record, Alias → ALB)
- **Name:** `www.yourdomain.com` (A record, Alias → ALB, or CNAME to yourdomain.com)

DNS propagation takes up to 48 hours but usually completes in minutes.

### 10f. Verify End-to-End

```
https://yourdomain.com/accounts/login/
```

Should load with a valid SSL certificate. If you see a certificate warning, the ACM certificate isn't attached correctly to the ALB listener.

---

## 12. Phase 9 — Production Settings

**Time: ~2 hours**

### 11a. Create `settings_production.py`

Create `topLevelProject/topLevelProject/settings_production.py`. This imports your base settings and overrides development values. Keep this file in Git — it contains no secrets.

```python
import os
import json
import boto3
import logging
from .settings import *  # import all base settings

logger = logging.getLogger(__name__)

# ── Load secrets from AWS Secrets Manager ──────────────────────────────────
def _load_aws_secrets():
    try:
        client = boto3.client("secretsmanager", region_name="us-east-1")
        response = client.get_secret_value(SecretId="digitalEstate/production/config")
        return json.loads(response["SecretString"])
    except Exception as e:
        logger.error("Failed to load secrets: %s", e)
        return {}

_secrets = _load_aws_secrets()
def _s(key, fallback=""):
    return _secrets.get(key, os.environ.get(key, fallback))

# ── Core ────────────────────────────────────────────────────────────────────
SECRET_KEY = _s("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = _s("ALLOWED_HOSTS", "yourdomain.com").split(",")

# ── Database (PostgreSQL) ───────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME":     _s("DB_NAME"),
        "USER":     _s("DB_USER"),
        "PASSWORD": _s("DB_PASSWORD"),
        "HOST":     _s("DB_HOST"),
        "PORT":     _s("DB_PORT", "5432"),
        "OPTIONS":  {"sslmode": "require"},
        "CONN_MAX_AGE": 60,  # reuse DB connections for 60 seconds
    }
}

# ── Redis Sessions & Cache ──────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": _s("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ── Vault Encryption ────────────────────────────────────────────────────────
VAULT_ENCRYPTION_KEY = _s("VAULT_ENCRYPTION_KEY")

# ── Static & Media Files (S3) ───────────────────────────────────────────────
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": _s("AWS_MEDIA_BUCKET_NAME"),
            "region_name": _s("AWS_S3_REGION_NAME", "us-east-1"),
            "default_acl":  "private",
            "file_overwrite": False,
            "custom_domain": None,
        },
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3StaticStorage",
        "OPTIONS": {
            "bucket_name": _s("AWS_STORAGE_BUCKET_NAME"),
            "region_name": _s("AWS_S3_REGION_NAME", "us-east-1"),
            "default_acl":  "public-read",
            "custom_domain": f"{_s('AWS_CLOUDFRONT_DOMAIN')}",
        },
    },
}
STATIC_URL  = f"https://{_s('AWS_CLOUDFRONT_DOMAIN')}/"
MEDIA_URL   = f"https://{_s('AWS_MEDIA_BUCKET_NAME')}.s3.amazonaws.com/"

# ── Email (Amazon SES) ──────────────────────────────────────────────────────
EMAIL_BACKEND    = "django_ses.SESBackend"
DEFAULT_FROM_EMAIL = _s("DEFAULT_FROM_EMAIL", "noreply@yourdomain.com")
AWS_SES_REGION_NAME     = "us-east-1"
AWS_SES_REGION_ENDPOINT = "email.us-east-1.amazonaws.com"

# ── Security Headers ────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT          = True
SECURE_HSTS_SECONDS          = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD          = True
SESSION_COOKIE_SECURE        = True
CSRF_COOKIE_SECURE           = True
SECURE_BROWSER_XSS_FILTER    = True
SECURE_CONTENT_TYPE_NOSNIFF  = True
X_FRAME_OPTIONS              = "DENY"

# ALB terminates SSL and forwards HTTP to Gunicorn.
# This tells Django to trust the X-Forwarded-Proto header from the ALB.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# ── CORS (production) ───────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    f"https://{_s('SITE_URL').replace('https://', '')}",
]

# ── Logging ─────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "accounts":   {"handlers": ["console"], "level": "INFO", "propagate": False},
        "infrapps":   {"handlers": ["console"], "level": "INFO", "propagate": False},
        "recovery":   {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

# ── Site URL ────────────────────────────────────────────────────────────────
SITE_URL = _s("SITE_URL", "https://yourdomain.com")
```

### 11b. Update Gunicorn to Use Production Settings

Edit `/etc/systemd/system/gunicorn.service`, add to `[Service]`:
```ini
Environment=DJANGO_SETTINGS_MODULE=topLevelProject.settings_production
```

Reload:
```bash
sudo systemctl daemon-reload && sudo systemctl restart gunicorn
```

### 11c. SECURE_PROXY_SSL_HEADER Explanation

This is a critical setting that many guides skip. Your ALB terminates SSL — it receives HTTPS from the browser and forwards HTTP to your EC2 instance. Without this setting, Django thinks all requests are HTTP and:
- `SECURE_SSL_REDIRECT` would cause an infinite redirect loop
- `request.is_secure()` would return False
- CSRF validation can fail

`SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` tells Django: "trust the `X-Forwarded-Proto` header set by the ALB." The ALB always sets this header to `https` when the original request was HTTPS.

### 11d. django-axes Configuration

Add to `settings_production.py`:

```python
INSTALLED_APPS += ["axes"]
MIDDLEWARE = ["axes.middleware.AxesMiddleware"] + MIDDLEWARE

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "accounts.backends.EmailOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AXES_ENABLED           = True
AXES_FAILURE_LIMIT     = 5          # lock after 5 failures
AXES_COOLOFF_TIME      = 0.5        # 30 minutes (in hours as float)
AXES_RESET_ON_SUCCESS  = True       # reset counter on successful login
AXES_LOCKOUT_CALLABLE  = None       # use default lockout response
AXES_CACHE             = "default"  # use Redis — shared across EC2 instances
```

**Why axes over your current model-based lockout:** Your `CustomUser.failed_login_attempts` is stored in the DB, which is shared — so the count is accurate. But `account_locked_until` is checked inside the view after `authenticate()` succeeds. Axes intercepts at the middleware/backend level before any DB queries run for the user lookup, and uses Redis so the lockout is instantaneous across all instances with no race conditions.

Run the migration: `python manage.py migrate axes`

---

## 13. Phase 10 — CI/CD Pipeline

**Time: ~2 hours**

### 12a. CodeDeploy Setup

CodeDeploy automates deploying new code from GitHub to your EC2 instances with zero downtime.

**Install CodeDeploy agent on EC2:**
```bash
sudo dnf install ruby wget -y
wget https://aws-codedeploy-us-east-1.s3.amazonaws.com/latest/install
chmod +x ./install
sudo ./install auto
sudo systemctl enable codedeploy-agent
sudo systemctl start codedeploy-agent
```

**Create CodeDeploy Application:**
- CodeDeploy → Applications → Create → EC2/On-Premises
- Create Deployment Group → attach your EC2 instances (use a tag: `App=digitalEstate`)
- Deployment type: In-place, OneAtATime (keeps one instance serving traffic while the other deploys)

### 12b. appspec.yml

Create in your repo root (`topLevelProject/appspec.yml`):

```yaml
version: 0.0
os: linux
files:
  - source: /
    destination: /opt/digitalEstate
    overwrite: true
file_exists_behavior: OVERWRITE
hooks:
  BeforeInstall:
    - location: scripts/stop_app.sh
      timeout: 30
  AfterInstall:
    - location: scripts/install_deps.sh
      timeout: 300
    - location: scripts/run_migrations.sh
      timeout: 120
    - location: scripts/collect_static.sh
      timeout: 120
  ApplicationStart:
    - location: scripts/start_app.sh
      timeout: 30
  ValidateService:
    - location: scripts/validate.sh
      timeout: 30
```

**Create deployment scripts** in `topLevelProject/scripts/`:

`stop_app.sh`:
```bash
#!/bin/bash
sudo systemctl stop gunicorn || true
```

`install_deps.sh`:
```bash
#!/bin/bash
cd /opt/digitalEstate
sudo -u appuser /opt/digitalEstate/venv/bin/pip install -r requirements.txt --quiet
```

`run_migrations.sh`:
```bash
#!/bin/bash
export DJANGO_SETTINGS_MODULE=topLevelProject.settings_production
cd /opt/digitalEstate
sudo -u appuser /opt/digitalEstate/venv/bin/python manage.py migrate --noinput
```

`collect_static.sh`:
```bash
#!/bin/bash
export DJANGO_SETTINGS_MODULE=topLevelProject.settings_production
cd /opt/digitalEstate
sudo -u appuser /opt/digitalEstate/venv/bin/python manage.py collectstatic --noinput
```

`start_app.sh`:
```bash
#!/bin/bash
sudo systemctl start gunicorn
```

`validate.sh`:
```bash
#!/bin/bash
sleep 5
curl -f http://localhost:8000/accounts/login/ || exit 1
```

### 12c. GitHub Connection (CodeStar Connections)

Before creating the pipeline, you must create a GitHub connection. CodePipeline uses GitHub Apps (not OAuth tokens), and the connection requires manual activation in the console — it cannot be done programmatically.

1. Go to **Developer Tools → Settings → Connections** (or search "CodeStar Connections")
2. **Create connection** → GitHub → name it `digitalEstate-github`
3. Click **Connect to GitHub** → AWS will ask you to install the GitHub App on your account/repo
4. Select the repository (`your-username/DjangoProject` or wherever your code lives) → **Install**
5. Back in AWS, the connection status will show **Pending** — click **Update pending connection** and complete the authorization
6. Status changes to **Available** — copy the **Connection ARN** (you'll paste it in CodePipeline)

**Why this extra step:** AWS deprecated GitHub OAuth tokens for CodePipeline in 2023. The GitHub App connection is more secure (scoped to specific repos, uses short-lived tokens) but requires this manual activation step that many guides skip.

### 12d. CodePipeline

CodePipeline → Create Pipeline

- **Source:** GitHub (Version 2) → select your connection from 12c, then your repo, branch: `main`
- **Build:** Skip (optional; add CodeBuild to run tests before deploy)
- **Deploy:** CodeDeploy (select your application and deployment group)

Every push to `main` now triggers a deployment automatically. This is the correct workflow — your `main` branch should always represent what's in production.

**Add CodeBuild for tests (highly recommended):**
Create `buildspec.yml` in repo root:
```yaml
version: 0.2
phases:
  install:
    runtime-versions:
      python: 3.11
  pre_build:
    commands:
      - pip install -r topLevelProject/requirements.txt
  build:
    commands:
      - cd topLevelProject
      - python manage.py test --verbosity=2
```

---

## 14. Phase 11 — WAF & Security

**Time: ~45 minutes**

### 13a. AWS WAF

WAF → Web ACLs → Create → Regional (for ALB)

Attach to your ALB. Add these rules in order:

1. **AWSManagedRulesCommonRuleSet** — Blocks XSS, SQLi, and other OWASP Top 10 attacks
2. **AWSManagedRulesKnownBadInputsRuleSet** — Blocks log4j exploitation, path traversal
3. **AWSManagedRulesAmazonIpReputationList** — Blocks known malicious IPs (bots, scrapers)
4. **Rate limit rule** (custom):
   - Action: Block
   - Rate: 2,000 requests per 5 minutes per IP
   - This prevents credential stuffing against `/accounts/login/`

5. **Admin protection rule** (custom):
   - URI path matches `/admin/*`
   - IP set: your office IP only
   - Action: Block everything else

**Why WAF matters for your specific app:** Your application stores estate planning data, vault credentials, and recovery request documents. It will be targeted by bots scanning for Django admin panels, credential stuffing the login page, and potentially targeted attacks if any user becomes high-profile. WAF handles this at the network edge before traffic reaches Django.

### 13b. S3 Bucket Policy (Media — Signed URLs)

Your estate documents and recovery upload files need to be served to authenticated users only. Serving them through Django with S3 signed URLs is the correct pattern.

The `django-storages` S3 backend generates signed URLs automatically when you use `{{ document.file.url }}` in templates. Ensure `default_acl: private` is set in your storage config (already in the settings above).

Signed URLs expire after 1 hour by default. For a download page, this is appropriate. The user's Django session must be valid to reach the view that generates the signed URL — the URL itself is time-limited.

---

## 15. Phase 12 — Monitoring & Alarms

**Time: ~1 hour**

### 14a. CloudWatch Alarms

Set up these alarms with SNS → your email as the endpoint:

```
ALB 5xx errors > 10 per minute  → something is crashing
EC2 CPU > 80% for 5 minutes     → scale up or investigate
RDS free storage < 2 GB         → database about to fill
RDS connections > 80            → connection pool exhausted
ElastiCache evictions > 0       → Redis running out of memory
```

For your vault specifically, add a metric filter:
```
CloudWatch → Log Groups → /digitalEstate/production/django
Filter pattern: "VaultEntry decryption failed"
Alarm: any occurrence → immediate notification
```

Decryption failures against your vault are either a bug or someone attempting to tamper with encrypted data. Both warrant immediate attention.

### 14b. CloudTrail

Enable CloudTrail for all regions — it logs every AWS API call. If your account is ever compromised, CloudTrail tells you exactly what happened and when.

- Create a trail
- Store logs in a new S3 bucket (`digitalEstate-cloudtrail-logs`)
- Enable CloudWatch Logs integration

### 14c. Auto Scaling Group

Convert your single EC2 instance to an Auto Scaling Group:

1. Create an AMI from your configured EC2 instance
2. Create a Launch Template using that AMI + `sg-app` + `digitalEstate-ec2-role`
3. Create Auto Scaling Group:
   - Min: 1, Desired: 1, Max: 3
   - Subnets: `private-1a`, `private-1b`
   - Attach to your ALB target group
   - Scale out policy: CPU > 70% for 2 minutes
   - Scale in policy: CPU < 30% for 10 minutes

At launch, running 1 instance keeps costs down. Auto Scaling ensures a replacement is automatically launched if your instance fails.

---

## 16. Go-Live Checklist

Run through this the day before launch:

### Application
- [ ] `python manage.py check --deploy` returns no errors
- [ ] All migrations applied: `python manage.py showmigrations | grep '\[ \]'` — empty output
- [ ] Superuser account created and tested
- [ ] `collectstatic` completed — static files visible in S3
- [ ] Test registration → email received → login works
- [ ] Test password reset flow end-to-end
- [ ] Test vault: create entry → encrypted in DB → reveal decrypts correctly
- [ ] Test recovery request form → verification email received → status page loads
- [ ] Upload a file in recovery form → file appears in S3 media bucket
- [ ] Python version confirmed: `python --version` on EC2 matches your requirements (3.11+ expected unless you compiled 3.14)

### Stripe & Payments
- [ ] Stripe live keys (not test keys) are in Secrets Manager
- [ ] Stripe webhook endpoint registered at `https://yourdomain.com/accounts/stripe/webhook/`
- [ ] Webhook signing secret (`whsec_...`) is in Secrets Manager as `STRIPE_WEBHOOK_SECRET`
- [ ] All 4 price IDs stored in Secrets Manager and match your Stripe product catalog
- [ ] Test checkout flow end-to-end: complete a payment → user subscription tier updates in Django admin
- [ ] Test webhook delivery: Stripe Dashboard → Webhooks → your endpoint → confirm recent deliveries show 200 responses
- [ ] `invoice.payment_failed` event: confirm user subscription status moves to `past_due`

### Security
- [ ] `DEBUG = False` confirmed (visit a non-existent URL — should see standard 404, not Django debug page)
- [ ] `ALLOWED_HOSTS` contains only your domain
- [ ] All cookies are `Secure` and `HttpOnly` (check browser dev tools)
- [ ] HSTS header present in responses
- [ ] SSL Labs test: `https://www.ssllabs.com/ssltest/` — should score A or A+
- [ ] WAF enabled and attached to ALB
- [ ] Admin URL is not accessible from outside your office IP
- [ ] Vault encryption key is in Secrets Manager, not in code or `.env`
- [ ] `VAULT_ENCRYPTION_KEY` setting in `settings.py` (dev file) removed/replaced with env var reference — not hardcoded

### Infrastructure
- [ ] Health check passing (ALB target group shows "Healthy")
- [ ] RDS in private subnet — confirm no public endpoint
- [ ] Redis in private subnet
- [ ] CloudWatch alarms configured and tested (manually trigger one)
- [ ] CloudWatch Logs agent running — logs visible in `/digitalEstate/production/django`
- [ ] CloudTrail enabled
- [ ] SES production access approved
- [ ] S3 buckets: public access blocked, versioning enabled on media bucket
- [ ] Backups: RDS automated backups enabled, verify a backup exists

### DNS & SSL
- [ ] `https://yourdomain.com` loads correctly
- [ ] `http://yourdomain.com` redirects to HTTPS
- [ ] `www.yourdomain.com` resolves correctly
- [ ] SSL certificate valid for both apex and www

---

## 17. Cost Estimate

Monthly costs for your architecture at launch (50 users):

| Service | Spec | Monthly |
|---------|------|---------|
| EC2 t3.small | 1 instance | ~$15 |
| RDS db.t3.micro | PostgreSQL, 20GB | ~$18 |
| ElastiCache cache.t3.micro | Redis | ~$13 |
| NAT Gateway | ~$0.045/hr + data | ~$33 |
| ALB | ~$0.008/hr + LCU | ~$16 |
| S3 | Static + media, minimal at launch | ~$1 |
| CloudFront | Static assets CDN | ~$2 |
| SES | <1,000 emails/month | ~$0 |
| WAF | $5/ACL + $1/rule | ~$10 |
| Secrets Manager | ~5 secrets | ~$2 |
| CloudWatch | Logs + alarms | ~$3 |
| Route 53 | 1 hosted zone | ~$1 |
| **Total** | | **~$114/month** |

**Biggest cost lever:** NAT Gateway at $33/month. If budget is tight at launch, replace with a NAT Instance (t3.nano, ~$3/month). It's less reliable but functional for low traffic. Swap to NAT Gateway when you have consistent paid users.

**Cost at Year 2 (250 users):** ~$180/month (add Multi-AZ RDS ~$18, Redis replica ~$13, larger instances as needed).

---

## 18. Post-Launch Runbook

### Deploying a Code Update
```bash
git push origin main
# CodePipeline triggers automatically
# Monitor: CodePipeline → your pipeline → watch stages
# Verify: check CloudWatch logs for errors after deploy
```

### Emergency Rollback
```bash
# CodeDeploy keeps the previous deployment
# CodeDeploy → Deployments → your deployment → Redeploy (previous)
```

### Checking Application Logs
```bash
# Via Session Manager on EC2:
sudo journalctl -u gunicorn -f --since "1 hour ago"
# Or in CloudWatch:
# Logs → /digitalEstate/production/django
```

### Rotating the Vault Encryption Key
**Do not do this unless absolutely necessary.** Rotating the Fernet key requires:
1. Decrypt every `VaultEntry.encrypted_password` with the old key
2. Re-encrypt with the new key
3. Store new key in Secrets Manager
4. Deploy

If you ever suspect the key is compromised, the priority is: notify affected users first, rotate second.

### Database Maintenance
```bash
# Connect to RDS (from EC2 via Session Manager):
psql -h YOUR_RDS_ENDPOINT -U digitalEstate_admin -d digitalEstate_db

# Check table sizes:
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

# Run migrations after code deploy (handled automatically by CodeDeploy):
python manage.py migrate
```

### Scaling Up
If you see consistent CPU > 70% on EC2:
1. First check if it's a specific endpoint (CloudWatch → ALB → by target)
2. If load-related: increase Auto Scaling desired count to 2
3. If instance is undersized: change Launch Template to `t3.medium` and cycle instances

---

## Timeline Recommendation

**Weeks 1-2:** Phases 1-4 (IAM, VPC, RDS, Redis, Secrets Manager)
**Weeks 3-4:** Phases 5-8 (S3, CloudFront, SES, EC2 setup)
**Week 5:** Phase 9-10 (Production settings, CI/CD pipeline)
**Week 6:** Phase 11-12 (WAF, monitoring, Auto Scaling)
**Week 7:** End-to-end testing, go-live checklist, soft launch to a few users
**Week 8:** Monitor, fix any issues found in production, full launch

The biggest risks to timeline are: SES production access approval (allow 24-48 hours), DNS propagation (allow 48 hours), and discovering settings issues in production that weren't caught in development. Budget buffer time around Week 7.
