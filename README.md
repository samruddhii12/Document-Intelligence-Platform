# DocMind — Document & Data Intelligence Platform

FastAPI + Streamlit + PostgreSQL/pgvector + local Ollama. Workspace authorization is shared by document intelligence and structured-data analysis.

## What is implemented

- PostgreSQL-backed original uploads with SHA-256 verification; no permanent filesystem upload dependency.
- Durable PostgreSQL jobs, worker leases/heartbeats, bounded retries, processing status, and deletion checks.
- PDF, DOCX, Markdown, and text ingestion with structural locations and embedding-tokenizer-aware chunks.
- Scoped semantic + indexed PostgreSQL full-text retrieval, citations, document chat, summaries, questions, and comparison.
- CSV/XLSX preview, schema, missing values, duplicates, descriptive statistics, filters, aggregations, trends, IQR outliers, correlations, charts, AI questions, summaries, and persisted analysis history.
- Email/password authentication, email verification, revocable access sessions, rotated refresh tokens, Google OIDC with PKCE/state/nonce checks, explicit account linking, expiring guest sessions, quotas, and guest claiming.

Email and Google authentication integrations require provider configuration. They are disabled clearly when credentials are absent. Guest mode and the document/data features can be used without either provider.

## Local setup

Use Python 3.11. PostgreSQL must have the pgvector extension installed; Ollama must have the selected generation model installed.

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
ollama pull qwen2.5:3b
```

Create `.env` in the project root. These are placeholders, not actual credentials:

```dotenv
DATABASE_URL=postgresql+psycopg2://YOUR_USER:YOUR_PASSWORD@127.0.0.1:5432/YOUR_DATABASE
JWT_SECRET_KEY=YOUR_RANDOM_SECRET_AT_LEAST_32_CHARACTERS
OLLAMA_URL=http://127.0.0.1:11434/api/generate
OLLAMA_MODEL=qwen2.5:3b
PUBLIC_API_URL=http://localhost:8000
FRONTEND_URL=http://localhost:8501
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM=
SMTP_STARTTLS=true
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

Generate a JWT secret with `python -c "import secrets; print(secrets.token_hex(32))"`. Keep `.env` and OAuth/SMTP secrets out of Git. The project honors your local `.gitignore`; `.dockerignore` independently excludes secrets, uploads, and caches from image build contexts.

Apply migrations before starting the app:

```bash
.venv/bin/python -m alembic upgrade head
```

`python -m backend.init_db` now applies Alembic migrations too. Existing users are preserved but must verify their email; old JWTs must be replaced by signing in again. Existing guest credentials are hashed and retain a bounded lifetime.

Run these in separate terminals:

```bash
ollama serve
.venv/bin/python -m uvicorn backend.main:app --reload
.venv/bin/python -m backend.worker
.venv/bin/python -m streamlit run frontend/app.py
```

Open http://localhost:8501 and API docs at http://localhost:8000/docs. If Ollama is already running, do not start a second copy. The worker is essential: uploads return HTTP 202 and remain queued until a worker processes them. Refresh processing status in the frontend.

## Verification emails with Gmail (local development)

1. Enable Google Account 2-Step Verification.
2. Create an app password at https://myaccount.google.com/apppasswords (availability depends on account policy).
3. Configure the following in `.env`, using your own email and app password:

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=YOUR_GMAIL_ADDRESS
SMTP_PASSWORD=YOUR_APP_PASSWORD_WITHOUT_SPACES
SMTP_FROM=YOUR_GMAIL_ADDRESS
SMTP_STARTTLS=true
```

Restart API and worker after configuration changes. Registration queues a one-time verification link for the worker to deliver. Links expire after 30 minutes, resends have a 60-second cooldown, and requests are rate limited. Open the link and click **Confirm email**, then sign in or refresh account status in your original tab. Old verification links are invalidated by resends. No verification bypass is enabled in development.

A different SMTP provider can use the same configuration. Provider sending limits apply. Check worker logs if delivery fails; the app never exposes verification tokens through a public endpoint.

## Google Sign-In setup

1. Create a project at https://console.cloud.google.com/.
2. Configure Google Auth Platform branding, external audience, and test users while the app is in testing.
3. Create an OAuth client of type **Web application**.
4. Add the authorized redirect URI **exactly**: `http://localhost:8000/auth/google/callback`.
5. Put the client ID and secret in `.env` as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.
6. Restart the API. Use **Start Google Sign-In**, complete the provider flow in the new tab, return to the original tab, and click **Complete Google Sign-In**.

