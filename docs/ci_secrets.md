# GitHub Actions Secret Configuration

Add the following repository secrets so the `backend-ci` workflow can run end-to-end.

| Secret Name           | Value / Source |
|-----------------------|----------------|
| `AWS_REGION`          | Your AWS region (e.g. `us-east-1`). |
| `AWS_ROLE_TO_ASSUME`  | IAM Role ARN with permissions to push to ECR. |
| `ECR_REPOSITORY`      | ECR repository name (e.g. `stock-evaluator-api`). |
| `GROQ_API_KEY`        | Copy from `config/api_keys.txt` (`api_key_groq`). |
| `GEMINI_API_KEY`      | Copy from `config/api_keys.txt` (`api_key_aistudio_google`). |

Optional extras:
| Secret | Description |
|--------|-------------|
| `SECRET_KEY` | Flask session key if you plan to run the legacy web UI in CI. |

## How to add secrets
1. In GitHub, open **Settings → Secrets and variables → Actions**.
2. Click **New repository secret** for each key above.
3. Paste the corresponding value (or ARN) and save.

For local runs, copy `.env` into the same directory and run:
```bash
cd FlowchartStocks/stock-evaluator
source .env  # or `set -a; source .env; set +a` on bash
```
