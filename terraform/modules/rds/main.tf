locals {
  name = "${var.project_name}-${var.environment}"
}

resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-subnet-group"
  subnet_ids = var.subnet_ids

  tags = {
    Name = "${local.name}-subnet-group"
  }
}

resource "aws_security_group" "rds" {
  name   = "${local.name}-rds-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.ecs_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name}-rds-sg"
  }
}

resource "aws_db_instance" "main" {
  identifier     = "${local.name}-postgres"
  engine         = "postgres"
  engine_version = "17.10"

  instance_class = "db.t4g.micro"

  allocated_storage = var.allocated_storage
  storage_type      = var.storage_type
  storage_encrypted = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  publicly_accessible = false

  backup_retention_period = var.backup_retention_period
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  skip_final_snapshot       = false
  final_snapshot_identifier = "${local.name}-final-snapshot"

  enabled_cloudwatch_logs_exports = ["postgresql"]

  tags = {
    Name = "${local.name}-postgres"
  }

  depends_on = [aws_security_group.rds]
}
