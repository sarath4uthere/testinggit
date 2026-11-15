# Runbook: what to do when something is wrong

## Quick status
```
bash scripts/status.sh          # version and health of every environment
docker compose -p shop-prod ps  # containers of one environment
```

## Deployment failed
1. Read the failing stage's console output in Jenkins.
2. If a **deploy** stage failed, `deploy.sh` already tried to roll back. The output says whether the
   rollback worked ("rollback succeeded") or not ("manual intervention needed").
3. If the rollback also failed:
   ```
   docker compose -p shop-<env> logs --tail 100 api
   docker compose -p shop-<env> logs --tail 100 db
   ```
4. Redeploy a known good tag by hand: `bash scripts/deploy.sh <env> <good-tag>`

## Symptom table
| Symptom | Likely cause | Check |
|---|---|---|
| `/api/ready` returns 503 | database unreachable or wrong password | `docker compose logs db`, DB_* values |
| api container restarts | migration failed or app crash | `docker compose logs api` (`[migrate]` lines) |
| Exit code 137 | out of memory (limit 256m) | `docker stats`, raise `mem_limit` |
| Web shows "Cannot reach the API" | api not healthy | `docker compose ps`, api logs |
| 502 from nginx | api container down | restart api, check logs |
| Disk filling up | old images and logs | `docker system df`, then `docker image prune` |
| Pipeline cannot reach ports | wrong `SMOKE_HOST` | must be `host.docker.internal` inside Jenkins |

## Routine tasks (what a sysadmin owns here)
- **Patch base images monthly:** rebuild with `docker build --no-cache`, run the pipeline, promote.
- **Back up databases:** `docker compose -p shop-prod exec db pg_dump -U shop shop > shop-prod.sql`
- **Restore:** `cat shop-prod.sql | docker compose -p shop-prod exec -T db psql -U shop shop`
- **Back up Jenkins:** back up the `jenkins_home` volume.
- **Clean up:** `docker image prune -a` (only when you are sure old tags are not needed for rollback).
- **Rotate a password:** change it in the env file/secret store AND in Postgres (`ALTER USER`),
  then redeploy. Changing only the env file does not change an existing database.
