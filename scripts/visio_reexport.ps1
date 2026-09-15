$ErrorActionPreference = "Continue"
$v = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Visio.Application")
Write-Output ("PID=" + $v.ProcessID + " docs=" + $v.Documents.Count)
$target = $null
$name = "InkLight-" + [string]([char]0x7CFB) + [string]([char]0x7EDF) + [string]([char]0x67B6) + [string]([char]0x6784) + [string]([char]0x56FE) + ".vsdx"
foreach ($d in @($v.Documents)) { if ($d.Name -eq $name) { $target = $d } }
if (-not $target) { Write-Output "DOC_NOT_FOUND"; exit 1 }

$outDir = "E:\InkLight\code\docs\architecture"
# 先设页面为活动并打开窗口（确保页面处于前台）
$p = $target.Pages.Item(1)
$win = $target.Windows.Item(1)
$win.Activate()
$win.Page = $p

$pdfA = Join-Path $outDir "InkLight-架构图-export-test.pdf"
try {
    $target.ExportAsFixedFormat(1, $pdfA, 1, 0)
    Write-Output ("PDF_A size=" + (Get-Item $pdfA).Length)
} catch { Write-Output ("PDF_A fail: " + $_.Exception.Message) }

$pdfB = Join-Path $outDir "InkLight-架构图-export-test2.pdf"
try {
    $target.ExportAsFixedFormat(1, $pdfB, 1, 2)
    Write-Output ("PDF_B size=" + (Get-Item $pdfB).Length)
} catch { Write-Output ("PDF_B fail: " + $_.Exception.Message) }
Write-Output "EXPORT_DONE"
