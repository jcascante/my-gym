# Terraform Infrastructure

This directory contains Terraform configurations for deploying MyGym to AWS using ECS Fargate, Application Load Balancer, and RDS PostgreSQL.

## Architecture Overview

The deployment architecture consists of:
- **Frontend**: Existing S3 + CloudFront (reused, not managed here)
- **Backend API**: ECS Fargate tasks behind an Application Load Balancer
- **Database**: RDS PostgreSQL (encrypted, backed up, non-publicly accessible)
- **CI/CD**: GitHub Actions with OIDC role assumption (no static credentials)
- **DNS**: Route53 alias records pointing to ALB and existing CloudFront

## Directory Structure

```
terraform/
├── bootstrap/                      # One-time account setup
│   ├── modules/
│   │   ├── ecr/                   # ECR repositories for container images
│   │   └── iam/                   # GitHub Actions OIDC role + permissions
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── README.md
├── modules/
│   ├── backend_ecs/               # ECS Fargate service + ALB
│   ├── iam/                       # ECS task execution/role IAM policies
│   └── rds/                       # RDS PostgreSQL database
├── main.tf                        # Root: VPC data, security groups, module composition
├── variables.tf                   # Root variables (DB, ECS sizing, secrets)
├── outputs.tf                     # Root outputs (ALB DNS, ECS details, frontend URLs)
├── terraform.tfvars              # Configuration (sensitive - do NOT commit)
├── terraform.tfvars.example       # Example template (safe to commit)
└── README.md
```

## Prerequisites

1. **AWS Account**: AWS credentials configured for account `691650344087`
2. **AWS CLI**: `aws configure` with appropriate IAM permissions
3. **Terraform**: >= 1.0 installed
4. **Docker**: For building and pushing backend images to ECR
5. **Node.js**: For building frontend (managed by CI/CD, or locally for testing)
6. **Bootstrap already applied**: `terraform/bootstrap/` must have been run once to create ECR repos and OIDC role

## Deployment Steps

### Step 1: Bootstrap Infrastructure (One-Time Setup)

Run this **once** per AWS account. Creates ECR repositories and GitHub Actions OIDC role.

```bash
cd terraform/bootstrap

# Initialize Terraform (uses S3 remote state backend, commented out first time)
terraform init

# Review the plan
terraform plan

# Apply the configuration
terraform apply

# Note the output: github_actions_role_arn
terraform output github_actions_role_arn
```

**Important for GitHub Actions**: Copy the `github_actions_role_arn` output and add it as the `AWS_DEPLOY_ROLE_ARN` secret in your GitHub repository. See `../GITHUB_ACTIONS_SECRETS.md` for complete setup.

### Step 2: Prepare Configuration

Copy the example variables and customize with your secrets:

```bash
cd terraform

# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your actual values:
# - db_username, db_password (strong passwords)
# - secret_key (JWT signing key)
# - backend_cors_origins (your frontend URL)
# - acm_certificate_arn (your TLS certificate)

vim terraform.tfvars
```

**CRITICAL**: The `terraform.tfvars` file contains secrets. Never commit it to version control. Add it to `.gitignore` (already done).

To generate a secure `secret_key`:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 3: Deploy Application Infrastructure

```bash
cd terraform

# Initialize Terraform (first time, or after adding new modules)
terraform init

# Review changes before applying (ALWAYS do this for production)
terraform plan -out=tfplan

# Review tfplan output carefully, especially:
# - Database will be created (RDS is persistent, so this only happens once)
# - ALB and ECS service will be created
# - Security groups will be created

# Apply the configuration (no new infrastructure after first apply)
terraform apply tfplan

# Verify deployment
terraform output backend_alb_dns
terraform output backend_ecs_cluster
```

Your backend API should now be accessible via the ALB DNS name. Route53 records point `api.costabirra.com` to this ALB.

### Step 4: GitHub Actions Setup

