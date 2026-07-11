# -*- coding: utf-8 -*-
"""
生成 Claude Dock 托盘 + EXE 图标（多分辨率 .ico）
- 256×256 主图（高 DPI 显示需要）
- 16/32/48/64/128/256 多分辨率（任务栏 + Alt-Tab + 资源管理器全支持）
- iOS 蓝渐变 (#0A84FF) + ◐ 半圆符号
"""
import os
from PIL import Image, ImageDraw

SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dock.ico')


def render(size: int) -> Image.Image:
    """画一张 size×size 的图标（透明底 + 蓝渐变圆 + 半圆符号）。"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 256.0

    # 径向蓝色圆背景
    for r in range(int(128 * s), 0, -1):
        alpha = int(255 * (1 - r / (128 * s)) * 0.95)
        if alpha < 0:
            alpha = 0
        d.ellipse([128 * s - r, 128 * s - r, 128 * s + r, 128 * s + r],
                  fill=(10, 132, 255, alpha))

    # ◐ 半圆：白色外环 + 填充左半
    pad = 48 * s
    d.ellipse([pad, pad, 256 * s - pad, 256 * s - pad],
              outline=(255, 255, 255, 235), width=max(1, int(10 * s)))
    d.chord([pad, pad, 256 * s - pad, 256 * s - pad],
            start=180, end=360, fill=(255, 255, 255, 235))
    return img


def main():
    images = [render(s) for s, _ in SIZES]
    images[0].save(OUT, format='ICO', sizes=SIZES,
                   append_images=images[1:])
    print(f'OK {OUT}  ({os.path.getsize(OUT)} bytes, {len(SIZES)} sizes)')


if __name__ == '__main__':
    main()