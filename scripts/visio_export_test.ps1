$ErrorActionPreference = "Stop"
$flags = [System.Reflection.BindingFlags]::InvokeMethod
$missing = [System.Type]::Missing

$v = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Visio.Application")
$d = $v.Documents.Add("")
$p = $d.Pages.Item(1)
$s = $p.DrawRectangle(0.2, 0.2, 3.0, 1.0)
$s.Text = "export test"
$s.CellsU("Char.Size").FormulaU = "10pt"

$png = "E:\InkLight\code\scripts\probe_exp.png"
try {
    $p.GetType().InvokeMember("Export", $flags, $null, $p, @($png, "PNG"))
    Write-Output "IM2_OK $(Test-Path $png)"
} catch { Write-Output ("IM2_FAIL: " + $_.Exception.Message) }

try {
    $p.GetType().InvokeMember("Export", $flags, $null, $p, @($png, "PNG", $missing, $missing))
    Write-Output "IM4_OK $(Test-Path $png)"
} catch { Write-Output ("IM4_FAIL: " + $_.Exception.Message) }

$d.Close()
