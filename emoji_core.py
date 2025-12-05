import json
import os
import re
import sys
import jieba
from collections import defaultdict
import imageio
from PIL import Image
import numpy as np

# -------------------------- 配置区 --------------------------
EMOJI_GIF_DIR = "emoji_export"
KEYWORD_FILE = "emojiNames.json"
DEFAULT_OUTPUT_FILE = "output.mp4"
CELL_SIZE = 240
VIDEO_HEIGHT = 240
DEFAULT_DURATION_SECONDS = 3
TWOWORD_PHRASE_FILE = "2.json"
THREEWORD_PHRASE_FILE = "3.json"
# 控制每个关键词返回的Emoji最大数量，None表示返回所有
MAX_EMOJI_RESULTS = None  

# -------------------------- 全局变量 --------------------------
emoji_code_to_char = {}
keyword_to_emojis_index = None
two_word_set = set()
three_word_set = set()

def init():
    """
    初始化核心组件，包括加载Emoji关键词和优先词库。
    """
    global keyword_to_emojis_index, two_word_set, three_word_set

    # 初始化关键词索引
    if not os.path.exists(KEYWORD_FILE):
        print(f"❌ 错误：未找到 Emoji 关键词文件 '{KEYWORD_FILE}'！请确保它在项目根目录下。")
        sys.exit(1)
    try:
        with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
            emoji_data = json.load(f)
    except json.JSONDecodeError:
        print(f"❌ 错误：'{KEYWORD_FILE}' 不是有效的 JSON 文件！")
        sys.exit(1)

    keyword_to_emojis_index = defaultdict(list)
    for emoji_char, keywords in emoji_data.items():
        try:
            code_points = [hex(ord(c))[2:].upper() for c in emoji_char]
            emoji_code = '-'.join(code_points)
        except Exception as e:
            continue
        emoji_code_to_char[emoji_code] = emoji_char
        for keyword in keywords:
            if keyword:
                keyword_to_emojis_index[keyword.lower()].append(emoji_code)

    # 加载优先词库
    try:
        if os.path.exists(TWOWORD_PHRASE_FILE):
            with open(TWOWORD_PHRASE_FILE, 'r', encoding='utf-8') as f:
                two_word_set = set(json.load(f))
        else:
            print(f"⚠️  警告：未找到 '{TWOWORD_PHRASE_FILE}'，两字词优先匹配功能已禁用。")

        if os.path.exists(THREEWORD_PHRASE_FILE):
            with open(THREEWORD_PHRASE_FILE, 'r', encoding='utf-8') as f:
                three_word_set = set(json.load(f))
        else:
            print(f"⚠️  警告：未找到 '{THREEWORD_PHRASE_FILE}'，三字词优先匹配功能已禁用。")
    except json.JSONDecodeError as e:
        print(f"❌ 错误：加载优先词组文件时发生 JSON 解析错误！错误: {e}")
        sys.exit(1)

def find_gif_path(emoji_code):
    """
    根据 Emoji 编码查找对应的 GIF 文件路径。
    """
    if not emoji_code:
        return None
    full_path = os.path.join(EMOJI_GIF_DIR, f"U+{emoji_code}", f"U+{emoji_code}.gif")
    return full_path if os.path.exists(full_path) else None

def search_emoji(keyword):
    """
    根据关键词搜索匹配的 Emoji 编码列表。
    """
    if not keyword_to_emojis_index:
        init()

    keyword = keyword.lower().strip()
    if not keyword:
        return []

    matched_emojis = set()

    # 精确匹配
    exact_match = keyword_to_emojis_index.get(keyword, [])
    matched_emojis.update(exact_match)

    # 反向匹配 (关键词包含在 Emoji 名称中)
    for kw, codes in keyword_to_emojis_index.items():
        if keyword in kw and kw != keyword:
            matched_emojis.update(codes)

    # 正向匹配 (Emoji 名称包含在关键词中)
    for kw, codes in keyword_to_emojis_index.items():
        if kw in keyword and kw not in exact_match:
            matched_emojis.update(codes)

    result_list = list(matched_emojis)
    
    # 根据配置项限制返回数量
    if MAX_EMOJI_RESULTS is not None and isinstance(MAX_EMOJI_RESULTS, int):
        return result_list[:MAX_EMOJI_RESULTS]
    
    return result_list

