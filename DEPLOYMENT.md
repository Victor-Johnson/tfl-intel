# Production deployment

The supported portfolio deployment is one Ubuntu/Debian VPS running Docker
Compose. The product surface is `https://tfl-intel.victorjohnson.dev`, with a
secondary BI workspace at `https://tfl-bi.victorjohnson.dev`. Postgres and
Airflow remain private, and Metabase administration requires authentication.

## Topology

```text
Internet -> DNS -> Nginx Proxy Manager -> tfl-intel-api:8000
                                          |
                         read-only DuckDB volume
                                          ^
TfL API -> Airflow -> Postgres -> DuckDB snapshot -> dbt
                                      |
                                      -> validated Postgres BI publication
                                           -> Metabase:3000
```

Only the API and Metabase join the external `npm_proxy` network. Postgres,
Airflow, and host-bound service ports listen on `127.0.0.1`, not the public
interface. Metabase reaches only its application database and a schema-limited
analytics account on the operational Postgres service.

## 1. Prepare the VPS

Install Docker Engine with the Compose and Buildx plugins, then create a restricted account
and directories. Allow at least 6 GB RAM for the combined Airflow and Metabase
stack. Replace the SSH key with your deployment public key.

Check `docker compose version` and `docker buildx version` before deployment.
On Debian/Ubuntu installations using Docker's official packages, the plugins
are `docker-compose-plugin` and `docker-buildx-plugin`.

```bash
sudo adduser --disabled-password --gecos '' tfl-deploy
sudo usermod -aG docker tfl-deploy
sudo install -d -o tfl-deploy -g tfl-deploy /opt/tfl-intel
sudo install -d -o tfl-deploy -g tfl-deploy /var/backups/tfl-intel
sudo install -d -m 700 -o tfl-deploy -g tfl-deploy /home/tfl-deploy/.ssh
sudoedit /home/tfl-deploy/.ssh/authorized_keys
```

Clone the repository as that account:

```bash
sudo -u tfl-deploy git clone https://github.com/Victor-Johnson/tfl-intel.git /opt/tfl-intel
cd /opt/tfl-intel
cp .env.example .env
mkdir -p secrets
cp secrets.example/postgres_password.txt.example secrets/postgres_password.txt
cp secrets.example/airflow_db_password.txt.example secrets/airflow_db_password.txt
cp secrets.example/metabase_app_db_password.txt.example secrets/metabase_app_db_password.txt
cp secrets.example/metabase_reader_password.txt.example secrets/metabase_reader_password.txt
chmod 600 .env secrets/*.txt
```

Replace all example passwords and the default Airflow administrator password.
Set `AIRFLOW_UID` in `.env` to the output of `id -u` while logged in as
`tfl-deploy`. Airflow runs under that UID, so it can read the owner-only
Compose secret files without making them world-readable; bootstrap rejects a
mismatch.
Set `TFL_APP_KEY` in `.env`; TfL recommends registration for Unified API use.
Keep `API_BIND_ADDRESS`, `POSTGRES_BIND_ADDRESS`, and
`AIRFLOW_BIND_ADDRESS` set to `127.0.0.1`.

## 2. Connect Nginx Proxy Manager

Use the Docker network already attached to Nginx Proxy Manager. The examples
assume it is named `npm_proxy`, matching `.env`.

```bash
docker network inspect npm_proxy >/dev/null 2>&1 || docker network create npm_proxy
docker network connect npm_proxy YOUR_NPM_CONTAINER
```

The second command is needed only when the proxy container is not already on
that network. In Nginx Proxy Manager create this proxy host:

| Setting | Value |
|---|---|
| Domain | `tfl-intel.victorjohnson.dev` |
| Scheme | `http` |
| Forward hostname | `tfl-intel-api` |
| Forward port | `8000` |
| Cache assets | Off |
| Block common exploits | On |
| WebSocket support | Off |

Create a second proxy host for Metabase:

| Setting | Value |
|---|---|
| Domain | `tfl-bi.victorjohnson.dev` |
| Scheme | `http` |
| Forward hostname | `tfl-intel-metabase` |
| Forward port | `3000` |
| Cache assets | Off |
| Block common exploits | On |
| WebSocket support | On |

Request a Let's Encrypt certificate, enable **Force SSL**, **HTTP/2**, and
**HSTS** on both hosts. Add `A` records for `tfl-intel.victorjohnson.dev` and
`tfl-bi.victorjohnson.dev` pointing to the VPS; add `AAAA` only when IPv6 is
configured and firewalled correctly.

Do not create proxy hosts for ports 5432 or 8080. Access Airflow when needed:

```bash
ssh -L 8080:127.0.0.1:8080 tfl-deploy@YOUR_VPS
```

Then open `http://localhost:8080`.

## 3. First deployment

Ensure Nginx Proxy Manager is reachable through the configured network, then:

