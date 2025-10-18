# Backend Deployment Plan (FastAPI Service)

## Target Platform
- **Primary**: AWS Fargate (ECS) behind an Application Load Balancer.
- **Rationale**: Managed container orchestration, automatic scaling, VPC integration for future data sources, and straightforward CI/CD with GitHub Actions + AWS CodeDeploy.
- **Fallback**: Azure App Service container deployment if AWS tenancy is unavailable.

## Container Image
- **Dockerfile**: `FlowchartStocks/stock-evaluator/Dockerfile`
- **Port**: 8000 (FastAPI via Uvicorn)
- **Runtime Env Vars**:
  - `GROQ_API_KEY`, `GEMINI_API_KEY` – managed via AWS Secrets Manager.
  - `SECRET_KEY` – for Flask legacy UI compatibility.
  - `LOG_LEVEL`, `CACHE_TTL` (optional tuning knobs added later).

## Infrastructure Components
1. **ECR Repository** – stores versioned images (`stock-evaluator-api`).
2. **ECS Cluster (Fargate)** – serverless containers, no host management.
3. **Application Load Balancer** – HTTPS termination, path routing, health checks hitting `/health`.
4. **CloudWatch Logs & Metrics** – centralised logging, alerting on 5xx spikes and latency.
5. **AWS WAF (Phase 2)** – optional for rate limiting and IP allow-listing.

## Deployment Workflow
1. GitHub Actions build job:
   - Run `pytest`, lint checks.
   - `docker build -t stock-evaluator-api`.
   - Push to ECR with commit SHA tag.
2. Deploy step:
   - Update ECS service with new task definition referencing image SHA.
   - Blue/Green deployment (CodeDeploy) with automatic rollback on failed health checks.
3. Post-deploy verification:
   - Hit `/health` and `/evaluate` smoke test via GitHub Actions.
   - Observe CloudWatch dashboards for 15 minutes.

## Networking & Security
- Fargate tasks in private subnets, NAT Gateway for outbound API calls.
- ALB in public subnets, HTTPS enforced via ACM certificate.
- Security groups:
  - ALB: inbound 443 from internet, outbound to Fargate.
  - Fargate: inbound 8000 from ALB SG, outbound 443 for yfinance/AI providers.
- IAM roles:
  - Task role grants Secrets Manager access for API keys.
  - Execution role for pulling images from ECR and CloudWatch logging.

## Observability
- Structured JSON logs from FastAPI (enable with `uvicorn --log-config` later).
- CloudWatch alarms:
  - `5XXErrorRate > 5%` over 5 minutes.
  - `TargetResponseTime > 4s` P95.
  - Container CPU/Mem > 70% sustained.
- Future enhancement: integrate AWS X-Ray for tracing.

## Local Parity
- Use `docker-compose up --build` to run the API locally (`docker-compose.yml`).
- `.env` file (gitignored) to supply local secrets.
- Tests executed in CI before builds to keep parity.

## Next Steps
1. Provision AWS resources via Terraform (todo).
2. Add CI workflow file referencing Dockerfile and ECR (todo).
3. Implement structured logging and health check metrics.
