from io import BytesIO
from pathlib import Path
import unittest
from PIL import Image, ImageDraw, ImageFont
from app import create_app
from ocr_api import extract_candidates


class OCRTests(unittest.TestCase):
    def test_alphanumeric_is_not_replaced_or_truncated(self):
        self.assertEqual(extract_candidates(['SN: AB09XZ001', 'AB09XZ001', 'SN: 000ABC-12']), ['AB09XZ001', '000ABC-12'])

    def test_real_ocr_on_camera_frame(self):
        picture = Image.new('RGB', (1200, 260), 'white')
        font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 64)
        ImageDraw.Draw(picture).text((40, 80), 'S/N: AB09XZ001', fill='black', font=font)
        stream = BytesIO(); picture.save(stream, 'JPEG'); stream.seek(0)
        client = create_app({}).test_client()
        response = client.post('/api/scan-text', data={'quadro': (stream, 'camera.jpg')})
        self.assertEqual(response.status_code, 200, response.json)
        self.assertIn('AB09XZ001', response.json['candidatos'])

    def test_invalid_image(self):
        client = create_app({}).test_client()
        self.assertEqual(client.post('/api/scan-text', data={'quadro': (BytesIO(b'bad'), 'camera.jpg')}).status_code, 400)
