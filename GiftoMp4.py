import json
import os
import re
import sys
from collections import defaultdict
from nltk.tokenize import word_tokenize

import imageio
from PIL import Image

# --- 配置 (与HTML文件中的配置保持一致) ---
# emojiNames.json 文件路径 (与HTML在同一目录)
KEYWORD_FILE = "emojiNames.json"
# Emoji GIF 文件存放目录 (建议与HTML在同一目录下)
EMOJI_GIF_DIR = "emoji_gifs"
# 输出视频文件
OUTPUT_VIDEO_FILE = "output.mp4"
# 视频固定高度
VIDEO_HEIGHT = 240
# 每个Emoji默认显示秒数
DEFAULT_DURATION_SECONDS = 3

# --- 全局变量 ---
# 存储 {emoji_code: emoji_char} 的映射，用于快速查找
emoji_code_to_char = {}

def find_file_path(filename):
    """
    智能查找文件路径。
    先在当前目录找，找不到再去上级目录找，适应不同的脚本运行位置。
    """
    if os.path.exists(filename):
        return filename
    parent_dir = os.path.join("..", filename)
    if os.path.exists(parent_dir):
        return parent_dir
    print(f"警告: 找不到文件 '{filename}' 在当前目录或上级目录。")
    return None

def load_emoji_data():
    """
    从 emojiNames.json 加载数据，并建立反向索引。
    文件格式是: {"😀": ["微笑", "笑脸", ...], ...}
    """
    global emoji_code_to_char
    
    keyword_file_path = find_file_path(KEYWORD_FILE)
    if not keyword_file_path:
        print(f"错误：找不到关键词文件 '{KEYWORD_FILE}'。")
        sys.exit(1)

    try:
        with open(keyword_file_path, 'r', encoding='utf-8') as f:
            emoji_data = json.load(f)
    except json.JSONDecodeError:
        print(f"错误：'{KEYWORD_FILE}' 文件格式不正确，不是有效的JSON。")
        sys.exit(1)

    # 建立两个反向索引
    # 1. 关键词到 emoji_code 的映射 (用于搜索)
    keyword_to_emojis = defaultdict(list)
    # 2. emoji_code 到 emoji_char 的映射 (用于快速查找字符)
    for emoji_char, keywords in emoji_data.items():
        # 计算每个emoji的Unicode编码
        try:
            # 处理可能包含多个代码点的emoji (如带肤色的)
            code_points = [hex(ord(c))[2:].upper() for c in emoji_char]
            emoji_code = '-'.join(code_points)
        except Exception as e:
            print(f"警告: 无法处理Emoji字符 '{emoji_char}', 错误: {e}")
            continue
        
        emoji_code_to_char[emoji_code] = emoji_char
        
        for keyword in keywords:
            keyword_to_emojis[keyword.lower()].append(emoji_code)

    print(f"✅ 成功从 '{KEYWORD_FILE}' 加载 {len(emoji_data)} 个Emoji定义。")
    return keyword_to_emojis

def find_gif_path(emoji_code):
    """根据Emoji编码查找GIF文件路径"""
    if not emoji_code:
        return None
        
    # 确保GIF目录存在
    gif_dir_path = find_file_path(EMOJI_GIF_DIR)
    if not gif_dir_path:
        return None

    # 处理带变体选择器的编码，如 1F469-200D-1F467-200D-1F466
    # 尝试用完整编码查找
    full_path = os.path.join(gif_dir_path, f"{emoji_code}.gif")
    if os.path.exists(full_path):
        return full_path
        
    # 如果找不到，尝试用基础编码查找 (去掉后面的变体)
    base_code = emoji_code.split('-')[0]
    for filename in os.listdir(gif_dir_path):
        if filename.startswith(base_code) and filename.lower().endswith('.gif'):
            return os.path.join(gif_dir_path, filename)
            
    return None

def search_emoji(keyword, keyword_to_emojis_index):
    """根据关键词搜索最相关的Emoji"""
    keyword = keyword.lower()
    matched_emojis = set()

    # 1. 精确匹配关键词
    if keyword in keyword_to_emojis_index:
        matched_emojis.update(keyword_to_emojis_index[keyword])

    # 2. 模糊匹配（关键词包含在Emoji的关键词中）
    for kw, emojis in keyword_to_emojis_index.items():
        if keyword in kw:
            matched_emojis.update(emojis)

    # 3. 反向模糊匹配（Emoji的关键词包含在输入关键词中）
    for kw, emojis in keyword_to_emojis_index.items():
        if kw in keyword:
            matched_emojis.update(emojis)

    # 对结果进行排序，优先考虑精确匹配的
    sorted_emojis = []
    if keyword in keyword_to_emojis_index:
        sorted_emojis.extend(keyword_to_emojis_index[keyword])
    # 添加其他匹配项，去重
    for emoji in matched_emojis:
        if emoji not in sorted_emojis:
            sorted_emojis.append(emoji)

    return sorted_emojis

