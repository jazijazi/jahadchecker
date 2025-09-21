# services/captcha_service.py
import random
import string
from PIL import Image, ImageDraw, ImageFont , ImageFilter
import io
import math
import base64
from django.conf import settings
import os
from django.conf import settings

class CaptchaGenerator:
    def __init__(self):
        self.width = 200
        self.height = 80
        self.length = 5
        
    def generate_text(self):
        """Generate random text for CAPTCHA"""
        # Exclude confusing characters like 0, O, I, l, 1
        chars = 'A2B9C4D8E6F7G8H6J3K5L5M4N7P3Q9R2S3TUVW4X2YZA'
        return ''.join(random.choice(chars) for _ in range(self.length))
    
    def generate_image(self, text) -> Image:
        """Generate a more complex CAPTCHA image"""
        # Create image
        image: Image = Image.new('RGB', (self.width, self.height), color='white')
        draw = ImageDraw.Draw(image)

        # Try to load a font, fallback to default if not found
        font_paths = [
            os.path.join(settings.BASE_DIR, "fonts", "dejavu-sans.bold.ttf"),
            os.path.join(settings.BASE_DIR, "fonts", "tomnr.ttf"),
            os.path.join(settings.BASE_DIR, "fonts", "ARIAL.TTF"),
        ]

        # Add more background noise dots with random colors
        for _ in range(200):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            draw.point((x, y), fill=(
                random.randint(100, 255),
                random.randint(100, 255),
                random.randint(100, 255)
            ))

        # Add a few very light geometric shapes
        for _ in range(8):
            x = random.randint(5, self.width - 15)
            y = random.randint(5, self.height - 15)
            size = random.randint(4, 8)
            
            color = (random.randint(220, 240), random.randint(220, 240), random.randint(220, 240))
            
            if random.choice([True, False]):
                draw.ellipse([x, y, x + size, y + size], fill=color)
            else:
                draw.rectangle([x, y, x + size, y + size], fill=color)

        # Add random arcs/curves for complexity
        for _ in range(5):
            x0 = random.randint(0, self.width - 10)
            y0 = random.randint(0, self.height - 10)
            x1 = random.randint(x0 + 5, self.width)
            y1 = random.randint(y0 + 5, self.height)
            start_angle = random.randint(0, 360)
            end_angle = start_angle + random.randint(45, 270)
            draw.arc([x0, y0, x1, y1], start=start_angle, end=end_angle, fill=(
                random.randint(50, 150),
                random.randint(50, 150),
                random.randint(50, 150)
            ), width=2)

        # Draw text with random rotation and jitter
        for i, char in enumerate(text):
            # Create a separate image for each char
            char_img = Image.new('RGBA', (50, 50), (255, 255, 255, 0))
            char_draw = ImageDraw.Draw(char_img)

            color = (
                random.randint(0, 100),
                random.randint(0, 100),
                random.randint(0, 100)
            )

            font_path = random.choice(font_paths)
            try:
                # Slight font size variation
                font_size = random.randint(38, 44)
                font = ImageFont.truetype(font_path, font_size)
            except:
                font = ImageFont.load_default()

            char_draw.text((5, 5), char, font=font, fill=color)

            # Apply random rotation
            angle = random.randint(-30, 30)
            rotated_char = char_img.rotate(angle, expand=1)

            # Paste onto main image with jitter
            x = 20 + i * 30 + random.randint(-10, 10)
            y = 10 + random.randint(-10, 10)
            image.paste(rotated_char, (x, y), rotated_char)

        # Add random lines for complexity
        for _ in range(6):
            start = (random.randint(0, self.width), random.randint(0, self.height))
            end = (random.randint(0, self.width), random.randint(0, self.height))
            draw.line([start, end], fill=(
                random.randint(50, 150),
                random.randint(50, 150),
                random.randint(50, 150)
            ), width=random.randint(1, 3))

        # Slight blur to make OCR harder but still readable
        image = image.filter(ImageFilter.GaussianBlur(radius=0.8))

        # Very mild wave distortion - barely noticeable
        pixels = image.load()
        distorted = Image.new('RGB', (self.width, self.height), 'white')
        distorted_pixels = distorted.load()
        
        wave_amplitude = random.randint(1, 2)  # Much smaller waves
        wave_frequency = 0.02
        
        for y in range(self.height):
            for x in range(self.width):
                offset_x = int(wave_amplitude * math.sin(y * wave_frequency))
                source_x = max(0, min(self.width - 1, x + offset_x))
                distorted_pixels[x, y] = pixels[source_x, source_y if 'source_y' in locals() else y]
        
        image = distorted

        # Light blur - just enough to break pixel-perfect OCR
        image = image.filter(ImageFilter.GaussianBlur(radius=0.6))

        return image

    
    def image_to_base64(self, image:Image) -> str:
        """Convert PIL image to base64 string"""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode()