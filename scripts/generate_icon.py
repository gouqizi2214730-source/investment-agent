from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
SIZE = 1024
ICO_SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
RESAMPLE = getattr(getattr(Image, "Resampling", Image), "LANCZOS")


def _lerp(a: int, b: int, t: float) -> int:
    return int(round(a + (b - a) * t))


def _create_gradient_bg(size: int) -> Image.Image:
    bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bg)
    # Diagonal deep space blue (#0B0F19 -> #172554) to emerald accent (#064E3B -> #10B981)
    for y in range(size):
        ty = y / (size - 1)
        r = _lerp(11, 16, ty * 0.85)
        g = _lerp(15, 185, (ty ** 1.35) * 0.65)
        b = _lerp(25, 129, ty * 0.9)
        if ty < 0.55:
            b = _lerp(35, 95, ty / 0.55)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))

    mask = Image.new("L", (size, size), 0)
    mdraw = ImageDraw.Draw(mask)
    pad = 48
    radius = 220
    mdraw.rounded_rectangle([pad, pad, size - pad, size - pad], radius=radius, fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(bg, (0, 0), mask)
    return out


def build_icon() -> Image.Image:
    img = _create_gradient_bg(SIZE)
    draw = ImageDraw.Draw(img)

    # Subtle outer glass border
    draw.rounded_rectangle(
        [52, 52, SIZE - 52, SIZE - 52],
        radius=216,
        outline=(56, 189, 248, 120),
        width=10,
    )

    # Subtle horizontal grid lines
    for gy in (300, 480, 660, 820):
        draw.line([(160, gy), (864, gy)], fill=(148, 163, 184, 38), width=4)

    # Stylized candlesticks
    candles = [
        (230, 560, 740, 600, 700, (56, 189, 248, 175)),
        (365, 440, 670, 490, 620, (16, 185, 129, 200)),
        (500, 470, 680, 520, 640, (56, 189, 248, 185)),
        (635, 310, 560, 360, 510, (16, 185, 129, 225)),
        (770, 210, 450, 250, 400, (52, 211, 153, 240)),
    ]
    for cx, wick_top, wick_bot, body_top, body_bot, color in candles:
        draw.line([(cx, wick_top), (cx, wick_bot)], fill=color, width=14)
        draw.rounded_rectangle(
            [cx - 32, body_top, cx + 32, body_bot],
            radius=14,
            fill=color,
        )

    # Macro trend polyline with glow
    pts = [(210, 700), (365, 550), (500, 595), (635, 385), (805, 235)]
    draw.line(pts, fill=(56, 189, 248, 110), width=42, joint="curve")
    draw.line(pts, fill=(248, 250, 252, 245), width=22, joint="curve")

    # Quant nodes along trend line
    for i, (px, py) in enumerate(pts):
        r_outer = 32 if i in (0, 4) else 26
        r_inner = 16 if i in (0, 4) else 12
        node_color = (16, 185, 129, 255) if i == 4 else (56, 189, 248, 255)
        draw.ellipse([px - r_outer, py - r_outer, px + r_outer, py + r_outer], fill=node_color)
        draw.ellipse([px - r_inner, py - r_inner, px + r_inner, py + r_inner], fill=(255, 255, 255, 255))

    return img


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    master = build_icon()
    png_path = ASSETS_DIR / "icon.png"
    ico_path = ASSETS_DIR / "icon.ico"

    png_img = master.resize((512, 512), RESAMPLE)
    png_img.save(png_path, format="PNG")

    ico_imgs = [master.resize(sz, RESAMPLE) for sz in ICO_SIZES]
    ico_imgs[0].save(
        ico_path,
        format="ICO",
        sizes=ICO_SIZES,
        append_images=ico_imgs[1:],
    )
    print(f"Generated {png_path} and {ico_path}")


if __name__ == "__main__":
    main()
