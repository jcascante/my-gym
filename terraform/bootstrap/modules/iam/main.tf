# Get current AWS account ID for OIDC provider ARN
data "aws_caller_identity" "current" {}

# GitHub OIDC Provider
# NOTE: a `data` lookup can't be used to conditionally skip creation here —
# aws_iam_openid_connect_provider hard-errors the whole plan on a 404 (NoSuchEntity)
# instead of returning null, so try() can't catch it. If the account already has
# a GitHub OIDC provider (e.g. from another Terraform config), `terraform import`
# it into this resource address instead of re-adding detection logic.
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1", "1b511abead59c6ce207077c0ef0285192718a2da"]

  tags = {
    Name = "github-oidc-provider"
  }
}

locals {
  github_oidc_provider_arn = aws_iam_openid_connect_provider.github.arn
}

# IAM Role for GitHub Actions with OIDC trust
resource "aws_iam_role" "github_actions_deploy" {
  name = "github-actions-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.github_oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:jcascante/my-gym:ref:refs/heads/main"
          }
        }
      }
    ]
  })

  tags = {
    Name    = "github-actions-deploy"
    Purpose = "GitHub Actions CI/CD with OIDC"
  }
}

# ECR policy for backend image push
resource "aws_iam_role_policy" "github_actions_ecr" {
  name = "github-actions-ecr"
  role = aws_iam_role.github_actions_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:DescribeImages",
          "ecr:DescribeRepositories",
          "ecr:ListImages",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "arn:aws:ecr:*:*:repository/gym-app-*"
      }
    ]
  })
}

# ECS deployment policy for backend service updates
resource "aws_iam_role_policy" "github_actions_ecs" {
  name = "github-actions-ecs"
  role = aws_iam_role.github_actions_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices"
        ]
        Resource = [
          "arn:aws:ecs:*:${data.aws_caller_identity.current.account_id}:service/gym-app-production-cluster/gym-app-production-backend",
          "arn:aws:ecs:*:${data.aws_caller_identity.current.account_id}:cluster/gym-app-production-cluster"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeTaskDefinition"
        ]
        Resource = "arn:aws:ecs:*:${data.aws_caller_identity.current.account_id}:task-definition/gym-app-production-backend:*"
      }
    ]
  })
}

# Frontend S3 and CloudFront policy for frontend deployment
resource "aws_iam_role_policy" "github_actions_frontend" {
  name = "github-actions-frontend"
  role = aws_iam_role.github_actions_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetObject"
        ]
        Resource = [
          "arn:aws:s3:::app.costabirra.com",
          "arn:aws:s3:::app.costabirra.com/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "cloudfront:CreateInvalidation",
          "cloudfront:GetInvalidation",
          "cloudfront:ListInvalidations"
        ]
        Resource = "arn:aws:cloudfront::*:distribution/E15DPRRJ6MVP5X"
      }
    ]
  })
}
