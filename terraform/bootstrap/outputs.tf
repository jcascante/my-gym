# # VPC Outputs
# output "vpc_id" {
#   description = "ID of the VPC"
#   value       = module.vpc.vpc_id
# }

# output "private_subnet_ids" {
#   description = "IDs of private subnets"
#   value       = module.vpc.private_subnet_ids
# }

# output "vpc_endpoints_security_group_id" {
#   description = "ID of the security group for VPC endpoints"
#   value       = module.vpc.vpc_endpoints_security_group_id
# }

# ECR Outputs
output "ecr_repository_urls" {
  description = "URLs of the ECR repositories"
  value       = module.ecr.repository_urls
}

output "backend_ecr_url" {
  description = "ECR repository URL for backend"
  value       = module.ecr.repository_urls["backend"]
}

# General Info
output "account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "region" {
  description = "AWS Region"
  value       = data.aws_region.current.name
}

# IAM Outputs (GitHub Actions CI/CD with OIDC)
output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions deployment role (for AWS_DEPLOY_ROLE_ARN secret)"
  value       = module.iam.github_actions_role_arn
}
