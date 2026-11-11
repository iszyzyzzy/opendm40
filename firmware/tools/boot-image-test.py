#!/usr/bin/env python3
"""验证透明像素的隐藏颜色不会进入 RGB565，以及半透明像素的黑底合成。"""
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image

script = Path(__file__).with_name("boot-image.py")
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    results = []
    for hidden in (0, 255):
        image = Image.new("RGBA", (32, 32), (hidden, hidden, hidden, 0))
        for y in range(8, 24):
            for x in range(8, 24):
                image.putpixel((x, y), (255, 0, 0, 255))
        source, output = root / "input.png", root / "BOOT.RAW"
        image.save(source)
        subprocess.run([sys.executable, str(script), str(source), "-o", str(output)], check=True)
        results.append(output.read_bytes())
    assert results[0] == results[1]
    assert len(results[0]) == 307200
    assert results[0][:2] == b"\0\0"
    image = Image.new("RGBA", (480, 320), (255, 255, 255, 128))
    image.save(source)
    subprocess.run([sys.executable, str(script), str(source), "-o", str(output)], check=True)
    assert output.read_bytes() == b"\x10\x84" * (480 * 320)
    subprocess.run([sys.executable, str(script), "--default", "-o", str(output)], check=True)
    assert output.read_bytes() == b"\0"
print("通过：透明隐藏颜色、缩放、半透明黑底合成、恢复默认")
