output "openai_key_name" { value = data.aws_ssm_parameter.openai_api_key.name }
output "redis_url_name"  { value = aws_ssm_parameter.redis_url.name }