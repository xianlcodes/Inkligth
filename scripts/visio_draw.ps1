$ErrorActionPreference = "Stop"

# ============ 页面常量（英寸，坐标从顶部向下布局，绘图时转换为 Visio 底部原点） ============
$W = 17.2
$H = 12.2

$txt = Get-Content -Raw -Encoding UTF8 "E:\InkLight\code\scripts\visio_texts.json" | ConvertFrom-Json

# ============ 颜色 ============
function RGB([string]$hex) { "RGB($([Convert]::ToInt32($hex.Substring(0,2),16)),$([Convert]::ToInt32($hex.Substring(2,2),16)),$([Convert]::ToInt32($hex.Substring(4,2),16)))" }
$cTitleBg   = RGB "1F4E79"   # 深蓝标题
$cTitleTx   = RGB "FFFFFF"
$cClient    = RGB "DDEBF7"
$cClientLn  = RGB "2E75B6"
$cNginx     = RGB "FCE4D6"
$cNginxLn   = RGB "C55A11"
$cFront     = RGB "DEEBF7"
$cFrontLn   = RGB "2E75B6"
$cBack      = RGB "E2EFDA"
$cBackLn    = RGB "548235"
$cData      = RGB "FFF2CC"
$cDataLn    = RGB "BF9000"
$cExt       = RGB "E4DFEC"
$cExtLn     = RGB "7030A0"
$cGrayFill  = RGB "F2F2F2"
$cGrayLn    = RGB "7F7F7F"
$cBandLine  = RGB "9E9E9E"
$cTextDark  = RGB "333333"
$cTitleGray = RGB "404040"
$cArrow     = RGB "595959"

# ============ Visio 连接 ============
$visio = $null
try {
    $visio = [System.Runtime.InteropServices.Marshal]::GetActiveObject("Visio.Application")
    Write-Output "Attached to running Visio instance, pid=$($visio.ProcessID)"
} catch {
    $visio = New-Object -ComObject Visio.Application
    Write-Output "Started new Visio instance, pid=$($visio.ProcessID)"
}
$visio.UndoEnabled = 0
$doc = $visio.Documents.Add("")
$page = $doc.Pages.Item(1)
$page.PageSheet.CellsU("PageWidth").FormulaU  = "$W in"
$page.PageSheet.CellsU("PageHeight").FormulaU = "$H in"

# ============ 辅助函数（所有 top/h 均以页面顶部为基准） ============
function New-Rect([double]$x, [double]$top, [double]$w, [double]$h) {
    $yb = $H - $top - $h
    return $page.DrawRectangle($x, $yb, $x + $w, $yb + $h)
}
function Set-BoxStyle($shp, [string]$fill, [string]$line, [double]$fs, [double]$lw = 0.75) {
    $shp.CellsU("FillForegnd").FormulaU = $fill
    $shp.CellsU("FillPattern").FormulaU = "1"
    $shp.CellsU("LineColor").FormulaU  = $line
    $shp.CellsU("LineWeight").FormulaU = "$lw pt"
    $shp.CellsU("Char.Size").FormulaU  = "$fs pt"
    $shp.CellsU("Char.Font").FormulaU  = '"Microsoft YaHei"'
    $shp.CellsU("Char.Color").FormulaU = $cTextDark
    $shp.CellsU("VerticalAlign").FormulaU = "1"          # 垂直居中
    $shp.CellsU("Para.HorzAlign").FormulaU = "1"         # 水平居中
    return $shp
}
function New-Label([double]$x, [double]$top, [double]$w, [double]$h, [string]$text, [double]$fs, [string]$color = $cTitleGray, [int]$halign = 0) {
    $shp = New-Rect $x $top $w $h
    $shp.Text = $text
    $shp.CellsU("FillPattern").FormulaU = "0"
    $shp.CellsU("LinePattern").FormulaU = "0"
    $shp.CellsU("Char.Size").FormulaU  = "$fs pt"
    $shp.CellsU("Char.Font").FormulaU  = '"Microsoft YaHei"'
    $shp.CellsU("Char.Color").FormulaU = $color
    $shp.CellsU("VerticalAlign").FormulaU = "1"
    $shp.CellsU("Para.HorzAlign").FormulaU = "$halign"
    return $shp
}
function New-TextBox([double]$x, [double]$top, [double]$w, [double]$h, [string]$text, [double]$fs, [string]$fill, [string]$line, [double]$lw = 0.75) {
    $shp = New-Rect $x $top $w $h
    $shp.Text = $text
    Set-BoxStyle $shp $fill $line $fs $lw | Out-Null
    return $shp
}
function New-Container([double]$x, [double]$top, [double]$w, [double]$h) {
    $shp = New-Rect $x $top $w $h
    $shp.CellsU("FillPattern").FormulaU = "0"
    $shp.CellsU("LinePattern").FormulaU = "1"
    $shp.CellsU("LineColor").FormulaU  = $cBandLine
    $shp.CellsU("LineWeight").FormulaU = "1 pt"
    return $shp
}
function New-Arrow([double]$x1, [double]$yTop1, [double]$x2, [double]$yTop2) {
    # 方向：从 (x1,yTop1) 指向 (x2,yTop2)，顶端带实心箭头
    $y1 = $H - $yTop1
    $y2 = $H - $yTop2
    $ln = $page.DrawLine($x1, $y1, $x2, $y2)
    $ln.CellsU("LineColor").FormulaU = $cArrow
    $ln.CellsU("LineWeight").FormulaU = "1.5 pt"
    $ln.CellsU("BeginArrow").FormulaU = "0"
    $ln.CellsU("EndArrow").FormulaU = "13"
    $null = $ln
}

