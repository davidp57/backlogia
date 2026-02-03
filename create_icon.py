"""
Generate a simple icon for Backlogia desktop app.
Requires: pip install pillow
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_icon():
    """Create a simple gradient icon with the letter 'B'."""
    # Create a 256x256 image with transparent background
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw gradient background circle
    center = size // 2
    radius = size // 2 - 10

    # Create gradient from purple to blue
    for r in range(radius, 0, -1):
        # Calculate color based on radius
        ratio = r / radius
        # Purple to blue gradient
        red = int(102 + (26 - 102) * (1 - ratio))
        green = int(126 + (33 - 126) * (1 - ratio))
        blue = int(234 + (62 - 234) * (1 - ratio))
        color = (red, green, blue, 255)
        draw.ellipse([center - r, center - r, center + r, center + r], fill=color)

    # Draw letter 'B' in the center
    try:
        # Try to use a nice font
        font = ImageFont.truetype("arial.ttf", 140)
    except Exception:
        # Fallback to default font
        font = ImageFont.load_default()

    # Draw text
    text = "B"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2 - 10

    # Draw text with shadow
    draw.text((text_x + 3, text_y + 3), text, font=font, fill=(0, 0, 0, 100))
    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))

    # Save in multiple sizes for Windows .ico format
    output_path = Path(__file__).parent / "icon.ico"
    img.save(output_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"[OK] Icon created: {output_path}")

    # Also save as PNG for reference
    png_path = Path(__file__).parent / "icon.png"
    img.save(png_path, format='PNG')
    print(f"[OK] PNG preview saved: {png_path}")

if __name__ == "__main__":
    create_icon()
