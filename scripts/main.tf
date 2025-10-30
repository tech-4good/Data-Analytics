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
    Name = "subrede-publica-route-table-anatytics"
  }
}

resource "aws_route_table_association" "subrede-publica" {
  subnet_id      = aws_subnet.subrede_publica.id
  route_table_id = aws_route_table.route_table_publica.id  
}

resource "aws_security_group" "sg_publica" {
  name = "sg_publica_analytics"
  description = "Permite acesso SSH de qualquer IP"
  vpc_id = aws_vpc.vpc_cco.id

  ingress {
    from_port = 22
    to_port = 22
    protocol = "tcp"
    cidr_blocks = [var.cidr_qualquer_ip]
  }

    ingress {
    from_port = 3000
    to_port = 3000
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

# instancia 

resource "aws_instance" "ec2_publica" {
  ami                         = "ami-0e86e20dae9224db8"
  key_name                    = "vockey"
  instance_type               = "t2.micro"
  subnet_id                   = aws_subnet.subrede_publica.id
  vpc_security_group_ids      = [aws_security_group.sg_publica.id]
  associate_public_ip_address = true

  user_data = join("\n\n", [
    file("${path.module}/instalacao/instalar_grafana.sh")
  ])

  user_data_replace_on_change = true

  connection {
    type        = "ssh"
    user        = "ubuntu"
    private_key = file("./vockey.pem")
    host        = self.public_ip 
  }

  tags = { Name = "ec2-analytics" }
}

#buckets 

resource "aws_s3_bucket" "raw" {
  bucket = "t4g-raw"
  tags = { Name = "Raw" }
}
resource "aws_s3_bucket" "trusted" {
  bucket = "t4g-trusted"
  tags = { Name = "Trusted" }
}
resource "aws_s3_bucket" "curated" {
  bucket = "t4g-curated"
  tags = { Name = "Curated" }
}

resource "aws_s3_bucket_public_access_block" "bloco_acesso_publico_s3" {
  bucket = aws_s3_bucket.curated.id

  block_public_acls       = false
  block_public_policy     = false 
  ignore_public_acls      = false 
  restrict_public_buckets = false  
}

resource "aws_s3_bucket_policy" "politica_acesso_publico_bucket" {
  bucket = aws_s3_bucket.curated.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = ["s3:GetObject"]
        Principal = "*"
        Effect = "Allow"
        Resource = "${aws_s3_bucket.curated.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.bloco_acesso_publico_s3]
}

# lambda

data "aws_iam_role" "lab_role" {
  name = "LabRole"
}

#ram -> trusted

data "archive_file" "lambda_RT_zip" {
  type = "zip"
  source_file = "lambda_raw_trusted.py"
  output_path = "lambda_raw_trusted.zip"
}

resource "aws_lambda_function" "funcao_lambda1_RT" {
  function_name    = "funcao1-terraform"
  handler          = "lambda_raw_trusted.lambda_handler"
  runtime          = "python3.12"
  timeout          = 300
  memory_size      = 512 
  role             = data.aws_iam_role.lab_role.arn
  filename         = data.archive_file.lambda_RT_zip.output_path
  source_code_hash = data.archive_file.lambda_RT_zip.output_base64sha256 
  layers           = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python312:19"]


  environment {
    variables = {
      BUCKET_RAW = aws_s3_bucket.raw.id
      BUCKET_TRUSTED = aws_s3_bucket.trusted.id
    }
  }

}

#trusted -> refined 

data "archive_file" "lambda_TR_zip" {
  type = "zip"
  source_file = "lambda_trusted_client.py"
  output_path = "lambda_trusted_client.zip"
}

resource "aws_lambda_function" "funcao_lambda2_TR" {
  function_name    = "funcao2-terraform"
  handler          = "lambda_trusted_client.lambda_handler"
  runtime          = "python3.12"
  timeout          = 300
  memory_size      = 512 
  role             = data.aws_iam_role.lab_role.arn
  filename         = data.archive_file.lambda_TR_zip.output_path
  source_code_hash = data.archive_file.lambda_TR_zip.output_base64sha256 
  layers           = ["arn:aws:lambda:us-east-1:336392948345:layer:AWSSDKPandas-Python312:19"]


  environment {
    variables = {
      BUCKET_TRUSTED = aws_s3_bucket.trusted.id
      BUCKET_CURATED = aws_s3_bucket.curated.id
    }
  }

}