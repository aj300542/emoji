import json
import os
import re
import sys
import jieba
import numpy as np
from collections import defaultdict
import imageio
from PIL import Image

# -------------------------- 配置区 --------------------------
EMOJI_GIF_DIR = "emoji_export"  # Emoji GIF 存储目录（需包含子目录和 GIF 文件）
KEYWORD_FILE = "emojiNames.json"  # Emoji 关键词映射文件
DEFAULT_OUTPUT_FILE = "output.mp4"  # 默认输出文件名
CELL_SIZE = 240  # 每个字符的宽度（像素）
VIDEO_HEIGHT = 240  # 视频高度（像素）
DEFAULT_DURATION_SECONDS = 3  # 默认视频时长（秒）
FONT_PATH = "C:/Windows/Fonts/simhei.ttf"  # 备用字体路径（当前逻辑未用到）

# -------------------------- 全局变量 --------------------------
emoji_code_to_char = {}  # Emoji 编码 -> 字符映射（如 "1F600" -> "😀"）
keyword_to_emojis_index = None  # 关键词 -> Emoji 编码列表映射（如 "开心" -> ["1F600", "1F601"]）

def init():
    """
    初始化 Emoji 关键词索引和编码映射
    从 emojiNames.json 读取数据，构建搜索索引
    """
    global keyword_to_emojis_index
    print("\n🔧 正在初始化 Emoji 核心逻辑...")

    # 1. 检查关键词文件是否存在
    if not os.path.exists(KEYWORD_FILE):
        print(f"❌ 错误：未找到 Emoji 关键词文件 '{KEYWORD_FILE}'，请放在项目根目录！")
        sys.exit(1)

    # 2. 检查 Emoji GIF 目录是否存在
    if not os.path.isdir(EMOJI_GIF_DIR):
        print(f"❌ 错误：未找到 Emoji GIF 目录 '{EMOJI_GIF_DIR}'，请确保目录存在且包含 GIF 文件！")
        sys.exit(1)

    # 3. 读取并解析关键词文件
    try:
        with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
            emoji_data = json.load(f)
    except json.JSONDecodeError:
        print(f"❌ 错误：'{KEYWORD_FILE}' 不是有效的 JSON 文件，请检查格式！")
        sys.exit(1)

    # 4. 构建关键词索引和编码映射
    keyword_to_emojis_index = defaultdict(list)
    for emoji_char, keywords in emoji_data.items():
        try:
            # 处理多码点 Emoji（如带皮肤 tone 的 Emoji："😀🏻" -> "1F600-1F3FB"）
            code_points = [hex(ord(c))[2:].upper() for c in emoji_char]
            emoji_code = '-'.join(code_points)
        except Exception as e:
            print(f"⚠️  警告：跳过无法处理的 Emoji '{emoji_char}'，错误：{str(e)}")
            continue

        # 存储编码 -> 字符映射
        emoji_code_to_char[emoji_code] = emoji_char

        # 存储关键词 -> 编码映射（支持多个关键词）
        for keyword in keywords:
            if keyword:  # 跳过空关键词
                keyword_to_emojis_index[keyword.lower()].append(emoji_code)

    print(f"✅ 初始化成功！加载 {len(emoji_data)} 个 Emoji，支持关键词搜索。")

def find_gif_path(emoji_code):
    """
    根据 Emoji 编码查找对应的 GIF 文件路径
    :param emoji_code: Emoji 编码（如 "1F600"、"1F600-1F3FB"）
    :return: GIF 文件绝对路径（未找到返回 None）
    """
    if not emoji_code:
        print("⚠️  警告：Emoji 编码为空，跳过查找。")
        return None

    # 构建 GIF 文件路径（格式：emoji_export/U+编码/U+编码.gif）
    dir_name = f"U+{emoji_code}"
    file_name = f"U+{emoji_code}.gif"
    full_path = os.path.join(EMOJI_GIF_DIR, dir_name, file_name)

    # 检查路径是否存在
    if not os.path.exists(full_path):
        print(f"❌ 错误：未找到 Emoji GIF 文件！路径：{full_path}")
        print(f"   请确认：1. '{EMOJI_GIF_DIR}' 目录下存在子目录 '{dir_name}'；2. 子目录下有 '{file_name}' 文件。")
        return None

    print(f"📂 找到 GIF 文件：{full_path}")
    return full_path

