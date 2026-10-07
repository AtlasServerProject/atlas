# Atlas API — M3 accounts, catalog and promotions

Java 21, Spring Boot 4.1.1, Spring MVC/Security/Validation/JDBC, PostgreSQL 18, Flyway, Actuator, Maven Wrapper 3.9.16. Versioned application: `0.5.0`.

M2 implements registration, login/logout, persisted JDBC sessions, email verification, password reset, current account and live USER/ADMIN authorization. Angular authentication uses the real API. M3 adds persistent catalog, administrative product/price changes and promotions. Sales remain disabled until payment and delivery milestones. No Mercado Pago credentials, Minecraft changes or game database access. See `../atlas-docs/M2-BACKEND.md` and its milestone OpenAPI for the complete account contract. See `../atlas-docs/M3-BACKEND.md` for catalog and promotion endpoints.

## Run and verify without Docker (available on the Atlas VM)

From `atlas-api`:

```sh
python3 scripts/verify-local.py
```

Uses PostgreSQL binaries from `/usr/lib/postgresql/18/bin` (override with `ATLAS_PG_BIN`), creates a fresh cluster bound to loopback on a free port, generates random credentials in a private temporary directory, runs all tests and packages the application. It then starts the real JAR, checks persistence of an authenticated session across restart, database failure/readiness/recovery and protected metrics. Add `--web-tests` to run the compiled frontend and Chromium suite with temporary verified USER/ADMIN accounts and local email delivery. Finally stops and deletes only its own cluster. It does not require sudo. Failure is not treated as a skipped test.

For an interactive demonstration:

```sh
python3 scripts/verify-local.py --serve --api-port 8080
```

Prints the local API address after verification. Ctrl+C closes the application and discards this temporary database. This demonstration does not preserve business data and is not production hosting. `ATLAS_KEEP_TEST_LOGS=1` preserves private temporary files for debugging; remove them afterwards. Never run the test suite against the Minecraft or production database.

## Persistent local development without Docker

On the VM, after a successful build:

```sh
python3 scripts/run-native-local.py
```

Creates only its private PostgreSQL 18 cluster under ignored `.runtime/postgres`, uses the dedicated local database on loopback:55432 and serves the API on loopback:8080. Stops its own processes on Ctrl+C and preserves data. Generates local .env if absent; never replaces existing data or credentials. Do not run simultaneously with Docker Compose on that port.

## Persistent local development with Docker

Requires Docker Compose and Java 21. No Maven installation is needed.

```sh
python3 scripts/init-local-env.py
docker compose --env-file .env up -d --wait
./scripts/run-local.sh
```

The first command creates `.env` with random local passwords and permissions 0600, and refuses to overwrite it. The database is bound only to `127.0.0.1:55432`; the API defaults to `127.0.0.1:8080`. The dedicated Docker volume persists data between restarts. Provisioning runs once on a fresh volume; changing passwords in .env alone does not rotate existing database roles. No passwords belong in documentation, source or commits.

`./mvnw -B -ntp verify` uses a separate disposable Testcontainers PostgreSQL database, not the persistent local database. Tests fail if Docker is unavailable; use the native verifier above in that case. Native and Docker paths execute the same test suite. The CI uses Docker/Testcontainers; that path is configured but cannot be executed on the current VM without Docker.

## Implemented endpoints

| Route | Behavior |
| --- | --- |
| GET `/api/v1/system` | Version, foundation stage, persisted schema generation/initialization time and UTC server time |
| GET `/api/v1/auth/csrf` | CSRF token and header name; no-store; creates an anonymous session |
| GET `/actuator/health` | Status only, no database details |
| GET `/actuator/health/liveness` | Application liveness, independently of the database |
| GET `/actuator/health/readiness` | Availability plus PostgreSQL connection; 503 when DB is unavailable |
| `/actuator/info`, `/actuator/metrics/**` | Requires OPERATIONS; real operator authentication still pending |
| `/api/v1/auth/**`, GET `/api/v1/users/me` | Implemented in M2; see milestone contract |
| GET `/api/v1/catalog`, `/api/v1/admin/catalog`, product/promotion POST/PATCH | Implemented in M3; ADMIN and CSRF required for writes |
| Future orders/payments/Minecraft routes | Closed; no fabricated backend results |

