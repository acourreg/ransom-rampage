resource "aws_acm_certificate" "cert" {
  domain_name               = "ransomrampage.com"
  subject_alternative_names = ["*.ransomrampage.com"]
  validation_method         = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

data "aws_route53_zone" "main" {
  name         = "ransomrampage.com"
  private_zone = false
}

resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.cert.domain_validation_options :
    dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  zone_id = data.aws_route53_zone.main.zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.record]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "cert" {
  certificate_arn         = aws_acm_certificate.cert.arn
  validation_record_fqdns = [for r in aws_route53_record.cert_validation : r.fqdn]
}

resource "aws_route53_record" "main" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "ransomrampage.com"
  type    = "A"

  alias {
    name                   = "k8s-ransomrampage-f3c7cf0d97-633248243.eu-west-1.elb.amazonaws.com"
    zone_id                = "Z32O12XQLNTSW2"
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "wildcard" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "*.ransomrampage.com"
  type    = "A"

  alias {
    name                   = "k8s-ransomrampage-f3c7cf0d97-633248243.eu-west-1.elb.amazonaws.com"
    zone_id                = "Z32O12XQLNTSW2"
    evaluate_target_health = true
  }
}
