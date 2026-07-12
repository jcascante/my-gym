output "account_id" {
  value = data.aws_caller_identity.current.account_id
}

output "region" {
  value = data.aws_region.current.name
}

output "frontend_bucket" {
  value = data.aws_s3_bucket.frontend.bucket
}

output "frontend_cloudfront_id" {
  value = data.aws_cloudfront_distribution.frontend.id
}

output "frontend_url" {
  value = "https://${data.aws_cloudfront_distribution.frontend.domain_name}"
}

output "backend_alb_dns" {
  value = module.backend_ecs.alb_dns_name
}

output "backend_ecs_cluster" {
  value = module.backend_ecs.ecs_cluster_name
}

output "backend_ecs_service" {
  value = module.backend_ecs.ecs_service_name
}
