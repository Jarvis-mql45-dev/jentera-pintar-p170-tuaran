"""Extract logo from Gemini image, crop background, and generate PWA icons."""
import os
from PIL import Image

# Paths
SRC_IMAGE = 'Gemini_Generated_Image_u5nj70u5nj70u5nj.png'
ICONS_DIR = 'frontend/icons'
BG_COLOR = (13, 49, 117, 255)  # #0d3175 (dark blue)
SIZES = [192, 512]

def crop_to_content(img):
    """Auto-crop to remove light gray background around the logo."""
    if img.mode != 'RGBA':
        img = img.convert('RGBA')
    
    pixels = img.load()
    w, h = img.size
    
    # Find bounding box of darker content pixels (logo is dark blue #30445f ~48,68,95)
    min_x, min_y = w, h
    max_x, max_y = 0, 0
    
    # Scan every 2nd pixel for speed
    for y in range(0, h, 2):
        for x in range(0, w, 2):
            r, g, b, a = pixels[x, y]
            # Logo content: darker pixels (sum < 500) or more saturated (not gray)
            is_content = (r + g + b) < 500 or abs(r - g) > 20 or abs(g - b) > 20
            if is_content and a > 30:
                if x < min_x: min_x = x
                if y < min_y: min_y = y
                if x > max_x: max_x = x
                if y > max_y: max_y = y
    
    # Add padding
    padding = 15
    min_x = max(0, min_x - padding)
    min_y = max(0, min_y - padding)
    max_x = min(w, max_x + padding)
    max_y = min(h, max_y + padding)
    
    print(f"  Content bounding box: ({min_x}, {min_y}) to ({max_x}, {max_y})")
    print(f"  Content size: {max_x - min_x} x {max_y - min_y}")
    
    cropped = img.crop((min_x, min_y, max_x, max_y))
    return cropped

def resize_with_padding(img, target_size):
    """Resize image to fit within target_size x target_size, padding with background color."""
    # Make the image square first by cropping to center
    w, h = img.size
    if w != h:
        # Crop to square (center)
        side = min(w, h)
        left = (w - side) // 2
        top = (h - side) // 2
        img = img.crop((left, top, left + side, top + side))
    
    # Resize to fit
    img_resized = img.resize((target_size, target_size), Image.LANCZOS)
    
    # Create final image with background color
    final = Image.new('RGBA', (target_size, target_size), BG_COLOR)
    
    # Paste the resized logo (use alpha as mask)
    if img_resized.mode == 'RGBA':
        final.paste(img_resized, (0, 0), img_resized)
    else:
        final.paste(img_resized, (0, 0))
    
    return final

def main():
    print("=" * 60)
    print("  GENERATE PWA ICONS FROM GEMINI IMAGE")
    print("=" * 60)
    
    # Open image
    print(f"\n📂 Membaca: {SRC_IMAGE}")
    img = Image.open(SRC_IMAGE)
    print(f"   Saiz asal: {img.size}, Mode: {img.mode}")
    
    # Crop to content
    print("\n✂️  Memotong latar belakang...")
    cropped = crop_to_content(img)
    print(f"   Saiz selepas crop: {cropped.size}")
    
    # Ensure icons directory exists
    os.makedirs(ICONS_DIR, exist_ok=True)
    
    # Generate icons at each size
    for size in SIZES:
        print(f"\n🖼️  Menjana ikon {size}x{size}...")
        icon = resize_with_padding(cropped, size)
        
        filepath = os.path.join(ICONS_DIR, f'icon-{size}x{size}.png')
        icon.save(filepath, 'PNG', optimize=True)
        
        file_size = os.path.getsize(filepath)
        print(f"   ✅ Disimpan: {filepath} ({file_size:,} bytes)")
    
    print("\n" + "=" * 60)
    print("  ✅ SEMUA IKON PWA BERJAYA DIJANA!")
    print("=" * 60)

if __name__ == '__main__':
    main()