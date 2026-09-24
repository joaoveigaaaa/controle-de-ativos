from io import BytesIO
import re
import threading
from flask import jsonify, request


def extract_candidates(texts):
    found = []
    for text in texts:
 
        for value in re.findall(r'[A-Za-z0-9][A-Za-z0-9._/-]{2,99}', text):
            value = value.strip('._/-')
            if len(value) >= 3 and any(c.isdigit() for c in value) and value not in found:
                found.append(value)
    return found[:20]


def register_ocr(app):
    engine = None
    lock = threading.Lock()

    @app.post('/api/scan-text')
    def scan_text():
        nonlocal engine
        from PIL import Image, ImageOps, UnidentifiedImageError
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR
        file = request.files.get('quadro')
        if not file:
            return jsonify(erro='Abra a câmera e clique em Ler série impressa.'), 400
        content = file.read(5 * 1024 * 1024 + 1)
        if not content or len(content) > 5 * 1024 * 1024:
            return jsonify(erro='A imagem da câmera deve ter até 5 MB.'), 400
        try:
            picture = Image.open(BytesIO(content))
            if picture.format not in ('JPEG', 'PNG') or picture.width * picture.height > 12_000_000:
                raise ValueError('Quadro de câmera inválido ou grande demais.')
            picture = ImageOps.exif_transpose(picture).convert('RGB')
            picture.thumbnail((2000, 2000))
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            return jsonify(erro='Não foi possível ler a imagem da câmera.'), 400
        if not lock.acquire(blocking=False):
            return jsonify(erro='Já há uma leitura em andamento. Aguarde e tente novamente.'), 429
        try:
            if engine is None:
                engine = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=2)
            results, _ = engine(np.asarray(picture)[:, :, ::-1].copy())
            texts = [row[1] for row in (results or [])]
            return jsonify(textos=texts, candidatos=extract_candidates(texts))
        finally:
            lock.release()