Once bootstrap and application infrastructure are deployed:

1. Get the OIDC role ARN from bootstrap:
   ```bash
   cd terraform/bootstrap
   terraform output github_actions_role_arn
   ```

2. Get the other variables:
   ```bash
   cd terraform
   terraform output backend_ecs_cluster
   terraform output backend_ecs_service
   terraform output frontend_bucket
   terraform output frontend_cloudfront_id
   ```

3. Add to GitHub repository secrets and variables:
   - **Secrets** → `AWS_DEPLOY_ROLE_ARN` (the role ARN from step 1)
   - **Variables** → `ECS_CLUSTER_NAME`, `ECS_SERVICE_NAME`, `FRONTEND_BUCKET`, `CLOUDFRONT_DISTRIBUTION_ID`

4. Push to `main` branch to trigger the first deployment via `.github/workflows/deploy.yml`

## Configuration

### Required Variables (in `terraform.tfvars`)

- `db_username`: PostgreSQL master username (e.g., `gymadmin`)
- `db_password`: PostgreSQL master password (strong, random)
- `secret_key`: JWT signing secret (use `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`)
- `backend_cors_origins`: JSON string of allowed CORS origins (e.g., `"[\"https://app.costabirra.com\"]"`)

### Optional Variables (defaults provided)

- `aws_region`: Default `us-east-1`
- `project_name`: Default `gym-app`
- `environment`: Default `production`
- `image_tag`: Docker image tag to deploy (default `latest`)
- `db_name`: PostgreSQL database name (default `mygym`)
- `backend_cpu`: ECS task CPU units (default `256`, options: 256, 512, 1024, 2048, 4096)
- `backend_memory`: ECS task memory in MB (default `512`)
- `backend_min_tasks`: Minimum number of running tasks (default `1`)
- `backend_max_tasks`: Maximum number for auto-scaling (default `4`)
- `algorithm`: JWT algorithm (default `HS256`)
- `access_token_expire_minutes`: JWT expiration (default `60` minutes)
- `cookie_secure`: HTTPS-only cookies (default `true`)

### ECS Task Sizing

Valid CPU/memory combinations for ECS Fargate:

| CPU (units) | Memory Options (MB) |
|-------------|---------------------|
| 256         | 512, 1024, 2048     |
| 512         | 1024-4096 (1024 increments) |
| 1024        | 2048-8192 (1024 increments) |
| 2048        | 4096-16384 (1024 increments) |
| 4096        | 8192-30720 (1024 increments) |

Default: 256 CPU + 512 MB memory (suitable for development/low traffic)

### Auto Scaling

ECS automatically scales tasks between `backend_min_tasks` and `backend_max_tasks` based on CPU/memory utilization.

## Managing Deployments

### Deploy New Backend Image

Deployments are automated via GitHub Actions (`.github/workflows/deploy.yml`):

1. **Push to main branch** automatically builds, pushes, and deploys new backend image
2. **Rollback**: Push a previous image tag or commit
3. **Manual deployment**: Use `workflow_dispatch` in GitHub Actions UI

Alternatively, manually update via ECS:

```bash
# After pushing a new image to ECR with tag v1.0.0:
CLUSTER=$(cd terraform && terraform output -raw backend_ecs_cluster)
SERVICE=$(cd terraform && terraform output -raw backend_ecs_service)

aws ecs update-service \
  --cluster $CLUSTER \
  --service $SERVICE \
  --force-new-deployment \
  --region us-east-1
```

### Update Infrastructure

To change ECS sizing, database configuration, or environment variables:

```bash
cd terraform

# Edit terraform.tfvars with your changes
vim terraform.tfvars

# Review what will change
terraform plan

# Apply after reviewing (be careful with database changes)
terraform apply
```

**Caution**: Changing RDS configuration (CPU, storage, etc.) may cause downtime.

### Scale Tasks Up/Down