The API intentionally creates no default user, generated login password, demo ADMIN or payment handler. OPERATIONS access is reserved for the operational authentication implemented later; tests use a test-only principal. Startup fails with absent database configuration, unavailable DB, missing schema or invalid Flyway history.

## Database responsibilities

Provision a **dedicated, empty API database** before starting. Local bootstrap uses `infra/postgres/provision.sql` to create two roles and the `atlas_web` schema:

- `atlas_api_migrator`: owns `atlas_web`, runs Flyway; no superuser/create-role/create-db.
- `atlas_api_runtime`: CONNECT + schema USAGE; SELECT on system_metadata and explicit DML on M2 account/session/token/mail/rate tables; SELECT/INSERT on auth_audit. Cannot create tables, change metadata/audit records, read the migration ledger or access Core tables.

Migrations in `src/main/resources/db/migration` run with the migrator credential, not the application's runtime credential. V1 creates singleton metadata; V2 adds account/session/token/mail/rate/audit tables and required grants. Commerce tables are reserved for later migrations. No shared Core migrations or public objects are changed by Flyway.

Flyway is restricted to `atlas_web`: schema auto-creation disabled, baseline disabled, clean disabled, validation enabled. Provisioning is separate from startup. `provision.sql` is for fresh isolated databases, not an instruction to execute it against the game database. Preserve applied migration files; new changes get new versions.

The temporary `public.core_sentinel` exists only in tests, proving that public data survives and runtime cannot access it. The active Minecraft database has not been inspected or modified by M1.

## Environment and profiles

Base configuration requires all database credentials from environment:

| Variable | Purpose |
| --- | --- |
| ATLAS_DB_URL | Dedicated PostgreSQL JDBC URL |
| ATLAS_DB_USERNAME / ATLAS_DB_PASSWORD | Runtime role credential |
| ATLAS_MIGRATION_USERNAME / ATLAS_MIGRATION_PASSWORD | Separate schema owner credential |
| SPRING_PROFILES_ACTIVE | `local`, `test`, `staging` or `prod` |
| ATLAS_BIND_ADDRESS / ATLAS_PORT | Bind address/port; defaults loopback:8080 |
| ATLAS_CORS_ORIGINS | Exact comma-separated frontend origins; empty permits no cross-origin requests |

`local` allows the two loopback Angular origins and HTTP session cookies; `test` is isolated. `staging`/`prod` require external secrets, use Secure/HttpOnly/SameSite=Lax cookies and permit no cross-origin traffic unless configured. Anonymous CSRF and authenticated sessions use Spring Session JDBC, survive API restart, expire and are revoked by logout/reset. Email delivery is private local files in local/test and authenticated STARTTLS SMTP in staging/prod. Configure ATLAS_MAIL_ENCRYPTION_KEY (32 random bytes, base64) and ATLAS_WEB_URL; SMTP additionally needs ATLAS_MAIL_FROM, ATLAS_SMTP_HOST/PORT/USERNAME/PASSWORD. Existing M1 .env files need the encryption key added securely before M2 startup. Environment files use plain KEY=value; the local runner does not evaluate shell syntax.

Same-origin deployment is preferred. A reverse proxy must terminate HTTPS; forwarded headers are not trusted by default. Exact domains/proxy rules await the infrastructure decision. Do not expose the application directly to the internet or expose metrics unauthenticated. `infra/atlas-api.service` is a deployment template, not an installed service; use a separate Linux user and environment file with restricted permissions.

## Structure and error contract

