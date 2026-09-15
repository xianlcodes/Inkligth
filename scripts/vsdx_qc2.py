# -*- coding: utf-8 -*-
"""VSDX 几何质检 v2：正确坐标系 + 逐行字号"""
import zipfile, re
from xml.etree import ElementTree as ET

NS = {'v': 'http://schemas.microsoft.com/office/visio/2012/main'}
z = zipfile.ZipFile(r'E:\InkLight\code\docs\architecture\InkLight-系统架构图.vsdx')
root = ET.fromstring(z.read('visio/pages/page1.xml'))

def cval(sh, name):
    for c in sh.findall('v:Cell', NS):
        if c.get('N') == name:
            return c.get('V', c.get('F'))
    return None

def num(v):
    if v is None: return 0.0
    m = re.match(r'(-?\d+(?:\.\d+)?)', v.strip())
    return float(m.group(1)) if m else 0.0

def text_of(sh):
    t = sh.find('v:Text', NS)
    if t is None: return ''
    s = ET.tostring(t, encoding='unicode')
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('&#10;', '\n').replace('&#xA;', '\n')
    s = s.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    return s

def font_size(sh):
    # 1) Character 段第一个有值的行
    sec = sh.find('v:Section[@N="Character"]', NS)
    if sec is not None:
        for row in sec.findall('v:Row', NS):
            sz = None
            for c in row.findall('v:Cell', NS):
                if c.get('N') == 'Char.Size': sz = num(c.get('V', c.get('F')))
            if sz: return sz
    # 2) 形状级 Char.Size（部分工具写法）
    for c in sh.findall('v:Cell', NS):
        if c.get('N') == 'Char.Size':
            v = num(c.get('V', c.get('F')))
            if v: return v
    return None

def width_est(line, sz):
    w = 0.0
    for ch in line:
        o = ord(ch)
        if o > 0x2E7F or ch in '，。；：、（）《》「」——…·%＋': w += 1.0
        else: w += 0.52
    return w * sz

PAGE_W, PAGE_H = 17.2, 12.2
shapes = []
for sh in root.iter('{%s}Shape' % NS['v']):
    w = num(cval(sh, 'Width')); h = num(cval(sh, 'Height'))
    pinx = num(cval(sh, 'PinX'))
    pinYraw = num(cval(sh, 'PinY'))
    locx = num(cval(sh, 'LocPinX')) or w/2
    locy = num(cval(sh, 'LocPinY')) or h/2
    # 坐标系: realTop = -(PinY - LocPinY)
    realTop = -(pinYraw - locy)
    fill = cval(sh, 'FillForegnd')
    shapes.append(dict(id=sh.get('ID'), w=w, h=h, x0=pinx-locx, top=realTop,
                       fill=fill, sz=font_size(sh), txt=text_of(sh)))
print('shapes:', len(shapes))

issues = []
for s in shapes:
    txt, sz = s['txt'], s['sz']
    if not txt.strip() or not sz: continue
    lines = txt.split('\n')
    est_h = len(lines) * sz * 1.25
    if est_h > s['h'] + 0.05:
        issues.append(('V_OVERFLOW', s['id'], repr(txt[:22]), 'h=%.2f est=%.2f sz=%s' % (s['h'], est_h, sz)))
    for ln in lines:
        ew = width_est(ln, sz)
        if ew > s['w'] - 0.12 + 0.001:
            issues.append(('H_OVERFLOW', s['id'], repr(ln[:30]), 'w=%.2f est=%.2f sz=%s' % (s['w'], ew, sz)))
    # 页面越界
    if s['x0'] < -0.02 or s['x0']+s['w'] > PAGE_W+0.02 or s['top'] < -0.02 or s['top']+s['h'] > PAGE_H+0.02:
        issues.append(('PAGE_OUT', s['id'], repr(txt[:16]), 'rect=(%.2f,%.2f,%.2f,%.2f)' % (s['x0'], s['top'], s['x0']+s['w'], s['top']+s['h'])))

solid = [s for s in shapes if s['fill'] and s['txt'].strip()]
for i in range(len(solid)):
    for j in range(i+1, len(solid)):
        a, b = solid[i], solid[j]
        ox = min(a['x0']+a['w'], b['x0']+b['w']) - max(a['x0'], b['x0'])
        oy = min(a['top']+a['h'], b['top']+b['h']) - max(a['top'], b['top'])
        if ox > 0.03 and oy > 0.03:
            issues.append(('BOX_OVERLAP', a['id'], b['id'],
                           '%s|%s ox=%.2f oy=%.2f' % (a['txt'][:12].replace('\n','/'), b['txt'][:12].replace('\n','/'), ox, oy)))

print('issues:', len(issues))
for it in issues[:40]: print(it)
