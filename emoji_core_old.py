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
# GIF文件存放目录
EMOJI_GIF_DIR = "emoji_export"
# Emoji关键词映射文件
KEYWORD_FILE = "emojiNames.json"
# 最终生成的视频文件名
OUTPUT_VIDEO_FILE = "output.mp4"
# 视频固定高度
VIDEO_HEIGHT = 240
# 每个Emoji默认显示秒数
DEFAULT_DURATION_SECONDS = 3

# -------------------------- 全局变量 --------------------------
# 存储：Emoji编码 -> Emoji字符 (e.g., "1F600" -> "😀")
emoji_code_to_char = {}
# 存储：关键词 -> Emoji编码列表 (e.g., "微笑" -> ["1F600", "1F601"])
keyword_to_emojis_index = None

def init():
    """
    初始化函数：加载 emojiNames.json 并建立搜索索引。
    脚本启动时自动执行。
    """
    global keyword_to_emojis_index
    print("🔧 正在初始化Emoji核心逻辑...")

    # 检查 emojiNames.json 文件是否存在
    if not os.path.exists(KEYWORD_FILE):
        print(f"❌ 错误：未找到 {KEYWORD_FILE} 文件，请确保它与脚本在同一目录下！")
        sys.exit(1)

    # 加载并解析 JSON 文件
    try:
        with open(KEYWORD_FILE, 'r', encoding='utf-8') as f:
            emoji_data = json.load(f)
    except json.JSONDecodeError:
        print(f"❌ 错误：{KEYWORD_FILE} 文件格式不正确，请检查是否为有效的JSON！")
        sys.exit(1)

    # 构建反向索引和编码-字符映射
    _keyword_to_emojis = defaultdict(list)
    for emoji_char, keywords in emoji_data.items():
        try:
            # 计算每个Emoji字符的Unicode编码
            code_points = [hex(ord(c))[2:].upper() for c in emoji_char]
            emoji_code = '-'.join(code_points)
        except Exception as e:
            print(f"⚠️  警告：跳过无法处理的Emoji字符 '{emoji_char}'，错误：{str(e)}")
            continue

        emoji_code_to_char[emoji_code] = emoji_char

        # 将每个关键词（转为小写）与Emoji编码关联
        for keyword in keywords:
            _keyword_to_emojis[keyword.lower()].append(emoji_code)

    keyword_to_emojis_index = _keyword_to_emojis
    print(f"✅ 初始化成功！加载了 {KEYWORD_FILE} 中的 {len(emoji_data)} 个Emoji定义。")

def find_gif_path(emoji_code):
    """
    根据Emoji编码查找对应的GIF文件路径。
    适配目录结构: emoji_export/U+<emoji_code>/U+<emoji_code>.gif

    :param emoji_code: Emoji的Unicode编码 (e.g., "1F43B")
    :return: GIF文件路径 (未找到返回None)
    """
    if not emoji_code or not os.path.isdir(EMOJI_GIF_DIR):
        return None

    # 构建完整的文件路径
    dir_name = f"U+{emoji_code}"
    file_name = f"U+{emoji_code}.gif"
    full_gif_path = os.path.join(EMOJI_GIF_DIR, dir_name, file_name)

    if os.path.exists(full_gif_path):
        return full_gif_path
    else:
        # 未找到时打印调试信息
        emoji_char = emoji_code_to_char.get(emoji_code, emoji_code)
        # print(f"⚠️  警告：未找到Emoji '{emoji_char}' 对应的GIF文件。期望路径: {os.path.abspath(full_gif_path)}")
        return None

def search_emoji(keyword):
    """
    根据关键词搜索最相关的Emoji。
    搜索优先级: 精确匹配 > 反向模糊匹配 > 正向模糊匹配

    :param keyword: 搜索关键词 (e.g., "猫", "炸鸡", "年")
    :return: 匹配的Emoji编码列表，按相关性排序
    """
    if not keyword_to_emojis_index:
        init()

    keyword = keyword.lower().strip()
    if not keyword:
        return []

    matched_emojis = set()
    exact_match_list = []
    reverse_match_list = []

    # 1. 精确匹配 (优先级最高)
    if keyword in keyword_to_emojis_index:
        exact_match_list = keyword_to_emojis_index[keyword]
        matched_emojis.update(exact_match_list)

    # 2. 反向模糊匹配 (Emoji的关键词包含输入的关键词, 优先级次之)
    # e.g., 输入 "年"，匹配关键词为 "年历", "新年" 等的Emoji
    for kw, codes in keyword_to_emojis_index.items():
        if keyword in kw and kw != keyword: # 排除已经精确匹配过的
            reverse_match_list.extend(codes)
            matched_emojis.update(codes)

    # 3. 正向模糊匹配 (输入的关键词包含Emoji的关键词, 优先级最低)
    # e.g., 输入 "年历"，匹配关键词为 "年" 的Emoji
    forward_match_list = []
    for kw, codes in keyword_to_emojis_index.items():
        if kw in keyword and kw not in exact_match_list: # 排除已经精确匹配过的
             forward_match_list.extend(codes)
             matched_emojis.update(codes)

    # 合并结果并去重，保持优先级顺序
    final_sorted_codes = []
    seen = set()
    
    # 先添加精确匹配的
    for code in exact_match_list:
        if code not in seen:
            seen.add(code)
            final_sorted_codes.append(code)
            
    # 再添加反向模糊匹配的
    for code in reverse_match_list:
        if code not in seen:
            seen.add(code)
            final_sorted_codes.append(code)
            
    # 最后添加正向模糊匹配的
    for code in forward_match_list:
        if code not in seen:
            seen.add(code)
            final_sorted_codes.append(code)

    return final_sorted_codes

