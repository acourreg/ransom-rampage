terraform {
  backend "s3" {
    bucket         = "ransom-rampage-tfstate"
    key            = "dev/terraform.tfstate"
    region         = "eu-west-1"
    use_lockfile   = true
    encrypt        = true
  }
}
