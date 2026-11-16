<# Contrôle développeur sur une VM Windows x64 propre, sans installation existante.
   Aucune désactivation ou exclusion antivirus. Aucun contournement SmartScreen.
   Ce script est destiné aux runners Windows propres et aux VM de test.
#>
param(
    [Parameter(Mandatory=$true)][string]$Installer,
    [Parameter(Mandatory=$true)][string]$Rapport,
    [switch]$ScannerDefender,
    [switch]$RequireDefender
)
$ErrorActionPreference = 'Stop'
$setup = (Resolve-Path -LiteralPath $Installer).Path
$appBase = Join-Path $env:LOCALAPPDATA 'Programs\UltraTransfert'
if (Test-Path -LiteralPath $appBase) {
    throw 'Utiliser une VM propre : une installation ou un dossier existe déjà. Aucun changement effectué.'
}
$temporary = Join-Path $env:TEMP ('UltraTransfert-validation-' + [guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $temporary | Out-Null
$result = [ordered]@{
    status = 'failed'; platform = 'Windows'; started = (Get-Date).ToString('o')
    installer_sha256 = (Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash.ToLowerInvariant()
    signature = (Get-AuthenticodeSignature -LiteralPath $setup).Status.ToString()
    defender = @{status='not_requested'}; predictive = $null; existing_install_refused = $false; reinstall_checked = $false; install_exit = $null; smoke = $null; uninstall_exit = $null
    foreign_file_preserved = $false; shortcuts_created = $false; error = $null
}
$sentinel = Join-Path $appBase 'app\fichier-etranger-test.txt'
try {
    if ($ScannerDefender) {
        try {
            $status = Get-MpComputerStatus
            if (-not $status.AntivirusEnabled -or -not $status.AMServiceEnabled) { throw 'Microsoft Defender non actif.' }
            $result.defender = @{status='pending'; signature_version=$status.AntivirusSignatureVersion}
            Start-MpScan -ScanType CustomScan -ScanPath $setup
            $detections = @(Get-MpThreatDetection | Where-Object { ($_.Resources -join ' ') -match [regex]::Escape($setup) })
            $result.defender = @{status='scanned'; signature_version=$status.AntivirusSignatureVersion; scanned_at=(Get-Date).ToString('o'); detections=$detections.Count; scope='installer'}
            if ($detections.Count -gt 0 -or -not (Test-Path -LiteralPath $setup)) { throw 'Détection ou quarantaine.' }
        } catch {
            if ($result.defender.status -in @('pending','scanned') -or $RequireDefender) { throw }
            $result.defender = @{status='unavailable'; reason=$_.Exception.Message}
        }
    }
    $process = Start-Process -FilePath $setup -ArgumentList '/S' -Wait -PassThru
    $result.install_exit = $process.ExitCode
    if ($process.ExitCode -ne 0) { throw 'Installation échouée.' }
    $installed = Join-Path $appBase 'app'
    $python = Join-Path $installed 'runtime\python.exe'
    $entry = Join-Path $installed 'installed_entry.py'
    $smoke = Join-Path $temporary 'smoke.json'
    & $python $entry '--smoke-test' $smoke
    if ($LASTEXITCODE -ne 0) { throw 'Contrôle autonome échoué.' }
    $data = Get-Content -LiteralPath $smoke -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($data.status -ne 'passed' -or $data.execution_environment -ne 'windows' -or -not $data.sharing_session_checked) {
        throw 'Le résultat ne prouve pas un contrôle Windows/TLS réussi.'
    }
    $result.smoke = $data
    $predictive = Join-Path $temporary 'predictive.json'
    & $python $entry '--predictive-test' $predictive
    if ($LASTEXITCODE -ne 0) { throw 'Compression prédictive intégrée échouée.' }
    $prediction = Get-Content -LiteralPath $predictive -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($prediction.status -ne 'passed' -or -not $prediction.native_windows -or -not $prediction.details.sha256_verified) { throw 'Aucune preuve Windows prédictive valide.' }
    $result.predictive = $prediction
    if ($result.defender.status -eq 'scanned') {
        Start-MpScan -ScanType CustomScan -ScanPath $installed
        $detections = @(Get-MpThreatDetection | Where-Object { ($_.Resources -join ' ') -match [regex]::Escape($installed) })
        $result.defender.installed_detections = $detections.Count
        $result.defender.scope = 'installer_and_installed_payload'
        if ($detections.Count -gt 0) { throw 'Détection du contenu installé.' }
    }
    $shortcut = Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs\UltraTransfert\UltraTransfert.lnk'
    $result.shortcuts_created = Test-Path -LiteralPath $shortcut
    if (-not $result.shortcuts_created) { throw 'Raccourci absent.' }
    Set-Content -LiteralPath $sentinel -Value 'Conserver ce fichier étranger.' -Encoding UTF8
    $again = Start-Process -FilePath $setup -ArgumentList '/S' -Wait -PassThru
    if ($again.ExitCode -ne 2 -or -not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath $sentinel)) { throw 'Protection de l’installation existante incorrecte.' }
    $result.existing_install_refused = $true
    $uninstaller = Join-Path $appBase 'Uninstall.exe'
    # _? conserve le processus dans son répertoire pour que Wait attende sa fin.
    $uninstall = Start-Process -FilePath $uninstaller -ArgumentList ('/S _?=' + $appBase) -Wait -PassThru
    $result.uninstall_exit = $uninstall.ExitCode
    if ($uninstall.ExitCode -ne 0) { throw 'Désinstallation échouée.' }
    $result.foreign_file_preserved = Test-Path -LiteralPath $sentinel
    if (-not $result.foreign_file_preserved) { throw 'Le fichier étranger a été supprimé.' }
    if (Test-Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\UltraTransfert') { throw 'Entrée de désinstallation encore présente.' }
    if (Test-Path -LiteralPath $python) { throw 'Runtime non retiré.' }
    # Remove only the exact sentinel created above, after checking its preservation.
    Remove-Item -LiteralPath $sentinel
    # Native non-recursive directory deletion fails if any unexpected file remains.
    [System.IO.Directory]::Delete($installed, $false)
    # NSIS _? keeps its own executable in place. Remove only that known test artifact.
    if (Test-Path -LiteralPath $uninstaller) { Remove-Item -LiteralPath $uninstaller }
    [System.IO.Directory]::Delete($appBase, $false)
    $reinstall = Start-Process -FilePath $setup -ArgumentList '/S' -Wait -PassThru
    if ($reinstall.ExitCode -ne 0) { throw 'Réinstallation propre échouée.' }
    & $python $entry '--install-check' (Join-Path $temporary 'reinstall.json')
    if ($LASTEXITCODE -ne 0) { throw 'Contrôle après réinstallation échoué.' }
    $result.reinstall_checked = $true
    $final = Start-Process -FilePath $uninstaller -ArgumentList ('/S _?=' + $appBase) -Wait -PassThru
    if ($final.ExitCode -ne 0 -or (Test-Path -LiteralPath $python)) { throw 'Désinstallation finale échouée.' }
    $result.status = 'passed' 
} catch {
    $result.error = $_.Exception.Message
} finally {
    $result.rdp_tested = $false
    $result.smartscreen_download_tested = $false
    $result.windows_edition = (Get-CimInstance Win32_OperatingSystem).Caption
    $result.completed = (Get-Date).ToString('o')
    $result | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $Rapport -Encoding UTF8
    # Les rapports et tout reste d'installation sont conservés pour diagnostic.
}
if ($result.status -ne 'passed') { throw ('Validation échouée : ' + $result.error) }
Write-Output ('Validation Windows terminée. Rapport : ' + $Rapport)