def _split_token_recursively(s):
    """
    递归地在字符串 s 中查找并提取所有可能的优先词。
    采用贪心策略：优先匹配更长的词。对于相同长度，优先匹配右侧的词。
    如果找不到，就返回第一个字符。
    """
    if not s:
        return []

    max_len = 3
    best_match = None
    best_start = -1

    # 1. 查找最佳匹配（最长、最靠右）
    for length in range(max_len, 1, -1):
        # 从右往左查找，优先匹配右侧的词
        for i in range(len(s) - length, -1, -1):
            sub_word = s[i:i+length]
            if (length == 3 and sub_word in three_word_set) or \
               (length == 2 and sub_word in two_word_set):
                best_start = i
                best_match = sub_word
                break
        if best_match:
            break

    # 2. 根据最佳匹配进行拆分
    if best_match:
        left_part = s[:best_start]
        matched_part = best_match
        right_part = s[best_start + len(best_match):]

        result = []
        if left_part:
            result.extend(list(left_part))
        result.append(matched_part)
        if right_part:
            result.extend(_split_token_recursively(right_part))
        return result
    else:
        # 3. 如果没有找到任何优先词，返回第一个字符并递归处理剩余部分
        return [s[0]] + _split_token_recursively(s[1:])

def tokenize_text(text):
    """
    主分词函数：实现 "jieba智能分词 -> 优先词验证 -> 深度递归拆分 -> 拆字fallback" 的完整逻辑。
    """
    if not text:
        return []
    if not two_word_set or not three_word_set:
        init()

    # 1. 过滤无效字符（仅保留中文、英文、数字）
    valid_pattern = re.compile(r'[一-龥a-zA-Z0-9]')
    cleaned_text = ''.join([c for c in text if valid_pattern.match(c)])
    if not cleaned_text:
        return []

    # 2. 使用 jieba 进行初步智能分词
    jieba_tokens = list(jieba.cut(cleaned_text))

    final_tokens = []

    # 3. 遍历 jieba 分词结果，进行验证和深度拆分
    for token in jieba_tokens:
        # 3.1 检查整个 token 是否是优先词，如果是，直接保留
        if len(token) == 2 and token in two_word_set:
            final_tokens.append(token)
        elif len(token) == 3 and token in three_word_set:
            final_tokens.append(token)
        else:
            # 3.2 如果不是，则调用辅助函数对这个 token 进行深度递归拆分
            split_parts = _split_token_recursively(token)
            final_tokens.extend(split_parts)

    return final_tokens

