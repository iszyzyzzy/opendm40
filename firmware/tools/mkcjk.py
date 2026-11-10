#!/usr/bin/env python3
"""按界面实际用字生成中文位图：python mkcjk.py FONT.ttf。需要 Pillow。"""

import argparse
from collections import Counter
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("font", type=Path)
    args = parser.parse_args()
    src = Path(__file__).resolve().parents[1] / "src"
    chars = set()
    for p in src.glob("*.rs"):
        if p.name.startswith("stockfont_"):
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("//"):
                continue
            for literal in re.findall(r'"([^"\n]*)"', line):
                chars.update(c for c in literal if "\u4e00" <= c <= "\u9fff" or c in "，。：；？！（）")
    font = ImageFont.truetype(str(args.font), 16)
    codes, glyphs = [], []
    for ch in sorted(chars):
        canvas = Image.new("L", (40, 40))
        ImageDraw.Draw(canvas).text((4, 26), ch, font=font, fill=255, anchor="ls")
        box = canvas.getbbox()
        if box is None:
            raise ValueError(f"字体缺字：{ch}")
        ink = canvas.crop(box)
        if ink.width > 15 or ink.height > 16:
            raise ValueError(f"字形超出 15×16：{ch}")
        cell = Image.new("L", (15, 16))
        cell.paste(ink, ((15 - ink.width) // 2, 16 - ink.height))
        glyphs.append([sum((cell.getpixel((x, y)) >= 110) << (14 - x) for x in range(15)) for y in range(16)])
        codes.append(f"0x{ord(ch):04x}")
    # 常见笔画行用一个字节，其余行用两个字节，省下不同字号所需的闪存。
    common = [row for row, _ in Counter(r for g in glyphs for r in g).most_common(128)]
    lookup = {row: i for i, row in enumerate(common)}
    data, offsets = [], []
    for glyph in glyphs:
        offsets.append(len(data))
        for row in glyph:
            data.extend([lookup[row]] if row in lookup else [0x80 | (row >> 8), row & 255])
    # 字库元数据放 A2；末尾字形放 C，给实时采样代码保留 B 区余量。
    split = offsets[max(0, len(offsets) - 70)]
    attr = '#[cfg_attr(target_os = "none", link_section = ".rodata.a2.cjk")]\n'
    def array(name, typ, values, section=""):
        return section + f"static {name}: [{typ}; {len(values)}] = [" + ",".join(values) + "];\n"
    out = "// 中文界面字形：15×16，常用行索引及 15 位原始笔画行。\n"
    out += array("CJK_CODES", "u16", codes, attr)
    out += array("CJK_OFFSETS", "u16", list(map(str, offsets)), attr)
    out += array("CJK_ROWS", "u16", [hex(r) for r in common], attr)
    out += f"const CJK_SPLIT: usize = {split};\n"
    out += array("CJK_BITS", "u8", [hex(b) for b in data[:split]])
    out += array("CJK_TAIL", "u8", [hex(b) for b in data[split:]], '#[cfg_attr(target_os = "none", link_section = ".rodata.cold.cjk")]\n')
    (src / "stockfont_cjk.rs").write_text(out, encoding="utf-8", newline="\n")
    print(f"中文字形 {len(codes)} 个，位图 {len(data)} 字节")


if __name__ == "__main__":
    main()
