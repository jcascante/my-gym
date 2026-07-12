variable "project_name" { type = string }
variable "environment"  { type = string }

variable "vpc_id"            { type = string }
variable "public_subnet_ids" { type = list(string) }

variable "ecr_repository_url" { type = string }

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "cpu" {
  type    = number
  default = 512
}

variable "memory" {
  type    = number
  default = 1024
}

variable "min_tasks" {
  type    = number
  default = 1
}

variable "max_tasks" {
  type    = number
  default = 4
}

variable "desired_tasks" {
  type    = number
  default = 1
}

variable "task_execution_role_arn" { type = string }
variable "task_role_arn"           { type = string }

variable "container_port" {
  type    = number
  default = 80
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "health_check_path" {
  type    = string
  default = "/health"
}

variable "acm_certificate_arn" {
  type = string
}

variable "additional_certificate_arns" {
  type    = list(string)
  default = []
}
