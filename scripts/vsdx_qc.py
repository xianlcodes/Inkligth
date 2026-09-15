# -*- coding: utf-8 -*-
"""VSDX 几何质检：校验每个图形文字是否超出矩形边界、色块是否重叠、内容是否齐全"""
import zipfile, re, math
from xml.etree import ElementTree as ET

NS = {'v': 'http://schemas.microsoft.com/office/visio/2012/main',
      'x': 'http://schemas.microsoft.com/office/visio/2012/extension'}
z = zipfile.ZipFile(r'E:\InkLight\code\docs\architecture\InkLight-系统架构图.vsdx')
root = ET.fromstring(z.read('visio/pages/page1.xml'))

def cell(sh, name, default=None):
    for c in sh.findall('v:Cell', NS):
        if c.get('N') == name:
            return c.get('V', c.get('F', default))
    return default

def formula_to_in(v):
    """把 '2.87 in'/'1.234' 之类的值转为英寸数"""
    if v is None: return 0.0
    m = re.match(r'(-?\d+(?:\.\d+)?)\s*(in|mm|cm|pt)?', v.strip())
    if not m: return 0.0
    val = float(m.group(1)); u = m.group(2)
    return {'in':1.0,'mm':1/25.4,'cm':1/2.54,'pt':1/72}.get(u,1.0)*val

def text_of(sh):
    t = sh.find('v:Text', NS)
    if t is None: return ''
    # 去掉 XML 标签（CP/Secu 等），保留文本
    s = ET.tostring(t, encoding='unicode')
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('&#10;', '\n').replace('&#xA;', '\n').replace('&amp;','&').replace('&lt;','<').replace('&gt;','>')
    return s

shapes = []
for sh in root.iter('{%s}Shape' % NS['v']):
    w = formula_to_in(cell(sh,'Width')); h = formula_to_in(cell(sh,'Height'))
    pinx = formula_to_in(cell(sh,'PinX')); piny = formula_to_in(cell(sh,'PinY'))
    locx = formula_to_in(cell(sh,'LocPinX')) or w/2; locy = formula_to_in(cell(sh,'LocPinY')) or h/2
    fill = cell(sh,'FillForegnd')
    csize = formula_to_in(cell(sh,'Char.Size'))
    if csize == 0.0: csize = None
    txt = text_of(sh)
    shapes.append(dict(id=sh.get('ID'), w=w, h=h,
                       x0=pinx-locx, y0=piny-locy, x1=pinx-locx+w, y1=piny-locy+h,
                       fill=fill, csize=csize, txt=txt))
print('total shapes:', len(shapes))

def est_width(line, size):
    # 中文≈1.0em, 全角标点≈1.0em, 半角≈0.52em
    w = 0.0
    for ch in line:
        o = ord(ch)
        if o > 0x2E7F or ch in '，。；：、（）《》「」——…·％＋': w += 1.0
        else: w += 0.52
    return w * size  # 英寸

issues = []
page_w, page_h = 17.2, 12.2
for s in shapes:
    txt = s['txt']
    if not txt or not s['csize']: continue
    lines = txt.split('\n')
    if len(lines) == 1 and txt.strip() == '': continue
    est_h = len(lines) * s['csize'] * 1.25
    if est_h > s['h'] + 0.06:
        issues.append(('V_OVERFLOW', s['id'], s['txt'][:24].replace('\n','/'), 'h=%.2f est_h=%.2f' % (s['h'], est_h)))
    for ln in lines:
        est_w = est_width(ln, s['csize'])
        if est_w > s['w'] + 0.05:
            issues.append(('H_OVERFLOW', s['id'], ln[:30], 'w=%.2f est=%.2f' % (s['w'], est_w)))

# 检查含文字的图形是否超出页面
for s in shapes:
    if s['txt']:
        if s['x0'] < -0.01 or s['y0'] < -0.01 or s['x1'] > page_w + 0.01 or s['y1'] > page_h + 0.01:
            issues.append(('PAGE_OUT', s['id'], s['txt'][:24].replace('\n','/'), 'rect=(%.2f,%.2f,%.2f,%.2f)' % (s['x0'],s['y0'],s['x1'],s['y1'])))

# 实心色块之间的重叠（非容器）
solid = [s for s in shapes if s['fill'] and s['h'] > 0.1]
for i in range(len(solid)):
    for j in range(i+1, len(solid)):
        a,b = solid[i],solid[j]
        ox = min(a['x1'],b['x1']) - max(a['x0'],b['x0'])
        oy = min(a['y1'],b['y1']) - max(a['y0'],b['y0'])
        if ox > 0.05 and oy > 0.05:
            issues.append(('BOX_OVERLAP', a['id'], b['id'], 'a=%s b=%s ox=%.2f oy=%.2f' % (a['txt'][:10].replace('\n','/'), b['txt'][:10].replace('\n','/'), ox, oy)))

print('issues:', len(issues))
for it in issues[:40]:
    print(it)
print('---- all texts ----')
for s in sorted(shapes, key=lambda s: -s['y0']):
    if s['txt']:
        print('id=%s y=%.2f h=%.2f csize=%s | %s' % (s['id'], s['y0'], s['h'], s['csize'], s['txt'][:60].replace('\n',' ⏎ ')))
EOF_MARK = True
