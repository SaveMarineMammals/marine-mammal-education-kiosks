param(
  [Parameter(Mandatory = $true)][string]$RootDir,
  [string]$VarFile = "terraform.tfvars"
)

$ErrorActionPreference = "Stop"
$extra = @()
if (Test-Path (Join-Path $RootDir $VarFile)) {
  $extra += "-var-file=$VarFile"
}
terraform -chdir=$RootDir apply -input=false -auto-approve @extra
