provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      environment = "production"
    }
  }
}

data "aws_vpc" "default" {
  default = true
}

data "aws_security_group" "default" {
  name   = "default"
  vpc_id = data.aws_vpc.default.id
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

data "aws_subnet" "first_default" {
  id = data.aws_subnets.default.ids[0]
}

data "aws_key_pair" "cloud_bot_key" {
  key_name = "cloud-bot"
}

# Security group allowing SSH and bot traffic
resource "aws_security_group" "cloud_bot_sg" {
  name        = "cloud_bot_sg"
  description = "Allow SSH and Discord bot traffic"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Restrict to your IP in production!
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# IAM role for EC2
resource "aws_iam_role" "ec2_role" {
  name = "ec2-docker-host-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

# Attach policies
resource "aws_iam_role_policy_attachment" "ecr_pull" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_role_policy" "ssm_read" {
  role   = aws_iam_role.ec2_role.name
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action   = ["ssm:GetParameters"],
      Effect   = "Allow",
      Resource = ["arn:aws:ssm:us-east-1:*:parameter/discord-bot/*"]
    }]
  })
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "ec2-docker-host-profile"
  role = aws_iam_role.ec2_role.name
}

module "ec2_instances" {
  source  = "terraform-aws-modules/ec2-instance/aws"
  version = "4.3.0"

  count = 1
  name  = "cloud-bot-docker-host"
  key_name = data.aws_key_pair.cloud_bot_key.key_name

  ami                    = "ami-0f88e80871fd81e91"
  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name
  instance_type          = "t2.micro"
  vpc_security_group_ids = [aws_security_group.cloud_bot_sg.id]
  subnet_id              = data.aws_subnet.first_default.id

  user_data = <<-EOF
              #!/bin/bash
              # Install Docker
              sudo yum update -y
              sudo yum install docker -y
              sudo systemctl enable --now docker
              sudo usermod -aG docker ec2-user
  
              # Install Docker Compose
              sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
              sudo chmod +x /usr/local/bin/docker-compose
              docker-compose version
              EOF

  tags = {
    Terraform   = "true"
    Environment = "production"
    Name = "cloud-bot"
  }
}

output "instance_ip" {
  value = module.ec2_instances[0].public_ip
}
