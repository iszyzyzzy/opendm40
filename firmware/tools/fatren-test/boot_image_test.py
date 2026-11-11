#!/usr/bin/env python3
"""虚拟盘开机图测试：boot_image_test.py FATREN_TEST_BINARY WORK_DIRECTORY。"""

import math
from pathlib import Path
import struct
import sys

from vserve import VServe


def u16(b, off):
    return struct.unpack_from("<H", b, off)[0]


def fixture(path):
    disk = bytearray(16 * 1024 * 1024)
    disk[:3] = b"\xeb\x3c\x90"
    struct.pack_into("<HBHBHHBH", disk, 11, 4096, 1, 1, 2, 512, 4096, 0xF8, 2)
    disk[510:512] = b"\x55\xaa"
    for off in (4096, 3 * 4096):
        disk[off:off + 4] = b"\xf8\xff\xff\xff"
    path.write_bytes(disk)


def stored(path):
    disk = path.read_bytes()
    files = []
    for off in range(5 * 4096, 9 * 4096, 32):
        e = disk[off:off + 32]
        if e[:11] != b"BOOT    RAW":
            continue
        c = u16(e, 26)
        size = struct.unpack_from("<I", e, 28)[0]
        data = bytearray()
        while 2 <= c < 0xFFF8:
            data.extend(disk[(9 + c - 2) * 4096:(10 + c - 2) * 4096])
            c = u16(disk, 4096 + 2 * c)
        files.append(bytes(data[:size]))
    assert len(files) <= 1, "重复根目录项"
    return files[0] if files else None


def upload(v, data, reverse=False, incomplete=False):
    b = v.read(0)
    spc, reserved, nf, fats = b[13], u16(b, 14), b[16], u16(b, 22)
    root = reserved + nf * fats
    base = root + u16(b, 17) * 32 // 512
    n = math.ceil(len(data) / (spc * 512))
    fat = bytearray(b"".join(v.read(reserved + i) for i in range(fats)))
    entries = bytearray(v.read(root))
    old = next((i for i in range(7 * 32, 512, 32) if entries[i:i + 11] == b"BOOT    RAW"), None)
    changed = set()
    if old is not None:
        c = u16(entries, old + 26)
        while 2 <= c < 0xFFF8:
            following = u16(fat, c * 2)
            struct.pack_into("<H", fat, c * 2, 0)
            changed.add(c * 2 // 512)
            c = following
    free = [c for c in range(2, len(fat) // 2) if u16(fat, c * 2) == 0][:n]
    assert len(free) == n
    for i, c in enumerate(free):
        struct.pack_into("<H", fat, c * 2, free[i + 1] if i + 1 < n else 0xFFFF)
        changed.add(c * 2 // 512)
    off = old if old is not None else next(i for i in range(7 * 32, 512, 32) if entries[i] in (0, 0xE5))
    e = memoryview(entries)[off:off + 32]
    e[:] = bytes(32)
    e[:11] = b"BOOT    RAW"
    e[11] = 0x20
    struct.pack_into("<HI", e, 26, free[0], len(data))
    writes = [(root, entries)]
    for f in range(nf):
        writes.extend((reserved + f * fats + i, fat[i * 512:(i + 1) * 512]) for i in sorted(changed))
    for off in range(0, len(data), 512):
        c = free[off // (spc * 512)]
        writes.append((base + (c - 2) * spc + off // 512 % spc, data[off:off + 512].ljust(512, b"\0")))
    for lba, sector in reversed(writes) if reverse else writes:
        if incomplete and lba == writes[-1][0]:
            continue
        assert v.write(lba, sector) == 0, f"扇区写入失败：{lba}"
    # 与实际复制后立即弹出相同，不能在提交图片前释放暂存簇。
    v.lock(False)
    v.idle(800)
    v._op(b"H")
    result = v._1()
    v._op(b"H")
    assert v._1() == 0, "保存结果重复显示"
    assert v.dialog() == 0 and not v.install(), "图片被当作固件处理"
    return result


def main():
    binary = str(Path(sys.argv[1]).resolve())
    work = Path(sys.argv[2]).resolve()
    work.mkdir(parents=True, exist_ok=True)
    spi, flash = work / "spi.img", work / "flash.bin"
    fixture(spi)
    flash.write_bytes(b"\xff" * (1 << 20))
    for name, size in (("UID.BIN", 12), ("OTP.BIN", 528), ("OPTBYTES.BIN", 16)):
        (work / name).write_bytes(bytes(size))
    image1 = bytes(range(256)) * 1200
    image2 = b"\x00\xf8\xe0\x07\x1f\x00" * 51200
    for label, data, expected, result, reverse in (
        ("首次保存", image1, image1, 1, False),
        ("重复换图", image2, image2, 1, True),
        ("拒绝短文件", b"invalid" * 100, image2, 2, False),
        ("恢复默认", b"\0", b"\0", 1, True),
    ):
        v = VServe(binary, str(spi), str(flash), str(work))
        try:
            v._op(b"H")
            assert v._1() == 0, "开机后出现保存消息"
            v.lock(True)
            v.tick(100)
            assert upload(v, data, reverse) == result, label
            saved = Path(v.save())
            assert stored(saved) == expected, label
            spi.write_bytes(saved.read_bytes())
        finally:
            v.close()
        print(f"通过：{label}", flush=True)

    v = VServe(binary, str(spi), str(flash), str(work))
    try:
        v.lock(True)
        v.tick(100)
        assert upload(v, image1) == 1
        v.lock(True)
        assert upload(v, image2, reverse=True) == 1
        assert stored(Path(v.save())) == image2
        v.bus_reset()
        v.mode(False, now=True)
        v.lock(True)
        assert upload(v, image1, incomplete=True) == 0
        assert stored(Path(v.save())) == image2
    finally:
        v.close()
    print("通过：同次连接覆盖图片、未完成复制保留原图", flush=True)


if __name__ == "__main__":
    main()
