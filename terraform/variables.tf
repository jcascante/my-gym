variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project_name" {
  type    = string
  default = "gym-app"
}

variable "environment" {
  type    = string
  default = "production"
}

variable "image_tag" {
  description = "Backend Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "backend_cpu" {
  type    = number
  default = 512
}

variable "backend_memory" {
  type    = number
  default = 1024
}

variable "backend_min_tasks" {
  type    = number
  default = 1
}

variable "backend_max_tasks" {
  type    = number
  default = 4
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "mygym"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "PostgreSQL master password"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "JWT signing secret"
  type        = string
  sensitive   = true
}

variable "backend_cors_origins" {
  description = "CORS origins allowed for the backend API"
  type        = string
  default     = "[\"https://app.costabirra.com\"]"
}

variable "algorithm" {
  description = "JWT signing algorithm"
  type        = string
  default     = "HS256"
}

variable "access_token_expire_minutes" {
  description = "JWT access token expiration in minutes"
  type        = number
  default     = 60
}

variable "cookie_secure" {
  description = "Set Secure flag on cookies (true for HTTPS/production)"
  type        = bool
  default     = true
}
