"""Generate valid PWA icons using Python."""
import struct
import zlib
import os

def create_png(width, height, color=(30, 58, 138)):
    """Create a minimal valid PNG with solid color."""
    # Create raw pixel data (RGBA)
    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'  # filter byte
        for x in range(width):
            raw_data += bytes([color[0], color[1], color[2], 255])
    
    def create_chunk(chunk_type, data):
        chunk = chunk_type + data
        crc = struct.pack('>I', zlib.crc32(chunk) & 0xffffffff)
        return struct.pack('>I', len(data)) + chunk + crc
    
    # PNG Signature
    signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr = create_chunk(b'IHDR', ihdr_data)
    
    # IDAT chunk (compressed image data)
    compressed = zlib.compress(raw_data)
    idat = create_chunk(b'IDAT', compressed)
    
    # IEND chunk
    iend = create_chunk(b'IEND', b'')
    
    return signature + ihdr + idat + iend

def create_maskable_icon(width, height):
    """Create a maskable icon with white circle on blue background."""
    raw_data = b''
    center_x, center_y = width // 2, height // 2
    radius = width * 0.4  # 80% of icon for maskable safe zone
    
    for y in range(height):
        raw_data += b'\x00'  # filter byte
        for x in range(width):
            dx, dy = x - center_x, y - center_y
            dist = (dx*dx + dy*dy) ** 0.5
            
            if dist < radius:
                # White circle
                raw_data += bytes([255, 255, 255, 255])
            else:
                # Blue background
                raw_data += bytes([30, 58, 138, 255])
    
    def create_chunk(chunk_type, data):
        chunk = chunk_type + data
        crc = struct.pack('>I', zlib.crc32(chunk) & 0xffffffff)
        return struct.pack('>I', len(data)) + chunk + crc
    
    signature = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    ihdr = create_chunk(b'IHDR', ihdr_data)
    compressed = zlib.compress(raw_data)
    idat = create_chunk(b'IDAT', compressed)
    iend = create_chunk(b'IEND', b'')
    
    return signature + ihdr + idat + iend

# Generate icons
icons_dir = os.path.join(os.path.dirname(__file__), 'frontend', 'icons')

# Simple blue square icon
icon_192 = create_png(192, 192)
icon_512 = create_png(512, 512)

# Maskable icons
maskable_192 = create_maskable_icon(192, 192)
maskable_512 = create_maskable_icon(512, 512)

with open(os.path.join(icons_dir, 'icon-192x192.png'), 'wb') as f:
    f.write(maskable_192)
print(f'icon-192x192.png: {len(maskable_192)} bytes')

with open(os.path.join(icons_dir, 'icon-512x512.png'), 'wb') as f:
    f.write(maskable_512)
print(f'icon-512x512.png: {len(maskable_512)} bytes')

print('Ikon PWA berjaya dihasilkan!')