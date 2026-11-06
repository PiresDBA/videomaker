# -*- coding: utf-8 -*-
"""
Gera miniatura de engajamento para YouTube a partir de imagem do video.
Uso:
  python scripts/generate_thumbnail.py --image <caminho> --out <saida.jpg>
      --title "Titulo do video" --subtitle "Subtitulo chamativo"
"""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance


def load_font(size, bold=True):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
    ]
    for c in candidates:
        p = Path(c)
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def draw_text_with_outline(draw, xy, text, font, fill, outline, anchor="mm"):
    x, y = xy
    for dx in (-2, -1, 0, 1, 2):
        for dy in (-2, -1, 0, 1, 2):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline, anchor=anchor)
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)


def generate_thumbnail(image_path, output_path, title, subtitle):
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    # YouTube thumbnail recommended: 1280x720 (16:9)
    target_w, target_h = 1280, 720
    img = ImageOps.fit(img, (target_w, target_h), method=Image.LANCZOS)

    # Aumentar contraste e saturacao para chamar atencao
    img = ImageEnhance.Color(img).enhance(1.3)
    img = ImageEnhance.Contrast(img).enhance(1.2)
    img = ImageEnhance.Brightness(img).enhance(1.05)

    draw = ImageDraw.Draw(img)

    # Sobreposicao escurecida na parte inferior para texto destacar
    overlay = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rectangle([0, int(target_h * 0.55), target_w, target_h], fill=(0, 0, 0, 140))
    # Destaque superior
    odraw.rectangle([0, 0, target_w, int(target_h * 0.12)], fill=(0, 0, 0, 120))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Fonte titulo
    title_font = load_font(64, bold=True)
    sub_font = load_font(44, bold=True)

    # Texto titulo (parte superior)
    draw_text_with_outline(
        draw, (target_w // 2, int(target_h * 0.075)),
        title.upper(), title_font, fill=(255, 255, 255), outline=(0, 0, 0),
    )

    # Texto subtitulo (parte inferior)
    draw_text_with_outline(
        draw, (target_w // 2, int(target_h * 0.815)),
        subtitle.upper(), sub_font, fill=(255, 215, 0), outline=(0, 0, 0),
    )

    # Faixa decorativa amarela abaixo do subtitulo
    draw.rectangle([int(target_w * 0.15), int(target_h * 0.885), int(target_w * 0.85), int(target_h * 0.905)], fill=(255, 215, 0))

    img.save(output_path, quality=92)
    print(f"Miniatura salva: {output_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="caminho da imagem base")
    ap.add_argument("--out", required=True, help="caminho de saida da miniatura")
    ap.add_argument("--title", required=True, help="titulo principal da miniatura")
    ap.add_argument("--subtitle", required=True, help="subtitulo chamativo")
    args = ap.parse_args()
    generate_thumbnail(args.image, args.out, args.title, args.subtitle)


if __name__ == "__main__":
    main()
