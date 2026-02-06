"""
Generate a simple icon for Backlogia desktop app.
Requires: pip install pillow
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_icon():
    """Create a simple icon with the letter 'B' - light purple on blue background."""
    # Create a 256x256 image
    size = 256
    img = Image.new('RGBA', (size, size))
    draw = ImageDraw.Draw(img)

    # Draw blue background circle
    center = size // 2
    radius = size // 2 - 10
    blue_bg = (30, 100, 200, 255)  # Nice blue
    draw.ellipse([center - radius, center - radius, center + radius, center + radius], fill=blue_bg)

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

    # Light purple color for the B
    light_purple = (200, 150, 255, 255)
    
    # Draw text with shadow
    draw.text((text_x + 3, text_y + 3), text, font=font, fill=(0, 0, 0, 100))
    draw.text((text_x, text_y), text, font=font, fill=light_purple)

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
