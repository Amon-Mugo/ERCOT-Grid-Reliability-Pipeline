[paste the content above]
# CI/CD Setup — Lessons Learned (ERCOT Grid Pipeline)

Reference notes from building GitHub Actions CI with AWS OIDC auth, Terraform,
Airflow DAG validation, and dbt/sqlfluff linting. Written for reuse on future
projects using this same stack (AWS + Terraform + Airflow + dbt/Snowflake + GitHub Actions).

## AWS OIDC Federation for GitHub Actions

**Setup:** OIDC identity provider + IAM role with a trust policy scoped to a
specific GitHub repo, authenticated via `aws-actions/configure-aws-credentials@v4`.
No long-lived AWS keys stored as GitHub secrets — the workflow requests a
short-lived token per run.

**Required workflow permissions** (job-level, not just workflow-level):
```yaml
permissions:
  id-token: write
  contents: read
```
Without this, GitHub won't mint an OIDC token at all, regardless of how correct
the AWS trust policy is.

**GitHub's `sub` claim uses immutable numeric IDs**, not just `owner/repo` names:

repo:OWNER@ACCOUNT_ID/REPO@REPO_ID:ref:refs/heads/main

not the classic:

Confirm the real format via CloudTrail (`AssumeRoleWithWebIdentity` events,
`subjectFromWebIdentityToken` field) rather than assuming the classic format —
a trust policy using the wrong format fails with a generic, unhelpful error:
`Not authorized to perform sts:AssumeRoleWithWebIdentity`. This error gives no
hint as to *why* — trust policy syntax, missing `id-token: write`, and repo/org
account differences can all produce the identical message. CloudTrail is the
only way to see the real `sub` claim GitHub actually sent vs. what the trust
policy expects.

**Debugging checklist for this exact error, in order:**
1. Confirm `permissions: id-token: write` + `contents: read` at job level in the workflow.
2. Pull the actual `AssumeRoleWithWebIdentity` CloudTrail event and compare its
   `subjectFromWebIdentityToken` against the trust policy's `sub` condition values, character for character.
3. Check for AWS Organizations SCPs only if 1–2 check out (rare cause in practice).

## Terraform AWS Provider in CI