def tokenize_text(text):
    """
    使用jieba库对中文文本进行分词。

    :param text: 待分词的中文文本 (e.g., "今天吃炸鸡")
    :return: 分词后的词语列表 (e.g., ["今天", "吃", "炸鸡"])
    """
    if not text:
        return []

    # 使用jieba进行精确分词
    words = jieba.lcut(text)

    # 过滤掉纯标点符号、空字符串和只包含空格的字符串
    # 正则表达式匹配至少包含一个汉字、字母或数字的词
    valid_pattern = re.compile(r'[一-龥a-zA-Z0-9]+')
    valid_words = [word.strip() for word in words if valid_pattern.search(word)]

    return valid_words

def find_emojis_recursive(text, depth=0, max_depth=3):
    """
    递归地为文本查找匹配的Emoji。
    如果直接搜索失败，会尝试分词后再逐个搜索。
    如果分词结果不变，则强制进行单字拆分。

    :param text: 待查找Emoji的文本
    :param depth: 当前递归深度
    :param max_depth: 最大递归深度，防止无限递归
    :return: 一个元组，包含(是否成功匹配, 找到的Emoji编码列表)
    """
    if depth >= max_depth:
        return (False, [])

    text = text.strip()
    if not text:
        return (False, [])

    # 1. 尝试直接为整个文本搜索Emoji
    emojis = search_emoji(text)
    if emojis:
        return (True, emojis)
    else:
        # 2. 如果直接搜索失败，则进行分词
        words = tokenize_text(text)

        # 3. 判断是否需要强制单字拆分
        # 如果分词结果和原文本一样（无法再分），则强制拆分成单个汉字
        if len(words) == 1 and words[0] == text:
            # 检查是否已经是单字，避免无限递归
            if len(text) == 1:
                return (False, []) # 单字也找不到，返回失败
            # 强制单字拆分
            words = list(text) 

        # 4. 对分词后的每个词递归调用此函数
        all_emojis = []
        for word in words:
            found, sub_emojis = find_emojis_recursive(word, depth + 1, max_depth)
            if found:
                all_emojis.extend(sub_emojis)

        # 5. 如果所有子词都找不到，返回失败
        if not all_emojis:
            return (False, [])
        
        # 6. 返回成功和收集到的Emoji列表
        return (True, all_emojis)

def create_emoji_video(selected_emoji_codes, duration_per_emoji):
    """
    根据选中的Emoji编码列表生成MP4视频。
    新逻辑：所有Emoji在同一画面中并排同时播放。

    :param selected_emoji_codes: 选中的Emoji编码列表
    :param duration_per_emoji: 每个Emoji显示的秒数 (这里指整个视频的时长)
    :return: 生成的视频文件路径
    :raises ValueError: 如果输入无效
    :raises RuntimeError: 如果视频生成失败
    """
    if not selected_emoji_codes:
        raise ValueError("❌ 生成视频失败：未选中任何Emoji！")

    if duration_per_emoji <= 0:
        duration_per_emoji = DEFAULT_DURATION_SECONDS
        print(f"⚠️  警告：显示秒数无效，已自动改为默认 {DEFAULT_DURATION_SECONDS} 秒！")

    print("\n🎬 开始生成视频...")
    
    # --- 准备工作：加载所有有效的GIF帧和元数据 ---
    emoji_data = []  # 存储 (emoji_char, frames, num_frames)
    video_fps = 10   # 默认帧率

    for emoji_code in selected_emoji_codes:
        gif_path = find_gif_path(emoji_code)
        if not gif_path:
            emoji_char = emoji_code_to_char.get(emoji_code, emoji_code)
            print(f"⚠️  跳过无法找到的Emoji '{emoji_char}' ({emoji_code})")
            continue

        try:
            frames = imageio.mimread(gif_path)
            if not frames:
                print(f"⚠️  警告：'{emoji_char}' 的GIF文件为空或无法读取，跳过。")
                continue
            
            # 统一转换为RGB
            processed_frames = []
            for frame in frames:
                if not isinstance(frame, np.ndarray):
                    frame = np.asarray(frame)
                if frame.ndim == 3 and frame.shape[-1] == 4:
                    img_rgba = Image.fromarray(frame)
                    img_rgb = img_rgba.convert("RGB")
                    frame = np.asarray(img_rgb)
                
                # 缩放每一帧到 240x240
                img = Image.fromarray(frame)
                resized_img = img.resize((VIDEO_HEIGHT, VIDEO_HEIGHT), Image.Resampling.LANCZOS)
                processed_frames.append(np.asarray(resized_img))

            # 只从第一个有效GIF获取帧率
            if not emoji_data:
                with imageio.get_reader(gif_path) as temp_reader:
                    meta_data = temp_reader.get_meta_data()
                    video_fps = meta_data.get('fps', 10)
            
            emoji_char = emoji_code_to_char.get(emoji_code, emoji_code)
            emoji_data.append( (emoji_char, processed_frames, len(processed_frames)) )
            print(f"✅ 已加载Emoji '{emoji_char}'")

        except Exception as e:
            emoji_char = emoji_code_to_char.get(emoji_code, emoji_code)
            print(f"⚠️  警告：加载 '{emoji_char}' 的GIF时出错，跳过。错误：{str(e)}")
            continue

    if not emoji_data:
        raise RuntimeError("❌ 生成视频失败：没有找到可用于生成视频的有效GIF！")

    num_emojis = len(emoji_data)
    total_width = VIDEO_HEIGHT * num_emojis
    total_height = VIDEO_HEIGHT
    total_frames = int(duration_per_emoji * video_fps)

    print(f"📊 视频参数：帧率 {video_fps} FPS，时长 {duration_per_emoji} 秒")
    print(f"📊 视频尺寸：{total_width}x{total_height} (宽x高)")
    print(f"📊 总帧数：{total_frames}")
    
    all_merged_frames = []
    
    # --- 核心逻辑：逐帧合并所有Emoji的画面 ---
    for i in range(total_frames):
        # 创建一个黑色背景的新画布
        merged_frame = np.zeros((total_height, total_width, 3), dtype=np.uint8)
        
        for j, (emoji_char, frames, num_frames) in enumerate(emoji_data):
            # 计算当前Emoji应该显示的帧索引（循环播放）
            frame_idx = i % num_frames
            current_frame = frames[frame_idx]
            
            # 计算当前Emoji在画布上的位置
            x_offset = j * VIDEO_HEIGHT
            y_offset = 0
            
            # 将当前Emoji的帧绘制到画布上
            merged_frame[y_offset:y_offset+VIDEO_HEIGHT, x_offset:x_offset+VIDEO_HEIGHT] = current_frame
        
        all_merged_frames.append(merged_frame)
        
        # 打印进度
        if (i + 1) % (total_frames // 10) == 0:
            print(f"⏳ 进度: {(i + 1) // (total_frames // 10) * 10}%")

    # --- 写入视频文件 ---
    try:
        writer = imageio.get_writer(OUTPUT_VIDEO_FILE, fps=video_fps)
        for frame in all_merged_frames:
            writer.append_data(frame)
        writer.close()
    except Exception as e:
        raise RuntimeError(f"❌ 写入视频文件失败：{str(e)}")

    output_path = os.path.abspath(OUTPUT_VIDEO_FILE)
    print(f"\n🎉 视频生成成功！已保存为：{output_path}")
    return output_path

# -------------------------- 初始化与测试 --------------------------
if __name__ == "__main__":
    # 自动初始化
    init()

    print("\n" + "="*50)
    print("📌 开始功能测试...")
    print("="*50)

    # 测试分词功能
    test_text = "今天天气真好，我想吃炸鸡，然后去公园散步。"
    tokenized_words = tokenize_text(test_text)
    print(f"\n[测试1/4] 中文分词:")
    print(f"  输入: {test_text}")
    print(f"  输出: {tokenized_words}")

    # 测试Emoji搜索功能
    print(f"\n[测试2/4] Emoji搜索:")
    test_keywords = ["猫", "炸鸡", "年"]
    for kw in test_keywords:
        found_codes = search_emoji(kw)
        found_chars = [emoji_code_to_char.get(code, code) for code in found_codes]
        print(f"  关键词 '{kw}': {found_chars[:5]}...")

    # 测试递归拆分与匹配功能
    print(f"\n[测试3/4] 递归拆分与匹配:")
    test_compound_words = ["年头", "电脑", "手机"]
    for word in test_compound_words:
        success, found_codes = find_emojis_recursive(word)
        found_chars = [emoji_code_to_char.get(code, code) for code in found_codes]
        status = "✅" if success else "❌"
        print(f"  词语 '{word}': {status} 找到 {found_chars}")

    # 测试GIF路径查找
    print(f"\n[测试4/4] GIF路径查找:")
    test_emoji_code = "1F600" # 😀
    gif_path = find_gif_path(test_emoji_code)
    emoji_char = emoji_code_to_char.get(test_emoji_code, test_emoji_code)
    if gif_path:
        print(f"  成功: '{emoji_char}' -> {gif_path}")
    else:
        print(f"  ⚠️  提示: 未找到 '{emoji_char}' 的GIF文件。")

    print("\n" + "="*50)
    print("✅ 所有测试完成！")
    print("="*50)