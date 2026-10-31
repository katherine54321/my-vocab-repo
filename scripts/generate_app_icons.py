import os
import struct
import zlib
import math
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def generate_icons():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icons_dir = os.path.join(base_dir, "icons")
    public_icons_dir = os.path.join(base_dir, "public", "icons")
    os.makedirs(icons_dir, exist_ok=True)
    os.makedirs(public_icons_dir, exist_ok=True)

    # 1. High-Resolution SVG Favicon & App Icon
    svg_content = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e40af" />
      <stop offset="50%" stop-color="#3b82f6" />
      <stop offset="100%" stop-color="#6366f1" />
    </linearGradient>
    <linearGradient id="gridGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#60a5fa" stop-opacity="0.8" />
      <stop offset="100%" stop-color="#a5b4fc" stop-opacity="0.8" />
    </linearGradient>
    <linearGradient id="glowGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" />
      <stop offset="100%" stop-color="#ffffff" />
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#0f172a" flood-opacity="0.35"/>
    </filter>
  </defs>

  <!-- Squircle Base with Drop Shadow -->
  <rect x="32" y="32" width="448" height="448" rx="112" fill="url(#bgGrad)" filter="url(#shadow)" />

  <!-- Subtle 2D Matrix Grid Motif -->
  <g opacity="0.22" stroke="#ffffff" stroke-width="2.5" stroke-dasharray="6,6">
    <line x1="96" y1="140" x2="416" y2="140" />
    <line x1="96" y1="210" x2="416" y2="210" />
    <line x1="96" y1="280" x2="416" y2="280" />
    <line x1="96" y1="350" x2="416" y2="350" />
    <line x1="160" y1="96" x2="160" y2="416" />
    <line x1="256" y1="96" x2="256" y2="416" />
    <line x1="352" y1="96" x2="352" y2="416" />
  </g>

  <!-- Accent CEFR Node Dots -->
  <circle cx="160" cy="140" r="10" fill="#38bdf8" opacity="0.9" />
  <circle cx="256" cy="140" r="8" fill="#a7f3d0" opacity="0.8" />
  <circle cx="352" cy="210" r="10" fill="#fde047" opacity="0.9" />
  <circle cx="160" cy="280" r="8" fill="#f472b6" opacity="0.8" />
  <circle cx="256" cy="350" r="12" fill="#60a5fa" opacity="0.95" />

  <!-- Distinctive "V M" Stylized Monogram Overlay -->
  <path d="M 124 165 L 204 350 L 256 240 L 308 350 L 388 165" 
        fill="none" 
        stroke="url(#glowGrad)" 
        stroke-width="38" 
        stroke-linecap="round" 
        stroke-linejoin="round" />

  <!-- Inner Sparkle Badge -->
  <circle cx="256" cy="240" r="16" fill="#ffffff" />
  <circle cx="256" cy="240" r="8" fill="#3b82f6" />
