Unicode true
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "x64.nsh"
!include "WinVer.nsh"
!include "Sections.nsh"

!ifndef APP_VERSION
!error "Passer APP_VERSION, PAYLOAD, OUTPUT et DELETE_INCLUDE avec build_installer.py."
!endif
Name "UltraTransfert ${APP_VERSION} (bêta)"
OutFile "${OUTPUT}"
Icon "ultra.ico"
UninstallIcon "ultra.ico"
InstallDir "$LOCALAPPDATA\Programs\UltraTransfert"
RequestExecutionLevel user
SetCompressor zlib
SetDatablockOptimize on
ManifestDPIAware true
ShowInstDetails show
ShowUninstDetails show
BrandingText "UltraTransfert · logiciel libre MIT"
VIProductVersion "${APP_VERSION}.0"
VIAddVersionKey /LANG=1036 "ProductName" "UltraTransfert"
VIAddVersionKey /LANG=1036 "CompanyName" "Maher Daoud-Brikci"
VIAddVersionKey /LANG=1036 "FileDescription" "Installation UltraTransfert (bêta non signée)"
VIAddVersionKey /LANG=1036 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1036 "LegalCopyright" "Copyright 2026 Maher Daoud-Brikci · MIT"
Var DeleteFailed

!define MUI_ABORTWARNING
!define MUI_WELCOMEPAGE_TITLE "Installer UltraTransfert"
!define MUI_WELCOMEPAGE_TEXT "Installation pour votre compte Windows, sans Python à préparer.$\r$\n$\r$\nVersion bêta : cet installateur est non signé et doit encore être validé sur un véritable Windows. Des protections peuvent le bloquer. Ne désactivez pas votre antivirus.$\r$\n$\r$\nAucun service, démarrage automatique ou règle de pare-feu ne sera ajouté."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "Ouvrir UltraTransfert"
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchApp
!define MUI_FINISHPAGE_RUN_NOTCHECKED
!define MUI_FINISHPAGE_TEXT "UltraTransfert est installé pour votre compte.$\r$\n$\r$\nUtilisez le raccourci du menu Démarrer pour copier des dossiers et vérifier le résultat.$\r$\n$\r$\nLes sources complètes et la licence MIT sont disponibles dans le dossier de l'application. Les dons Bitcoin restent facultatifs."
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "French"

Function .onInit
  SetShellVarContext current
  ${IfNot} ${IsNativeAMD64}
    IfSilent +2
    MessageBox MB_ICONSTOP "Cette version nécessite Windows x64 (processeur Intel ou AMD)."
    SetErrorLevel 1
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin10}
    IfSilent +2
    MessageBox MB_ICONSTOP "Windows 10 ou 11 x64 est requis."
    SetErrorLevel 1
    Abort
  ${EndIf}
  SetRegView 64
  ; Chemin fixe personnel ; aucun chemin fourni par le registre n'est exécuté.
  StrCpy $INSTDIR "$LOCALAPPDATA\Programs\UltraTransfert"
FunctionEnd

