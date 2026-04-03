data "aws_ssm_parameter" "openai_api_key" {
  name            = "/ransom-rampage/openai-api-key"
  with_decryption = true
}

resource "aws_ssm_parameter" "redis_url" {
  name  = "/ransom-rampage/redis-url"
  type  = "String"
  value = "redis://${var.redis_endpoint}:6379"
}