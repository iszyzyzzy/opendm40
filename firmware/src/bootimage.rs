//! 开机图片保存在 SPI 磁盘，像素逐行读取，避免占用全屏缓冲区。

pub const NAME: [u8; 11] = *b"BOOT    RAW";
pub const SIZE: u32 = 480 * 320 * 2;

#[cfg(target_os = "none")]
#[inline(never)]
pub fn draw() -> bool {
    use crate::dlog::{self, Src};
    let mut disk = dlog::disk();
    let Some(geo) = dlog::geometry(&mut disk) else { return false };
    let Some(file) = dlog::find(&mut disk, &geo, &NAME) else { return false };
    if file.size != SIZE {
        return false;
    }
    let mut file = dlog::FatFile::new(disk, geo, file.start, file.size);
    let mut row = [0u8; 960];
    for y in 0..320 {
        if !file.read(y * 960, &mut row) {
            return false;
        }
        crate::lcd::set_window(0, y as u16, 479, y as u16);
        for p in row.chunks_exact(2) {
            crate::lcd::data(u16::from_le_bytes([p[0], p[1]]));
        }
        crate::wdt::kick_if_feeding();
    }
    true
}
