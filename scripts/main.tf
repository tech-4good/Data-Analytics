terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.92"
    }
  }

  required_version = ">= 1.2"
}

provider "aws" {
  region = "us-east-1"
}

resource "aws_vpc" "vpc_cco" {
  cidr_block = "10.0.0.0/24"
  tags = {
    Name = "vpc-analytics"
  }
}

resource "aws_subnet" "subrede_publica" {
  vpc_id = aws_vpc.vpc_cco.id
  cidr_block = "10.0.0.0/25"
  availability_zone = "us-east-1a"
  tags = {
    Name = "subnet-analytics"
  }
}

resource "aws_internet_gateway" "igw_cco" {
  vpc_id = aws_vpc.vpc_cco.id
  tags = {
    Name = "igw-cco"
  }
}

variable "cidr_qualquer_ip" {
    description = "Qualquer IP do mundo"
    type = string 
    default = "0.0.0.0/0"
}

resource "aws_route_table" "route_table_publica" {
  vpc_id = aws_vpc.vpc_cco.id
  route {
    cidr_block = var.cidr_qualquer_ip
    gateway_id = aws_internet_gateway.igw_cco.id
  }
  tags = {
    Name = "subrede-publica-route-table"
  }
}

resource "aws_route_table_association" "subrede-publica" {
  subnet_id      = aws_subnet.subrede_publica.id
  route_table_id = aws_route_table.route_table_publica.id  
}

resource "aws_security_group" "sg_publica" {
  name = "sg_publica"
  description = "Permite acesso SSH de qualquer IP"
  vpc_id = aws_vpc.vpc_cco.id

  ingress {
    from_port = 22
    to_port = 22
    protocol = "tcp"
    cidr_blocks = [var.cidr_qualquer_ip]
  }

  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = [var.cidr_qualquer_ip]
  }

}