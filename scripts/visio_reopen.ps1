$ErrorActionPreference = "Stop"
$v = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Visio.Application")
Write-Output ("PID=" + $v.ProcessID + " Visible=" + $v.Visible + " Windows=" + $v.Windows.Count)

$path = "E:\InkLight\code\docs\architecture\InkLight-" + [char]0x7CFB + [char]0x7EDF + [char]0x67B6 + [char]0x6784 + [char]0x56FE + ".vsdx"
# 上面用 Unicode 码位拼出 “系统架构图”，避免脚本编码问题
$d2 = $v.Documents.Open($path)
Write-Output ("Opened: " + $d2.Name + " | win count: " + $d2.Windows.Count)
if ($d2.Windows.Count -gt 0) {
    $win = $d2.Windows.Item(1)
    $win.Activate()
    try { $win.WindowState = 1 } catch { }
    try { $win.Zoom = 45 } catch { }
    Write-Output "WINDOW_READY"
}
