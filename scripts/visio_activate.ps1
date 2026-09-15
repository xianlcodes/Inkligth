$ErrorActionPreference = "Stop"
$v = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Visio.Application")
Write-Output ("PID=" + $v.ProcessID + " docs before=" + $v.Documents.Count)

# 用 Unicode 码位拼出文件名 “InkLight-系统架构图.vsdx”，避免脚本编码问题
$name = "InkLight-" + [string]([char]0x7CFB) + [string]([char]0x7EDF) + [string]([char]0x67B6) + [string]([char]0x6784) + [string]([char]0x56FE) + ".vsdx"
$path = "E:\InkLight\code\docs\architecture\" + $name

$target = $null
foreach ($d in @($v.Documents)) {
    if ($d.Name -eq $name) { $target = $d }
}
if (-not $target) {
    $target = $v.Documents.Open($path)
    Write-Output "File opened"
} else {
    Write-Output "Already open"
}
Write-Output ("Doc windows: " + $target.Windows.Count)
$win = $target.Windows.Item(1)
$win.Activate()
try { $win.WindowState = 1 } catch { Write-Output ("WindowState err: " + $_.Exception.Message) }
try { $win.Zoom = 45 } catch { Write-Output ("Zoom err: " + $_.Exception.Message) }
Write-Output "ACTIVATED_OK"
