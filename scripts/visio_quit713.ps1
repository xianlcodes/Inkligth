$ErrorActionPreference = "Continue"
$v = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Visio.Application")
Write-Output ("Before quit, PID=" + $v.ProcessID + " docs=" + $v.Documents.Count)
# 关闭所有文档（不保存），再退出实例
foreach ($d in @($v.Documents)) {
    try { $d.Close(0); Write-Output ("closed: " + $d.Name) } catch { Write-Output ("close fail: " + $_.Exception.Message) }
}
try { $v.Quit(); Write-Output "QUIT_OK" } catch { Write-Output ("quit fail: " + $_.Exception.Message) }