def create_emoji_video(words, selected_emojis, word_char_counts, duration_per_video, output_file=DEFAULT_OUTPUT_FILE):
    """
    根据分词结果、选择的Emoji和视频参数，生成最终的MP4视频。
    """
    if len(words) != len(selected_emojis) or len(words) != len(word_char_counts):
        raise ValueError("❌ 输入参数错误：词语列表、Emoji列表、字数列表的长度必须一致！")

    total_char_count = sum(word_char_counts)
    if total_char_count == 0:
        raise ValueError("❌ 文本错误：无有效字符！")

    if duration_per_video <= 0:
        duration_per_video = DEFAULT_DURATION_SECONDS
        print(f"⚠️  警告：视频时长无效，自动设置为 {DEFAULT_DURATION_SECONDS} 秒。")

    video_width = total_char_count * CELL_SIZE
    print(f"\n🎬 开始生成视频...")
    print(f"📊 视频参数：尺寸 {video_width}×{VIDEO_HEIGHT}px, 时长 {duration_per_video}s, 总字数 {total_char_count}")
    print(f"📁 输出路径：{os.path.abspath(output_file)}")

    # 构建最终的Emoji序列（处理多Emoji循环）
    final_emoji_sequence = []
    for emojis_for_word, char_count in zip(selected_emojis, word_char_counts):
        if not emojis_for_word:
            final_emoji_sequence.extend([None] * char_count)
            continue
        for i in range(char_count):
            emoji_idx = i % len(emojis_for_word)
            final_emoji_sequence.append(emojis_for_word[emoji_idx])

    if all(emoji is None for emoji in final_emoji_sequence):
        raise Warning("⚠️  警告：所有位置均无有效 Emoji，生成的视频将为全黑色！")

    # 预加载所有Emoji的GIF帧数据
    video_fps = 10
    emoji_frames_data = []
    for emoji_code in final_emoji_sequence:
        if emoji_code is None:
            emoji_frames_data.append(None)
            continue

        gif_path = find_gif_path(emoji_code)
        if not gif_path:
            emoji_frames_data.append(None)
            continue

        try:
            with imageio.get_reader(gif_path) as reader:
                frames = [np.asarray(frame) for frame in reader]
                meta_data = reader.get_meta_data()

            if len(frames) == 0:
                raise ValueError("GIF文件为空。")

            # 处理带Alpha通道的GIF，转换为RGB
            processed_frames = []
            for frame in frames:
                if frame.ndim == 3 and frame.shape[-1] == 4:
                    frame = Image.fromarray(frame).convert("RGB")
                    frame = np.asarray(frame)
                processed_frames.append(frame)

            if len(processed_frames) == 0:
                raise ValueError("GIF处理后无有效帧。")

            # 从GIF元数据中获取帧率
            if video_fps == 10 and len(processed_frames) > 0:
                video_fps = meta_data.get('fps', 10)

            emoji_frames_data.append({'frames': processed_frames, 'num_frames': len(processed_frames)})
        except Exception as e:
            print(f"❌ 加载 Emoji (编码: {emoji_code}) 失败，错误：{e}")
            emoji_frames_data.append(None)

    # 计算总帧数并开始绘制
    total_frames = int(duration_per_video * video_fps)
    all_merged_frames = []
    print(f"\n🎨 开始绘制视频帧（共 {total_frames} 帧）...")

    for frame_idx in range(total_frames):
        merged_frame = Image.new('RGB', (video_width, VIDEO_HEIGHT), color='black')
        current_x = 0

        for i, (emoji_data, char_count) in enumerate(zip(emoji_frames_data, [1] * len(emoji_frames_data))):
            if emoji_data is None:
                current_x += CELL_SIZE * char_count
                continue

            # 循环播放GIF帧
            current_gif_frame_idx = frame_idx % emoji_data['num_frames']
            gif_frame = emoji_data['frames'][current_gif_frame_idx]

            if gif_frame.size == 0:
                current_x += CELL_SIZE * char_count
                continue

            # 计算缩放比例以适应单元格
            orig_h, orig_w = gif_frame.shape[:2]
            max_display_width = CELL_SIZE * char_count
            scale = min(max_display_width / orig_w, VIDEO_HEIGHT / orig_h)
            new_w, new_h = int(orig_w * scale), int(orig_h * scale)

            # 缩放并粘贴到合并帧
            gif_img = Image.fromarray(gif_frame)
            resized_gif = gif_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            offset_x = current_x + (max_display_width - new_w) // 2
            offset_y = (VIDEO_HEIGHT - new_h) // 2

            if 0 <= offset_x < video_width and 0 <= offset_y < VIDEO_HEIGHT:
                merged_frame.paste(resized_gif, (offset_x, offset_y))

            current_x += CELL_SIZE * char_count

        all_merged_frames.append(np.asarray(merged_frame))

        # 打印进度
        if (frame_idx + 1) % (max(1, total_frames // 10)) == 0:
            progress = int((frame_idx + 1) / total_frames * 100)
            print(f"⏳ 绘制进度：{progress}%（{frame_idx + 1}/{total_frames} 帧）。")

    if not all_merged_frames:
        raise RuntimeError("❌ 错误：无有效帧数据，无法生成视频！")

    # 写入视频文件
    try:
        print(f"\n💾 正在写入视频文件：{output_file}...")
        imageio.mimsave(output_file, all_merged_frames, fps=video_fps, format='mp4', codec='libx264', quality=9)
    except Exception as e:
        error_msg = f"❌ 写入视频失败：{e}"
        if "ffmpeg" in str(e).lower() or "plugin" in str(e).lower():
            error_msg += "\n   解决方案：请安装 imageio-ffmpeg 依赖 → pip install imageio-ffmpeg"
        raise RuntimeError(error_msg)

    output_path = os.path.abspath(output_file)
    print(f"\n🎉 视频生成成功！\n📁 保存路径：{output_path}\n📊 信息：{video_width}×{VIDEO_HEIGHT}px, {duration_per_video}s, {video_fps} FPS")
    return output_path

# -------------------------- 测试用例 --------------------------
if __name__ == "__main__":
    init()
    print("--- 测试用例 1: '卧闻海棠花' (无匹配词组) ---")
    tokens = tokenize_text("卧闻海棠花")
    print(f"分词结果: {tokens}\n")

    print("--- 测试用例 2: '我有一个新手机' (包含 '手机') ---")
    tokens2 = tokenize_text("我有一个新手机")
    print(f"分词结果: {tokens2}\n")

    print("--- 测试用例 3: '今天是中秋节' (包含 '中秋节') ---")
    tokens3 = tokenize_text("今天是中秋节")
    print(f"分词结果: {tokens3}\n")

    print("--- 测试用例 4: '他在研究人工智能' (包含 '人工', '智能') ---")
    tokens4 = tokenize_text("他在研究人工智能")
    print(f"分词结果: {tokens4}\n")
    
    print("--- 测试用例 5: 搜索 '头' 相关的Emoji ---")
    emojis_for_head = search_emoji("头")
    print(f"与 '头' 相关的Emoji编码: {emojis_for_head}")
    print(f"对应的Emoji字符: {[emoji_code_to_char.get(code, f'[{code}]') for code in emojis_for_head]}")