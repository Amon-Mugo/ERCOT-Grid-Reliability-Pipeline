# this the cd speciffically exactly mutating the OIDC trust policy to allow CI to assume the role
# works alongside the ci_oidc.tf file to form a standard ci/cd pipeline

data "aws_iam_policy_document" "cd_trust" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"] # allow assume role to assume the role that has the terraform state access

    principals {
      type        = "Federated"                                          # federated means it's coming from the OIDC provider
      identifiers = [aws_iam_openid_connect_provider.github_actions.arn] #enables us to use the same identifire as the ci role 

    }
    #grant sts credentils to the role
    condition {
      test     = "StringEquals"                            #used to enforece the token will come from aws 
      variable = "token.actions.githubusercontent.com:aud" # will hold the OIDC token
      values   = ["sts.amazonaws.com"]
    }
    #the destination account id
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:Amon-Mugo@205969589/ERCOT-Grid-Reliability-Pipeline@1312976241:ref:refs/heads/main",
        "repo:Amon-Mugo@205969589/ERCOT-Grid-Reliability-Pipeline@1312976241:environment:production",
      
      ]
    }
  }
}

#iam role resource
resource "aws_iam_role" "cd_role" {
  name                 = "ercot-cd-role"
  assume_role_policy   = data.aws_iam_policy_document.cd_trust.json
  max_session_duration = 3600
  tags = {
    Project   = "ercot-grid-reliability-pipeline"
    ManagedBy = "terraform"
    Purpose   = "cd-deploy-and-apply"
  }
}

#iam permission policy
data "aws_iam_policy_document" "cd_permissions" {
  statement {
    sid     = "TerraformStateFullAccess"
    effect  = "Allow"
    actions = ["s3:*", ] # this grants full access to the state bucket
    resources = [
      "arn:aws:s3:::${var.terraform_state_bucket}",   #main state bucket
      "arn:aws:s3:::${var.terraform_state_bucket}/*", #state locking
    ]
  }
  #storage buckets
  statement {
    sid     = "DataBucketFullAccess"
    effect  = "Allow"
    actions = ["s3:*", ]
    resources = [
      "arn:aws:s3:::${var.raw_bucket_name}",
      "arn:aws:s3:::${var.raw_bucket_name}/*",
      "arn:aws:s3:::${var.curated_bucket_name}",
      "arn:aws:s3:::${var.curated_bucket_name}/*",
    ]
  }

  #ecr management permissions
  statement {
    sid     = "ECRRepoFullAccess"
    effect  = "Allow"
    actions = ["ecr:*", ]
    resources = [
      "arn:aws:ecr:${var.aws_region}:*:repository/${var.ecr_repo_name}",
    ]

  }

  #erc token permissions access
  statement {
    sid       = "ECRGetAuthToken"
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"] #all resources
  }
  #emr serverless permissions
  statement {
    sid     = "EMRServerlessFullAccess"
    effect  = "Allow"
    actions = ["emr-serverless:*", ]
    resources = [
      "arn:aws:emr-serverless:${var.aws_region}:*:/applications/*",
    ]
  }

  #iam role administration
  statement {
    sid     = "IAMErcotRolesFullAccess"
    effect  = "Allow"
    actions = ["iam:*", ]
    resources = [
      "arn:aws:iam::*:role/ercot-*",
      "arn:aws:iam::*:policy/ercot-*",
    ]
  }

  #OIDC provider -terraform reads/messages stored in resources
  statement {
    sid    = "IMAOIDCProviderAccess"
    effect = "Allow"
    actions = [
      "iam:GetOpenIDConnectProvider",
      "iam:ListOpenIDConnectProviders",
      "iam:UpdateOpenIDConnectProviderThumbprint",
      "iam:TagOpenIDConnectProvider",
    ]
    resources = [
      "arn:aws:iam::*:oidc-provider/token.actions.githubusercontent.com",
    ]
  }

  #getcaller identity delcalred earlier
  statement {
    sid       = "STSGetCallerIdentity"
    effect    = "Allow"
    actions   = ["sts:GetCallerIdentity", ]
    resources = ["*"]
  }
}

#policy attachmnet and output
resource "aws_iam_role_policy" "cd_permissions" {
  name   = "ercot-cd-deploy-policy"
  role   = aws_iam_role.cd_role.id
  policy = data.aws_iam_policy_document.cd_permissions.json
}

output "cd_role_arn" {
  description = "ARN to set as the AWS_CD_ROLE_ARN GitHub Actions secret"
  value       = aws_iam_role.cd_role.arn
}