**Never hardcode a named AWS profile in the provider block.** Local dev uses
SSO profiles (`~/.aws/config`); CI authenticates via OIDC-issued environment
variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`)
with no profile at all. Make the profile conditional:
```hcl
variable "aws_profile" {
  type    = string
  default = ""  # empty = use default credential chain (CI-safe)
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile != "" ? var.aws_profile : null
}
```
Locally, export `AWS_PROFILE=<profile>` before running Terraform instead of
relying on a hardcoded default.

**A least-privilege read-only CI role needs far more S3 permissions than
expected.** The `aws_s3_bucket` resource type (and its companion resources
like `aws_s3_bucket_public_access_block`, `aws_s3_bucket_ownership_controls`)
each read multiple sub-resource configs on every `refresh`/`plan`, even when
nothing changed. Build the full set up front instead of discovering it one
`AccessDenied` at a time:

s3:GetBucketPolicy, GetBucketVersioning, GetBucketAcl, GetBucketTagging,
GetBucketLocation, GetBucketCORS, GetBucketWebsite, GetBucketLogging,
GetBucketRequestPayment, GetBucketObjectLockConfiguration, GetBucketPolicyStatus,
GetBucketPublicAccessBlock, GetBucketOwnershipControls, GetReplicationConfiguration,
GetAccelerateConfiguration, GetEncryptionConfiguration, GetLifecycleConfiguration,
ListBucket, ListAllMyBuckets

Plus, for S3-native state locking (`use_lockfile = true`, no DynamoDB):
`terraform plan` still acquires a lock even though it doesn't write state, so
the role needs `s3:PutObject`/`s3:DeleteObject` scoped narrowly to `*.tflock`
objects only — not the state file itself.

**`terraform fmt -check -recursive` in CI catches un-formatted `.tf` files**
written by hand without ever running `terraform fmt` locally. Run
`terraform fmt -recursive -diff` locally before the first CI push on a new
project to avoid a surprise failure — the fixes are pure whitespace/alignment,
safe to apply blindly, but worth a quick `git diff` scan regardless.

**Use `-target` to apply narrow changes safely** when unrelated drift exists
elsewhere in the state (e.g. a manually-pushed Docker image tag that hasn't
been reflected in Terraform code yet). Don't let an unrelated `plan` diff
block or get bundled into an unrelated change:
```bash
terraform apply -target=aws_iam_role_policy.some_policy
```
This produces a "resource targeting is in effect" warning — expected and safe
for narrow, deliberate applies; not something to use routinely.

## Python Linting (flake8)

Hand-written code without a formatter run against it accumulates dozens of
minor violations (missing whitespace after commas, inconsistent blank lines,
comment formatting) that are tedious to fix by hand but trivial to
auto-fix. **`autopep8 --aggressive --aggressive`** fixes flake8's exact rule
set without imposing a different formatter's broader style opinions (unlike
`ruff format`, which rewrites more aggressively and can touch things flake8
never flagged — riskier for a first pass, save `ruff` for after establishing
a formatting baseline everyone's reviewed).

```bash
pip install autopep8
autopep8 --in-place --max-line-length=100 --aggressive --aggressive <paths> -r
flake8 <paths> --max-line-length=100  # confirm clean
git diff --stat                        # confirm scope looks like formatting only
git diff <one representative file>     # spot-check no logic changed
```

Always spot-check at least one file's diff before committing an
autopep8/ruff pass — confirm it's whitespace/spacing only, not a reordered
argument or changed value.

## Airflow DAG Import Validation

`airflow dags list-import-errors --output json` can produce a *non-empty but
still valid* result if optional dependencies emit warnings to the same
stream — e.g. a missing `graphviz` package prints a UserWarning ahead of the
JSON output, breaking a naive `if [ "$(cat file.json)" != "[]" ]` string
comparison even though the actual import error list is empty. Install
optional CLI dependencies (`graphviz`) in the CI job explicitly rather than
patching around warning noise.

## SQL Linting (sqlfluff) with dbt

`sqlfluff lint --project-dir <path>` is not a valid flag in current
sqlfluff versions — `cd` into the dbt project directory first, then run
`sqlfluff lint models` with a relative path.

**The `--templater dbt` option requires a working dbt profile with live
credentials** (`~/.dbt/profiles.yml`, plus a reachable warehouse connection)
— not viable in a lightweight `lint-and-test` CI job with no Snowflake
credentials configured. Use **`--templater jinja`** instead for pure
style/syntax linting without needing a live database connection. Slightly
less precise for dbt-specific macro resolution (`ref()`/`source()` won't
fully resolve to real table names), but sufficient for catching real
formatting issues. Reserve full `dbt` templater + live credentials for a
`cd.yml`-style deploy job where Snowflake auth is already being set up
for other reasons (e.g. dbt run via RSA key-pair auth).

`sqlfluff fix` auto-fixes nearly everything sqlfluff flags (indentation,
spacing, Jinja tag padding, trailing newlines, redundant `else null` in
CASE statements) — same spot-check-before-commit discipline as autopep8.

## General CI Debugging Workflow

1. **Use `gh` CLI over the browser once auth is confirmed working**
   (`gh auth status` should show `repo` + `workflow` scopes). `gh run list`,
   `gh run view <run-id>`, and `gh api /repos/OWNER/REPO/actions/jobs/<job-id>/logs`
   are far faster and more copy-paste-reliable than screenshotting the Actions UI,
   especially for long logs that get visually truncated in a terminal or browser.
2. **Iterative missing-permission errors are normal** for a fresh least-privilege
   IAM role encountering a full Terraform resource refresh for the first time —
   expect several rounds of `AccessDenied` → add permission → re-test, not a
   sign anything is fundamentally wrong.
3. **Always verify locally (`terraform plan`, `flake8`, `sqlfluff lint`) before
   pushing** — catches the fix before spending a CI run cycle confirming it.
4. **Spot-check auto-fixer diffs before committing**, every time — auto-fixers
   are generally safe for pure style rules but worth a five-second visual
   confirmation that scope matches expectations.