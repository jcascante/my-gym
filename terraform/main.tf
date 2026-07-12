terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "691650344087-terraform-state"
    key            = "gym-app/application/terraform.tfstate"
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
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_ecr_repository" "backend" {
  name = "gym-app-backend"
}

# ── Networking — existing default VPC (reused, not managed here) ─────────────

data "aws_vpc" "main" {
  id = "vpc-0b7eec76"
}

data "aws_subnets" "public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.main.id]
  }
  filter {
    name   = "map-public-ip-on-launch"
    values = ["true"]
  }
}

# ── Security Groups ─────────────────────────────────────────────────────────
# Create security groups at root level to avoid circular dependency between backend_ecs and rds

resource "aws_security_group" "ecs_tasks" {
  name   = "${var.project_name}-${var.environment}-ecs-sg"
  vpc_id = data.aws_vpc.main.id

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "rds" {
  name   = "${var.project_name}-${var.environment}-rds-sg"
  vpc_id = data.aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ── IAM ─────────────────────────────────────────────────────────────────────

module "iam" {
  source = "./modules/iam"

  project_name = var.project_name
  environment  = var.environment
}

# ── Frontend — existing resources (reused, not managed here) ─────────────────

data "aws_s3_bucket" "frontend" {
  bucket = "app.costabirra.com"
}

# ACM cert already attached: arn:aws:acm:us-east-1:691650344087:certificate/9ba09513-c68c-40a7-af6f-68cc42f4d10c
data "aws_cloudfront_distribution" "frontend" {
  id = "E15DPRRJ6MVP5X"
}

data "aws_route53_zone" "frontend" {
  name = "costabirra.com"
}

# ── Route53: api.costabirra.com → backend ALB ─────────────
resource "aws_route53_record" "api" {
  zone_id = data.aws_route53_zone.frontend.zone_id
  name    = "api.costabirra.com"
  type    = "A"
  alias {
    name                   = module.backend_ecs.alb_dns_name
    zone_id                = module.backend_ecs.alb_zone_id
    evaluate_target_health = true
  }
}

# ── Backend API (ECS Fargate + ALB) ─────────────────────────────────────────

module "backend_ecs" {
  source = "./modules/backend_ecs"

  project_name      = var.project_name
  environment       = var.environment
  vpc_id            = data.aws_vpc.main.id
  public_subnet_ids = data.aws_subnets.public.ids

  ecr_repository_url = data.aws_ecr_repository.backend.repository_url
  image_tag          = var.image_tag

  cpu           = var.backend_cpu
  memory        = var.backend_memory
  min_tasks     = var.backend_min_tasks
  max_tasks     = var.backend_max_tasks
  desired_tasks = var.backend_min_tasks

  task_execution_role_arn = module.iam.ecs_execution_role_arn
  task_role_arn           = module.iam.ecs_task_role_arn

  acm_certificate_arn = "arn:aws:acm:us-east-1:691650344087:certificate/9eed0ca3-3d14-4892-915c-d757b3408b4e"
  container_port      = 8000

  environment_variables = {
    ENVIRONMENT                 = var.environment
    DATABASE_URL                = "postgresql+asyncpg://${var.db_username}:${var.db_password}@${module.rds.address}:5432/${var.db_name}"
    SECRET_KEY                  = var.secret_key
    BACKEND_CORS_ORIGINS        = var.backend_cors_origins
    ALGORITHM                   = var.algorithm
    ACCESS_TOKEN_EXPIRE_MINUTES = tostring(var.access_token_expire_minutes)
    COOKIE_SECURE               = tostring(var.cookie_secure)
  }

  depends_on = [module.rds]
}

# ── RDS PostgreSQL ──────────────────────────────────────────────────────────

module "rds" {
  source = "./modules/rds"

  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = data.aws_vpc.main.id
  subnet_ids            = data.aws_subnets.public.ids
  ecs_security_group_id = aws_security_group.ecs_tasks.id

  db_name     = var.db_name
  db_username = var.db_username
  db_password = var.db_password
}
