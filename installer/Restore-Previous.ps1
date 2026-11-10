$ErrorActionPreference = 'Stop'
$installationPath = [IO.Path]::GetFullPath($PSScriptRoot)
$backupPath = Join-Path $installationPath '.previous'
foreach ($mutexName in @('Local\HexenMap.LiveOverlay','Local\GenshinGemWish.LiveOverlay')) {
    try {
        $runningMutex = [Threading.Mutex]::OpenExisting($mutexName)
        $runningMutex.Dispose()
        throw 'Feche o overlay antes de restaurar.'
    } catch [Threading.WaitHandleCannotBeOpenedException] { }
}
$restoreNames = @('HexenMap.exe','HexenMapLauncher.exe','HexenMapBridge.exe','BUILD.json','installed-version.txt')
foreach ($fileName in $restoreNames) {
    if (-not (Test-Path -LiteralPath (Join-Path $backupPath $fileName) -PathType Leaf)) {
        throw 'Backup incompleto. Reinstale o instalador da versão anterior; seus dados serão preservados.'
    }
}
$previousVersion = (Get-Content -LiteralPath (Join-Path $backupPath 'installed-version.txt') -Raw).Trim()
if ($previousVersion -notmatch '^(\d+\.\d+\.\d+)' -or [version]$Matches[1] -lt [version]'1.0.1') {
    throw 'A versão anterior não usa a pasta fixa de saves. Restauração bloqueada para evitar abrir marcações antigas. Reinstale uma versão 1.0.1 ou posterior.'
}
Write-Host 'Feche também o launcher antes de continuar. As coletas e configurações serão preservadas.'
Read-Host 'Pressione Enter para restaurar os arquivos do aplicativo'
foreach ($fileName in $restoreNames) {
    Copy-Item -LiteralPath (Join-Path $backupPath $fileName) -Destination (Join-Path $installationPath $fileName) -Force
}
Set-Content -LiteralPath (Join-Path $installationPath 'updates-paused') -Value 'recovery'
Write-Host 'Versão anterior restaurada. Abra Hexen Map pelo menu Iniciar.'
