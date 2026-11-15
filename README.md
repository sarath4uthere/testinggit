# Shop DevOps Lab

A complete, realistic practice project: a small shop (web + API + database) with a multi-stage
Docker build, a Jenkins pipeline that promotes **one image** through four environments, automatic
rollback, monitoring, Kubernetes manifests and an Ansible playbook.

It is a lab. Parts that need real company infrastructure (registry, change tickets, secrets manager,
dedicated build agents) are simplified and marked in the files.

## What is inside

```
shop-devops-lab/
├── api/                    Flask API (Python) - products and orders
│   ├── Dockerfile          4 stages: base, deps, test, runtime
│   ├── app/                code (repo.py = database layer, __init__.py = routes)
│   ├── migrations/         SQL files applied once each by migrate.py
│   └── tests/              23 unit tests (run during the Docker build)
├── web/                    Static frontend + nginx
│   ├── Dockerfile          2 stages: node build, nginx runtime (non-root)
│   └── nginx.conf          serves files, proxies /api to the api container
├── docker-compose.yml      db + api + web (one file, four environments)
├── docker-compose.monitoring.yml   optional Prometheus + Grafana
├── env/                    dev, test, staging, prod settings (ports 8090-8093)
├── Jenkinsfile             16-stage pipeline with approval gate
├── jenkins/                Jenkins container for your lab (Docker + Compose inside)
├── scripts/                build, test, scan, deploy (with rollback), smoke, integration, status
├── k8s/                    Kubernetes manifests (probes, rolling update, limits, security context)
├── ansible/                Playbook to deploy to a Linux VM
├── monitoring/             Prometheus and Grafana config
├── .github/workflows/      the same checks as a GitHub Actions workflow
└── run.ps1                 Windows helper (no bash needed)
```

## Step 1: run it on your PC (Docker Desktop, PowerShell)

```powershell
cd shop-devops-lab
.\run.ps1 test        # unit tests inside Docker (build fails if a test fails)
.\run.ps1 up          # builds both images, starts db + api + web, waits until healthy
```

Open **http://localhost:8090**. You should see 4 sample products, a "Buy 1" button and an
"Add product" form. The footer shows the web and API versions.

Useful extras:

```powershell
.\run.ps1 status                  # containers and health
.\run.ps1 logs                    # follow logs
.\run.ps1 up -Target test         # second environment on port 8091 (own database volume)
.\run.ps1 monitoring              # Prometheus :9090, Grafana :3000 (admin / admin-change-me)
.\run.ps1 down                    # stop, keep data
.\run.ps1 reset                   # stop and delete the database volume
```

API endpoints: `/api/health`, `/api/ready`, `/api/version`, `/api/metrics`,
`/api/products` (GET, POST), `/api/products/<id>`, `/api/orders` (GET, POST).

## Step 2: understand the Dockerfiles

| File | Stage | Purpose |
|---|---|---|
| api/Dockerfile | `deps` | install production libraries only |
| | `test` | run pytest; if a test fails, the image does not build |
| | `runtime` | small final image: no test tools, non-root user 10001, HEALTHCHECK |
| web/Dockerfile | `build` | Node runs build.js and stamps the version |
| | `runtime` | unprivileged nginx on 8080 with only the built files |

Try these:
```powershell
docker build --target test ./api                # only the tests
docker history shop/shop-api:local              # layers and sizes
docker build --progress=plain ./api             # full build output
```
Break a test on purpose, then build again and watch the build stop at the `test` stage.

## Step 3: Jenkins pipeline

1. Create a new GitHub repository (for example `shop-devops-lab`) and push this folder:
   ```powershell
   git init
   git add .
   git commit -m "Shop DevOps lab"
   git branch -M main
   git remote add origin https://github.com/YOURNAME/shop-devops-lab.git
   git push -u origin main
   ```
2. Start the lab Jenkins (stop your old one first if it uses port 8081):
   ```powershell
   cd jenkins
   docker compose up -d --build
   docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
   ```
   Open http://localhost:8081, install the suggested plugins, create your admin user.
3. **New Item** -> name `shop` -> **Pipeline** -> Definition **Pipeline script from SCM** -> Git ->
   your repo URL -> branch `*/main` -> Script Path `Jenkinsfile` -> Save.
4. Click **Build now**. The first run asks for parameters after it has been loaded once; run it a
   second time with **Build with Parameters**.

### What the pipeline does

| # | Stage | What happens |
|---|---|---|
| 1 | Prepare | tag = short Git commit; decides if this is the main branch |
| 2 | Validate (parallel) | compose files valid for all 4 environments; shell scripts have no syntax errors |
| 3 | Unit tests | Docker `test` stage |
| 4 | Build images | api and web built **once**, tagged with the commit |
| 5 | Vulnerability scan | Trivy on both images (report only, or fail with `SCAN_STRICT`) |
| 6 | Push | only if you give a REGISTRY (needs Jenkins credential `registry-creds`) |
| 7-8 | Deploy DEV + integration tests | creates a product, orders it, checks stock, checks refusals |
| 9-10 | Deploy TEST + integration tests | main branch only |
| 11 | Deploy STAGING | main branch only |
| 12 | Approval | a person clicks **Deploy** (stands in for the change ticket) |
| 13 | Deploy PROD | smoke test; **automatic rollback** if it fails |

