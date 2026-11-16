<# Utilise uniquement un certificat de signature de code déjà approuvé et disponible
   dans le magasin personnel. Ne crée pas de certificat auto-signé ni de secret.
   À exécuter après validation Windows, avec les outils du SDK Windows installés.
#>
param(
    [Parameter(Mandatory=$true)][string]$Installer,
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Fa-f0-9]{40}$')][string]$CertificateThumbprint,
    [Parameter(Mandatory=$true)][string]$SignTool,
    [Parameter(Mandatory=$true)][string]$RapportWindows
)
$ErrorActionPreference = 'Stop'
$proof = Get-Content -LiteralPath $RapportWindows -Raw -Encoding UTF8 | ConvertFrom-Json
$setup = (Resolve-Path -LiteralPath $Installer).Path
$hashBefore = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash
if ($proof.status -ne 'passed' -or -not $proof.smoke.installed -or $proof.smoke.execution_environment -ne 'windows' -or $proof.installer_sha256 -ne $hashBefore -or -not $proof.reinstall_checked -or -not $proof.predictive.details.sha256_verified) { throw 'Le rapport ne valide pas exactement cet installateur.' }
if ($proof.defender.status -ne 'scanned' -or $proof.defender.detections -ne 0 -or $proof.defender.installed_detections -ne 0) { throw 'Un scan Defender du fichier et du contenu installé est requis.' }
$cert = Get-Item -LiteralPath ('Cert:\CurrentUser\My\' + $CertificateThumbprint)
if (-not $cert.HasPrivateKey -or $cert.NotAfter -le (Get-Date)) { throw 'Certificat privé valide requis.' }
& $SignTool sign /sha1 $CertificateThumbprint /fd SHA256 /tr https://timestamp.digicert.com /td SHA256 $setup
if ($LASTEXITCODE -ne 0) { throw 'Signature échouée.' }
$signature = Get-AuthenticodeSignature -LiteralPath $setup
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Thumbprint -ne $CertificateThumbprint) { throw 'Signature non valide ou éditeur inattendu.' }
# The signature changes the binary: rerun the complete Windows validation and
# Defender scan on this exact signed file before any publication.
$record = @{status='signed_pending_revalidation'; sha256_before=$hashBefore; sha256_after=(Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash; signer=$signature.SignerCertificate.Subject; thumbprint=$signature.SignerCertificate.Thumbprint; signed_at=(Get-Date).ToString('o')}
$record | ConvertTo-Json | Set-Content -LiteralPath ($setup + '.signature.json') -Encoding UTF8
Write-Output 'Signature valide. Relancer Valider_Windows.ps1 avec -ScannerDefender -RequireDefender sur le fichier signé avant publication.'
