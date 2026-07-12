variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "ecs_security_group_id" {
  type        = string
  description = "Security group ID of ECS tasks for database access"
}

variable "db_name" {
  type    = string
  default = "mygym"
}

variable "db_username" {
  type        = string
  sensitive   = true
  description = "Database master username"
}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "Database master password"
}

variable "allocated_storage" {
  type    = number
  default = 20
}

variable "storage_type" {
  type    = string
  default = "gp3"
}

variable "backup_retention_period" {
  type    = number
  default = 7
}
