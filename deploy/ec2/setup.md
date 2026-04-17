# AWS deployment setup

This repository deploys:

- `frontend/` to S3 and serves it through CloudFront
- `server/` as a Docker image in ECR, pulled by an EC2 host running Docker Compose

## 1. AWS resources

Create these resources in `us-east-1`:

1. An S3 bucket for the frontend static files.
2. A CloudFront distribution with the S3 bucket as origin.
3. An ECR repository for the backend image.
4. One EC2 instance for the FastAPI container.

## 2. GitHub configuration

Create these GitHub **Variables**:

- `AWS_DEPLOY_ROLE_ARN`: IAM role assumed by GitHub Actions through OIDC.
- `S3_BUCKET_NAME`: frontend bucket name.
- `CLOUDFRONT_DISTRIBUTION_ID`: CloudFront distribution ID.
- `FRONTEND_API_BASE_URL`: optional public API base URL. Leave it empty if CloudFront routes `/api/*` and `/health` to the EC2 origin on the same distribution.
- `ECR_REPOSITORY`: ECR repository name.
- `EC2_SSH_HOST`: public DNS or IP of the EC2 instance.
- `EC2_SSH_USER`: SSH username used by the EC2 instance, for example `ec2-user` or `ubuntu`.
- `SERVER_PORT`: optional host port for the backend container, usually `8000`.

Create this GitHub **Secret**:

- `EC2_SSH_PRIVATE_KEY`: private key used by the workflow to connect to EC2.

## 3. OIDC IAM role for GitHub Actions

The role referenced by `AWS_DEPLOY_ROLE_ARN` should trust GitHub's OIDC provider and allow:

- `s3:ListBucket`, `s3:PutObject`, `s3:DeleteObject`
- `cloudfront:CreateInvalidation`
- `ecr:GetAuthorizationToken`
- `ecr:BatchCheckLayerAvailability`
- `ecr:CompleteLayerUpload`
- `ecr:InitiateLayerUpload`
- `ecr:PutImage`
- `ecr:UploadLayerPart`

You can scope the permissions to the specific bucket, distribution, and ECR repository.

## 4. EC2 bootstrap

Use an x86_64 EC2 instance if you keep the current image build defaults.

Install Docker, Docker Compose, and AWS CLI on the EC2 host. Example for Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl unzip awscli
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
mkdir -p ~/medical-redaction
```

Attach an IAM role to the EC2 instance with permission to pull from ECR:

- `ecr:GetAuthorizationToken`
- `ecr:BatchGetImage`
- `ecr:GetDownloadUrlForLayer`
- `ecr:BatchCheckLayerAvailability`

## 5. Backend runtime configuration on EC2

Create `~/medical-redaction/backend.env` on the EC2 host based on `deploy/backend.env.example`.

Example:

```bash
cat > ~/medical-redaction/backend.env <<'EOF'
APP_NAME=Medical Records Redaction API
DEBUG=false
AWS_REGION=us-east-1
SYNC_MAX_BYTES=512000
SYNC_MAX_SECONDS=60
REDACTION_TOKEN=[REDACTED]
CONFIDENCE_REVIEW_THRESHOLD=0.75
USE_AWS_COMPREHEND=false
CORS_ORIGINS=https://your-distribution-id.cloudfront.net,http://127.0.0.1:5500,http://localhost:5500
EOF
```

The backend workflow copies `deploy/docker-compose.yml` into `~/medical-redaction/docker-compose.yml` and then runs:

```bash
docker compose pull
docker compose up -d
```

## 6. Frontend hosting notes

- Point the CloudFront default root object to `index.html`.
- If the bucket is private, use CloudFront Origin Access Control.
- Preferred no-domain setup: use the same CloudFront distribution with S3 as the default origin and an EC2 origin for `/api/*` and `/health`. In that case, keep `FRONTEND_API_BASE_URL` empty so the browser uses the same origin.
- Alternative setup: publish the API behind a second HTTPS endpoint, such as another CloudFront distribution in front of the EC2 origin, and set `FRONTEND_API_BASE_URL` to that HTTPS URL.
- Avoid pointing the frontend to plain `http://<ec2-ip>:8000` when the frontend is loaded over HTTPS, or the browser will block the requests as mixed content.
- The frontend workflow rewrites `config.js` at deploy time so the browser calls `FRONTEND_API_BASE_URL` when it is provided.

## 7. First deployment checklist

1. Confirm the EC2 security group allows inbound traffic on `8000` from the internet or from a reverse proxy.
2. Confirm the S3 bucket and CloudFront distribution are created.
3. Confirm the ECR repository exists.
4. Confirm GitHub variables and secret are set.
5. Push a change to `main` or `feature-ui`, or trigger the workflows manually.