Section "UltraTransfert (obligatoire)" Main
  SectionIn RO
  SetShellVarContext current
  SetRegView 64
  IfFileExists "$INSTDIR\app\*.*" 0 fresh
    ReadRegStr $0 HKCU "Software\UltraTransfert" "InstallLocation"
    StrCmp $0 $INSTDIR 0 occupied
    IfFileExists "$INSTDIR\Uninstall.exe" 0 occupied
    IfSilent occupied
    MessageBox MB_OKCANCEL|MB_ICONINFORMATION "Fermez UltraTransfert avant de continuer. L'ancienne version sera désinstallée puis remplacée. Vos dossiers transférés et connexions personnels sont conservés. Sauvegardez vos éventuelles modifications des sources installées." IDCANCEL cancelled
    ExecWait '"$INSTDIR\Uninstall.exe" /S _?=$INSTDIR' $0
    StrCmp $0 0 0 occupied
    IfFileExists "$INSTDIR\app\*.*" occupied fresh
  occupied:
    IfSilent +2
    MessageBox MB_ICONSTOP "Le dossier d'application existe déjà ou est encore utilisé. Aucun fichier existant ne sera écrasé. Fermez UltraTransfert et désinstallez l'ancienne version ; conservez ailleurs les fichiers personnels restants dans ce dossier, puis recommencez."
    SetErrorLevel 2
    Abort
  cancelled:
    SetErrorLevel 2
    Abort
  fresh:
  IfFileExists "$INSTDIR\app" occupied 0
  SetOutPath "$INSTDIR\app"
  SetOverwrite off
  ClearErrors
  File /r "${PAYLOAD}\*"
  IfErrors failed
  InitPluginsDir
  ExecWait '"$INSTDIR\app\runtime\pythonw.exe" "$INSTDIR\app\installed_entry.py" --install-check "$PLUGINSDIR\controle.json"' $0
  StrCmp $0 0 checked
  failed:
    StrCpy $DeleteFailed "0"
    ClearErrors
    !include "${DELETE_INCLUDE}"
    IfSilent +2
    MessageBox MB_ICONSTOP "L'installation n'a pas réussi son contrôle local. Aucun lancement n'est annoncé prêt. Vérifiez les protections Windows, les droits et l'espace libre. Ne désactivez pas votre antivirus. Vos fichiers transférés n'ont pas été modifiés."
    SetErrorLevel 3
    Abort
  checked:
  CreateDirectory "$SMPROGRAMS\UltraTransfert"
  CreateShortCut "$SMPROGRAMS\UltraTransfert\UltraTransfert.lnk" "$INSTDIR\app\runtime\pythonw.exe" '"$INSTDIR\app\installed_entry.py"' "$INSTDIR\app\ultra.ico"
  CreateShortCut "$SMPROGRAMS\UltraTransfert\Code source et licence.lnk" "$WINDIR\explorer.exe" '"$INSTDIR\app"'
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  WriteRegStr HKCU "Software\UltraTransfert" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\UltraTransfert" "Version" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UltraTransfert" "DisplayName" "UltraTransfert ${APP_VERSION} (bêta)"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UltraTransfert" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UltraTransfert" "Publisher" "Maher Daoud-Brikci"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UltraTransfert" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UltraTransfert" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UltraTransfert" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UltraTransfert" "DisplayIcon" "$INSTDIR\app\ultra.ico"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UltraTransfert" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UltraTransfert" "NoRepair" 1
  SetErrorLevel 0
SectionEnd

Section /o "Raccourci sur le Bureau" Desktop
  CreateShortCut "$DESKTOP\UltraTransfert.lnk" "$INSTDIR\app\runtime\pythonw.exe" '"$INSTDIR\app\installed_entry.py"' "$INSTDIR\app\ultra.ico"
SectionEnd

Function LaunchApp
  Exec '"$INSTDIR\app\runtime\pythonw.exe" "$INSTDIR\app\installed_entry.py"'
FunctionEnd

Section "Uninstall"
  SetShellVarContext current
  SetRegView 64
  StrCpy $DeleteFailed "0"
  ClearErrors
  ; Liste exacte produite à la compilation : aucune suppression récursive.
  !include "${DELETE_INCLUDE}"
  StrCmp $DeleteFailed "0" removed
    IfSilent +2
    MessageBox MB_ICONSTOP "Des fichiers sont encore utilisés. Fermez UltraTransfert puis relancez la désinstallation. Les dossiers personnels sont conservés."
    SetErrorLevel 4
    Abort
  removed:
  Delete "$DESKTOP\UltraTransfert.lnk"
  Delete "$SMPROGRAMS\UltraTransfert\UltraTransfert.lnk"
  Delete "$SMPROGRAMS\UltraTransfert\Code source et licence.lnk"
  RMDir "$SMPROGRAMS\UltraTransfert"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\UltraTransfert"
  DeleteRegKey HKCU "Software\UltraTransfert"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
  SetErrorLevel 0
SectionEnd
