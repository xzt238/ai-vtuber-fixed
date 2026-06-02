"""
GuguGaga AI-VTuber �� Ʒ����Դ������

����:
  - app.ico (��ߴ� ICO)
  - app.png (256x256 PNG)
  - splash.png (������� 600x300)
  - tray_icon.png (ϵͳ���� 32x32)

����: Pillow (PIL)
"""

import os
import struct

# ��Դ���Ŀ¼
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESOURCES_DIR = SCRIPT_DIR  # ���� resources/ ��


def create_app_icon_png():
    """����Ӧ��ͼ�� PNG (256x256) �� AI�Ƽ����"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not installed, generating SVG fallback")
        return None

    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ���� �� Բ�Ǿ���
    margin = 8
    radius = 40
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill=(30, 30, 46, 255),  # ��������ɫ
        outline=(88, 166, 255, 255),  # �������
        width=3
    )

    # ���������� �� AI�ڵ�
    cx, cy = size // 2, size // 2 - 10
    hex_r = 60
    import math
    hex_points = []
    for i in range(6):
        angle = math.radians(60 * i - 30)
        hex_points.append((
            cx + hex_r * math.cos(angle),
            cy + hex_r * math.sin(angle)
        ))
    draw.polygon(hex_points, fill=(45, 45, 70, 255), outline=(88, 166, 255, 255))

    # �ڵ����� �� ������
    node_positions = [
        (cx - 40, cy - 35),  # ����
        (cx + 40, cy - 35),  # ����
        (cx - 50, cy + 15),  # ����
        (cx + 50, cy + 15),  # ����
        (cx - 30, cy + 40),  # ����
        (cx + 30, cy + 40),  # ����
        (cx, cy - 50),       # ��
    ]
    # ����
    connections = [
        (0, 1), (0, 2), (0, 6), (1, 3), (1, 6),
        (2, 4), (3, 5), (2, 3), (4, 5)
    ]
    for i, j in connections:
        draw.line([node_positions[i], node_positions[j]], fill=(88, 166, 255, 180), width=2)

    # �ڵ�Բ��
    for pos in node_positions:
        draw.ellipse(
            [pos[0] - 5, pos[1] - 5, pos[0] + 5, pos[1] + 5],
            fill=(136, 204, 255, 255),
            outline=(200, 230, 255, 255)
        )

    # ���Ľڵ� �� ��Բ
    draw.ellipse(
        [cx - 10, cy - 10, cx + 10, cy + 10],
        fill=(255, 200, 80, 255),  # ��ɫ����
        outline=(255, 230, 150, 255)
    )

    # �ײ����� "GG"
    try:
        font = ImageFont.truetype("arial.ttf", 42)
    except (IOError, OSError):
        font = ImageFont.load_default()
    draw.text((cx, cy + 75), "GG", fill=(255, 255, 255, 255), font=font, anchor="mm")

    return img


def create_splash_image():
    """����������� (600x300)"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    width, height = 600, 300
    img = Image.new('RGBA', (width, height), (18, 18, 30, 255))
    draw = ImageDraw.Draw(img)

    # �����ɫ��
    for x in range(width):
        r = int(30 + 20 * (x / width))
        g = int(30 + 30 * (x / width))
        b = int(50 + 50 * (x / width))
        draw.line([(x, 0), (x, height)], fill=(r, g, b, 255))

    # ����
    try:
        title_font = ImageFont.truetype("arial.ttf", 36)
        sub_font = ImageFont.truetype("arial.ttf", 16)
    except (IOError, OSError):
        title_font = ImageFont.load_default()
        sub_font = ImageFont.load_default()

    draw.text((width // 2, 100), "GuguGaga AI-VTuber",
              fill=(255, 255, 255, 255), font=title_font, anchor="mm")
    draw.text((width // 2, 150), "v1.11.23 - Native Desktop",
              fill=(136, 204, 255, 255), font=sub_font, anchor="mm")
    draw.text((width // 2, 250), "Loading...",
              fill=(150, 150, 170, 255), font=sub_font, anchor="mm")

    # �ײ�����������
    draw.rounded_rectangle(
        [100, 270, 500, 280],
        radius=5,
        fill=(40, 40, 60, 255)
    )

    return img


def create_tray_icon():
    """����ϵͳ����ͼ�� (32x32)"""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None

    size = 32
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # �򻯰� �� Բ�� + GG
    draw.ellipse([2, 2, 30, 30], fill=(30, 30, 46, 255), outline=(88, 166, 255, 255), width=2)

    # ���ĵ�
    draw.ellipse([12, 12, 20, 20], fill=(255, 200, 80, 255))

    return img


def save_ico(img, path):
    """����Ϊ ICO (��ߴ�)"""
    from PIL import Image
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_images = []
    for s in sizes:
        resized = img.resize(s, Image.LANCZOS)
        ico_images.append(resized)

    # ICO ����
    img.save(path, format='ICO', sizes=[(i.width, i.height) for i in ico_images])
    print(f"  Saved: {path}")


def generate_all():
    """����������Դ"""
    print("Generating brand resources...")

    # Ӧ��ͼ��
    app_icon = create_app_icon_png()
    if app_icon:
        save_ico(app_icon, os.path.join(RESOURCES_DIR, 'app.ico'))
        app_icon.save(os.path.join(RESOURCES_DIR, 'app.png'), format='PNG')
        print(f"  Saved: {os.path.join(RESOURCES_DIR, 'app.png')}")

    # �������
    splash = create_splash_image()
    if splash:
        splash.save(os.path.join(RESOURCES_DIR, 'splash.png'), format='PNG')
        print(f"  Saved: {os.path.join(RESOURCES_DIR, 'splash.png')}")

    # ����ͼ��
    tray = create_tray_icon()
    if tray:
        tray.save(os.path.join(RESOURCES_DIR, 'tray_icon.png'), format='PNG')
        print(f"  Saved: {os.path.join(RESOURCES_DIR, 'tray_icon.png')}")

    # ��� Pillow �����ã����� SVG ����
    if not app_icon:
        svg_path = os.path.join(RESOURCES_DIR, 'app.svg')
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write(APP_ICON_SVG)
        print(f"  Saved (SVG fallback): {svg_path}")

    print("Done!")


# SVG ���� �� ��� Pillow ������
APP_ICON_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1e1e2e"/>
      <stop offset="100%" style="stop-color:#2a2a4a"/>
    </linearGradient>
  </defs>
  <rect x="8" y="8" width="240" height="240" rx="40" fill="url(#bg)" stroke="#58a6ff" stroke-width="3"/>
  <!-- Neural network nodes -->
  <g stroke="#58a6ff" stroke-width="2" opacity="0.7">
    <line x1="88" y1="93" x2="168" y2="93"/>
    <line x1="88" y1="93" x2="78" y2="143"/>
    <line x1="168" y1="93" x2="178" y2="143"/>
    <line x1="78" y1="143" x2="178" y2="143"/>
    <line x1="78" y1="143" x2="98" y2="178"/>
    <line x1="178" y1="143" x2="158" y2="178"/>
    <line x1="98" y1="178" x2="158" y2="178"/>
    <line x1="128" y1="78" x2="88" y2="93"/>
    <line x1="128" y1="78" x2="168" y2="93"/>
  </g>
  <!-- Nodes -->
  <circle cx="128" cy="118" r="10" fill="#ffc850" stroke="#ffe696"/>
  <circle cx="88" cy="93" r="5" fill="#88ccff"/>
  <circle cx="168" cy="93" r="5" fill="#88ccff"/>
  <circle cx="78" cy="143" r="5" fill="#88ccff"/>
  <circle cx="178" cy="143" r="5" fill="#88ccff"/>
  <circle cx="98" cy="178" r="5" fill="#88ccff"/>
  <circle cx="158" cy="178" r="5" fill="#88ccff"/>
  <circle cx="128" cy="78" r="5" fill="#88ccff"/>
  <!-- Text -->
  <text x="128" y="220" text-anchor="middle" fill="white" font-family="Arial" font-size="36" font-weight="bold">GG</text>
</svg>'''


if __name__ == '__main__':
    generate_all()
