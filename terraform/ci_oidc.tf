#used in setting up the CI/CD pipeline key less authentications for GITHUB ACTIONS to run
#automated terraform plan checks in ci/cd

variable "github_repo" {
  description = "Github repo in 'owner/repo' format that is allowed to assume CI plan role"
  type        = string
  default     = "Amon-Mugo/ERCOT-Grid-Reliability-Pipeline"
}

#check variables from main.tf
variable "terraform_state_bucket" {
  description = "S3 bucket name holding the terraform remote state for this project"
  type        = string
}

#gain access to main.tf pipeline state
variable "terraform_look_table" {
  description = "used S3 native lookup table to gain access to the main.tf pipeline state"
  type        = string
  default     = ""
}


#OIDC policy config 
resource "aws_iam_openid_connect_provider" "github_actions" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = {
    Project   = "ercot-grid-reliability-pipeline"
    ManagedBy = "terraform"
    Purpose   = "github-actions-ci-cd"
  }
}

# OIDC role config and iam policy 
data "aws_iam_policy_document" "ci_plan_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github_actions.arn]
    }

    # allow assume role to assume the role that has the terraform state access
    condition {
      test     = "StringEquals" 
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [
        "repo:${var.github_repo}:ref:refs/heads/main",
        "repo:${var.github_repo}:pull_request*"
      ]
    }
  }
}

#iam role definition
resource "aws_iam_role" "ci_plan_role" {
  name                 = "ercot-ci-plan-role"
  assume_role_policy   = data.aws_iam_policy_document.ci_plan_trust.json # attach the OIDC trust policy
  max_session_duration = 3600 #1 hour

  tags = {
    Project   = "ercot-grid-reliability-pipeline"
    ManagedBy = "terraform"
    Purpose   = "ci-terraform-plan-readonly"
  }
}

#iam read only policy

data "aws_iam_policy_document" "ci_plan_permissions" {
  statement {
    sid       = "AllowReadOnly"
    effect    = "Allow"
    actions   = [
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      "arn:aws:s3:::${var.terraform_state_bucket}",
      "arn:aws:s3:::${var.terraform_state_bucket}/*",
    ]
  }

  #scoped for s3 native lookup table permission in (use_lookfile=true) in main.tf

  statement {
    sid       = "TerraformS3NativeLookup"
    effect    = "Allow"
    actions   = [
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "arn:aws:s3:::${var.terraform_state_bucket}/*.tflock",
    ]
  }

  #readonly s3 bucket access for terraform state
  statement {
    sid     = "ReadOnlyS3"
    effect  = "Allow"
    actions = [
      "s3:GetBucketPolicy",
      "s3:GetBucketVersioning",
      "s3:GetBucketAcl",
      "s3:GetBucketTagging",
      "s3:GetBucketLocation",
      "s3:GetEncryptionConfiguration",
      "s3:GetLifecycleConfiguration",
      "s3:ListBucket",
      "s3:ListAllMyBuckets",
    ]
    resources = ["*"]
  }

  #readonly iam statement
  statement {
    sid     = "ReadOnlyIAM"
    effect  = "Allow"
    actions = [
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:ListPolicyVersions",
      "iam:GetOpenIDConnectProvider",
      "iam:ListOpenIDConnectProviders",
      "iam:GetInstanceProfile",
    ]
    resources = ["*"]
  }

  #readonly ecr statement
  statement {
    sid     = "ReadOnlyECR"
    effect  = "Allow"
    actions = [
      "ecr:DescribeRepositories",
      "ecr:GetRepositoryPolicy",
      "ecr:ListTagsForResource",
      "ecr:DescribeImages",
      "ecr:GetLifecyclePolicy",
    ]
    resources = ["*"]
  }
    
  #emr readonly statement
  statement {
    sid     = "ReadOnlyEMRServerless"
    effect  = "Allow"
    actions = [
      "emr-serverless:GetApplication",
      "emr-serverless:ListApplications",
      "emr-serverless:ListTagsForResource",
    ]
    resources = ["*"]
  }

  #getcaller identity statement
  statement {
    sid     = "STSGetCallerIdentity"
    effect  = "Allow"
    actions = [
      "sts:GetCallerIdentity",
    ]
    resources = ["*"]
  }
}

#inline policy attachment
resource "aws_iam_role_policy" "ci_plan_permissions" {
  name   = "ercot-ci-plan-readonly-policy"
  role   = aws_iam_role.ci_plan_role.id
  policy = data.aws_iam_policy_document.ci_plan_permissions.json
}

#output block
output "ci_plan_role_arn" {
  description = "ARN to set as the AWS_CI_PLAN_ROLE_ARN GitHub Actions secret"
  value       = aws_iam_role.ci_plan_role.arn
}