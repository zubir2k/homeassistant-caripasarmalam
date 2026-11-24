"""Generate official Home Assistant brand icons and logos for CariPasarMalam using mdi:store."""
import math
from pathlib import Path
import cairo

BRAND_DIR = Path(__file__).parent

# Signature Teal from pasarmalam.app
TEAL_RGB = (0 / 255, 162 / 255, 154 / 255)       # #00a29a
NAVY_RGB = (15 / 255, 23 / 255, 42 / 255)       # #0f172a
WHITE_RGB = (255 / 255, 255 / 255, 255 / 255)
SUBTITLE_LIGHT = (100 / 255, 116 / 255, 139 / 255)  # #64748b
SUBTITLE_DARK = (148 / 255, 163 / 255, 184 / 255)   # #94a3b8


def draw_mdi_store_path(ctx: cairo.Context) -> None:
    """Draw the standard mdi:store 24x24 path."""
    # Window / Counter opening
    ctx.move_to(12, 18)
    ctx.line_to(6, 18)
    ctx.line_to(6, 14)
    ctx.line_to(12, 14)
    ctx.close_path()

    # Main store building & pillars
    ctx.move_to(21, 14)
    ctx.line_to(21, 12)
    ctx.line_to(20, 7)
    ctx.line_to(4, 7)
    ctx.line_to(3, 12)
    ctx.line_to(3, 14)
    ctx.line_to(4, 14)
    ctx.line_to(4, 20)
    ctx.line_to(14, 20)
    ctx.line_to(14, 14)
    ctx.line_to(18, 14)
    ctx.line_to(18, 20)
    ctx.line_to(20, 20)
    ctx.line_to(20, 14)
    ctx.close_path()

    # Roof sign / top bar
    ctx.move_to(20, 4)
    ctx.line_to(4, 4)
    ctx.line_to(4, 6)
    ctx.line_to(20, 6)
    ctx.close_path()


def draw_squircle(ctx: cairo.Context, x: float, y: float, w: float, h: float, r: float) -> None:
    """Draw a smooth rounded rectangle / squircle."""
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def draw_icon(ctx: cairo.Context, size: int) -> None:
    """Draw the CariPasarMalam mdi:store emblem on a square of given size."""
    scale = size / 512.0
    ctx.save()
    ctx.scale(scale, scale)

    # 1. Signature Teal Squircle Base
    ctx.set_source_rgb(*TEAL_RGB)
    draw_squircle(ctx, 24, 24, 464, 464, 108)
    ctx.fill()

    # 2. Centered White mdi:store Glyph
    ctx.save()
    # At scale 18, 24x24 glyph has center at (12*18=216).
    # To center in 512x512: offset is (512 - 24*18)/2 = (512 - 432)/2 = 40.
    ctx.translate(40, 40)
    ctx.scale(18, 18)
    ctx.set_source_rgb(*WHITE_RGB)
    draw_mdi_store_path(ctx)
    ctx.fill()
    ctx.restore()

    ctx.restore()


def draw_logo(ctx: cairo.Context, width: int, height: int, dark: bool = False) -> None:
    """Draw wide horizontal brand logo with mdi:store tile and clean typography."""
    scale = height / 160.0
    ctx.save()
    ctx.scale(scale, scale)

    # 1. Left mdi:store Tile (128x128)
    ctx.save()
    ctx.translate(16, 16)
    ctx.set_source_rgb(*TEAL_RGB)
    draw_squircle(ctx, 0, 0, 128, 128, 30)
    ctx.fill()

    # Inside mdi:store glyph
    ctx.translate(10, 10)
    ctx.scale(4.5, 4.5)
    ctx.set_source_rgb(*WHITE_RGB)
    draw_mdi_store_path(ctx)
    ctx.fill()
    ctx.restore()

    # 2. Right Typography
    ctx.select_font_face("Segoe UI", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(52)

    base_y = 90
    cur_x = 168

    # "Cari" (Navy or White)
    if dark:
        ctx.set_source_rgb(*WHITE_RGB)
    else:
        ctx.set_source_rgb(*NAVY_RGB)
    ctx.move_to(cur_x, base_y)
    ctx.show_text("Cari")
    cur_x += ctx.text_extents("Cari").x_advance

    # "PasarMalam" (Teal)
    ctx.set_source_rgb(*TEAL_RGB)
    ctx.move_to(cur_x, base_y)
    ctx.show_text("PasarMalam")

    # Subtitle
    ctx.select_font_face("Segoe UI", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(14)
    if dark:
        ctx.set_source_rgb(*SUBTITLE_DARK)
    else:
        ctx.set_source_rgb(*SUBTITLE_LIGHT)
    ctx.move_to(170, base_y + 30)
    ctx.show_text("NIGHT MARKET TRACKER FOR HOME ASSISTANT")

    ctx.restore()


def main():
    print("Generating CariPasarMalam mdi:store brand assets...")

    # 1. icon.png (256x256)
    s256 = cairo.ImageSurface(cairo.FORMAT_ARGB32, 256, 256)
    draw_icon(cairo.Context(s256), 256)
    s256.write_to_png(str(BRAND_DIR / "icon.png"))
    print("✓ Created icon.png (256x256) [mdi:store]")

    # 2. icon@2x.png (512x512)
    s512 = cairo.ImageSurface(cairo.FORMAT_ARGB32, 512, 512)
    draw_icon(cairo.Context(s512), 512)
    s512.write_to_png(str(BRAND_DIR / "icon@2x.png"))
    print("✓ Created icon@2x.png (512x512) [mdi:store]")

    # 3. logo.png (512x128)
    s_logo = cairo.ImageSurface(cairo.FORMAT_ARGB32, 512, 128)
    draw_logo(cairo.Context(s_logo), 512, 128, dark=False)
    s_logo.write_to_png(str(BRAND_DIR / "logo.png"))
    print("✓ Created logo.png (512x128)")

    # 4. logo@2x.png (1024x256)
    s_logo2x = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1024, 256)
    draw_logo(cairo.Context(s_logo2x), 1024, 256, dark=False)
    s_logo2x.write_to_png(str(BRAND_DIR / "logo@2x.png"))
    print("✓ Created logo@2x.png (1024x256)")

    # 5. dark_logo.png (512x128)
    s_dlogo = cairo.ImageSurface(cairo.FORMAT_ARGB32, 512, 128)
    draw_logo(cairo.Context(s_dlogo), 512, 128, dark=True)
    s_dlogo.write_to_png(str(BRAND_DIR / "dark_logo.png"))
    print("✓ Created dark_logo.png (512x128)")

    # 6. dark_logo@2x.png (1024x256)
    s_dlogo2x = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1024, 256)
    draw_logo(cairo.Context(s_dlogo2x), 1024, 256, dark=True)
    s_dlogo2x.write_to_png(str(BRAND_DIR / "dark_logo@2x.png"))
    print("✓ Created dark_logo@2x.png (1024x256)")

    print("All mdi:store brand assets updated successfully!")


if __name__ == "__main__":
    main()