`system/controller` → `system/service` → `system/repository` → PostgreSQL. Shared HTTP concerns live in `shared/web`, JSON errors in `shared/error`, security/CORS/clock in `config`. Add each business feature as its own module/package in M2 onward. Filters handle security concerns only; business workflows stay in services and no SQL in controllers. A central injectable UTC Clock is available for future time-sensitive rules. Metadata is deliberately uncached so DB failure is visible and there is no unnecessary cache invalidation mechanism.

Application/security JSON errors include `code`, `message`, `requestId`, `fieldErrors`; validation never includes the rejected values. Request IDs are generated server-side and returned as X-Request-ID. Logs are structured JSON with request ID, method, status and duration; bodies, query strings, authorization headers and credentials are not logged. Actuator responses follow its health protocol; CORS rejections follow Spring's CORS protocol.

## Tests and CI

Integration tests use real PostgreSQL: migration reentry/checksums, role isolation, metadata access, readiness, metrics protection, future ADMIN rejection, exact CORS, CSRF, malformed JSON and Bean Validation. Unit tests reject wildcard/path/credential origins. The native harness additionally verifies packaged-JAR startup, restart persistence, DB outage and recovery/startup failure.

Workflow in the parent repository: `.github/workflows/atlas-api.yml`. On push/PR it builds, runs PostgreSQL integration tests, produces the JAR, dependency inventory and test reports. PR dependency review rejects newly introduced high/critical advisories according to GitHub's database. It is not a substitute for a complete periodic vulnerability scan or a guarantee of no vulnerabilities. Remote CI and dependency review are not yet executed/published from this workspace; availability of dependency review depends on repository/account support.

The VM local user service `atlas-api.service` runs native persistent development; `atlas-web.service` proxies its account routes. No external publish, production deployment or Git push was performed. Hosted staging/production, operational authentication and secret-store configuration require the deployment environment and remain external rollout tasks.

## Official references

- [Spring Boot requirements](https://docs.spring.io/spring-boot/system-requirements.html)
- [Spring Boot Actuator health and endpoint exposure](https://docs.spring.io/spring-boot/reference/actuator/endpoints.html)
- [Spring Security CSRF](https://docs.spring.io/spring-security/reference/servlet/exploits/csrf.html)

Commercial/API contract and VIP pause/resume decisions live in `atlas-docs/M0-BACKEND.md` and `atlas-docs/api/openapi-m0.json`. Gateway confirmed: Mercado Pago Checkout Pro via Orders API, PIX/card; integration comes after the account/catalog/order milestones.

Release 0.3.1 adds branded multipart HTML/text verification and recovery emails, a registration confirmation dialog with spam guidance and a styled verification success page. Token and session rules are unchanged.

M4 (0.4.2) adds hashed Minecraft link challenges, trusted same-VM Core proofs, final web confirmation, password-protected unlink, owner-scoped orders and transactional idempotency. Checkout snapshots canonical site subject and server-recalculated pricing. Sales remain disabled by both the global switch and each offer. See `../atlas-docs/M4-BACKEND.md`. Run `python3 scripts/verify-local.py --core-tests --web-tests` to include real Core repository migration/merge checks on a separate disposable database.

Release 0.4.2 changes Minecraft linking to six ASCII digits (leading zeroes preserved), five-minute expiry, keyed hashes and bounded proof attempts. V6 retires legacy pending challenges without touching confirmed links. Active code uniqueness and a fifteen-minute reuse cooldown are protected in the database transaction.

M5 (0.5.0, V7) adds hosted Mercado Pago preferences, a unique durable creation attempt per order, authenticated/deduplicated webhooks, leased payment jobs, reconciliation, compensations held for review and an atomic delivery outbox. External test credentials/homologation are pending. Both sales and payments remain disabled. See `../atlas-docs/M5-BACKEND.md` and `.env.example`. Install the verified API only with `scripts/deploy-m5-local.py`; M4 installation script is historical and targets its old artifact.
