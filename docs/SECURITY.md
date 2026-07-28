# Security and Trust Boundaries

## Security posture

Incident SLA Ledger is a bounded portfolio backend with explicit security controls. It is not a security certification, managed identity product, encrypted audit vault, or production deployment blueprint.

## Trusted components

- The repository operator and deployment configuration
- PostgreSQL under an application role permitted to run the supplied schema
- The API and worker source built from the reviewed revision
- Deployment-provided TLS termination and secret injection

## Untrusted inputs

- HTTP headers, JWTs, JSON, form credentials, query parameters, and UUIDs
- Idempotency keys chosen by clients
- Incident title and description
- SMTP responses and network failures
- Worker timing and process interruption

## Authentication

The owner-operated user-provisioning CLI prompts for passwords by default and supports standard-input automation so plaintext passwords are not placed in the process argument list.

- Passwords are bounded and hashed with Argon2.
- JWTs use HS256 and require subject, issuer, audience, issued-at, not-before, expiry, and token ID.
- Production configuration rejects placeholder or short secrets.
- Authentication failures are generic.
- Users are provisioned by an operator CLI; there is no registration or password-reset endpoint.

Limitations:

- No refresh token, revocation list, MFA, SSO, password rotation workflow, or login rate limiter is included.
- A stolen valid token remains usable until expiry or the user is deactivated.
- HS256 requires protecting the shared signing secret on every verifier.
- Deployments must provide HTTPS; the application does not terminate TLS itself.

## Authorization

- Reporters and assignees can read related incidents. API principal summaries omit email addresses and administrator flags.
- Administrators can read all incidents and assign them.
- Assignee or administrator may acknowledge and resolve.
- Reporter or administrator may close after resolution.

This is single-deployment authorization, not tenant isolation. Adding tenants or teams requires [RFC-0002](rfc/0002-multi-tenant-authorization.md).

## Input and query controls

- Command models reject unknown fields.
- Text is NFC-normalized, trimmed, bounded, and rejects control/surrogate characters.
- Identity input is NFKC-normalized and casefolded.
- CORS accepts only exact HTTP(S) origins.
- Search escapes SQL wildcard syntax and uses SQLAlchemy parameters.
- Idempotency keys use a bounded ASCII grammar.
- Pagination is bounded, and durable transport diagnostics retain an error class plus a sanitized SMTP response code rather than raw provider exception text.

An upstream proxy should also enforce request-body, connection, and rate limits. Those are not currently absolute application-level guarantees for chunked bodies.

## Data integrity

- Policy snapshot and priority are protected by triggers.
- Incident and SLA progress are checked at deferred transaction completion.
- Events reject update/delete operations.
- Breach timestamps must equal deadlines.
- Commands, events, and receipt results share transactions.

These controls defend against ordinary application mistakes and roles. A PostgreSQL superuser, schema owner, or compromised migration process can disable or replace them. The ledger is not cryptographically tamper-evident.

## Notification privacy

Outbox rows contain recipient email, incident title, priority, objective, and timestamps. Database access and backups therefore carry personal and operational data.

The console transport logs only outbox ID, deduplication key, topic, incident ID, objective, and attempt. It does not log recipient, title, or the full payload by default. SMTP necessarily submits recipient and message content to the configured provider.

Operators must define retention and access controls before using real incident data.

Controlled transport tests observe successful plaintext submission when explicitly configured and STARTTLS refusal without plaintext fallback when TLS is required. They do not establish trust or acceptance for an arbitrary production provider.

## At-least-once risk

A provider may accept a message immediately before a worker crashes. PostgreSQL may still show the row as processing, leading to later redelivery. The stable deduplication key reduces ambiguity but does not force an SMTP recipient to deduplicate.

No documentation or UI should call this exactly once. Stronger provider receipts are a draft in [RFC-0003](rfc/0003-provider-delivery-receipts.md).

## Secret handling

Never commit:

- `.env`
- JWT secrets
- database passwords
- SMTP credentials
- production URLs containing credentials
- database dumps or real incident exports

The example values are local placeholders. Production should use a secret manager and a least-privileged database role.

## Reporting a vulnerability

Follow the private process in [../SECURITY.md](../SECURITY.md). Do not open a public issue containing exploitable details or real credentials.
