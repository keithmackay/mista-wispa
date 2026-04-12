"""Generate PNG icons from the SVG designs.

The menu bar icon is a template image (black on transparent).
The app icon has a dark background with white lines.

Both use the MW zigzag polyline design.

Usage: uv run python scripts/generate_icons.py
"""
from PIL import Image, ImageDraw
import subprocess
import os

RESOURCES = os.path.join(os.path.dirname(__file__), "..", "resources")
os.makedirs(RESOURCES, exist_ok=True)


def draw_mw_lines(draw, size, color, width):
    """Draw the MW zigzag: two connected V shapes."""
    # Scale coordinates from 22x22 reference to target size
    s = size / 22.0
    w = max(1, round(width * s))

    # Top chevron: points=(3,11 3,3 11,11 19,3 19,11)
    top = [(3*s, 11*s), (3*s, 3*s), (11*s, 11*s), (19*s, 3*s), (19*s, 11*s)]
    # Bottom chevron: points=(3,11 3,19 11,11 19,19 19,11)
    bot = [(3*s, 11*s), (3*s, 19*s), (11*s, 11*s), (19*s, 19*s), (19*s, 11*s)]

    draw.line(top, fill=color, width=w, joint="curve")
    draw.line(bot, fill=color, width=w, joint="curve")


def generate_menubar_icons():
    """Generate menu bar template images (black on transparent)."""
    for size, suffix in [(22, ""), (44, "@2x")]:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw_mw_lines(draw, size, color=(0, 0, 0, 255), width=2)
        path = os.path.join(RESOURCES, f"menubar-icon{suffix}.png")
        img.save(path)
        print(f"  Created {path}")


def draw_appicon(draw, size):
    """Draw the app icon MW design (white lines on dark bg)."""
    s = size / 1024.0
    w = max(1, round(70 * s))

    # Top chevron: points=(205,512 205,205 512,512 819,205 819,512)
    top = [(205*s, 512*s), (205*s, 205*s), (512*s, 512*s), (819*s, 205*s), (819*s, 512*s)]
    # Bottom chevron: points=(205,512 205,819 512,512 819,819 819,512)
    bot = [(205*s, 512*s), (205*s, 819*s), (512*s, 512*s), (819*s, 819*s), (819*s, 512*s)]

    draw.line(top, fill=(255, 255, 255, 255), width=w, joint="curve")
    draw.line(bot, fill=(255, 255, 255, 255), width=w, joint="curve")


def draw_rounded_rect(img, radius, fill):
    """Draw a rounded rectangle as the background."""
    size = img.size[0]
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, size-1, size-1], radius=radius, fill=255)
    bg = Image.new("RGBA", (size, size), fill)
    img.paste(bg, mask=mask)


def generate_app_icons():
    """Generate app icon PNGs at all required sizes."""
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    for size in sizes:
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        radius = round(230 * size / 1024.0)
        draw_rounded_rect(img, radius, (10, 10, 10, 255))
        draw = ImageDraw.Draw(img)
        draw_appicon(draw, size)
        path = os.path.join(RESOURCES, f"icon_{size}x{size}.png")
        img.save(path)
        print(f"  Created {path}")


def generate_icns():
    """Create .icns file from PNGs using macOS iconutil."""
    iconset = os.path.join(RESOURCES, "mista-wispa.iconset")
    os.makedirs(iconset, exist_ok=True)

    # iconutil expects specific filenames
    mapping = {
        16: "icon_16x16.png",
        32: "icon_16x16@2x.png",  # 32px is also 16@2x
        64: "icon_32x32@2x.png",  # 64px is also 32@2x
        128: "icon_128x128.png",
        256: "icon_128x128@2x.png",  # 256px is also 128@2x
        512: "icon_256x256@2x.png",  # 512px is also 256@2x
        1024: "icon_512x512@2x.png",  # 1024px is also 512@2x
    }
    # Also need the base sizes
    extra_mapping = {
        32: "icon_32x32.png",
        256: "icon_256x256.png",
        512: "icon_512x512.png",
    }

    for size, filename in {**mapping, **extra_mapping}.items():
        src = os.path.join(RESOURCES, f"icon_{size}x{size}.png")
        dst = os.path.join(iconset, filename)
        if os.path.exists(src):
            img = Image.open(src)
            img.save(dst)

    icns_path = os.path.join(RESOURCES, "mista-wispa.icns")
    result = subprocess.run(
        ["iconutil", "-c", "icns", iconset, "-o", icns_path],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"  Created {icns_path}")
    else:
        print(f"  iconutil failed: {result.stderr}")

    # Clean up iconset directory
    import shutil
    shutil.rmtree(iconset, ignore_errors=True)


if __name__ == "__main__":
    print("Generating menu bar icons...")
    generate_menubar_icons()
    print("Generating app icons...")
    generate_app_icons()
    print("Generating .icns file...")
    generate_icns()
    print("Done!")
