from flask import Flask, request, send_file, jsonify
import tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io

app = Flask(__name__)

def generate_gfx_font_proper(font_path, font_size, charset):
    font = ImageFont.truetype(font_path, font_size)
    gfx_output = io.StringIO()
    gfx_output.write(f"// GFX font generated from {font_path}\n\n")
    gfx_output.write("#include <stdint.h>\n")
    gfx_output.write("#include <Adafruit_GFX.h>\n\n")
    
    bitmaps = bytearray()
    glyphs = []
    bitmap_offset = 0

    for char in charset:
        bbox = font.getbbox(char)
        if bbox is None:
            width, height, offset_x, offset_y = 0, 0, 0, 0
            mask = Image.new("L", (1, 1), 0)
        else:
            left, top, right, bottom = bbox
            width, height = right - left, bottom - top
            offset_x, offset_y = left, top
            mask = Image.new("L", (width, height), 0)
            draw = ImageDraw.Draw(mask)
            draw.text((-left, -top), char, fill=255, font=font)

        bitmap = np.array(mask).astype(np.uint8)
        bitmap = (bitmap > 128).astype(np.uint8)

        packed_bits = bytearray()
        for y in range(bitmap.shape[1]):
            byte = 0
            bit_count = 0
            for x in range(bitmap.shape[0]):
                byte = (byte << 1) | bitmap[x, y]
                bit_count += 1
                if bit_count == 8:
                    packed_bits.append(byte)
                    byte = 0
                    bit_count = 0
            if bit_count > 0:
                byte <<= (8 - bit_count)
                packed_bits.append(byte)

        bitmaps.extend(packed_bits)

        advance = font.getlength(char)
        glyphs.append({
            'offset': bitmap_offset,
            'width': width,
            'height': height,
            'xAdvance': int(advance),
            'xOffset': offset_x,
            'yOffset': offset_y
        })

        bitmap_offset += len(packed_bits)

    gfx_output.write(f"const uint8_t RajdhaniBitmaps[] PROGMEM = {{\n")
    for i, byte in enumerate(bitmaps):
        gfx_output.write(f"0x{byte:02X}, ")
        if i % 16 == 15:
            gfx_output.write("\n")
    gfx_output.write("};\n\n")

    gfx_output.write(f"const GFXglyph RajdhaniGlyphs[] PROGMEM = {{\n")
    for i, g in enumerate(glyphs):
        gfx_output.write("  { ")
        gfx_output.write(f"{g['offset']}, {g['width']}, {g['height']}, {g['xAdvance']}, {g['xOffset']}, {g['yOffset']}")
        gfx_output.write(f" }}, // 0x{ord(charset[i]):02X} '{charset[i]}'\n")
    gfx_output.write("};\n\n")

    gfx_output.write(f"const GFXfont Rajdhani120pt7b PROGMEM = {{\n")
    gfx_output.write(f"  (uint8_t  *)RajdhaniBitmaps,\n")
    gfx_output.write(f"  (GFXglyph *)RajdhaniGlyphs,\n")
    gfx_output.write(f"  0x20, 0x7E, {font_size}\n")
    gfx_output.write("};\n")

    return gfx_output.getvalue()

@app.route('/generate_gfx', methods=['POST'])
def generate_gfx_route():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    with tempfile.NamedTemporaryFile(delete=False, suffix='.ttf') as temp_font:
        file.save(temp_font.name)
        try:
            charset = ''.join([chr(i) for i in range(32, 127)])
            gfx_content = generate_gfx_font_proper(temp_font.name, 120, charset)

            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.h')
            with open(temp_output.name, "w") as f:
                f.write(gfx_content)

            return send_file(temp_output.name, as_attachment=True, download_name="Rajdhani120pt7b.h")
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/')
def home():
    return 'GFX Endpoint'

@app.route('/about')
def about():
    return 'GFX creation flask endpoint'
