"""Gera o ícone do Markinho (PNG, ICO e ICNS). Uso: python packaging/make_icons.py"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
S = 1024


def font(size: int):
    for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # folha de papel com canto dobrado
    m = 90
    d.rounded_rectangle([m, m, S - m, S - m], radius=150, fill=(37, 99, 235))
    fold = 230
    d.polygon([(S - m - fold, m), (S - m, m + fold), (S - m - fold, m + fold)], fill=(147, 180, 255))
    # "M" e seta para baixo (símbolo do Markdown)
    f = font(470)
    d.text((S * 0.40, S * 0.56), "M", font=f, fill="white", anchor="mm")
    x = S * 0.73
    d.rectangle([x - 45, S * 0.40, x + 45, S * 0.62], fill="white")
    d.polygon([(x - 120, S * 0.60), (x + 120, S * 0.60), (x, S * 0.76)], fill="white")
    return img


def main():
    img = draw()
    img.resize((512, 512), Image.LANCZOS).save(ROOT / "markinho" / "resources" / "markinho.png")
    img.resize((256, 256), Image.LANCZOS).save(ROOT / "packaging" / "icons" / "markinho.png")
    img.save(ROOT / "packaging" / "icons" / "markinho.ico",
             sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    try:
        img.save(ROOT / "packaging" / "icons" / "markinho.icns")
    except Exception as exc:  # noqa: BLE001
        print("ICNS não gerado:", exc)
    print("ícones gerados")


if __name__ == "__main__":
    main()
