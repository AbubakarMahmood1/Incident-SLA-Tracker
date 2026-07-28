#!/bin/sh
set -eu

command -v docker >/dev/null 2>&1 || {
  echo "docker is required" >&2
  exit 2
}
command -v curl >/dev/null 2>&1 || {
  echo "curl is required" >&2
  exit 2
}

backup_file=""

cleanup() {
  if [ -n "$backup_file" ]; then
    rm -f "$backup_file"
  fi
  docker compose down -v --remove-orphans >/dev/null 2>&1 || true
}

docker compose down -v --remove-orphans >/dev/null 2>&1 || true
trap cleanup EXIT INT TERM

docker compose up -d --build postgres migrate api worker

wait_for_ready() {
  attempt=0
  until curl --fail --silent --max-time 8 \
    http://127.0.0.1:8000/health/ready >/dev/null; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 40 ]; then
      docker compose logs
      exit 1
    fi
    sleep 2
  done
}

wait_for_ready

printf '%s\n' 'smoke administrator password' | \
  docker compose exec -T api incident-sla create-user \
    --username smoke-admin \
    --email smoke-admin@example.com \
    --display-name "Smoke Admin" \
    --password-stdin \
    --admin

token_json=$(curl --fail --silent \
  -X POST http://127.0.0.1:8000/api/v1/auth/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode 'username=smoke-admin' \
  --data-urlencode 'password=smoke administrator password')
token=$(printf '%s' "$token_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

payload='{"title":"Compose smoke","description":"Verifies migration, auth, idempotency, and API persistence","priority":"high"}'
first=$(curl --fail --silent \
  -X POST http://127.0.0.1:8000/api/v1/incidents \
  -H "Authorization: Bearer $token" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: compose-smoke-create-001' \
  -d "$payload")
second=$(curl --fail --silent \
  -X POST http://127.0.0.1:8000/api/v1/incidents \
  -H "Authorization: Bearer $token" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: compose-smoke-create-001' \
  -d "$payload")

incident_id=$(FIRST="$first" SECOND="$second" python3 - <<'PY'
import json, os
first = json.loads(os.environ["FIRST"])
second = json.loads(os.environ["SECOND"])
assert first["id"] == second["id"]
assert first["sla"]["response_outcome"] == "pending"
assert first["revision"] == 1
print(first["id"])
PY
)

API_ID=$(docker compose ps -q api) \
WORKER_ID=$(docker compose ps -q worker) \
POSTGRES_ID=$(docker compose ps -q postgres) \
python3 - <<'PY'
import json
import os
import subprocess


def inspect(identifier: str) -> dict:
    return json.loads(subprocess.check_output(["docker", "inspect", identifier]))[0]


api = inspect(os.environ["API_ID"])
worker = inspect(os.environ["WORKER_ID"])
postgres = inspect(os.environ["POSTGRES_ID"])

for container in (api, worker):
    assert container["Config"]["User"] in {"app", "10001"}
    host = container["HostConfig"]
    assert host["ReadonlyRootfs"] is True
    assert "ALL" in host["CapDrop"]
    assert "no-new-privileges:true" in host["SecurityOpt"]
    assert "/tmp" in host["Tmpfs"]

bindings = api["HostConfig"]["PortBindings"]["8000/tcp"]
assert bindings == [{"HostIp": "127.0.0.1", "HostPort": "8000"}]
assert not postgres["HostConfig"]["PortBindings"]

api_networks = set(api["NetworkSettings"]["Networks"])
worker_networks = set(worker["NetworkSettings"]["Networks"])
postgres_networks = set(postgres["NetworkSettings"]["Networks"])
backend = next(name for name in postgres_networks if name.endswith("_backend"))
edge = next(name for name in api_networks if name.endswith("_edge"))
egress = next(name for name in worker_networks if name.endswith("_egress"))
assert postgres_networks == {backend}
assert api_networks == {backend, edge}
assert worker_networks == {backend, egress}

network = json.loads(subprocess.check_output(["docker", "network", "inspect", backend]))[0]
assert network["Internal"] is True
PY

docker compose stop postgres >/dev/null
live_code=$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --max-time 8 http://127.0.0.1:8000/health/live)
ready_code=$(curl --silent --output /dev/null --write-out '%{http_code}' \
  --max-time 8 http://127.0.0.1:8000/health/ready || true)
test "$live_code" = "200"
test "$ready_code" != "200"

docker compose start postgres >/dev/null
wait_for_ready

after_database_recovery=$(curl --fail --silent \
  -X POST http://127.0.0.1:8000/api/v1/incidents \
  -H "Authorization: Bearer $token" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: compose-smoke-create-001' \
  -d "$payload")

docker compose restart api worker >/dev/null
wait_for_ready

after_process_restart=$(curl --fail --silent \
  -X POST http://127.0.0.1:8000/api/v1/incidents \
  -H "Authorization: Bearer $token" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: compose-smoke-create-001' \
  -d "$payload")

INCIDENT_ID="$incident_id" \
DATABASE_RECOVERY="$after_database_recovery" \
PROCESS_RESTART="$after_process_restart" \
python3 - <<'PY'
import json
import os

expected = os.environ["INCIDENT_ID"]
assert json.loads(os.environ["DATABASE_RECOVERY"])["id"] == expected
assert json.loads(os.environ["PROCESS_RESTART"])["id"] == expected
PY

backup_file=$(mktemp)
docker compose exec -T postgres \
  pg_dump -U incident -d incident_sla --format=custom --no-owner --no-acl \
  >"$backup_file"

state_query="SELECT concat_ws(':',
  (SELECT count(*) FROM users),
  (SELECT count(*) FROM incidents),
  (SELECT count(*) FROM slas),
  (SELECT count(*) FROM incident_events),
  (SELECT count(*) FROM command_receipts),
  (SELECT count(*) FROM outbox_messages),
  (SELECT version_num FROM alembic_version));"

source_state=$(docker compose exec -T postgres \
  psql -U incident -d incident_sla -Atc "$state_query")

docker compose exec -T postgres \
  dropdb --if-exists -U incident --force incident_sla_restore
docker compose exec -T postgres createdb -U incident incident_sla_restore
docker compose exec -T postgres \
  pg_restore -U incident -d incident_sla_restore --no-owner --no-acl \
  <"$backup_file"

restored_state=$(docker compose exec -T postgres \
  psql -U incident -d incident_sla_restore -Atc "$state_query")
restored_incident_id=$(docker compose exec -T postgres \
  psql -U incident -d incident_sla_restore -Atc \
    "SELECT id FROM incidents WHERE title = 'Compose smoke';")

test "$restored_state" = "$source_state"
test "$restored_incident_id" = "$incident_id"

if docker compose exec -T postgres \
  psql -v ON_ERROR_STOP=1 -U incident -d incident_sla_restore -c \
    "UPDATE incident_events
     SET source = 'tampered'
     WHERE sequence = (SELECT min(sequence) FROM incident_events);" \
  >/dev/null 2>&1; then
  echo "restored event-ledger trigger did not reject mutation" >&2
  exit 1
fi

docker compose exec -T postgres \
  dropdb -U incident --force incident_sla_restore
printf '%s\n' "backup/restore rehearsal passed: $source_state"

docker compose ps
