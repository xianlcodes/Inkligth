$ErrorActionPreference = "Continue"
$v = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Visio.Application")
Write-Output ("PID=" + $v.ProcessID)
while ($v.Documents.Count -gt 0) {
    $d = $v.Documents.Item(1)
    $nm = $d.Name
    try {
        $d.Close(0)
        Write-Output ("closed doc: " + $nm)
    } catch {
        Write-Output ("close fail: " + $_.Exception.Message)
        break
    }
}
Start-Sleep -Milliseconds 500
try { $v.Quit() } catch { Write-Output ("quit err: " + $_.Exception.Message) }
Start-Sleep -Seconds 2
$p = Get-Process -Id 713 -ErrorAction SilentlyContinue
if ($p) { Write-Output "PROCESS_STILL_ALIVE" } else { Write-Output "PROCESS_GONE" }
