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

## 2. GitHub configuration (MVP with access keys)

The workflows authenticate to AWS using **long-lived IAM user access keys** stored as GitHub **Secrets** (no OIDC role).

### 2.1 GitHub Variables (repository or environment)

- `S3_BUCKET_NAME`: frontend bucket name.
- `CLOUDFRONT_DISTRIBUTION_ID`: CloudFront distribution ID.
- `FRONTEND_API_BASE_URL`: optional public API base URL. Leave it **empty** if CloudFront routes `/api/*` and `/health` to the EC2 origin on the same distribution (same-origin HTTPS).
- `ECR_REPOSITORY`: ECR repository name (only the repository name, not the full URI).
- `EC2_SSH_HOST`: public DNS or IP of the EC2 instance.
- `EC2_SSH_USER`: SSH username, for example `ec2-user` (Amazon Linux) or `ubuntu` (Ubuntu).
- `SERVER_PORT`: optional host port mapped on the EC2 host, usually `8000`.

You do **not** need `AWS_DEPLOY_ROLE_ARN` for this MVP.

### 2.2 GitHub Secrets

Create these in **Settings → Secrets and variables → Actions**:

| Secret | Purpose |
| --- | --- |
| `AWS_ACCESS_KEY_ID` | Access key ID of an IAM user used only for CI deploy. |
| `AWS_SECRET_ACCESS_KEY` | Secret access key for that user. |
| `EC2_SSH_PRIVATE_KEY` | Full PEM private key text used to SSH into the EC2 instance (the same material as your `.pem` file, including `BEGIN` / `END` lines). |

Treat these like passwords. Rotate the access keys if they leak.

## 3. IAM user for GitHub Actions (access keys)

1. In **IAM → Users → Create user**, create a user intended only for this pipeline (no console password required).
2. **Create access key** for the user (use case: “Application running outside AWS” or “CLI” depending on the console wording).
3. Attach an **inline policy** or a **customer managed policy** with the minimum actions the workflows need.

Required API actions (scope ARNs to your bucket, distribution, and ECR repository when possible):

- **S3 (frontend sync):** `s3:ListBucket`, `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject` on the frontend bucket and objects.
- **CloudFront:** `cloudfront:CreateInvalidation` on your distribution.
- **ECR (image push):** `ecr:GetAuthorizationToken` (resource `*` is normal for this API), plus `ecr:BatchCheckLayerAvailability`, `ecr:CompleteLayerUpload`, `ecr:InitiateLayerUpload`, `ecr:PutImage`, `ecr:UploadLayerPart`, and often `ecr:BatchGetImage` / `ecr:GetDownloadUrlForLayer` on your repository ARN.

**Security note:** access keys never expire by default. For class projects or MVPs this is acceptable if the user has **only** these permissions and you rotate keys after the course.

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
4. Confirm GitHub **Variables** and **Secrets** (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `EC2_SSH_PRIVATE_KEY`) are set.
5. Push a change to `main` or `feature-ui`, or trigger the workflows manually.
6. For the **deploy-to-ec2** job, the EC2 security group must allow **inbound TCP 22 (SSH)** from the internet (see section 8).

## 8. Troubleshooting: `dial tcp ...:22: i/o timeout` on deploy-to-ec2

GitHub Actions runs on **shared runners** with **changing public IPs**. The `appleboy/scp-action` step needs to open **SSH (port 22)** from the runner to your instance.

Checklist:

1. **Public IPv4**  
   In the EC2 console, confirm the instance has **Auto-assign public IP** enabled (or attach an **Elastic IP**). If the instance is **only** in a private subnet with no bastion, GitHub cannot SSH in.

2. **Security group inbound rules**  
   Add an inbound rule: **Type SSH**, **Port 22**, **Source**  
   - For a class / MVP: `0.0.0.0/0` (anywhere) is the simplest way to confirm it works; tighten later.  
   - Restricting to “My IP” **does not** include GitHub’s runners, so the workflow will time out.

3. **Network ACL**  
   If you use a custom NACL on the subnet, ensure it allows ephemeral return traffic and TCP 22 inbound.

4. **Host variable**  
   `EC2_SSH_HOST` should be the **public** DNS name (e.g. `ec2-...amazonaws.com`) or the **Elastic IP**, not the private IP unless you use a self-hosted runner inside the VPC.

After fixing the security group, **re-run** the failed workflow job (no code change required).

**More secure alternatives** (for later): self-hosted GitHub runner in the VPC, AWS SSM instead of SSH, or deploy only to ECR and pull on the instance via cron/SSM without opening SSH to the internet.