</svg>
'''

    with open(os.path.join(icons_dir, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(svg_content)
    with open(os.path.join(public_icons_dir, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write(svg_content)

    # 2. Pure Python PNG Generator (Anti-aliased rendering of the Icon)
    def render_png(size, maskable=False):
        raw = bytearray()
        radius = size * 0.23
        cx = size / 2.0
        cy = size / 2.0
        corner_r = size * (0.0 if maskable else 0.22)
        margin = size * (0.0 if maskable else 0.05)

        for y in range(size):
            raw.append(0)  # Filter 0
            ny = (y - cy) / (size / 2.0)
            for x in range(size):
                nx = (x - cx) / (size / 2.0)
                
                # Check squircle bounds if not maskable
                in_bounds = True
                alpha = 255
                if not maskable:
                    dx = abs(x - cx) - (size / 2.0 - margin - corner_r)
                    dy = abs(y - cy) - (size / 2.0 - margin - corner_r)
                    if dx > 0 and dy > 0:
                        dist = math.sqrt(dx*dx + dy*dy)
                        if dist > corner_r:
                            in_bounds = False
                        elif dist > corner_r - 1.5:
                            alpha = int(255 * (corner_r - dist) / 1.5)
                    elif dx > corner_r or dy > corner_r:
                        in_bounds = False

                if not in_bounds or alpha <= 0:
                    raw.extend([0, 0, 0, 0])
                    continue

                # Gradient Background: #1e40af (30,64,175) to #4f46e5 (79,70,229) to #3b82f6 (59,130,246)
                t = (nx + ny + 2.0) / 4.0
                t = max(0.0, min(1.0, t))
                r = int(30 + t * 45)
                g = int(64 + t * 66)
                b = int(175 + t * 71)

                # Monogram "V M" shape sampling
                # Points: (0.24, 0.32) -> (0.40, 0.68) -> (0.50, 0.47) -> (0.60, 0.68) -> (0.76, 0.32)
                # Let's compute distance to polyline segments
                px = x / float(size)
                py = y / float(size)
                
                pts = [(0.24, 0.32), (0.40, 0.68), (0.50, 0.47), (0.60, 0.68), (0.76, 0.32)]
                min_dist = 999.0
                for i in range(len(pts) - 1):
                    x1, y1 = pts[i]
                    x2, y2 = pts[i+1]
                    vx, vy = x2 - x1, y2 - y1
                    wx, wy = px - x1, py - y1
                    c1 = vx * wx + vy * wy
                    c2 = vx * vx + vy * vy
                    param = max(0.0, min(1.0, c1 / c2)) if c2 > 0 else 0.0
                    proj_x = x1 + param * vx
                    proj_y = y1 + param * vy
                    d = math.hypot(px - proj_x, py - proj_y)
                    if d < min_dist:
                        min_dist = d

                stroke_w = 0.038
                if min_dist < stroke_w:
                    # White/Cyan Glowing Stroke
                    mix = 1.0 - (min_dist / stroke_w)
                    r = int(r * (1.0 - mix) + 255 * mix)
                    g = int(g * (1.0 - mix) + 255 * mix)
                    b = int(b * (1.0 - mix) + 255 * mix)
                elif min_dist < stroke_w * 1.8:
                    # Outer Glow
                    glow = (stroke_w * 1.8 - min_dist) / (stroke_w * 0.8) * 0.35
                    r = min(255, int(r + 56 * glow))
                    g = min(255, int(g + 189 * glow))
                    b = min(255, int(b + 248 * glow))

                raw.extend([r, g, b, alpha])

        compressor = zlib.compressobj()
        compressed = compressor.compress(raw) + compressor.flush()
        
        png = bytearray(b'\x89PNG\r\n\x1a\n')
        # IHDR
        ihdr_data = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
        ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data)
        png.extend(struct.pack('>I', len(ihdr_data)) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc))
        # IDAT
        idat_crc = zlib.crc32(b'IDAT' + compressed)
        png.extend(struct.pack('>I', len(compressed)) + b'IDAT' + compressed + struct.pack('>I', idat_crc))
        # IEND
        iend_crc = zlib.crc32(b'IEND')
        png.extend(struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc))
        return bytes(png)

    # Generate 192, 512, apple-touch 180, and maskable 512
    targets = [
        ("icon-192.png", 192, False),
        ("icon-512.png", 512, False),
        ("apple-touch-icon.png", 180, False),
        ("maskable-icon-512.png", 512, True)
    ]

    for fname, sz, mask in targets:
        print(f"Generating {fname} ({sz}x{sz}, maskable={mask})...")
        data = render_png(sz, mask)
        with open(os.path.join(icons_dir, fname), "wb") as f:
            f.write(data)
        with open(os.path.join(public_icons_dir, fname), "wb") as f:
            f.write(data)
        print(f"  ✓ {fname} written ({len(data)} bytes)")

    print("All PWA app icons generated successfully!")

if __name__ == "__main__":
    generate_icons()