# ============ 1. 标题 ============
$t = New-TextBox 0.35 0.12 16.5 0.62 ($txt.titleL1 + "`n" + $txt.titleL2) 14 $cTitleBg $cTitleBg 1
$t.CellsU("Char.Color").FormulaU = $cTitleTx

# ============ 2. 用户层 ============
New-TextBox 4.6 0.88 8.0 0.62 $txt.client 10 $cClient $cClientLn | Out-Null
New-Arrow 8.6 1.5 8.6 1.8

# ============ 3. Nginx 接入层 ============
New-TextBox 0.35 1.8 16.5 1.05 ($txt.nginxL1 + "`n" + $txt.nginxL2 + "`n" + $txt.nginxL3) 9.5 $cNginx $cNginxLn | Out-Null
New-Arrow 8.6 2.85 8.6 3.2

# ============ 4. 前端应用层 ============
$frontX  = 0.35; $frontTop = 3.2; $frontW = 16.5; $frontH = 2.15
New-Container $frontX $frontTop $frontW $frontH | Out-Null
New-Label 0.6 ($frontTop + 0.05) 12 0.3 $txt.frontBand 10.5 $cFrontLn 0 | Out-Null

$fm = @(
    @{ t = $txt.f1; d = $txt.f1d },
    @{ t = $txt.f2; d = $txt.f2d },
    @{ t = $txt.f3; d = $txt.f3d },
    @{ t = $txt.f4; d = $txt.f4d },
    @{ t = $txt.f5; d = $txt.f5d },
    @{ t = $txt.f6; d = $txt.f6d }
)
$fw = 2.45; $fg = 0.24; $fx0 = 0.6; $fTop = 3.62; $fh = 1.15
for ($i = 0; $i -lt 6; $i++) {
    New-TextBox ($fx0 + $i * ($fw + $fg)) $fTop $fw $fh ($fm[$i].t + "`n" + $fm[$i].d) 9 $cFront $cFrontLn | Out-Null
}
New-TextBox 0.6 4.95 15.9 0.28 $txt.frontTech 8.5 $cGrayFill $cGrayLn | Out-Null
New-Arrow 5.2 5.35 5.2 5.65
New-Arrow 11.6 5.35 11.6 5.65

# ============ 5. 后端服务层（主区）+ 右侧 AI/外部服务栏 ============
$backX = 0.35; $backTop = 5.65; $backW = 12.35; $backH = 3.25   # 5.65..8.90
New-Container $backX $backTop $backW $backH | Out-Null
New-Label 0.55 ($backTop + 0.05) 12 0.3 $txt.backBand 10.5 $cBackLn 0 | Out-Null

