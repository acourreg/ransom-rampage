resource "aws_ecr_repository" "services_repo" {
  for_each = var.services
  name                 = each.value["ecr_name"]
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "services_repo_policy" {
  repository = aws_ecr_repository.services_repo[each.key].name
  policy = data.aws_ecr_lifecycle_policy_document.services_repo_policy_doc.json
}

data "aws_ecr_lifecycle_policy_document" "services_repo_policy_doc" {
  rule {
    priority    = 1
    description = "Keep last 3 images"
    selection {
      tag_status   = "any"
      count_type   = "imageCountMoreThan"
      count_number = 3
    }
  }
}
