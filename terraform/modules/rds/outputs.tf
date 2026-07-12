output "endpoint" {
  value       = aws_db_instance.main.endpoint
  description = "RDS instance endpoint (address:port)"
}

output "address" {
  value       = aws_db_instance.main.address
  description = "RDS instance address"
}

output "port" {
  value       = aws_db_instance.main.port
  description = "RDS instance port"
}

output "db_name" {
  value       = aws_db_instance.main.db_name
  description = "Database name"
}
