output "openai_key_name" { value = data.aws_ssm_parameter.openai_api_key.name }
output "redis_url_name"  { value = length(aws_ssm_parameter.redis_url) > 0 ? aws_ssm_parameter.redis_url[0].name : "" }

output "google_client_id"     { value = data.aws_ssm_parameter.google_client_id.value }
output "google_client_secret" {
  value     = data.aws_ssm_parameter.google_client_secret.value
  sensitive = true
}