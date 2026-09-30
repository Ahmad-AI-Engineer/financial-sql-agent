# Financial SQL Agent

A Streamlit application that answers questions about a PostgreSQL financial
database. The LangChain agent sends each question to an OpenRouter model, lets
the model call a read-only `run_sql` tool, and turns the returned rows into a
plain-language answer.

## Architecture

```text
Browser -> Streamlit -> LangChain agent -> OpenRouter LLM
                          |                    |
                          |<-- tool request ---|
                          v
                    run_sql tool -> PostgreSQL
```

- `src/agent.py` creates the LLM, prompt, memory checkpointer, and agent.
- `src/tools.py` exposes the guarded `run_sql` tool and retry handling.
- `src/db.py` opens read-only query connections to PostgreSQL.
- `src/seed_data.py` creates the local demonstration database.
- `src/extract_schema.py` refreshes the schema supplied to the agent.
- `schema.yaml` tells the LLM which tables, columns, and joins exist.
- `app.py` provides the Streamlit chat interface.

Start with `app.py` for the frontend flow and `src/agent.py` for the main agent
logic. The remaining files support configuration, database access, setup, and
deployment.

## Requirements

- Docker with Docker Compose (recommended), or Python 3.11+
- An [OpenRouter API key](https://openrouter.ai/keys)
- A tool-calling model available through OpenRouter

## Environment configuration

Create your local environment file:

```bash
cp .env.example .env
```

PowerShell equivalent:

```powershell
Copy-Item .env.example .env
```

Open `.env`, replace `OPENROUTER_API_KEY`, and change `DB_PASSWORD` before a
server deployment. `.env` is ignored by both Git and Docker builds.

Important settings:

| Variable | Purpose | Default |
|---|---|---|
| `OPENROUTER_API_KEY` | OpenRouter authentication; required | none |
| `OPENROUTER_MODEL` | Tool-calling model ID | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| `DATABASE_URL` | Optional complete PostgreSQL connection URL | none |
| `DB_HOST`, `DB_PORT` | Database host and port when `DATABASE_URL` is absent | `localhost`, `5432` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Database credentials | demo values |
| `DB_CONNECT_TIMEOUT` | Connection timeout in seconds | `10` |
| `SCHEMA_PATH` | Schema YAML path, absolute or project-relative | `schema.yaml` |
| `MAX_RETRIES` | SQL correction attempts | `3` |
| `APP_PORT` | Host port used by Docker Compose | `8502` |

`DATABASE_URL` takes priority over the individual `DB_*` connection settings.

## Recommended: run everything with Docker

After creating `.env`:

```bash
docker compose up --build
```

If your Docker installation uses the standalone command, replace
`docker compose` with `docker-compose`.

Open `http://localhost:8502`, or use the port configured as `APP_PORT`.

Compose performs startup in this order:

1. PostgreSQL starts and passes its health check.
2. The `setup` service initializes demo data only when the tables are absent.
3. The setup service extracts the live database schema into a shared volume.
4. Streamlit starts only after setup finishes successfully.

Useful commands:

```bash
docker compose ps
docker compose logs -f app
docker compose down
```

Database data and the generated schema use named Docker volumes, so they survive
container recreation. `docker compose down -v` deletes those volumes and all
demo database data.

## Local Python development

Start only PostgreSQL in Docker:

```bash
docker compose up -d postgres
```

Create and activate a virtual environment, then install the pinned dependencies:

```bash
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Ensure local `.env` uses the published PostgreSQL port (default `5433`), then run:

```bash
python -m src.seed_data
python -m src.extract_schema
python -m streamlit run app.py
```

Seeding is safe to run again: it skips a database that already has all four demo
tables. To deliberately erase and rebuild the demo tables, use:

```bash
python -m src.seed_data --force
```

That command is destructive and should only be used for demo data.

## Server deployment

For a VPS or any server supporting Docker Compose:

1. Copy the project to the server.
2. Create `.env` from `.env.example`.
3. Set a real `OPENROUTER_API_KEY` and a strong `DB_PASSWORD`.
4. Set `APP_PORT` to the port exposed by your firewall or reverse proxy.
5. Run `docker compose up -d --build`.
6. Put HTTPS in front of Streamlit with your normal reverse proxy.

PostgreSQL binds to `127.0.0.1` by default, so it is not exposed publicly. The
containers communicate by the Compose service name `postgres`, not a fixed IP.

For a platform that builds only the `Dockerfile`, supply these server variables:

```text
OPENROUTER_API_KEY=...
DATABASE_URL=postgresql://user:password@database-host:5432/database
```

The container listens on the platform-provided `PORT`, falling back to `8501`.
If the external database does not use the included demo schema, generate a
matching `schema.yaml` during deployment and point `SCHEMA_PATH` to it.

## Portable path behavior

- `.env` is loaded from the project root, independent of the launch directory.
- Relative `SCHEMA_PATH` values resolve from the project root.
- Absolute Linux or Windows schema paths are accepted.
- Docker uses internal service names and named volumes instead of fixed machine paths.
- No source code contains a developer-specific absolute path.

## Verification

Run static/import checks without calling OpenRouter:

```bash
python -m compileall -q app.py src
python -c "from src.agent import build_agent; build_agent(); print('agent build: OK')"
docker compose config --quiet
```

After starting Docker, verify the web server:

```bash
docker compose ps
curl http://localhost:8502/_stcore/health
```

Expected health response:

```text
ok
```

## Example questions

- How many customers do we have?
- What is the total amount of unpaid invoices?
- Show the top five customers by total invoice amount.
- How much did we spend on salaries last year?
- Which country has the most customers?

## Safety and limitations

- The tool accepts only one `SELECT`/`WITH` statement and rejects common write
  keywords. Database queries also run in a read-only transaction.
- Use a PostgreSQL account with database-level read-only permissions for
  production defense in depth.
- Conversation memory is in-process and requires a single app instance. See
  [Known limitation: conversation memory](#known-limitation-conversation-memory).
- Free OpenRouter models can have availability and rate-limit changes. Choose a
  stable tool-calling model for production.

## Known limitation: conversation memory

- Conversation memory uses `InMemorySaver`, which holds history in the RAM of the
  running app process.
- Because of that:
  - Conversation history is cleared whenever the app restarts.
  - The app must run as a **single instance**, not multiple replicas. With more
    than one replica, a user's follow-up question can land on a different replica
    and lose the conversation memory. The retry counter in `src/tools.py` is
    per-process for the same reason.
- Switching the checkpointer to `PostgresSaver` would remove this limitation by
  storing history in the database. It is intentionally **not** implemented in
  this version.

## Project structure

```text
.
|-- .env.example
|-- .gitignore
|-- .dockerignore
|-- Dockerfile
|-- docker-compose.yml
|-- requirements.txt
|-- schema.yaml
|-- app.py
`-- src/
    |-- __init__.py
    |-- agent.py
    |-- config.py
    |-- db.py
    |-- extract_schema.py
    |-- seed_data.py
    `-- tools.py
```

Local-only items are kept out of the main code: `.venv/` contains installed
Python packages, while `archive/` contains the original uploaded ZIP. Both are
ignored by Git and Docker.
