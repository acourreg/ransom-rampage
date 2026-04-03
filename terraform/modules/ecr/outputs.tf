output "repo_urls" {
  value = { for k, v in aws_ecr_repository.services_repo : k => v.repository_url }
}