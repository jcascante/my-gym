output "github_actions_role_arn" {
  description = "ARN of the GitHub Actions deployment role (for AWS_DEPLOY_ROLE_ARN secret)"
  value       = aws_iam_role.github_actions_deploy.arn
}
