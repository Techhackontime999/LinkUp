from PIL import Image, ImageDraw
import os

OUT = os.path.dirname(os.path.abspath(__file__))

def create_icon(size, path):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cx = cy = size // 2

    draw = ImageDraw.Draw(img)

    draw.ellipse([0, 0, size - 1, size - 1], fill=(59, 130, 246, 255))

    chain_color = (255, 255, 255, 255)
    w = size * 0.12
    gap = size * 0.08

    left = cx - w - gap * 0.3
    right = cx + w + gap * 0.3
    top = cy - w * 1.8
    bottom = cy + w * 1.8
    mid = (top + bottom) / 2

    draw.arc([left - w, top, left + w, mid], 90, 270, fill=chain_color, width=max(1, int(w * 0.6)))
    draw.arc([right - w, mid, right + w, bottom], 270, 450, fill=chain_color, width=max(1, int(w * 0.6)))

    link_top = top + (mid - top) * 0.6
    link_bot = mid + (bottom - mid) * 0.4
    bar_w = max(1, int(w * 0.35))
    draw.rectangle([left - bar_w, link_top, left + bar_w, link_bot], fill=chain_color)
    draw.rectangle([right - bar_w, link_top, right + bar_w, link_bot], fill=chain_color)

    img.save(path, "PNG")
    print(f"  {path} ({size}x{size})")

sizes = [72, 96, 128, 144, 152, 192, 384, 512]
for s in sizes:
    create_icon(s, os.path.join(OUT, f"icon-{s}x{s}.png"))

print("Done generating icons.")
