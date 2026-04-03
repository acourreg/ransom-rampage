resource "aws_vpc" "ransom_rampage_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "ransom-rampage-vpc" }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.ransom_rampage_vpc.id
  tags   = { Name = "ransom-rampage-igw" }
}

# ── Public subnets ──────────────────────────────────────────
resource "aws_subnet" "public_1" {
  vpc_id                  = aws_vpc.ransom_rampage_vpc.id
  cidr_block              = var.subnet_cidrs["public_1"]
  availability_zone       = var.azs[0]
  map_public_ip_on_launch = true
  tags = { Name = "public-subnet-1" }
}

resource "aws_subnet" "public_2" {
  vpc_id                  = aws_vpc.ransom_rampage_vpc.id
  cidr_block              = var.subnet_cidrs["public_2"]
  availability_zone       = var.azs[1]
  map_public_ip_on_launch = true
  tags = { Name = "public-subnet-2" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.ransom_rampage_vpc.id
  tags   = { Name = "public-rt" }
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.gw.id
}

resource "aws_route_table_association" "public_1" {
  subnet_id      = aws_subnet.public_1.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_2" {
  subnet_id      = aws_subnet.public_2.id
  route_table_id = aws_route_table.public.id
}

# ── NAT Gateway (single AZ — portfolio cost) ────────────────
resource "aws_eip" "nat" {
  domain     = "vpc"
  depends_on = [aws_internet_gateway.gw]
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public_1.id
  depends_on    = [aws_internet_gateway.gw]
  tags          = { Name = "ransom-rampage-nat" }
}

# ── Private subnets ─────────────────────────────────────────
resource "aws_subnet" "private_1" {
  vpc_id            = aws_vpc.ransom_rampage_vpc.id
  cidr_block        = var.subnet_cidrs["private_1"]
  availability_zone = var.azs[0]
  tags              = { Name = "private-subnet-1" }
}

resource "aws_subnet" "private_2" {
  vpc_id            = aws_vpc.ransom_rampage_vpc.id
  cidr_block        = var.subnet_cidrs["private_2"]
  availability_zone = var.azs[1]
  tags              = { Name = "private-subnet-2" }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.ransom_rampage_vpc.id
  tags   = { Name = "private-rt" }
}

resource "aws_route" "private_nat" {
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main.id
}

resource "aws_route_table_association" "private_1" {
  subnet_id      = aws_subnet.private_1.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_2" {
  subnet_id      = aws_subnet.private_2.id
  route_table_id = aws_route_table.private.id
}