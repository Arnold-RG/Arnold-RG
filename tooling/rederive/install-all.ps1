# Set up Rederive for all repositories owned by Arnold-RG.
# Run in PowerShell: .\install-all.ps1
param(
  [string]$Owner = 'Arnold-RG',
  [string]$Workspace = (Join-Path $HOME 'code\Arnold-RG'),
  [switch]$SkipClone
)
$ErrorActionPreference = 'Stop'
foreach ($tool in @('git', 'gh', 'node', 'npx', 'python')) {
  if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
    throw "Missing prerequisite: $tool. Install it before continuing."
  }
}
& gh auth status
if ($LASTEXITCODE -ne 0) { throw 'Sign in with: gh auth login' }

Write-Host 'Installing Rederive at user scope for Codex, Cursor and Claude Code...'
& npx --yes skills add EricJujianZou/rederive --skill rederive --global --yes --agent codex --agent cursor --agent claude-code
if ($LASTEXITCODE -ne 0) { throw 'Rederive installation failed; no repositories were changed.' }

if (-not $SkipClone) {
  New-Item -ItemType Directory -Path $Workspace -Force | Out-Null
  $listJson = & gh repo list $Owner --limit 500 --json name,isArchived
  if ($LASTEXITCODE -ne 0) { throw 'Unable to list accessible GitHub repositories.' }
  $repos = @($listJson | ConvertFrom-Json)
  foreach ($repo in $repos) {
    if ($repo.isArchived) { continue }
    $destination = Join-Path $Workspace $repo.name
    if (Test-Path $destination) {
      Write-Host "Keeping existing folder: $destination"
      continue
    }
    Write-Host "Cloning $Owner/$($repo.name)"
    & gh repo clone "$Owner/$($repo.name)" $destination
    if ($LASTEXITCODE -ne 0) { Write-Warning "Clone failed: $Owner/$($repo.name)" }
  }
}
Write-Host 'Rederive is available to supported agents. Open a project in your coding agent and run /rederive.'
Write-Host 'This setup does not run code, tests, or automatic code changes in your projects.'
