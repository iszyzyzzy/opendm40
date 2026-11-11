#!/usr/bin/env python3
"""把图片转换为开机画面 BOOT.RAW（480×320，RGB565 小端）。需要 Pillow。"""

import argparse
import struct
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, nargs="?")
    parser.add_argument("-o", "--output", type=Path, default=Path("BOOT.RAW"))
    parser.add_argument("--default", action="store_true", help="生成恢复默认开机画面的文件")
    args = parser.parse_args()
    if args.default:
        if args.image:
            parser.error("恢复默认画面时不需要图片")
        data = b"\0"
    else:
        if not args.image:
            parser.error("请指定图片，或使用 --default")
        from PIL import Image, ImageOps

        with Image.open(args.image) as source:
            source = ImageOps.exif_transpose(source).convert("RGBA")
            # RGB565 没有透明通道，先与黑底合成，避免透明像素的隐藏颜色进入缩放边缘。
            background = Image.new("RGBA", source.size, "black")
            source = Image.alpha_composite(background, source).convert("RGB")
            image = ImageOps.pad(source, (480, 320), method=Image.Resampling.LANCZOS, color="black")
            data = b"".join(struct.pack("<H", (r >> 3) << 11 | (g >> 2) << 5 | b >> 3) for r, g, b in struct.iter_unpack("BBB", image.tobytes()))
    args.output.write_bytes(data)
    print(f"已保存 {args.output}（{len(data)} 字节）")


if __name__ == "__main__":
    main()
