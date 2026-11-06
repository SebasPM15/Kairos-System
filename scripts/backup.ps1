<#
.SYNOPSIS
  Backs up the Kairos Docker volume to a dated .tgz and keeps only the newest ones.

.DESCRIPTION
  The database is copied with SQLite's own backup API from a throwaway container that mounts the volume
  READ-ONLY. That gives a consistent snapshot while the backend keeps running (a plain file copy could catch
  a write half-way), and it cannot modify the real data. The snapshot is packed as kairos-data-YYYYMMDD-HHmm.tgz
  (containing kairos.db) under a temporary name and renamed only when complete, so a failure never leaves a
  partial .tgz. Retention deletes older files matching that exact pattern, only inside -Destination.

.PARAMETER Volume       Docker volume to back up (default kairos-system_kairos-data).
.PARAMETER Destination  Folder for the .tgz files (default %USERPROFILE%\Backups\Kairos; created if missing).
.PARAMETER Keep         How many backups to keep (default 14).
.PARAMETER Image        Image used for the helper container (default python:3.12-slim, already used by the stack).
#>
[CmdletBinding()]
param(
  [string]$Volume = 'kairos-system_kairos-data',
  [string]$Destination = (Join-Path $env:USERPROFILE 'Backups\Kairos'),
  [ValidateRange(1, 3650)][int]$Keep = 14,
  [string]$Image = 'python:3.12-slim'
)
# Continue, not Stop: docker may print warnings on stderr, which Stop would turn into fatal errors;
# failures are detected through $LASTEXITCODE and explicit throws instead
$ErrorActionPreference = 'Continue'
$pattern = '^kairos-data-\d{8}-\d{4}\.tgz$'
$temp = $null

try {
  docker volume inspect $Volume *> $null
  if ($LASTEXITCODE -ne 0) { throw "Volume '$Volume' does not exist (is Docker running?)." }

  New-Item -ItemType Directory -Force -Path $Destination | Out-Null
  $Destination = (Resolve-Path -LiteralPath $Destination).Path
  $name = 'kairos-data-{0}.tgz' -f (Get-Date -Format 'yyyyMMdd-HHmm')
  $temp = Join-Path $Destination ($name + '.part')
  $final = Join-Path $Destination $name
  if (Test-Path -LiteralPath $final) { throw "$name already exists; wait a minute and retry." }

  # Inside the container: SQLite backup of kairos.db (read-only source) -> tar.gz written under a .part name
  $script = @'
import sqlite3, tarfile, os, sys
src = sqlite3.connect('file:/data/kairos.db?mode=ro', uri=True)
os.makedirs('/tmp/snap', exist_ok=True)
dst = sqlite3.connect('/tmp/snap/kairos.db')
src.backup(dst); dst.close(); src.close()
chk = sqlite3.connect('/tmp/snap/kairos.db')
if chk.execute('pragma integrity_check').fetchone()[0] != 'ok': sys.exit('integrity_check failed')
with tarfile.open('/out/' + sys.argv[1], 'w:gz') as t: t.add('/tmp/snap/kairos.db', arcname='kairos.db')
'@
  docker run --rm -v "${Volume}:/data:ro" -v "${Destination}:/out" $Image python -c $script ($name + '.part')
  if ($LASTEXITCODE -ne 0) { throw 'The backup container failed.' }
  if (-not (Test-Path -LiteralPath $temp) -or (Get-Item -LiteralPath $temp).Length -eq 0) { throw 'No archive was produced.' }

  Move-Item -LiteralPath $temp -Destination $final
  $temp = $null
  Write-Host ("Backup written: {0} ({1:N0} bytes)" -f $final, (Get-Item -LiteralPath $final).Length)

  # Retention: newest $Keep files with the exact name pattern, in this folder only
  $old = Get-ChildItem -LiteralPath $Destination -File | Where-Object { $_.Name -match $pattern } |
    Sort-Object Name -Descending | Select-Object -Skip $Keep
  foreach ($file in $old) { Remove-Item -LiteralPath $file.FullName -Force; Write-Host "Removed old backup: $($file.Name)" }
}
catch {
  Write-Error $_.Exception.Message
  exit 1
}
finally {
  if ($temp -and (Test-Path -LiteralPath $temp)) { Remove-Item -LiteralPath $temp -Force -ErrorAction SilentlyContinue }
}
