import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parent.parent / "rsl" / "ui" / "backdrop.jpg"
WIDTH, HEIGHT = 1600, 900
SEED = 41
TOP, BOTTOM = 118, 74
CEILING = 112
SOFTNESS = 0.35
TINT = (0.93, 1.0, 1.05)


def gradient():
    ramp = Image.linear_gradient("L").resize((WIDTH, HEIGHT))
    return ramp.point(lambda v: int(TOP - (TOP - BOTTOM) * v / 255))


def haze(rng):
    layer = Image.new("L", (WIDTH, HEIGHT), 128)
    canvas = ImageDraw.Draw(layer)
    for _ in range(110):
        radius = rng.randint(70, 380)
        x = rng.randint(-200, WIDTH + 200)
        y = rng.randint(-200, HEIGHT + 200)
        canvas.ellipse((x - radius, y - radius * 0.6, x + radius, y + radius * 0.6), fill=rng.randint(92, 164))
    return layer.filter(ImageFilter.GaussianBlur(80)).point(lambda v: v // 2)


def compress(value):
    if value > CEILING:
        value = CEILING + (value - CEILING) * SOFTNESS
    return int(value * 0.95 + 12)


def main():
    rng = random.Random(SEED)
    light = ImageChops.add(gradient(), haze(rng), scale=1.0, offset=-64).point(compress)
    channels = [light.point(lambda v, k=k: min(255, int(v * k))) for k in TINT]
    image = Image.merge("RGB", channels).filter(ImageFilter.GaussianBlur(1))
    image.save(OUT, quality=84, optimize=True, progressive=True)
    print(OUT)


if __name__ == "__main__":
    main()
