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

# Variables
variable "db_user" {
  description = "PostgreSQL username"
  type        = string
}

variable "db_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
}

variable "ecr_repository_url" {
  description = "ECR repository URL (e.g., 123456789012.dkr.ecr.us-east-1.amazonaws.com/my-repo)"
  type        = string
}

variable "docker_image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# Enable ECR access for EC2
resource "aws_iam_role" "ec2_ecr_access" {
  name = "ec2-ecr-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecr_pull" {
  role       = aws_iam_role.ec2_ecr_access.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "ec2-ecr-access-profile"
  role = aws_iam_role.ec2_ecr_access.name
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

              # Login to ECR
              aws ecr get-login-password --region ${var.aws_region} | \
              docker login --username AWS --password-stdin ${var.ecr_repository_url}
  
              # Create docker-compose.yml
              mkdir -p /home/ec2-user/postgres_data
              cat <<EOL > /home/ec2-user/docker-compose.yml
              version: '3.8'
              services:
                postgres:
                    image: postgres:13-alpine
                    restart: always
                    environment:
                        POSTGRES_PASSWORD: ${var.db_password}
                        POSTGRES_USER: ${var.db_user}
                        POSTGRES_DB: ${var.db_name}
                    volumes:
                        - ./postgres_data:/var/lib/postgresql/data
                    # Removed port exposure - access via container networking
                    
                discord_bot:
                    image: ${var.ecr_repository_url}:${var.docker_image_tag}
                    restart: unless-stopped
                    depends_on:
                        - postgres
              EOL
  
              # Start containers
              cd /home/ec2-user
              docker-compose up -d
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

output "ecr_repository" {
  value = var.ecr_repository_url
}