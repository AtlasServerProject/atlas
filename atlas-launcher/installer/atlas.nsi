Unicode true
!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "x64.nsh"
Name "Atlas Launcher"
OutFile "${INSTALLER_OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\AtlasLauncher"
RequestExecutionLevel user
SetCompressor /FINAL zlib
CRCCheck force
ShowInstDetails nevershow
ShowUninstDetails nevershow
!define MUI_ICON "${ATLAS_ICON}"
!define MUI_UNICON "${ATLAS_ICON}"
VIProductVersion "${EXE_VERSION}"
VIAddVersionKey "ProductName" "Atlas Launcher"
VIAddVersionKey "FileDescription" "Instalador Atlas Launcher"
VIAddVersionKey "FileVersion" "${APP_VERSION}"
VIAddVersionKey "LegalCopyright" "Atlas Cobblemon"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "PortugueseBR"
Var Stage
Var Backup
Var Restart
Var Parent
Var Handle
Var Retry
Function .onInit
  ${IfNot} ${RunningX64}
    MessageBox MB_OK|MB_ICONSTOP "O Atlas Launcher precisa do Windows 64 bits."
    SetErrorLevel 1
    Quit
  ${EndIf}
  SetShellVarContext current
  StrCpy $INSTDIR "$LOCALAPPDATA\Programs\AtlasLauncher"
  StrCpy $Stage "$LOCALAPPDATA\Programs\AtlasLauncher.staging"
  StrCpy $Backup "$LOCALAPPDATA\Programs\AtlasLauncher.previous"
  ${GetParameters} $0
  ${GetOptions} $0 "/RESTART=" $Restart
  ClearErrors
  ${GetOptions} $0 "/PARENT_PID=" $Parent
  StrCmp $Parent "" wait_done
  IntOp $Parent $Parent + 0
  IntCmp $Parent 0 wait_done wait_done 0
  System::Call 'kernel32::OpenProcess(i 0x100000, i 0, i $Parent) p.r0'
  StrCpy $Handle $0
  StrCmp $Handle 0 wait_done
  System::Call 'kernel32::WaitForSingleObject(p $Handle, i 120000) i.r0'
  System::Call 'kernel32::CloseHandle(p $Handle)'
  IntCmp $0 0 wait_done 0 0
  SetErrorLevel 2
  Quit
wait_done:
FunctionEnd
Section "Instalar"
  IfFileExists "$INSTDIR\AtlasLauncher.exe" 0 begin_stage
  IfFileExists "$INSTDIR\.atlas-installation.json" begin_stage
  MessageBox MB_OK|MB_ICONSTOP "A pasta de instalação já contém outro aplicativo. Feche o instalador e procure o suporte Atlas."
  SetErrorLevel 3
  Quit
begin_stage:
  RMDir /r "$Stage"
  SetOutPath "$Stage"
  ClearErrors
  File /r "${APP_PAYLOAD}/*"
  IfErrors failed_stage
  WriteUninstaller "$Stage\Uninstall.exe"
  FileOpen $0 "$Stage\.atlas-installation.json" w
  FileWrite $0 '{"appId":"br.com.atlascobblemon.launcher","version":"${APP_VERSION}"}'
  FileClose $0
  IfErrors failed_stage
  SetOutPath "$TEMP"
  IfFileExists "$INSTDIR\AtlasLauncher.exe" 0 activate
  RMDir /r "$Backup"
  StrCpy $Retry 0
retry_rename:
  ClearErrors
  Rename "$INSTDIR" "$Backup"
  IfErrors 0 activate
  IntOp $Retry $Retry + 1
  IntCmp $Retry 20 failed_locked 0 failed_locked
  Sleep 500
  Goto retry_rename
activate:
  ClearErrors
  Rename "$Stage" "$INSTDIR"
  IfErrors failed_activate
  CreateDirectory "$SMPROGRAMS\Atlas Launcher"
  CreateShortcut "$SMPROGRAMS\Atlas Launcher\Atlas Launcher.lnk" "$INSTDIR\AtlasLauncher.exe"
  CreateShortcut "$DESKTOP\Atlas Launcher.lnk" "$INSTDIR\AtlasLauncher.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AtlasLauncher" "DisplayName" "Atlas Launcher"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AtlasLauncher" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AtlasLauncher" "Publisher" "Atlas Cobblemon"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AtlasLauncher" "DisplayIcon" "$INSTDIR\AtlasLauncher.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AtlasLauncher" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AtlasLauncher" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AtlasLauncher" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AtlasLauncher" "NoRepair" 1
  StrCmp $Restart "1" launch
  IfSilent done launch
launch:
  Exec '$\"$INSTDIR\AtlasLauncher.exe$\"'
done:
  SetErrorLevel 0
  Goto section_done
failed_activate:
  Rename "$Backup" "$INSTDIR"
  Goto failed_stage
failed_locked:
  MessageBox MB_OK|MB_ICONSTOP "Feche o Atlas Launcher e tente instalar novamente. A versão atual foi preservada." /SD IDOK
failed_stage:
  SetOutPath "$TEMP"
  RMDir /r "$Stage"
  SetErrorLevel 4
  Quit
section_done:
SectionEnd
Section "Uninstall"
  SetShellVarContext current
  SetOutPath "$TEMP"
  ClearErrors
  Rename "$LOCALAPPDATA\Programs\AtlasLauncher" "$LOCALAPPDATA\Programs\AtlasLauncher.removing"
  IfErrors 0 uninstall_ready
  MessageBox MB_OK|MB_ICONSTOP "Feche o Atlas Launcher antes de desinstalar."
  Abort
uninstall_ready:
  Delete "$DESKTOP\Atlas Launcher.lnk"
  RMDir /r "$SMPROGRAMS\Atlas Launcher"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\AtlasLauncher"
  SetOutPath "$TEMP"
  RMDir /r "$LOCALAPPDATA\Programs\AtlasLauncher.previous"
  RMDir /r "$LOCALAPPDATA\Programs\AtlasLauncher.removing"
  ; Never remove APPDATA, Minecraft instances, saved games or credentials.
SectionEnd
