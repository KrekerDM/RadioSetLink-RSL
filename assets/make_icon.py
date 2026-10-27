from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "rsl" / "ui" / "logo.ico"
PREVIEW = Path(__file__).resolve().parent / "logo.png"
GROUND = (14, 14, 14, 255)
FRAME = (242, 242, 242, 255)
CROSS = (90, 90, 90, 255)
ACCENT = (255, 204, 0, 255)
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def draw(size):
    image = Image.new("RGBA", (size, size), GROUND)
    canvas = ImageDraw.Draw(image)
    stroke = max(1, round(size / 24))
    inset = max(1, round(size * 0.14))
    low, high = inset, size - inset - 1
    middle = size // 2
    if size >= 32:
        canvas.line((middle, low, middle, high), fill=CROSS, width=max(1, stroke // 2))
        canvas.line((low, middle, high, middle), fill=CROSS, width=max(1, stroke // 2))
    canvas.rectangle((low, low, high, high), outline=FRAME, width=stroke)
    dot = max(3, round(size * 0.2))
    x = round(size * 0.63) - dot // 2
    y = round(size * 0.37) - dot // 2
    canvas.rectangle((x, y, x + dot - 1, y + dot - 1), fill=ACCENT)
    return image


def main():
    images = [draw(size) for size in SIZES]
    images[-1].save(OUT, format="ICO", sizes=[(s, s) for s in SIZES], append_images=images[:-1])
    images[-1].save(PREVIEW)
    print(OUT)


if __name__ == "__main__":
    main()
