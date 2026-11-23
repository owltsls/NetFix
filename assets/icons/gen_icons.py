# -*- coding: utf-8 -*-
"""按 netfix-icon.svg 的几何参数，用 Pillow 高分辨率绘制并降采样导出多尺寸图标。"""
from PIL import Image, ImageDraw
import os

OUT = os.path.dirname(os.path.abspath(__file__))
S = 4          # 超采样倍数
BASE = 512     # 设计基准尺寸

BG   = (59, 110, 168, 255)     # #3B6EA8 沉稳蓝
WHITE= (255, 255, 255, 255)
LINE = (255, 255, 255, 220)    # 链路半透明白
TEAL = (94, 234, 212, 255)     # #5EEAD4 青绿对勾

def sc(p):  # 设计坐标 -> 超采样坐标
    return tuple(int(v * S) for v in p)

def bezier(p0, p1, p2, p3, n=30):
    pts = []
    for i in range(n + 1):
        t = i / n
        mt = 1 - t
        x = mt**3*p0[0] + 3*mt**2*t*p1[0] + 3*mt*t**2*p2[0] + t**3*p3[0]
        y = mt**3*p0[1] + 3*mt**2*t*p1[1] + 3*mt*t**2*p2[1] + t**3*p3[1]
        pts.append(sc((x, y)))
    return pts

def draw_icon(size):
    C = BASE * S
    img = Image.new("RGBA", (C, C), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # background 圆角方形
    d.rounded_rectangle([0, 0, C-1, C-1], radius=104*S, fill=BG)

    # main 盾牌轮廓（无填充，白描边）
    shield = [sc((256, 84)), sc((388, 134)), sc((388, 244))]
    shield += bezier((388,244), (388,330), (330,392), (256,424))
    shield += bezier((256,424), (182,392), (124,330), (124,244))
    shield += [sc((124, 134))]
    d.line(shield + [shield[0]], fill=WHITE, width=26*S, joint="curve")

    # accent 左/右链路
    d.line([sc((174,258)), sc((222,258))], fill=LINE, width=20*S)
    d.line([sc((290,258)), sc((338,258))], fill=LINE, width=20*S)
    for cx in (174, 222, 290, 338):
        r = 10*S
        x, y = sc((cx, 258))
        d.ellipse([x-r, y-r, x+r, y+r], fill=LINE)

    # accent 桥接对勾
    d.line([sc((214,262)), sc((242,290)), sc((300,226))], fill=TEAL, width=24*S, joint="curve")
    for cx, cy in ((214,262), (300,226)):
        r = 12*S
        x, y = sc((cx, cy))
        d.ellipse([x-r, y-r, x+r, y+r], fill=TEAL)

    return img.resize((size, size), Image.LANCZOS)

sizes = [16, 32, 48, 64, 128, 256, 512, 1024]
master = {}
for s in sizes:
    im = draw_icon(s)
    path = os.path.join(OUT, f"netfix-icon-{s}.png")
    im.save(path)
    master[s] = im
    print("saved", path, im.size)

# Windows 多尺寸 ico
ico_path = os.path.join(OUT, "app.ico")
master[256].save(ico_path, format="ICO",
                 sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
print("saved", ico_path)
