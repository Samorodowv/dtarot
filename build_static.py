#!/usr/bin/env python
"""
Static file build script for Tarot project
Optimizes CSS and JavaScript files for production
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Add Django project to path
sys.path.insert(0, str(Path(__file__).parent / 'tarot_project'))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tarot_project.settings')

import django
django.setup()

from django.conf import settings
from django.core.management import call_command

def main():
    """Main build process"""
    print("🔨 Building static files for production...")
    
    # Ensure static directories exist
    static_dir = Path(settings.BASE_DIR) / 'static'
    static_dir.mkdir(exist_ok=True)
    (static_dir / 'css').mkdir(exist_ok=True)
    (static_dir / 'js').mkdir(exist_ok=True)
    
    # Collect static files
    print("📦 Collecting static files...")
    call_command('collectstatic', '--noinput', verbosity=0)
    
    # Create basic optimization
    optimize_css()
    optimize_js()
    
    # Create icons directory for PWA
    create_pwa_icons()
    
    print("✅ Static files built successfully!")
    print(f"📁 Static files location: {settings.STATIC_ROOT}")

def optimize_css():
    """Basic CSS optimization"""
    print("🎨 Optimizing CSS...")
    
    css_file = Path(settings.BASE_DIR) / 'static' / 'css' / 'app.css'
    if css_file.exists():
        # Read original CSS
        with open(css_file, 'r', encoding='utf-8') as f:
            css_content = f.read()
        
        # Basic minification (remove comments and extra whitespace)
        # Remove comments
        import re
        css_content = re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
        
        # Remove extra whitespace (but preserve necessary spaces)
        css_content = re.sub(r'\s+', ' ', css_content)
        css_content = re.sub(r';\s*}', '}', css_content)
        css_content = re.sub(r'{\s*', '{', css_content)
        css_content = re.sub(r'}\s*', '}', css_content)
        css_content = re.sub(r':\s*', ':', css_content)
        css_content = re.sub(r';\s*', ';', css_content)
        
        # Write minified version
        minified_file = css_file.parent / 'app.min.css'
        with open(minified_file, 'w', encoding='utf-8') as f:
            f.write(css_content.strip())
        
        print(f"   ✓ CSS minified: {css_file} -> {minified_file}")

def optimize_js():
    """Basic JavaScript optimization"""
    print("⚙️ Optimizing JavaScript...")
    
    js_file = Path(settings.BASE_DIR) / 'static' / 'js' / 'app.js'
    if js_file.exists():
        # Read original JS
        with open(js_file, 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Basic minification (remove comments and extra whitespace)
        import re
        # Remove single-line comments (but preserve URLs)
        js_content = re.sub(r'//(?![:/]).*$', '', js_content, flags=re.MULTILINE)
        
        # Remove multi-line comments
        js_content = re.sub(r'/\*.*?\*/', '', js_content, flags=re.DOTALL)
        
        # Remove extra whitespace
        js_content = re.sub(r'\s+', ' ', js_content)
        js_content = re.sub(r';\s*', ';', js_content)
        js_content = re.sub(r'{\s*', '{', js_content)
        js_content = re.sub(r'}\s*', '}', js_content)
        
        # Write minified version
        minified_file = js_file.parent / 'app.min.js'
        with open(minified_file, 'w', encoding='utf-8') as f:
            f.write(js_content.strip())
        
        print(f"   ✓ JavaScript minified: {js_file} -> {minified_file}")

def create_pwa_icons():
    """Create PWA icon placeholders"""
    print("📱 Creating PWA icons...")
    
    static_root = Path(settings.STATIC_ROOT)
    icons_dir = static_root / 'icons'
    icons_dir.mkdir(exist_ok=True)
    
    # Create simple icon placeholders (in production, use proper icons)
    icon_sizes = [192, 512]
    
    for size in icon_sizes:
        icon_file = icons_dir / f'icon-{size}.png'
        if not icon_file.exists():
            # Create a simple colored square as placeholder
            try:
                from PIL import Image, ImageDraw
                
                # Create image
                img = Image.new('RGB', (size, size), color='#9333EA')
                draw = ImageDraw.Draw(img)
                
                # Draw simple tarot card shape
                margin = size // 8
                draw.rectangle(
                    [margin, margin, size - margin, size - margin],
                    fill='#1F2937',
                    outline='#FFFFFF',
                    width=2
                )
                
                # Add text
                text = "🔮"
                font_size = size // 4
                try:
                    from PIL import ImageFont
                    # Try to use a system font
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                
                # Calculate text position
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (size - text_width) // 2
                y = (size - text_height) // 2
                
                draw.text((x, y), text, fill='#9333EA', font=font)
                
                img.save(icon_file)
                print(f"   ✓ Created icon: {icon_file}")
                
            except ImportError:
                # Fallback: create empty file
                icon_file.touch()
                print(f"   ⚠️ Created placeholder for: {icon_file} (install Pillow for proper icons)")

def download_fallback_css():
    """Download Tailwind CSS as fallback"""
    print("📦 Downloading Tailwind CSS fallback...")
    
    try:
        import urllib.request
        
        tailwind_url = "https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css"
        fallback_file = Path(settings.STATIC_ROOT) / 'css' / 'tailwind-fallback.min.css'
        
        urllib.request.urlretrieve(tailwind_url, fallback_file)
        print(f"   ✓ Downloaded Tailwind CSS fallback: {fallback_file}")
        
    except Exception as e:
        print(f"   ⚠️ Could not download Tailwind fallback: {e}")

if __name__ == '__main__':
    main()