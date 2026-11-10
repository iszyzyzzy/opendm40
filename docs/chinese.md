# 中文版与自定义开机画面

`0.5.0-zh1` 基于上游 **v0.4.1**，移植
[OpenDM40-Chinese](https://github.com/xingyan4117-sketch/OpenDM40-Chinese)
的中文文案，并支持从 USB 虚拟磁盘导入开机图片。

主菜单、设置、示波器选项、图库、功率计、触摸校准和操作提示使用中文。
测量单位、协议名称、按键标识及 `AUTO`、`RUN`、`HOLD` 等状态缩写保留原样。
设置分类、手势、测量与校准逻辑沿用 v0.4.1。

## 安装

构建产物是 `firmware/dm40_opendm40_v0.5.0-zh1.bin`。
已有 opendm40 的设备，在“设置 → 其他 → U盘”选择“可写”，重新插拔 USB，
将固件复制到磁盘根目录，并在设备上确认安装。
首次安装及恢复原厂固件见[上游安装说明](manual/README.md#install)。

## 更换开机画面

未导入图片时，设备显示内置的 opendm40 名称、版本和加载进度。

1. 在仓库根目录转换图片：

   ```powershell
   uv run --with pillow python firmware/tools/boot-image.py picture.png -o BOOT.RAW
   ```

   支持 Pillow 能读取的图片格式，包括 PNG、JPEG、BMP。
   图片等比例缩放到 480×320，空白区域补黑，不裁剪。

2. 在设备上打开“设置 → 其他 → U盘”，选择“可写”，重新插拔 USB。
3. 将 **`BOOT.RAW`** 复制到虚拟磁盘根目录，等待设备提示“开机图已保存，重启生效”。
4. 安全弹出磁盘，重新开机。

图片保存在内部 SPI 闪存，断电后保留。虚拟盘上的 `BOOT.RAW` 是导入入口，
重新连接后不再显示；再次复制同名文件即可更换图片。
图片不会触发固件安装，也不修改标定数据。

## 恢复默认画面

```powershell
uv run python firmware/tools/boot-image.py --default -o BOOT.RAW
```

将生成的文件按相同步骤复制到虚拟盘。保存后重新开机，恢复内置画面。

## 文件格式

`BOOT.RAW` 不含文件头，按从上到下、从左到右的顺序存储 RGB565 小端像素，
大小固定为 **307,200 字节**。恢复默认文件只有一个 `0x00` 字节。
文件尺寸不正确时保留已有图片并提示失败；开机找不到有效图片或读取失败时显示内置画面。

## 构建

日常构建使用已收录的中文字形，不需要系统字体或 Pillow：

```bash
firmware/build.sh --locked
```

新增中文文案后，使用宋体重新收集实际用字并更新字库：

```powershell
uv run --with pillow python firmware/tools/mkcjk.py C:/Windows/Fonts/simsun.ttc
```

中文字形采用 15×16 单色笔画行压缩，按控件字号显示。
翻译来源为上述汉化项目的 MIT 代码；中文字形由 SimSun 渲染，字体许可独立于代码许可。

## 已知问题

- 尚未在实机上验证本版本的 USB 导入、开机显示和测量运行。
- 闪存余量较小，新增字形或功能需要重新运行完整构建的空间检查。
- 调试专用的 `memprobe` 构建变体超过 B 区闪存余量要求；正式固件不启用此特性。
