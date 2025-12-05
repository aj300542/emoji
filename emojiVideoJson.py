import json
import os
import re
from collections import Counter
import jieba
import jieba.posseg as pseg

def main():
    """
    从 emojiNames.json 中智能提取有意义的 2 字和 3 字中文关键词。
    采用多种过滤策略，以生成高质量的优先词库。
    """
    emoji_names_file = "emojiNames.json"
    output_2_file = "2.json"
    output_3_file = "3.json"

    if not os.path.exists(emoji_names_file):
        print(f"❌ 错误：未找到 '{emoji_names_file}' 文件。")
        return

    print(f"📖 正在读取 '{emoji_names_file}'...")
    try:
        with open(emoji_names_file, 'r', encoding='utf-8') as f:
            emoji_data = json.load(f)
    except json.JSONDecodeError:
        print(f"❌ 错误：'{emoji_names_file}' 不是一个有效的 JSON 文件。")
        return

    two_word_candidates = Counter()
    three_word_candidates = Counter()

    # --- 核心策略 1: 定义停用词和可接受的词性 ---
    STOP_WORDS = {'的', '了', '着', '过', '在', '和', '或', '但', '也', '就', '都', '还', '只', '会', '要', '能', '可', '有', '是'}
    # 可接受的词性（名词、动词、形容词等）
    # 参考：https://github.com/fxsjy/jieba/blob/master/posseg/__init__.py#L11
    ACCEPTABLE_POS = {'n', 'v', 'a', 'ad', 'an', 'vn', 'vd', 'ag', 'lg', 'mg'}

    chinese_pattern = re.compile(r'^[\u4e00-\u9fff]+$')

    print("🔍 正在筛选和提取关键词...")
    all_keywords = set()
    for emoji_char, keywords in emoji_data.items():
        if not isinstance(keywords, list):
            continue
        for keyword in keywords:
            keyword = keyword.strip()
            if chinese_pattern.match(keyword):
                all_keywords.add(keyword)

    print("🔧 正在使用 jieba 进行词性标注和过滤...")
    # --- 核心策略 2: 遍历所有原始关键词，进行智能拆分和过滤 ---
    for keyword in all_keywords:
        # 1. 完整的2/3字关键词，直接赋予高权重
        if len(keyword) == 2:
            two_word_candidates[keyword] += 5  # 高权重
        elif len(keyword) == 3:
            three_word_candidates[keyword] += 5 # 高权重

        # 2. 从更长的关键词（>=4字）中智能提取子词
        if len(keyword) >= 4:
            # 使用 jieba 进行分词，而不是暴力提取
            words = pseg.cut(keyword)
            for word, flag in words:
                word_len = len(word)
                # --- 核心策略 3: 过滤逻辑 ---
                # 过滤条件：
                # a. 长度为2或3
                # b. 词性是我们接受的
                # c. 不包含停用词
                # d. 本身不是一个完整的长词（避免重复计数）
                if word_len in [2, 3] and flag in ACCEPTABLE_POS and not any(sw in word for sw in STOP_WORDS) and word not in all_keywords:
                    if word_len == 2:
                        two_word_candidates[word] += 1
                    else: # word_len == 3
                        three_word_candidates[word] += 1

    # --- 核心策略 4: 应用频次阈值进行最终筛选 ---
    # 阈值可以根据你的 emojiNames.json 大小和内容进行调整
    MIN_FREQ_2 = 1  # 2字词的最低出现次数
    MIN_FREQ_3 = 1  # 3字词的最低出现次数

    # 对于那些本身就是完整关键词的子词，即使频次低也保留
    final_two_words = [word for word, count in two_word_candidates.most_common() if count >= MIN_FREQ_2]
    final_three_words = [word for word, count in three_word_candidates.most_common() if count >= MIN_FREQ_3]

    # 合并：将原始的2/3字关键词与筛选出的子词合并，并去重
    final_two_words = list(set(final_two_words + [kw for kw in all_keywords if len(kw) == 2]))
    final_three_words = list(set(final_three_words + [kw for kw in all_keywords if len(kw) == 3]))

    # 排序
    final_two_words.sort()
    final_three_words.sort()

    print(f"✅ 提取完成！")
    print(f"   - 2字词组: {len(final_two_words)} 个")
    print(f"   - 3字词组: {len(final_three_words)} 个")

    try:
        with open(output_2_file, 'w', encoding='utf-8') as f:
            json.dump(final_two_words, f, ensure_ascii=False, indent=4)
        print(f"📄 '{output_2_file}' 文件已成功生成。")
    except Exception as e:
        print(f"❌ 写入 '{output_2_file}' 文件时出错: {e}")

    try:
        with open(output_3_file, 'w', encoding='utf-8') as f:
            json.dump(final_three_words, f, ensure_ascii=False, indent=4)
        print(f"📄 '{output_3_file}' 文件已成功生成。")
    except Exception as e:
        print(f"❌ 写入 '{output_3_file}' 文件时出错: {e}")

    print("\n🎉 所有操作已完成！生成的词库质量已大幅提升，但仍建议进行最终审核。")

if __name__ == "__main__":
    main()