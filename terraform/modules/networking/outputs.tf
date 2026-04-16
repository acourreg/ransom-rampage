output "vpc_id" {
  value = aws_vpc.ransom_rampage_vpc.id
}

output "public_subnet_ids" {
  value = [aws_subnet.public_1.id, aws_subnet.public_2.id]
}

output "private_subnet_ids" {
  value = [aws_subnet.private_1.id, aws_subnet.private_2.id]
}

output "nat_gateway_id" {
  value = aws_nat_gateway.main.id
}