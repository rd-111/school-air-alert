# Deployment checklist

Deployment has **not** been run or verified. Do not describe this project as
deployed until the health and forecast smoke checks succeed against the
deployed endpoints. The current environment has no AWS CLI or SAM CLI, so
these steps require a machine with AWS access.

## Before deploying

- Use Node.js 22.12+ and Python 3.12. Review `template.yaml`, `amplify.yml`, and
  the current AWS account/region and stack before creating resources.
- AWS CLI and SAM CLI must be installed and authenticated by the account owner.
  Verify identity locally with `aws sts get-caller-identity`; never paste
  credential output or files into the repository.
- The SAM template creates an API, Lambda functions, four on-demand DynamoDB
  tables, and two EventBridge schedules. API requests, Lambda execution,
  DynamoDB requests/storage, Scheduler, SNS, and optional Bedrock use may incur
  charges. Check current pricing and budgets before deployment.
- The template currently takes Telegram credentials as `NoEcho` parameters;
  it does not read them from Secrets Manager. Deploy without Telegram only if
  the template's required parameter handling is deliberately adapted and
  reviewed. Never put bot tokens in frontend variables, source files, command
  history, or Git.
- F19 and F20 are not implemented. F21 is implemented locally, but scheduled
  delivery is not verified in AWS.

## Backend (SAM)

From the repository root, validate and build before deploying:

```sh
sam validate --lint --template-file template.yaml
sam build --template-file template.yaml
```

Review the existing stack and resources in the AWS console before creating or
updating anything. If there is no existing stack and all costs/permissions are
approved, use `sam deploy --guided` and choose a reviewed stack name and
`ap-south-1` region. Set `FrontendAllowedOrigins` to the exact Amplify site
origin, with no path and no wildcard. Provide the required Telegram token and
webhook secret only through the reviewed secure deployment input flow. Do not
accept broad IAM changes or replace existing resources blindly.

After deployment, record the `ApiBaseUrl` output and verify both endpoints:

```sh
curl -i https://<api-id>.execute-api.ap-south-1.amazonaws.com/api/v1/health
curl -i 'https://<api-id>.execute-api.ap-south-1.amazonaws.com/api/v1/forecast?latitude=19.0760&longitude=72.8777'
```

Confirm the forecast identifies its source, retrieval time, and forecast data
type. A successful local test is not proof of deployed scheduled or
notification behavior.

## Frontend (Amplify Hosting)

Connect the existing GitHub repository and `main` branch in Amplify. The
existing `amplify.yml` uses `frontend/`, `npm ci`, `npm run build`, and `dist/`.
Set these **public build-time** variables in Amplify only after the backend is
reachable:

```text
VITE_DATA_MODE=live
VITE_API_URL=<verified-api-base-url>
VITE_TELEGRAM_BOT_USERNAME=schoolalert11_bot
```

Set API Gateway/SAM CORS to the exact Amplify origin, then rebuild. Do not put
Telegram bot tokens or any other secrets in `VITE_` variables. Confirm the
deployed site loads the live forecast and that report/poster routes work before
sharing its URL. No deployed frontend or backend URL is currently verified.
