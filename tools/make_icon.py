"""Build assets/straks.ico: a warm yellow clock with a small marker."""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "straks.ico")


def render(size: int) -> Image.Image:
    s = 8  # supersampling
    n = size * s
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = n * 0.04
    # disc
    d.ellipse((pad, pad, n - pad, n - pad), fill=(250, 186, 48, 255))
    d.ellipse((n * 0.14, n * 0.14, n * 0.86, n * 0.86), fill=(255, 247, 220, 255))
    # hands: "straks" (Dutch for "later") = a little past now
    cx = cy = n / 2
    w = max(2, int(n * 0.07))
    d.line((cx, cy, cx, n * 0.26), fill=(70, 45, 0, 255), width=w)
    d.line((cx, cy, n * 0.70, n * 0.58), fill=(70, 45, 0, 255), width=w)
    d.ellipse((cx - w, cy - w, cx + w, cy + w), fill=(70, 45, 0, 255))
    # marker top-right: the moment "later"
    d.ellipse((n * 0.70, n * 0.20, n * 0.80, n * 0.30), fill=(220, 60, 40, 255))
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    frames = [render(sz) for sz in sizes]
    frames[-1].save(OUT, format="ICO", sizes=[(sz, sz) for sz in sizes],
                    append_images=frames[:-1])
    print("written:", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