Use `openid email profile` scopes only. Public deployment needs the correct HTTPS callback/frontend URLs and appropriate consent-screen publishing configuration. No Google access/refresh tokens are retained. Existing password accounts are never silently merged: sign in to your verified account and use **Link Google**. Linking requires the same verified email and a live application session.

## Storage and legacy imports

`stored_objects` contains upload metadata and checksums; `object_payloads` stores original bytes separately. Documents, chunks, datasets, jobs, users, sessions, and analysis results are also in PostgreSQL. Normalized datasets use compressed JSON with typed pandas table schemas, not uploaded Python pickle files.

PDF/DOCX/text parsers work on in-memory bytes. Frameworks may spool request content transiently; no processing path depends on a permanent upload file. Model caches and PostgreSQL's own data directory remain independent infrastructure storage.

For an existing installation:

```bash
.venv/bin/python -m backend.migrate_content
```

This imports files inside the configured legacy `STORAGE_DIR`, verifies their bytes, and switches document records to PostgreSQL. Missing originals are reported; previously extracted chunks remain usable but cannot reconstruct the original file. To remove an original during its initial verified import, explicitly use `--remove-verified-local`. Importing by default leaves old files as backup copies. Never remove legacy files until the database is backed up and content checks have passed.

Deleting a document removes its bytes, chunks, jobs, and entire conversations that cite it. Dataset deletion removes original/normalized data, jobs, and analysis results in the same transaction. Expired guest workspaces are removed by worker maintenance. Database backups may retain deleted information until the backup retention window ends.

## Data Analysis behavior and limits

- Each XLSX worksheet is an independent table. Stable internal column IDs (`c1`, `c2`, ...) distinguish duplicate display names.
- XLSX formulas are not executed; cached formula values may be absent. Macros and legacy `.xls` are not supported.
- CSV/TXT/Markdown use UTF-8 or UTF-8 with BOM. Other encodings must be converted before upload.
- Defaults: 20 MB upload, 100,000 dataset rows across a workbook, 200 columns, 10 worksheets, 100 MB normalized/unpacked content.
- DuckDB runs in memory with external access disabled, one thread, 128 MB engine memory, and an interrupt timer. Only trusted compiled operations run; AI/user-supplied SQL and Python are rejected.
- Results have a maximum of 500 displayed rows. Statistics and aggregations use all filtered rows, not just the preview.
- Missing values, duplicates, correlations, and IQR outlier flags are deterministic calculations. Correlation does not establish causation.
- AI questions produce schema-constrained, validated plans; unsupported or ambiguous requests ask for clarification or return a validation message. Small local models can still misunderstand a question: inspect the recorded plan and use Explore to specify exact calculations.
- Guest defaults: 24-hour lifetime, two workspaces, ten uploads, and 100 API requests per hour. Guests can sign in/register, verify, and claim their current session into an account.

## Docker

```bash
docker compose up --build
```

Compose starts PostgreSQL, runs migrations, and starts API, worker, and frontend. There is no upload-directory bind mount. The PostgreSQL volume persists all platform data; database backups are required. The frontend uses the internal `http://backend:8000` address.

The database container is exposed on localhost port 5433 to avoid clashing with an existing local PostgreSQL installation. Containers use `db:5432` internally. If changing `POSTGRES_PASSWORD`, also set `DOCKER_DATABASE_URL` to matching credentials in `.env`. Changing the environment does not change the password in an already-initialized PostgreSQL volume.

Ollama runs on the host. It must be reachable from containers; an Ollama instance bound only to host loopback may require an explicit host networking configuration. Scope any non-loopback listener to your local development network. Public deployment also needs HTTPS, deployment secrets, proxy upload limits, operational monitoring, and resource isolation for parsers/analysis workers.

## Validation

Tests remain local and are excluded from Git as requested. In the development workspace:

```bash
.venv/bin/python -m pytest -q
RUN_DB_TESTS=1 HF_HUB_OFFLINE=1 .venv/bin/python -m pytest -q
```

Integration tests use a real PostgreSQL database, cached embeddings, and Ollama. Test changes are rolled back. Email transport and Google provider responses are simulated; live delivery/provider acceptance require your configuration. The tests cover uploads, all formats, analysis, ownership, guest expiry, deletion, refresh/logout, verification, Google replay/account-linking protections, and frontend interactions.

The `eval/` directory contains a retrieval-evaluation scaffold; it does not claim measured answer accuracy. Current limitations include no scanned-PDF OCR pipeline, no arbitrary-code analysis, no cross-dataset joins, and no large-dataset distributed engine.