def search_emoji(keyword):
    """
    根据关键词搜索匹配的 Emoji 编码
    :param keyword: 搜索关键词（如 "开心"、"哭"）
    :return: 匹配的 Emoji 编码列表（最多返回 5 个结果）
    """
    # 确保初始化已完成
    if not keyword_to_emojis_index:
        init()

    # 预处理关键词（转为小写、去除首尾空格）
    keyword = keyword.lower().strip()
    if not keyword:
        return []

    # 存储所有匹配的 Emoji 编码（去重）
    matched_emojis = set()

    # 1. 精确匹配（关键词完全一致）
    exact_match = keyword_to_emojis_index.get(keyword, [])
    matched_emojis.update(exact_match)

    # 2. 反向匹配（关键词包含在 Emoji 名称中，如关键词 "笑" 匹配 "大笑"）
    reverse_match = []
    for kw, codes in keyword_to_emojis_index.items():
        if keyword in kw and kw != keyword:
            reverse_match.extend(codes)
    matched_emojis.update(reverse_match)

    # 3. 正向匹配（Emoji 名称包含在关键词中，如关键词 "大笑" 匹配 "笑"）
    forward_match = []
    for kw, codes in keyword_to_emojis_index.items():
        if kw in keyword and kw not in exact_match:
            forward_match.extend(codes)
    matched_emojis.update(forward_match)

    # 限制最多返回 5 个结果
    return list(matched_emojis)[:5]

def tokenize_text(text):
    """
    文本分词（仅保留中文、英文、数字，过滤特殊字符）
    :param text: 待分词文本（如 "我来到黄州"）
    :return: 分词结果列表（如 ["我", "来到", "黄州"]）
    """
    if not text:
        return []

    # 1. 分词（使用 jieba 分词）
    words = jieba.lcut(text)

    # 2. 过滤无效字符（仅保留中文、英文、数字）
    valid_pattern = re.compile(r'[一-龥a-zA-Z0-9]+')
    valid_words = [word.strip() for word in words if valid_pattern.search(word)]

    return valid_words

def find_emojis_recursive(text, depth=0, max_depth=3):
    """
    递归查找文本对应的 Emoji（支持多词组合和单字拆分）
    :param text: 待查找文本（如 "我来到黄州"）
    :param depth: 当前递归深度（默认 0）
    :param max_depth: 最大递归深度（默认 3，避免无限递归）
    :return: (是否找到匹配 Emoji, 匹配的 Emoji 编码列表)
    """
    # 递归终止条件：深度超过限制或文本为空
    if depth >= max_depth or not text.strip():
        return (False, [])

    # 1. 优先精确匹配完整文本
    emojis = search_emoji(text.strip())
    if emojis:
        return (True, emojis)

    # 2. 分词后递归匹配每个词
    words = tokenize_text(text)
    if not words:
        return (False, [])

    # 3. 处理单字情况（如果分词后只有一个词且长度 > 1，拆分为单字）
    if len(words) == 1 and len(words[0]) > 1:
        words = list(words[0])

    # 4. 递归匹配每个词
    all_emojis = []
    for word in words:
        found, sub_emojis = find_emojis_recursive(word, depth + 1, max_depth)
        if found:
            all_emojis.extend(sub_emojis)

    return (bool(all_emojis), all_emojis)