def select_emoji(word, keyword_to_emojis_index):
    """为指定的词语搜索并让用户选择一个Emoji"""
    print(f"\n正在为词语 '{word}' 搜索相关Emoji...")
    candidates = search_emoji(word, keyword_to_emojis_index)

    if not candidates:
        print(f"抱歉，没有找到与 '{word}' 相关的Emoji。")
        return None

    print("请选择一个Emoji (输入序号):")
    for i, emoji_code in enumerate(candidates[:5]):  # 最多显示5个候选
        gif_path = find_gif_path(emoji_code)
        emoji_char = emoji_code_to_char.get(emoji_code, "?")
        if gif_path:
            print(f"[{i + 1}] {emoji_char} (编码: {emoji_code})")
        else:
            print(f"[{i + 1}] {emoji_char} (编码: {emoji_code}) - 未找到GIF文件")

    while True:
        choice = input("你的选择: ")
        if choice.isdigit():
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(candidates[:5]):
                selected_code = candidates[choice_idx]
                if find_gif_path(selected_code):
                    return selected_code
                else:
                    print("你选择的Emoji没有对应的GIF文件，请重新选择。")
            else:
                print("输入无效，请输入列表中的序号。")
        else:
            print("输入无效，请输入一个数字。")

def create_emoji_video(selected_emoji_codes, duration_per_emoji):
    """将选中的Emoji GIF合成为一个MP4视频"""
    if not selected_emoji_codes:
        print("没有选中任何Emoji，无法生成视频。")
        return

    print("\n正在准备生成视频...")
    writer = None
    try:
        all_frames = []
        for emoji_code in selected_emoji_codes:
            gif_path = find_gif_path(emoji_code)
            if not gif_path:
                print(f"警告: 跳过Emoji {emoji_code_to_char.get(emoji_code, emoji_code)}，因为找不到GIF文件。")
                continue

            print(f"正在处理: {emoji_code_to_char.get(emoji_code, emoji_code)}")
            reader = imageio.get_reader(gif_path)
            meta_data = reader.get_meta_data()
            
            fps = meta_data.get('fps', 10)
            total_frames_in_gif = reader.count_frames()
            frames_needed = int(duration_per_emoji * fps)
            
            for i in range(frames_needed):
                frame = reader.get_data(i % total_frames_in_gif)
                
                img = Image.fromarray(frame)
                w, h = img.size
                new_width = int((VIDEO_HEIGHT / h) * w)
                img_resized = img.resize((new_width, VIDEO_HEIGHT), Image.Resampling.LANCZOS)
                
                all_frames.append(imageio.core.util.Array(img_resized))

            reader.close()

        if not all_frames:
            print("错误: 没有可用的帧来生成视频。")
            return

        first_gif_path = find_gif_path(selected_emoji_codes[0])
        first_reader = imageio.get_reader(first_gif_path)
        video_fps = first_reader.get_meta_data().get('fps', 10)
        first_reader.close()

        print(f"\n正在写入视频文件 '{OUTPUT_VIDEO_FILE}'...")
        writer = imageio.get_writer(OUTPUT_VIDEO_FILE, fps=video_fps)
        for frame in all_frames:
            writer.append_data(frame)
        
        print(f"\n成功！视频已保存为 '{OUTPUT_VIDEO_FILE}'")

    except Exception as e:
        print(f"\n生成视频时出错: {e}")
    finally:
        if writer:
            writer.close()

def main():
    """主函数"""
    print("--- Emoji 句子视频生成器 (与HTML配置同步) ---")
    
    # 1. 加载Emoji数据
    print("正在加载Emoji数据...")
    keyword_to_emojis_index = load_emoji_data()
    if not keyword_to_emojis_index:
        return

    # 2. 输入句子
    sentence = input("\n请输入一个中文句子: ")
    if not sentence:
        print("句子不能为空。")
        return

    # 3. 分词
    print("\n正在分析句子...")
    words = word_tokenize(sentence)
    words = [word for word in words if re.match(r'\w+', word)]
    
    print(f"分词结果: {words}")

    # 4. 搜索和选择Emoji
    selected_emojis = []
    for word in words:
        selected_code = select_emoji(word, keyword_to_emojis_index)
        if selected_code:
            selected_emojis.append(selected_code)

    if not selected_emojis:
        print("\n未能为你的句子选择任何Emoji。")
        return

    print(f"\n你最终选择的Emoji序列: {[emoji_code_to_char.get(code, code) for code in selected_emojis]}")

    # 5. 输入视频参数
    try:
        duration_input = input(f"\n每个Emoji显示的秒数 (默认 {DEFAULT_DURATION_SECONDS}): ")
        duration = float(duration_input) if duration_input else DEFAULT_DURATION_SECONDS
        if duration <= 0:
            duration = DEFAULT_DURATION_SECONDS
    except ValueError:
        print("输入无效，将使用默认值。")
        duration = DEFAULT_DURATION_SECONDS

    # 6. 生成视频
    create_emoji_video(selected_emojis, duration)

if __name__ == "__main__":
    main()