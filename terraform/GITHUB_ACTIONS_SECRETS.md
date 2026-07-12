# GitHub Actions deployment variables and secrets for Gym App

Set these in your GitHub repository settings:

## Secrets
`AWS_DEPLOY_ROLE_ARN` = ARN of the GitHub Actions deployment role with OIDC trust

## Repository Variables
`ECS_CLUSTER_NAME` = gym-app-production-cluster
`ECS_SERVICE_NAME` = gym-app-production-backend
`FRONTEND_BUCKET` = app.costabirra.com
`CLOUDFRONT_DISTRIBUTION_ID` = E15DPRRJ6MVP5X

## To populate secrets and variables, run:

```bash
# From the bootstrap directory, get the OIDC role ARN
cd terraform/bootstrap
terraform output github_actions_role_arn
# Copy the ARN and set it as the AWS_DEPLOY_ROLE_ARN secret in GitHub

# From the application Terraform directory, get the frontend and ECS values
cd ../
terraform output frontend_bucket
terraform output frontend_cloudfront_id
terraform output backend_ecs_cluster
terraform output backend_ecs_service
```

Then set these values in GitHub repository settings:
- Settings → Secrets and variables → Actions → Secrets
- Settings → Secrets and variables → Actions → Variables