def create_emoji_video(words, selected_emojis, word_char_counts, duration_per_video, output_file=DEFAULT_OUTPUT_FILE):
    """
    生成 Emoji 视频（核心功能）
    :param words: 分词列表（如 ["我", "来到", "黄州"]）
    :param selected_emojis: 每个词语的选中 Emoji 编码列表（二维列表，如 [["1F600"], ["1F601", "1F602"], ["1F3EF"]]）
    :param word_char_counts: 每个词语的字数（如 [1, 2, 2]）
    :param duration_per_video: 视频时长（秒）
    :param output_file: 自定义输出文件路径（默认 "output.mp4"）
    :return: 视频保存绝对路径
    """
    # 1. 参数合法性校验
    if len(words) != len(selected_emojis) or len(words) != len(word_char_counts):
        raise ValueError("❌ 输入参数错误：词语列表、Emoji 列表、字数列表长度必须一致！")

    total_char_count = sum(word_char_counts)
    if total_char_count == 0:
        raise ValueError("❌ 文本错误：无有效字符（仅支持中文、英文、数字）！")

    if duration_per_video <= 0:
        duration_per_video = DEFAULT_DURATION_SECONDS
        print(f"⚠️  警告：视频时长无效，自动设置为 {DEFAULT_DURATION_SECONDS} 秒。")

    # 2. 视频基础参数计算
    video_width = total_char_count * CELL_SIZE
    print(f"\n🎬 开始生成视频...")
    print(f"📊 视频参数：")
    print(f"   - 尺寸：{video_width}×{VIDEO_HEIGHT} 像素")
    print(f"   - 时长：{duration_per_video} 秒")
    print(f"   - 总字数：{total_char_count}")
    print(f"   - 输出路径：{os.path.abspath(output_file)}")

    # 3. 生成最终的 Emoji 序列（循环填充选中的 Emoji）
    final_emoji_sequence = []
    for emojis_for_word, char_count in zip(selected_emojis, word_char_counts):
        if not emojis_for_word:  # 该词语未选择任何 Emoji，填充 None
            final_emoji_sequence.extend([None] * char_count)
            continue

        # 循环使用选中的 Emoji 填充对应字数的位置（如 2 个字配 3 个 Emoji → [0, 1]）
        for i in range(char_count):
            emoji_idx = i % len(emojis_for_word)
            final_emoji_sequence.append(emojis_for_word[emoji_idx])

    print(f"📋 最终 Emoji 序列（长度：{len(final_emoji_sequence)}）：{final_emoji_sequence}")

    # 检查是否有有效 Emoji
    if all(emoji is None for emoji in final_emoji_sequence):
        raise Warning("⚠️  警告：所有位置均无有效 Emoji，生成的视频将为全黑色！")

    # 4. 加载所有 Emoji 的 GIF 帧（核心修复：numpy 数组布尔判断错误）
    video_fps = 10  # 默认帧率（可从 GIF 中读取实际帧率）
    emoji_frames_data = []  # 存储每个位置的 Emoji 帧数据（与 final_emoji_sequence 一一对应）

    for emoji_code in final_emoji_sequence:
        if emoji_code is None:
            emoji_frames_data.append(None)
            continue

        # 4.1 查找 GIF 文件路径
        gif_path = find_gif_path(emoji_code)
        if not gif_path:
            emoji_frames_data.append(None)
            continue

        # 4.2 读取并处理 GIF 帧
        try:
            # 使用 imageio 读取 GIF 所有帧（返回 numpy 数组列表）
            with imageio.get_reader(gif_path) as reader:
                frames = [np.asarray(frame) for frame in reader]
                meta_data = reader.get_meta_data()

            # 检查帧是否有效（用帧数量判断，避免直接对 numpy 数组做布尔判断）
            if len(frames) == 0:
                raise ValueError("GIF 文件为空，无有效帧。")

            # 4.3 处理帧格式（RGBA → RGB，去除透明通道；确保帧尺寸有效）
            processed_frames = []
            for frame in frames:
                # 跳过无效帧（如空数组、尺寸异常）
                if frame is None or frame.size == 0 or len(frame.shape) < 2:
                    continue

                # 若为 RGBA 格式，转为 RGB（避免透明通道导致的绘制异常）
                if frame.ndim == 3 and frame.shape[-1] == 4:
                    frame = Image.fromarray(frame).convert("RGB")
                    frame = np.asarray(frame)

                processed_frames.append(frame)

            # 检查处理后的帧是否有效
            if len(processed_frames) == 0 or not all(f.size > 0 for f in processed_frames):
                raise ValueError("GIF 处理后无有效帧。")

            # 4.4 从第一个有效 GIF 读取帧率（覆盖默认值）
            if video_fps == 10 and len(processed_frames) > 0:
                video_fps = meta_data.get('fps', 10)
                print(f"⚡ 从 GIF 读取帧率：{video_fps} FPS（默认 10 FPS）。")

            # 4.5 存储帧数据（帧列表 + 帧数量）
            emoji_frames_data.append({
                'frames': processed_frames,
                'num_frames': len(processed_frames)
            })

            # 打印加载成功信息
            emoji_char = emoji_code_to_char.get(emoji_code, emoji_code)
            print(f"✅ 加载成功：Emoji '{emoji_char}'（编码：{emoji_code}），共 {len(processed_frames)} 帧。")

        except Exception as e:
            print(f"❌ 加载 Emoji 失败（编码：{emoji_code}），错误：{str(e)}")
            emoji_frames_data.append(None)

    # 5. 逐帧绘制视频画面
    total_frames = int(duration_per_video * video_fps)  # 视频总帧数
    all_merged_frames = []  # 存储所有绘制完成的帧（用于后续写入视频）

    print(f"\n🎨 开始绘制视频帧（共 {total_frames} 帧）...")
    for frame_idx in range(total_frames):
        # 5.1 创建黑色背景画布（RGB 格式）
        merged_frame = Image.new('RGB', (video_width, VIDEO_HEIGHT), color='black')
        current_x = 0  # 当前绘制的 X 坐标（每个字符占 CELL_SIZE 宽度）

        # 5.2 遍历每个位置，绘制对应的 Emoji 帧
        for i, (emoji_data, char_count) in enumerate(zip(emoji_frames_data, [1] * len(emoji_frames_data))):
            if emoji_data is None:
                # 无有效 Emoji，跳过绘制，直接移动 X 坐标
                current_x += CELL_SIZE * char_count
                continue

            # 5.2.1 获取当前要绘制的 GIF 帧（循环播放）
            current_gif_frame_idx = frame_idx % emoji_data['num_frames']
            gif_frame = emoji_data['frames'][current_gif_frame_idx]

            # 跳过无效帧
            if gif_frame is None or gif_frame.size == 0:
                current_x += CELL_SIZE * char_count
                continue

            # 5.2.2 计算 Emoji 缩放尺寸（保持宽高比，不超过单元格大小）
            orig_h, orig_w = gif_frame.shape[:2]  # numpy 数组形状：(高度, 宽度, 通道)
            max_display_width = CELL_SIZE * char_count  # 最大显示宽度（当前词语的总宽度）
            max_display_height = VIDEO_HEIGHT  # 最大显示高度（视频高度）

            # 计算缩放比例（取宽、高中的较小值，避免超出边界）
            scale = min(max_display_width / orig_w, max_display_height / orig_h)

            # 避免缩放比例为 0（极端情况处理）
            if scale <= 0:
                scale = 1.0

            # 计算缩放后的尺寸（整数）
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)

            # 5.2.3 缩放 Emoji 帧（保持清晰度）
            gif_img = Image.fromarray(gif_frame)
            resized_gif = gif_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # 5.2.4 计算居中绘制的坐标（水平居中 + 垂直居中）
            offset_x = current_x + (max_display_width - new_w) // 2  # 水平居中
            offset_y = (VIDEO_HEIGHT - new_h) // 2  # 垂直居中

            # 5.2.5 绘制到画布（确保坐标在有效范围内）
            if 0 <= offset_x < video_width and 0 <= offset_y < VIDEO_HEIGHT:
                merged_frame.paste(resized_gif, (offset_x, offset_y))

            # 5.2.6 移动 X 坐标，准备绘制下一个位置
            current_x += CELL_SIZE * char_count

        # 5.3 将绘制完成的帧添加到列表
        all_merged_frames.append(np.asarray(merged_frame))

        # 5.4 打印绘制进度（每 10% 反馈一次）
        if (frame_idx + 1) % (max(1, total_frames // 10)) == 0:
            progress = int((frame_idx + 1) / total_frames * 100)
            print(f"⏳ 绘制进度：{progress}%（已完成 {frame_idx + 1}/{total_frames} 帧）。")

    # 6. 写入视频文件（核心修复：明确编码格式，确保兼容性）
    if not all_merged_frames or len(all_merged_frames) == 0:
        raise RuntimeError("❌ 错误：无有效帧数据，无法生成视频！")

    try:
        print(f"\n💾 正在写入视频文件：{output_file}...")
        # 使用 imageio 写入 MP4 视频（指定 H.264 编码，确保兼容性）
        imageio.mimsave(
            output_file,
            all_merged_frames,
            fps=video_fps,
            format='mp4',
            codec='libx264',  # 明确指定编码，避免默认编码问题
            quality=9  # 视频质量（0-10，10 最高）
        )
    except Exception as e:
        error_msg = f"❌ 写入视频失败：{str(e)}"
        # 处理 ffmpeg 依赖缺失问题
        if "ffmpeg" in str(e).lower() or "plugin" in str(e).lower():
            error_msg += "\n   解决方案：安装 imageio-ffmpeg 依赖 → pip install imageio-ffmpeg"
        raise RuntimeError(error_msg)

    # 7. 返回视频保存绝对路径
    output_path = os.path.abspath(output_file)
    print(f"\n🎉 视频生成成功！")
    print(f"📁 保存路径：{output_path}")
    print(f"📊 视频信息：{video_width}×{VIDEO_HEIGHT} 像素，{duration_per_video} 秒，{video_fps} FPS")
    return output_path

# -------------------------- 测试用例 --------------------------
if __name__ == "__main__":
    # 初始化 Emoji 核心逻辑
    init()

    # 测试参数（模拟 GUI 传递的参数）
    test_words = ["我", "来到", "黄州"]
    test_selected_emojis = [["1F600"], ["1F601", "1F602"], ["1F3EF"]]  # 每个词语的选中 Emoji
    test_word_char_counts = [1, 2, 2]  # 每个词语的字数
    test_duration = 3  # 视频时长（秒）
    test_output_file = "test_output.mp4"  # 测试输出文件名

    try:
        # 生成视频
        video_path = create_emoji_video(
            words=test_words,
            selected_emojis=test_selected_emojis,
            word_char_counts=test_word_char_counts,
            duration_per_video=test_duration,
            output_file=test_output_file
        )
        print(f"\n✅ 测试用例执行成功！视频路径：{video_path}")
    except Exception as e:
        print(f"\n❌ 测试用例执行失败：{str(e)}")
        sys.exit(1)