Adjust `backend_min_tasks` and `backend_max_tasks` in `terraform.tfvars`:

```hcl
backend_min_tasks = 2  # At least 2 running tasks for HA
backend_max_tasks = 8  # Scale up to 8 under load
```

Then apply:
```bash
terraform plan
terraform apply
```

## Monitoring and Logs

### Backend Application Logs

ECS Fargate logs go to CloudWatch Logs:

```bash
CLUSTER=$(cd terraform && terraform output -raw backend_ecs_cluster)
SERVICE=$(cd terraform && terraform output -raw backend_ecs_service)

# View live logs
aws logs tail /ecs/${CLUSTER}-${SERVICE} --follow

# View logs for a specific date
aws logs filter-log-events \
  --log-group-name /ecs/${CLUSTER}-${SERVICE} \
  --start-time $(date -d '1 hour ago' +%s)000
```

Or view in AWS Console: CloudWatch → Log Groups → `/ecs/gym-app-production-*`

### Database Logs

RDS PostgreSQL logs are also in CloudWatch Logs:

```bash
aws logs tail /aws/rds/instance/gym-app-production-postgres --follow
```

### Health Checks

ECS performs health checks on the `/health` endpoint (no database ping, so transient issues don't cause task kills).

## Cost Optimization

ECS Fargate pricing:
1. **Compute**: Charged per vCPU-hour (0.25 vCPU minimum)
2. **Memory**: Charged per GB-hour (0.5 GB minimum)
3. **Data transfer**: Outbound data charges apply

Tips:
- Start with `backend_cpu = 256` and `backend_memory = 512` for low traffic
- Set `backend_min_tasks = 1` for dev, scale up in production
- Use auto-scaling to right-size for actual traffic
- RDS `t4g.micro` is cost-effective for moderate databases (covered under free tier if within limits)

## Production Considerations

### Database

RDS PostgreSQL is fully managed and encrypted:

- **Encryption**: Storage is encrypted by default (AWS KMS)
- **Backups**: Automatic backups with 7-day retention (configurable in `terraform/modules/rds/`)
- **Snapshots**: Final snapshot on destruction preserves data for recovery
- **Access**: Database is not publicly accessible (only ECS tasks can connect via security group)
- **Credentials**: Never stored in version control, passed via ECS task environment

Monitor database:
```bash
aws rds describe-db-instances \
  --db-instance-identifier gym-app-production-postgres \
  --query 'DBInstances[0].[DBInstanceStatus,AvailabilityZone,AllocatedStorage]'
```

### Secrets Management

Sensitive values in `terraform.tfvars`:
- `db_password`: Never commit, generate strong random passwords
- `secret_key`: Generate fresh key for production: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

**Best practice**: Consider rotating `secret_key` and `db_password` regularly:
1. Generate new values locally
2. Update `terraform.tfvars`
3. Run `terraform apply` (triggers task restart)
4. Old JWT tokens become invalid after restart

### Custom Domain & TLS

Domain `api.costabirra.com` is already configured with Route53 alias pointing to ALB.

For TLS (HTTPS):
1. ACM certificate ARN is in `terraform/main.tf` (set in `backend_ecs` module)
2. ALB listens on 443 (HTTPS) and redirects 80 (HTTP) to 443
3. Update `acm_certificate_arn` in `terraform/main.tf` if using a different certificate

### Security

- ✅ `terraform.tfvars` is in `.gitignore` (not committed)
- ✅ ECS tasks run with minimal IAM permissions (least privilege)
- ✅ Database is not publicly accessible (security group restricted to ECS)
- ✅ JWT tokens use strong `SECRET_KEY` (configure in `terraform.tfvars`)
- ✅ All traffic is HTTPS (ALB enforces TLS)
- ✅ Environment variables include `COOKIE_SECURE=true` (HTTP-only cookies with Secure flag)
- ✅ GitHub Actions uses OIDC (no static credentials stored)

### High Availability

For production deployments:
1. Set `backend_min_tasks = 2` or higher (multiple tasks spread across AZs)
2. ECS automatically distributes tasks across availability zones
3. ALB health checks detect and replace failed tasks
4. RDS Multi-AZ (not enabled by default; can be added to `terraform/modules/rds/main.tf` if needed)

### Monitoring

- **CloudWatch Logs**: `/ecs/gym-app-production-*` for application logs
- **CloudWatch Metrics**: CPU, memory, network utilization (auto-enabled for ECS)
- **CloudWatch Alarms**: Can be added to alert on high error rates or resource exhaustion
- **ALB Metrics**: Response times, request count, target health

## Troubleshooting

### ECS Tasks Failing to Start

**Symptoms**: Task spins up, then stops immediately

1. **Check ECS task logs**:
   ```bash
   aws ecs describe-tasks \
     --cluster $(cd terraform && terraform output -raw backend_ecs_cluster) \
     --tasks $(aws ecs list-tasks --cluster ... --query 'taskArns[0]' --output text) \
     --query 'tasks[0].stoppedReason'
   ```

2. **Check CloudWatch Logs**:
   ```bash
   aws logs tail /ecs/gym-app-production-backend --follow
   ```

3. **Common issues**:
   - Image doesn't exist in ECR: Check `image_tag` in `terraform.tfvars`
   - Task definition doesn't exist: Run `terraform apply` to update
   - Environment variables missing: Verify all vars in `terraform.tfvars` are set
   - Database unreachable: Check security group allows 5432 from ECS tasks

### Health Check Failures

**Symptoms**: ALB marks tasks as unhealthy, keeps restarting them

1. **Verify `/health` endpoint exists**:
   ```bash
   curl https://api.costabirra.com/health
   # Should return: {"status":"ok"}
   ```

2. **Check health check configuration** in `terraform/modules/backend_ecs/main.tf`:
   - Path: `/health` (no database ping, so transient DB issues don't cause cascading failures)
   - Port: 8000
   - Timeout: 5 seconds (increase if startup is slow)

3. **View ALB target health**:
   ```bash
   aws elbv2 describe-target-health \
     --target-group-arn $(aws elbv2 describe-target-groups \
       --query "TargetGroups[?contains(TargetGroupName, 'backend')].TargetGroupArn" \
       --output text)
   ```

### Database Connection Issues

**Symptoms**: Backend logs show "connection refused" or "timeout"

1. **Verify database is running**:
   ```bash
   aws rds describe-db-instances \
     --db-instance-identifier gym-app-production-postgres \
     --query 'DBInstances[0].DBInstanceStatus'
   ```

2. **Check security group allows ECS**: In `terraform/main.tf`, verify:
   ```hcl
   # aws_security_group.rds ingress allows 5432 from aws_security_group.ecs_tasks
   ```

3. **Test connectivity from ECS task** (SSH into task and run):
   ```bash
   # Inside ECS task:
   psql -h <RDS_ENDPOINT> -U gymadmin -d mygym -c "SELECT 1;"
   ```

4. **Check DATABASE_URL** is correct in ECS task definition (should be set from `terraform/main.tf`)

## Cleanup

To destroy resources:

```bash
# Destroy application infrastructure (RDS, ECS, ALB, etc.)
cd terraform
terraform destroy

# Destroy bootstrap infrastructure (ECR repositories and images)
# WARNING: This is destructive and irreversible
cd terraform/bootstrap
terraform destroy
```

**Warnings**:
- RDS will create a final snapshot before deletion (preserves data for recovery)
- ECR repositories and all Docker images will be deleted
- ALB and ECS tasks will be terminated
- Security groups will be removed

## Additional Resources

- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS RDS PostgreSQL](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html)
- [AWS Application Load Balancer](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [GitHub Actions OIDC with AWS](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