```bash
cd /opt/tfl-intel
./scripts/bootstrap_production.sh
curl --fail https://tfl-intel.victorjohnson.dev/health
curl --fail https://tfl-intel.victorjohnson.dev/ready
curl --fail https://tfl-bi.victorjohnson.dev/api/health
```

Bootstrap is idempotent. It validates configuration, starts the stack, applies
the numbered SQL migrations, loads reference and status data, snapshots into
DuckDB, runs dbt and mart validation, unpauses both DAGs, and checks the API.
It also creates the restricted Metabase reader, publishes the validated marts,
and verifies Metabase health. Complete the one-time dashboard configuration in
[the Metabase guide](docs/metabase/README.md).

## 4. Continuous deployment

Create a protected GitHub environment named `production` with required review
if desired. Add these secrets:

| Secret | Meaning |
|---|---|
| `DEPLOY_HOST` | VPS hostname or address |
| `DEPLOY_USER` | `tfl-deploy` |
| `DEPLOY_PATH` | `/opt/tfl-intel` |
| `DEPLOY_SSH_KEY` | Private key dedicated to deployment |
| `DEPLOY_KNOWN_HOSTS` | Output of a separately verified `ssh-keyscan` |

A push to `main` deploys only after lint, formatting, typing, Python unit and
integration tests, dbt tests, Compose validation, and container builds pass.
The workflow passes the exact tested commit SHA, so a later push cannot be
deployed by an earlier workflow run. The server refuses to deploy over a dirty
checkout. If bootstrap fails, the deployment script restores the previous Git
revision and rebuilds that version against the unchanged persistent volumes.

## 5. Backups

Install the supplied systemd units:

```bash
sudo cp deploy/systemd/tfl-intel-backup.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tfl-intel-backup.timer
sudo systemctl start tfl-intel-backup.service
sudo systemctl status tfl-intel-backup.service
```

The script writes custom-format dumps for the operational Postgres database and
the Metabase application database to `/var/backups/tfl-intel`, retaining seven
daily and four Sunday copies of each. It checks both archives, restores the
operational dump into a disposable database, then prunes operational raw
history older than 90 days. A failed restore stops before pruning. Reserve
disk headroom for the temporary restore. The published BI schema is
rebuildable; the Metabase application dump preserves users, questions, and
dashboard definitions. Copy backups outside the VPS. Backup rotation may
retain records older than 90 days for a short period after they leave the
operational database.

Test a dump before relying on it:

```bash
pg_restore --list /var/backups/tfl-intel/daily/YOUR_BACKUP.dump >/dev/null
pg_restore --list /var/backups/tfl-intel/metabase/daily/YOUR_BACKUP.dump >/dev/null
```

To restore, stop Airflow, restore into an empty Postgres database, and rebuild
the analytical file:

```bash
docker compose -f docker-compose.yml -f docker-compose.airflow.yml \
  -f docker-compose.metabase.yml -f docker-compose.production.yml \
  stop airflow-scheduler airflow-webserver
docker compose -f docker-compose.yml -f docker-compose.airflow.yml \
  -f docker-compose.metabase.yml -f docker-compose.production.yml \
  exec -T postgres \
  pg_restore --clean --if-exists --no-owner -U tfl_intel -d tfl_intel \
  < /var/backups/tfl-intel/daily/YOUR_BACKUP.dump
./scripts/bootstrap_production.sh
```

Restore the Metabase application database separately when its saved questions
or dashboard configuration must be recovered:

```bash
docker compose -f docker-compose.yml -f docker-compose.airflow.yml \
  -f docker-compose.metabase.yml \
  -f docker-compose.production.yml stop metabase
docker compose -f docker-compose.yml -f docker-compose.airflow.yml \
  -f docker-compose.metabase.yml \
  -f docker-compose.production.yml exec -T metabase-db \
  pg_restore --clean --if-exists --no-owner -U metabase -d metabase \
  < /var/backups/tfl-intel/metabase/daily/YOUR_BACKUP.dump
docker compose -f docker-compose.yml -f docker-compose.airflow.yml \
  -f docker-compose.metabase.yml \
  -f docker-compose.production.yml start metabase
```

## Operations checklist

- `/health` returns HTTP 200.
- `/ready` reports `ready` with no missing tables.
- The latest successful pipeline is less than 15 minutes old.
- Both Airflow DAGs are unpaused and the five-minute DAG is succeeding.
- Metabase health succeeds and only the curated dashboard is publicly shared.
- The `metabase_reader` account cannot query `raw`, `staging`, or `ml`.
- Postgres and Airflow are not reachable from the public internet.
- The backup timer is active and a recent dump passes `pg_restore --list`.
- Docker logs remain within the configured three-by-10 MB rotation policy.

Data provided by [Transport for London](https://tfl.gov.uk/info-for/open-data-users/).
This is an independent, unofficial portfolio project.
