"""Generate official Home Assistant brand icons and logos for CariPasarMalam using Cairo."""
import math
from pathlib import Path
import cairo

BRAND_DIR = Path(__file__).parent


def draw_icon(ctx: cairo.Context, size: int) -> None:
    """Draw the CariPasarMalam emblem on a square context of given size."""
    scale = size / 512.0
    ctx.save()
    ctx.scale(scale, scale)

    # 1. Squircle background
    r = 108
    x, y, w, h = 24, 24, 464, 464
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()

    # Sky gradient
    pat = cairo.LinearGradient(24, 24, 488, 488)
    pat.add_color_stop_rgb(0.0, 15 / 255, 23 / 255, 42 / 255)    # #0f172a
    pat.add_color_stop_rgb(0.5, 30 / 255, 27 / 255, 75 / 255)   # #1e1b4b
    pat.add_color_stop_rgb(1.0, 9 / 255, 13 / 255, 22 / 255)    # #090d16
    ctx.set_source(pat)
    ctx.fill_preserve()

    # Subtle border
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.12)
    ctx.set_line_width(4)
    ctx.stroke()

    # 2. Night Sky: Crescent Moon
    ctx.save()
    ctx.set_source_rgba(253 / 255, 224 / 255, 71 / 255, 0.92)  # #fde047
    ctx.arc(385, 130, 36, 0, 2 * math.pi)
    ctx.fill()
    # Mask out inner part of moon
    ctx.set_operator(cairo.OPERATOR_CLEAR)
    ctx.arc(370, 115, 34, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()

    # Stars
    ctx.set_source_rgba(1.0, 1.0, 1.0, 0.8)
    for sx, sy, sr in [(120, 110, 3), (160, 85, 2), (310, 100, 2.5), (430, 190, 2)]:
        ctx.arc(sx, sy, sr, 0, 2 * math.pi)
        ctx.fill()

    # 3. Ambient Stall Glow
    glow = cairo.RadialGradient(256, 300, 10, 256, 300, 170)
    glow.add_color_stop_rgba(0.0, 254 / 255, 240 / 255, 138 / 255, 0.6)
    glow.add_color_stop_rgba(0.4, 245 / 255, 158 / 255, 11 / 255, 0.25)
    glow.add_color_stop_rgba(1.0, 245 / 255, 158 / 255, 11 / 255, 0.0)
    ctx.set_source(glow)
    ctx.arc(256, 300, 170, 0, 2 * math.pi)
    ctx.fill()

    # 4. Stall Structure: Poles
    ctx.set_source_rgb(203 / 255, 213 / 255, 225 / 255)  # #cbd5e1
    ctx.set_line_width(8)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(110, 240)
    ctx.line_to(110, 400)
    ctx.stroke()
    ctx.move_to(402, 240)
    ctx.line_to(402, 400)
    ctx.stroke()

    # 5. Stall Counter Table
    ctx.set_source_rgb(30 / 255, 41 / 255, 59 / 255)  # #1e293b
    ctx.rectangle(88, 360, 336, 48)
    ctx.fill()
    ctx.set_source_rgb(51 / 255, 65 / 255, 85 / 255)  # #334155
    ctx.set_line_width(4)
    ctx.rectangle(88, 360, 336, 48)
    ctx.stroke()

    # Amber Table Runner
    ctx.set_source_rgba(245 / 255, 158 / 255, 11 / 255, 0.85)
    ctx.rectangle(100, 370, 312, 12)
    ctx.fill()

    # Grill / Food Platter
    ctx.set_source_rgb(71 / 255, 85 / 255, 105 / 255)
    ctx.rectangle(180, 348, 152, 14)
    ctx.fill()

    # Skewers (Satay / Night market food)
    ctx.set_line_width(4)
    for x1, y1, x2, y2, color in [
        (210, 334, 230, 350, (251 / 255, 191 / 255, 36 / 255)),
        (230, 330, 245, 350, (249 / 255, 115 / 255, 22 / 255)),
        (250, 332, 260, 350, (251 / 255, 191 / 255, 36 / 255)),
        (270, 330, 275, 350, (249 / 255, 115 / 255, 22 / 255)),
        (290, 334, 290, 350, (251 / 255, 191 / 255, 36 / 255)),
    ]:
        ctx.set_source_rgb(*color)
        ctx.move_to(x1, y1)
        ctx.line_to(x2, y2)
        ctx.stroke()

    # Festoon hanging light string
    ctx.set_source_rgb(100 / 255, 116 / 255, 139 / 255)
    ctx.set_line_width(3)
    ctx.move_to(110, 240)
    ctx.curve_to(183, 260, 329, 260, 402, 240)
    ctx.stroke()

    # Bulbs
    for bx, by in [(180, 254), (256, 250), (332, 254)]:
        ctx.set_source_rgb(254 / 255, 240 / 255, 138 / 255)
        ctx.arc(bx, by, 7.5, 0, 2 * math.pi)
        ctx.fill()

    # 6. Canopy Roof Stripes
    # Alternating Amber & Teal stripes converging to peak (256, 140)
    peak_x, peak_y = 256, 140
    stripes = [
        (72, 126, (245 / 255, 158 / 255, 11 / 255)),   # Amber
        (126, 190, (13 / 255, 148 / 255, 136 / 255)),  # Teal
        (190, 256, (245 / 255, 158 / 255, 11 / 255)),  # Amber
        (256, 322, (13 / 255, 148 / 255, 136 / 255)),  # Teal
        (322, 386, (245 / 255, 158 / 255, 11 / 255)),  # Amber
        (386, 440, (13 / 255, 148 / 255, 136 / 255)),  # Teal
    ]

    for x_start, x_end, col in stripes:
        ctx.set_source_rgb(*col)
        ctx.move_to(x_start, 236)
        ctx.line_to(x_end, 236)
        ctx.line_to(peak_x, peak_y)
        ctx.close_path()
        ctx.fill()

    # Scalloped valance (curved frills)
    ctx.set_source_rgb(248 / 255, 250 / 255, 252 / 255)  # #f8fafc
    ctx.move_to(72, 236)
    frill_w = (440 - 72) / 10  # 36.8
    for i in range(10):
        fx1 = 72 + i * frill_w
        fx2 = fx1 + frill_w
        fmid = (fx1 + fx2) / 2
        ctx.curve_to(fx1 + 5, 252, fx2 - 5, 252, fx2, 236)
    ctx.line_to(440, 232)
    ctx.line_to(72, 232)
    ctx.close_path()
    ctx.fill()

    # 7. GPS Location Pin at Roof Apex
    pin_x, pin_y = 256, 122
    ctx.save()
    ctx.set_source_rgb(225 / 255, 29 / 255, 72 / 255)  # #e11d48
    # Teardrop pin
    ctx.arc(pin_x, pin_y - 20, 24, math.pi * 0.75, math.pi * 2.25)
    ctx.line_to(pin_x, pin_y + 24)
    ctx.close_path()
    ctx.fill_preserve()
    ctx.set_source_rgb(1.0, 1.0, 1.0)
    ctx.set_line_width(4)
    ctx.stroke()

    # White inner dot
    ctx.set_source_rgb(1.0, 1.0, 1.0)
    ctx.arc(pin_x, pin_y - 20, 9, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()

    ctx.restore()


def draw_logo(ctx: cairo.Context, width: int, height: int, dark: bool = False) -> None:
    """Draw wide horizontal brand logo with icon mark and typography."""
    scale = height / 160.0
    ctx.save()
    ctx.scale(scale, scale)

    # 1. Draw scaled icon mark on left
    ctx.save()
    ctx.translate(16, 16)
    ctx.scale(128 / 512, 128 / 512)
    draw_icon(ctx, 512)
    ctx.restore()

    # 2. Text layout
    # "Cari" + "Pasar" + "Malam"
    ctx.select_font_face("Segoe UI", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(52)

    # Text Y baseline
    base_y = 90
    cur_x = 168

    # "Cari"
    if dark:
        ctx.set_source_rgb(248 / 255, 250 / 255, 252 / 255)  # #f8fafc (white)
    else:
        ctx.set_source_rgb(15 / 255, 23 / 255, 42 / 255)     # #0f172a (navy)
    ctx.move_to(cur_x, base_y)
    ctx.show_text("Cari")
    cur_x += ctx.text_extents("Cari").x_advance

    # "Pasar" (Teal)
    ctx.set_source_rgb(0 / 255, 162 / 255, 154 / 255)       # #00a29a
    ctx.move_to(cur_x, base_y)
    ctx.show_text("Pasar")
    cur_x += ctx.text_extents("Pasar").x_advance

    # "Malam" (Amber)
    ctx.set_source_rgb(245 / 255, 158 / 255, 11 / 255)      # #f59e0b
    ctx.move_to(cur_x, base_y)
    ctx.show_text("Malam")

    # Subtitle
    ctx.select_font_face("Segoe UI", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(14)
    if dark:
        ctx.set_source_rgb(148 / 255, 163 / 255, 184 / 255)  # #94a3b8
    else:
        ctx.set_source_rgb(100 / 255, 116 / 255, 139 / 255)  # #64748b
    ctx.move_to(170, base_y + 30)
    ctx.show_text("NIGHT MARKET TRACKER FOR HOME ASSISTANT")

    ctx.restore()


def main():
    print("Generating CariPasarMalam official brand assets...")

    # 1. icon.png (256x256)
    s256 = cairo.ImageSurface(cairo.FORMAT_ARGB32, 256, 256)
    draw_icon(cairo.Context(s256), 256)
    s256.write_to_png(str(BRAND_DIR / "icon.png"))
    print("✓ Created icon.png (256x256)")

    # 2. icon@2x.png (512x512)
    s512 = cairo.ImageSurface(cairo.FORMAT_ARGB32, 512, 512)
    draw_icon(cairo.Context(s512), 512)
    s512.write_to_png(str(BRAND_DIR / "icon@2x.png"))
    print("✓ Created icon@2x.png (512x512)")

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

    print("All brand assets generated successfully!")


if __name__ == "__main__":
    main()
