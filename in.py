import nltk
import os
import zipfile
from urllib.request import urlretrieve
from urllib.error import URLError

# 清华镜像源的 punkt_tab 下载地址（国内速度快，不会断连）
PUNKT_TAB_URL = "https://mirrors.tuna.tsinghua.edu.cn/nltk_data/packages/tokenizers/punkt_tab.zip"
# NLTK 数据存放目录（默认路径，确保 Python 能找到）
NLTK_DATA_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "nltk_data")
# 解压后的目标目录
TARGET_DIR = os.path.join(NLTK_DATA_DIR, "tokenizers", "punkt_tab")

def download_and_extract_punkt_tab():
    """用清华镜像源下载并解压 punkt_tab 模型"""
    # 创建必要的目录
    os.makedirs(NLTK_DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(NLTK_DATA_DIR, "tokenizers"), exist_ok=True)
    
    # 下载临时文件
    zip_path = os.path.join(NLTK_DATA_DIR, "punkt_tab.zip")
    print(f"📥 正在从清华镜像源下载 punkt_tab...")
    print(f"URL: {PUNKT_TAB_URL}")
    
    try:
        # 下载文件（显示进度）
        def progress_hook(count, block_size, total_size):
            if total_size > 0:
                percent = (count * block_size) / total_size * 100
                print(f"⏳ 下载进度: {percent:.1f}%", end="\r")
        
        urlretrieve(PUNKT_TAB_URL, zip_path, reporthook=progress_hook)
        print("\n📥 下载完成！开始解压...")
        
        # 解压文件
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(os.path.join(NLTK_DATA_DIR, "tokenizers"))
        
        # 删除临时压缩包
        os.remove(zip_path)
        print(f"✅ 解压完成！模型已保存到: {TARGET_DIR}")
        return True
    
    except URLError as e:
        print(f"\n❌ 下载失败：网络连接错误 - {str(e)}")
        return False
    except Exception as e:
        print(f"\n❌ 处理失败：{str(e)}")
        return False

def check_punkt_tab():
    """检查 punkt_tab 模型是否已存在"""
    try:
        # 验证 NLTK 能否找到该资源
        nltk.data.find('tokenizers/punkt_tab/english.pickle')
        return True
    except LookupError:
        return False

def test_tokenize():
    """测试分词功能是否正常"""
    try:
        from nltk.tokenize import word_tokenize
        test_sentence = "今天天气很好，我想去公园散步，还想吃炸鸡！"
        words = word_tokenize(test_sentence)
        print(f"\n✅ 分词测试成功！")
        print(f"原始句子：{test_sentence}")
        print(f"分词结果：{words}")
        return True
    except Exception as e:
        print(f"\n❌ 分词测试失败：{str(e)}")
        return False

if __name__ == "__main__":
    print("=== NLTK punkt_tab 模型配置工具（Python 3.10）===")
    
    # 1. 检查模型是否已存在
    if check_punkt_tab():
        print("✅ punkt_tab 模型已存在，无需下载！")
    else:
        # 2. 下载并解压模型
        if not download_and_extract_punkt_tab():
            print("\n❌ 模型配置失败，请检查网络后重试！")
            exit(1)
    
    # 3. 测试分词功能
    if test_tokenize():
        print("\n🎉 所有配置完成！可以正常使用分词功能了～")
    else:
        print("\n❌ 配置未完成，请重新运行脚本！")