$bm = @(
    @{ t = $txt.b1; d = $txt.b1d },
    @{ t = $txt.b2; d = $txt.b2d },
    @{ t = $txt.b3; d = $txt.b3d },
    @{ t = $txt.b4; d = $txt.b4d },
    @{ t = $txt.b5; d = $txt.b5d },
    @{ t = $txt.b6; d = $txt.b6d },
    @{ t = $txt.b7; d = $txt.b7d },
    @{ t = $txt.b8; d = $txt.b8d }
)
$bw = 2.87; $bg = 0.13; $bx0 = 0.55; $bh = 1.28
$r1 = 6.05; $r2 = 7.48
for ($i = 0; $i -lt 8; $i++) {
    $rowTop = if ($i -lt 4) { $r1 } else { $r2 }
    $col = $i % 4
    New-TextBox ($bx0 + $col * ($bw + $bg)) $rowTop $bw $bh ($bm[$i].t + "`n" + $bm[$i].d) 8.5 $cBack $cBackLn | Out-Null
}

# ---- 右侧 AI / 外部服务栏 ----
$railX = 12.95; $railTop = 5.65; $railW = 3.9; $railH = 5.0    # 5.65..10.65
New-Container $railX $railTop $railW $railH | Out-Null
New-Label ($railX + 0.15) ($railTop + 0.05) 3.6 0.3 $txt.extBand 10 $cExtLn 0 | Out-Null

$em = @(
    @{ t = $txt.e1; d = $txt.e1d },
    @{ t = $txt.e2; d = $txt.e2d },
    @{ t = $txt.e3; d = $txt.e3d },
    @{ t = $txt.e4; d = $txt.e4d }
)
$ew = 3.5; $ex0 = $railX + 0.2; $eh = 1.0; $eg = 0.2
for ($i = 0; $i -lt 4; $i++) {
    New-TextBox $ex0 (6.0 + $i * ($eh + $eg)) $ew $eh ($em[$i].t + "`n" + $em[$i].d) 8.5 $cExt $cExtLn | Out-Null
}

# 后端 -> 外部服务 的水平调用箭头
New-Arrow 12.7 6.55 12.95 6.55
New-Arrow 12.7 8.35 12.95 8.35

# 后端 -> 数据层 垂直箭头
New-Arrow 2.44 8.9 2.44 9.22
New-Arrow 6.35 8.9 6.35 9.22
New-Arrow 10.26 8.9 10.26 9.22

# ============ 6. 数据与存储层 ============
$dataX = 0.35; $dataTop = 9.22; $dataW = 12.35; $dataH = 1.43  # 9.22..10.65
New-Container $dataX $dataTop $dataW $dataH | Out-Null
New-Label 0.55 ($dataTop + 0.05) 8 0.3 $txt.dataBand 10.5 $cDataLn 0 | Out-Null

$dm = @(
    @{ t = $txt.pg1; d = $txt.pg2 },
    @{ t = $txt.redis1; d = $txt.redis2 },
    @{ t = $txt.file1; d = $txt.file2 }
)
$dw = 3.78; $dg = 0.13; $dx0 = 0.55; $dh = 0.85
for ($i = 0; $i -lt 3; $i++) {
    New-TextBox ($dx0 + $i * ($dw + $dg)) 9.55 $dw $dh ($dm[$i].t + "`n" + $dm[$i].d) 8.5 $cData $cDataLn | Out-Null
}

# ============ 7. 部署与设计要点（底部说明） ============
New-TextBox 0.35 10.95 16.5 0.35 $txt.deploy 9 $cGrayFill $cGrayLn | Out-Null
$f = New-TextBox 0.35 11.45 16.5 0.6 $txt.footer 8.5 $cGrayFill $cGrayLn 0.75
$f.CellsU("Para.HorzAlign").FormulaU = "0"

# ============ 保存 ============
$outDir = "E:\InkLight\code\docs\architecture"
$vsdxPath = Join-Path $outDir "InkLight-系统架构图.vsdx"
$pdfPath = Join-Path $outDir "InkLight-系统架构图.pdf"
$doc.SaveAs($vsdxPath)
Write-Output "VSDX saved: $vsdxPath"
try {
    $doc.ExportAsFixedFormat(1, $pdfPath, 1, 0)
    Write-Output "PDF exported: $(Test-Path $pdfPath)"
} catch {
    Write-Output ("PDF export failed: " + $_.Exception.Message)
}

# 清理本次运行产生的其它未保存文档（保留已保存的成品文档打开）
foreach ($d in @($visio.Documents)) {
    if ($d.Name -ne $doc.Name -and $d.Path -eq "") {
        try { $d.Close(0) } catch { }
    }
}
Write-Output "PID=$($visio.ProcessID)"
Write-Output "DONE_OK"
