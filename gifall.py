from PIL import Image, ImageEnhance
import os
import glob
import time

# 修复tqdm导入（关键）
try:
    from tqdm import tqdm  # 正确导入tqdm类
except ImportError:
    print("⚠️ 缺少tqdm库，正在自动安装...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "tqdm"])
    from tqdm import tqdm  # 安装后重新导入

def create_contrast_curve():
    """S形曲线增强对比度"""
    curve = []
    for input_val in range(256):
        if input_val < 64:
            output_val = 10 + (input_val * 70) / 63
        elif input_val < 192:
            output_val = 80 + ((input_val - 64) * 120) / (191 - 64)
        else:
            output_val = 200 + ((input_val - 192) * 55) / (255 - 192)
        output_val = min(255, int(output_val))
        output_val = max(input_val, output_val)  # 确保整体提亮
        curve.append(output_val)
    return curve

def warm_up_image(frame, red_gain=1.15, green_gain=1.1, blue_attn=0.85):
    """调节图像为暖色"""
    pixels = frame.load()
    width, height = frame.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if a == 0:  # 跳过透明像素
                continue
            
            # 调整色道
            r = int(r * red_gain)
            g = int(g * green_gain)
            b = int(b * blue_attn)
            
            # 限制范围
            r = max(0, min(255, r))
            g = max(0, min(255, g))
            b = max(0, min(255, b))
            
            pixels[x, y] = (r, g, b, a)
    return frame

def process_single_gif(
    input_path,
    output_root,
    black_point=15,
    white_point=240,
    contrast_factor=1.3,
    red_gain=1.15,
    green_gain=1.1,
    blue_attn=0.85
):
    try:
        output_dir = os.path.join(output_root, "new")
        os.makedirs(output_dir, exist_ok=True)
        
        file_name = os.path.basename(input_path)
        name_without_ext, ext = os.path.splitext(file_name)
        output_file = f"{name_without_ext}s{ext}"
        output_path = os.path.join(output_dir, output_file)

        contrast_curve = create_contrast_curve()

        with Image.open(input_path) as im:
            frames = []
            durations = []
            loop = im.info.get('loop', 0)

            frame_idx = 0
            while True:
                try:
                    durations.append(im.info.get('duration', 100))
                    frame = im.convert("RGBA")
                    pixels = frame.load()
                    width, height = frame.size

                    # 1. 色阶调整
                    range_scale = 255.0 / max(1, white_point - black_point)
                    for y in range(height):
                        for x in range(width):
                            r, g, b, a = pixels[x, y]
                            if a == 0:
                                continue
                            r = int(max(0, min(255, r - black_point)) * range_scale)
                            g = int(max(0, min(255, g - black_point)) * range_scale)
                            b = int(max(0, min(255, b - black_point)) * range_scale)
                            pixels[x, y] = (r, g, b, a)

                    # 2. S形曲线增强对比度
                    for y in range(height):
                        for x in range(width):
                            r, g, b, a = pixels[x, y]
                            if a == 0:
                                continue
                            r = contrast_curve[r]
                            g = contrast_curve[g]
                            b = contrast_curve[b]
                            pixels[x, y] = (r, g, b, a)

                    # 3. 调节为暖色
                    frame = warm_up_image(frame, red_gain, green_gain, blue_attn)

                    # 4. 增强对比度
                    enhancer = ImageEnhance.Contrast(frame)
                    frame_contrasted = enhancer.enhance(contrast_factor)
                    frames.append(frame_contrasted)

                    frame_idx += 1
                    im.seek(frame_idx)

                except EOFError:
                    break

            if frames:
                frames[0].save(
                    output_path,
                    format='GIF',
                    append_images=frames[1:],
                    save_all=True,
                    duration=durations,
                    loop=loop,
                    disposal=2,
                    optimize=False
                )
        return True, output_file  # 成功返回True和文件名
    except Exception as e:
        return False, f"{os.path.basename(input_path)}（错误：{str(e)}）"  # 失败返回False和错误信息

def format_time(seconds):
    """将秒数转换为 时:分:秒 格式"""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def batch_process_gifs(root_dir):
    # 获取根目录下所有GIF文件
    gif_files = glob.glob(os.path.join(root_dir, "*.gif"))
    total = len(gif_files)
    
    if total == 0:
        print("⚠️ 未在根目录找到任何GIF文件")
        return
    
    print(f"📌 批量处理开始 | 总文件数：{total}")
    start_time = time.time()  # 记录开始时间
    success_count = 0
    fail_count = 0
    fail_list = []
    
    # 修复后的tqdm调用（直接使用tqdm类）
    with tqdm(total=total, desc="处理进度", unit="文件", ncols=100) as pbar:
        for i, gif_path in enumerate(gif_files, 1):
            # 处理单个文件
            success, result = process_single_gif(
                input_path=gif_path,
                output_root=root_dir,
                black_point=15,
                white_point=240,
                contrast_factor=1.3,
                red_gain=1.00,
                green_gain=1.0,
                blue_attn=0.95
            )
            
            # 更新统计
            if success:
                success_count += 1
            else:
                fail_count += 1
                fail_list.append(result)
            
            # 计算耗时和剩余时间
            elapsed = time.time() - start_time
            avg_time_per_file = elapsed / i  # 平均每个文件耗时
            remaining = avg_time_per_file * (total - i)  # 预估剩余时间
            
            # 更新进度条信息（优化显示格式）
            pbar.set_postfix({
                "已用时间": format_time(elapsed),
                "剩余时间": format_time(remaining),
                "成功": success_count,
                "失败": fail_count
            })
            pbar.update(1)  # 进度条+1
    
    # 处理完成后显示汇总信息
    total_time = time.time() - start_time
    print("\n" + "="*50)
    print(f"🎉 批量处理完成 | 总耗时：{format_time(total_time)}")
    print(f"📊 统计：总{total}个 | 成功{success_count}个 | 失败{fail_count}个")
    if fail_count > 0:
        print("❌ 失败文件列表：")
        for fail in fail_list[:10]:  # 只显示前10个失败文件，避免输出过长
            print(f"  - {fail}")
        if len(fail_list) > 10:
            print(f"  - 还有{len(fail_list)-10}个文件处理失败，可查看日志详情")
    print(f"📦 结果保存目录：{os.path.join(root_dir, 'new')}")
    print("="*50)

if __name__ == "__main__":
    # 根目录路径
    ROOT_DIR = r"Z:\2025\emojigif"
    batch_process_gifs(ROOT_DIR)