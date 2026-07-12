terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Note: For the initial bootstrap run, this backend configuration should be commented out
  # After the state-backend module creates the S3 bucket and DynamoDB table,
  # uncomment this and run `terraform init -migrate-state`
  backend "s3" {
    bucket         = "691650344087-terraform-state"
    key            = "gym-app/bootstrap/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "691650344087-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "bootstrap"
      ManagedBy   = "Terraform"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# Module: ECR Repositories
module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  repositories = var.ecr_repositories
}

# Module: IAM user for GitHub Actions CI/CD
module "iam" {
  source = "./modules/iam"
}
