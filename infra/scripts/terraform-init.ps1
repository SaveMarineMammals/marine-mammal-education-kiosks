param(
  [Parameter(Mandatory = $true)][string]$RootDir,
  [Parameter(Mandatory = $true)][string]$Bucket,
  [Parameter(Mandatory = $true)][string]$Key,
  [string]$Region = "us-east-1",
  [Parameter(Mandatory = $true)][string]$LockTable
)

$ErrorActionPreference = "Stop"
terraform -chdir=$RootDir init -input=false `
  "-backend-config=bucket=$Bucket" `
  "-backend-config=key=$Key" `
  "-backend-config=region=$Region" `
  "-backend-config=dynamodb_table=$LockTable"
