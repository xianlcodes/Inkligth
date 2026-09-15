$ErrorActionPreference = "Stop"

$txt = Get-Content -Raw -Encoding UTF8 "E:\InkLight\code\scripts\visio_texts.json" | ConvertFrom-Json

$visio = $null
try {
    $visio = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Visio.Application")
    Write-Output "Attached to running Visio instance, pid=$($visio.ProcessID)"
} catch {
    $visio = New-Object -ComObject Visio.Application
    Write-Output "Started new Visio instance, pid=$($visio.ProcessID)"
}

$doc = $visio.Documents.Add("")
$page = $doc.Pages.Item(1)

$page.PageSheet.CellsU("PageWidth").FormulaU = "17 in"
$page.PageSheet.CellsU("PageHeight").FormulaU = "12 in"
Write-Output "Page size: $($page.PageSheet.CellsU('PageWidth').ResultStr('in')) x $($page.PageSheet.CellsU('PageHeight').ResultStr('in'))"

$s = $page.DrawRectangle(0.5, 0.5, 4.0, 1.5)
$s.Text = $txt.titleL1 + "`nsecond"
$s.CellsU("FillForegnd").FormulaU = "RGB(221,235,247)"
$s.CellsU("LineColor").FormulaU = "RGB(46,117,182)"
$s.CellsU("Char.Size").FormulaU = "10pt"
$s.CellsU("Char.Font").FormulaU = '"Microsoft YaHei"'
$s.CellsU("VerticalAlign").FormulaU = "1"
Write-Output "Fill formula: $($s.CellsU('FillForegnd').Formula)"
Write-Output "CharSize: $($s.CellsU('Char.Size').ResultStr('pt'))"
Write-Output "CharFont: $($s.CellsU('Char.Font').Formula)"

$ln = $page.DrawLine(2.25, 1.7, 2.25, 2.3)
$ln.CellsU("EndArrow").FormulaU = "13"
Write-Output "EndArrow formula: $($ln.CellsU('EndArrow').Formula)"

$outPng = "E:\InkLight\code\scripts\visio_probe.png"
$page.Export($outPng, "PNG")
Write-Output "PNG exported: $(Test-Path $outPng)"

$outVsdx = "E:\InkLight\code\scripts\visio_probe.vsdx"
$doc.SaveAs($outVsdx)
Write-Output "VSDX saved: $(Test-Path $outVsdx)"

$doc.Close()
Write-Output "PROBE_OK"
