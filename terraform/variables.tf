variable "cluster_name" {
  type = string
  default = "ransom_rampage_vpc"
}

variable "aws_region" {
  type    = string
  default = "eu-west-1"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "subnet_cidrs" {
  type = map(string)
  default = {
    public_1  = "10.0.1.0/24"
    public_2  = "10.0.2.0/24"
    private_1 = "10.0.10.0/24"
    private_2 = "10.0.11.0/24"
  }
}

variable "availability_zones" {
  type    = list(string)
  default = ["eu-west-1a", "eu-west-1b"]
}

variable "services" {
  type = map(map(string))
  default = {
    dashboard = {
      ecr_name = "dashboard"
    }
    api_gateway = {
      ecr_name = "api_gateway"
    }
  }
}