The same image tag moves through every environment. Only the env file differs.

### Things to try (this is where you learn)

- **Rollback demo.** Let a build reach prod. Then break the API on purpose (for example make
  `/api/ready` always return 503 in `app/__init__.py`), commit, run the pipeline, approve prod.
  The new version fails its smoke test, and `deploy.sh` redeploys the previous tag by itself.
  Check with `bash scripts/status.sh` (run it inside the Jenkins container or Git Bash).
- **Manual rollback:** `bash scripts/rollback.sh prod`.
- **Fail the scan:** run with `SCAN_STRICT` ticked and read `reports/trivy.txt`.
- **Failing test:** edit a test so it fails and watch the pipeline stop at stage 3.

## Step 4: Kubernetes (optional, with Docker Desktop Kubernetes, kind or minikube)

```powershell
.\run.ps1 up                                   # builds shop/shop-api:local and shop/shop-web:local
# kind only:  kind load docker-image shop/shop-api:local shop/shop-web:local
# minikube:   minikube image load shop/shop-api:local ; minikube image load shop/shop-web:local

kubectl create namespace shop
kubectl -n shop create secret generic shop-db --from-literal=DB_PASSWORD="choose-a-password"
cd k8s
kustomize edit set image shop/shop-api=shop/shop-api:local shop/shop-web=shop/shop-web:local
kubectl apply -k .
kubectl -n shop get pods -w
kubectl -n shop port-forward svc/web 8085:80        # then open http://localhost:8085
```

Try: `kubectl -n shop scale deploy/api --replicas=3`, delete a pod and watch it come back, change
the image tag and watch the rolling update (`kubectl -n shop rollout status deploy/api`,
`kubectl -n shop rollout undo deploy/api`).

## Step 5: Ansible (optional, needs a Linux VM or WSL Ubuntu)

```bash
cd ansible
# edit inventory.ini with your VM, then:
ansible-playbook deploy.yml -e shop_env=dev -e shop_tag=<tag> -e shop_registry=<registry>
```
Run it twice: the second run reports `changed=0` (idempotent).

## Environments

| Env | URL | Compose project | Database volume |
|---|---|---|---|
| dev | http://localhost:8090 | shop-dev | shop-dev_dbdata |
| test | http://localhost:8091 | shop-test | shop-test_dbdata |
| staging | http://localhost:8092 | shop-staging | shop-staging_dbdata |
| prod | http://localhost:8093 | shop-prod | shop-prod_dbdata |

## Troubleshooting

| Problem | Fix |
|---|---|
| `docker compose` not found | Update Docker Desktop (Compose v2 is built in) |
| Port already in use | Change `WEB_PORT` in `env/<env>.env` |
| `password authentication failed` | Postgres keeps the password from the first start. `.\run.ps1 reset` deletes the volume (data lost) |
| api unhealthy at start | `docker compose -p shop-dev logs api` (migrations print `[migrate] ...`) |
| `exec ./entrypoint.sh: no such file` / `^M` | Windows changed line endings. `.gitattributes` prevents it; run `git add --renormalize .` |
| Jenkins: `docker: command not found` | You are using an old Jenkins container. Rebuild from `jenkins/` |
| Jenkins: smoke tests cannot connect | `SMOKE_HOST` must be `host.docker.internal` (set in the Jenkinsfile; the jenkins compose file adds the mapping) |
| Trivy fails on download | First scan downloads a vulnerability database; check internet, retry |
| Everything stuck | `docker compose -p shop-dev down -v` and start again |

## What is simplified compared with a real company

- Passwords live in env files. Real setups inject them from Vault or a cloud key vault.
- Jenkins uses the host Docker socket. Real setups use isolated build agents and rootless builders.
- The database is a container. Real setups usually use a managed or DB-team-run database.
- The approval step is a button. Real setups check an approved change ticket in ServiceNow.
- No TLS, no ingress, no autoscaling, no log shipping.
- Everything runs on one PC, so "environments" are separate Compose projects.

## Talking points for interviews

- Built a multi-stage Docker build with a test stage that fails the image build, and a non-root runtime image.
- Built one image per commit and promoted the same image through dev, test, staging and prod.
- Smoke and integration tests after each deploy; automatic rollback to the previous tag.
- Health vs readiness endpoints, Prometheus metrics, Kubernetes probes and rolling updates.
- Database migrations tracked in a table, safe when several instances start at once.
- Be honest about the level: this is a lab you built and understand, not production experience.
