<#
.SYNOPSIS
  Restores a backup .tgz (from backup.ps1) into a Docker volume.

.DESCRIPTION
  Refuses to touch the real volume (kairos-system_kairos-data) unless -OverwriteReal is given, refuses while a
  container is using the target volume, and asks you to type the volume name to confirm (skip with -Yes for
  scripts). An existing kairos.db in the target is kept as kairos.db.pre-restore. Nothing is written to the real
  volume by default: pass the name of a scratch volume to rehearse a restore.

.PARAMETER Archive        Path of the kairos-data-*.tgz to restore.
.PARAMETER Volume         Target volume (created if it does not exist).
.PARAMETER OverwriteReal  Required to restore into kairos-system_kairos-data.
.PARAMETER Yes            Skip the typed confirmation.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory)][string]$Archive,
  [Parameter(Mandatory)][string]$Volume,
  [switch]$OverwriteReal,
  [switch]$Yes,
  [string]$Image = 'python:3.12.16-slim-trixie'
)
# Continue, not Stop: docker may print warnings on stderr, which Stop would turn into fatal errors;
# failures are detected through $LASTEXITCODE and explicit throws instead
$ErrorActionPreference = 'Continue'
$real = 'kairos-system_kairos-data'

try {
  if (-not (Test-Path -LiteralPath $Archive -PathType Leaf)) { throw "Archive not found: $Archive" }
  $Archive = (Resolve-Path -LiteralPath $Archive).Path
  if ((Split-Path -Leaf $Archive) -notmatch '^kairos-data-\d{8}-\d{4}\.tgz$') { throw 'The archive name must look like kairos-data-YYYYMMDD-HHmm.tgz.' }
  if ($Volume -eq $real -and -not $OverwriteReal) {
    throw "Refusing to overwrite the real volume '$real'. Restore into another volume, or add -OverwriteReal if you really mean it."
  }
  docker info *> $null
  if ($LASTEXITCODE -ne 0) { throw 'Docker is not running.' }

  $users = docker ps -q --filter "volume=$Volume" 2>$null
  if ($users) { throw "A running container uses '$Volume'. Stop it first (docker compose down)." }

  if (-not $Yes) {
    $typed = Read-Host "This replaces kairos.db in volume '$Volume'. Type the volume name to continue"
    if ($typed -ne $Volume) { throw 'Confirmation did not match; nothing was changed.' }
  }

  docker volume inspect $Volume *> $null
  if ($LASTEXITCODE -ne 0) { docker volume create $Volume | Out-Null; if ($LASTEXITCODE -ne 0) { throw 'Could not create the volume.' } }

  $dir = Split-Path -Parent $Archive
  $file = Split-Path -Leaf $Archive
  $script = @'
import tarfile, os, shutil, sys, sqlite3
tmp = '/data/.restore-tmp'
shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
with tarfile.open('/in/' + sys.argv[1]) as t:
    m = t.getmember('kairos.db')
    if not m.isfile(): sys.exit('kairos.db is not a regular file')
    t.extract(m, tmp, filter='data')
if sqlite3.connect(tmp + '/kairos.db').execute('pragma integrity_check').fetchone()[0] != 'ok': sys.exit('restored database failed integrity_check')
if os.path.exists('/data/kairos.db'): os.replace('/data/kairos.db', '/data/kairos.db.pre-restore')
os.replace(tmp + '/kairos.db', '/data/kairos.db')
shutil.rmtree(tmp, ignore_errors=True)
os.chown('/data', 10001, 0); os.chown('/data/kairos.db', 10001, 0)
'@
  docker run --rm -v "${Volume}:/data" -v "${dir}:/in:ro" $Image python -c $script $file
  if ($LASTEXITCODE -ne 0) { throw 'The restore container failed; the previous database (if any) was not replaced.' }
  Write-Host "Restored $file into volume '$Volume'. Start the stack with: docker compose up -d"
}
catch {
  Write-Error $_.Exception.Message
  exit 1
}
