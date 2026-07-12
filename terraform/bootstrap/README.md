# Bootstrap - Account Setup

This directory contains Terraform configuration for one-time AWS account setup. Run this **once** per account before deploying the application.

## What Gets Created

1. **ECR Repositories**
   - Container registries for storing Docker images
   - Lifecycle policies for automatic image cleanup

2. **GitHub Actions OIDC Role**
   - IAM role with trust relationship for GitHub Actions
   - Scoped to `repo:jorgecascante/my-gym:*` (only this repository)
   - Permissions for:
     - ECR: push/pull images to `gym-app-*` repositories
     - ECS: update services and describe task definitions
     - S3: sync frontend build to `app.costabirra.com` bucket
     - CloudFront: invalidate cache for frontend distribution
   - No static credentials (uses short-lived OIDC tokens from GitHub)

## Prerequisites

- AWS CLI configured with credentials for account `691650344087`
- Terraform >= 1.0
- Permissions to create IAM roles and ECR repositories

## Initial Setup

### 1. Deploy Bootstrap Infrastructure

```bash
cd terraform/bootstrap

# Initialize Terraform
terraform init

# Review what will be created
terraform plan

# Create ECR repositories and OIDC role
terraform apply
```

### 2. Save Important Outputs

```bash
# Get the GitHub Actions OIDC role ARN (needed for GitHub setup)
terraform output github_actions_role_arn

# Get the ECR repository URL (needed for pushing images)
terraform output backend_ecr_url

# Get the account ID
terraform output account_id
```

### 3. Configure GitHub Repository

1. Copy the `github_actions_role_arn` from the terraform output above
2. In your GitHub repository settings:
   - **Secrets and variables** → **Actions** → **Secrets**
   - Create secret: `AWS_DEPLOY_ROLE_ARN` = (paste the role ARN from step 2)

3. After deploying the application infrastructure (in `../`), add these variables:
   - **Secrets and variables** → **Actions** → **Variables**
   - `ECS_CLUSTER_NAME` (from `terraform output backend_ecs_cluster`)
   - `ECS_SERVICE_NAME` (from `terraform output backend_ecs_service`)
   - `FRONTEND_BUCKET` (from `terraform output frontend_bucket`)
   - `CLOUDFRONT_DISTRIBUTION_ID` (from `terraform output frontend_cloudfront_id`)

See `../GITHUB_ACTIONS_SECRETS.md` for complete instructions.

## What's Next

After bootstrap is complete:
1. Proceed to `../` (application Terraform) to deploy backend API, database, and load balancer
2. Follow instructions in `../README.md`

## Outputs

The bootstrap deployment outputs:

```bash
# Get all outputs
terraform output

# Key outputs:
terraform output github_actions_role_arn      # Use for AWS_DEPLOY_ROLE_ARN GitHub secret
terraform output backend_ecr_url               # URL to push backend Docker images
terraform output ecr_repository_urls           # All ECR repositories
terraform output account_id                    # AWS account ID (for reference)
terraform output region                        # AWS region
```

## Updating Bootstrap

To add new ECR repositories or update GitHub Actions permissions:

```bash
# Edit terraform/modules/iam/main.tf to update policies
# Or edit terraform/modules/ecr/main.tf to add repositories

# Review changes
terraform plan

# Apply changes
terraform apply
```

## Troubleshooting

### OIDC Provider Already Exists

If the account already has a GitHub OIDC provider configured, Terraform will detect it and reuse it instead of creating a duplicate. This is the expected behavior.

### ECR Push Fails

1. Verify you have ECR permissions:
   ```bash
   aws ecr get-authorization-token --region us-east-1
   ```

2. Login to ECR:
   ```bash
   aws ecr get-login-password --region us-east-1 | \
     docker login --username AWS --password-stdin <ECR_REGISTRY>
   ```

3. Get the ECR registry URL:
   ```bash
   terraform output backend_ecr_url
   ```

## Destroying Bootstrap Resources

**⚠️ WARNING**: Only destroy when decommissioning the entire project.

```bash
# First, destroy application infrastructure in ../
cd ..
terraform destroy

# Then destroy bootstrap
cd bootstrap
terraform destroy
```

This will delete:
- All ECR repositories and Docker images
- GitHub Actions OIDC role
- Terraform state (keep backups!)

**Important**: Once deleted, you'll need to:
- Re-run bootstrap to recreate ECR and OIDC role
- Reconfigure GitHub Actions secrets/variables
- Rebuild and push Docker images to new ECR repositories
