import sys
import os
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QScrollArea, QFrame, QMessageBox, QSpinBox, QGroupBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject

# 导入我们的核心逻辑模块
import emoji_core

# --- 后台工作线程 ---
class EmojiProcessorWorker(QObject):
    update_status = pyqtSignal(str)
    text_processed = pyqtSignal(list, list, list, str) # 新增：传递原始文本内容
    finished = pyqtSignal(bool, str)
    video_progress = pyqtSignal(int)

    def __init__(self, file_path, duration, output_dir):
        super().__init__()
        self.file_path = file_path
        self.duration = duration # 视频总时长
        self.output_dir = output_dir # 接收固定的输出目录
        self.is_running = True

    def process_text(self):
        try:
            self.update_status.emit("正在读取文本文件...")
            with open(self.file_path, 'r', encoding='utf-8') as f:
                text_content = f.read().strip()
            if not text_content:
                self.finished.emit(False, "错误：选择的文本文件为空。")
                return

            self.update_status.emit("正在对文本进行分词...")
            words = emoji_core.tokenize_text(text_content)
            if not words:
                self.finished.emit(False, "错误：文本中未找到有效词语。")
                return
            
            word_char_counts = [len(word) for word in words]
            total_char_count = sum(word_char_counts)
            self.update_status.emit(f"分词完成（总字数：{total_char_count}），正在匹配Emoji...")
            
            words_emojis = []
            for word in words:
                found, emojis = emoji_core.find_emojis_recursive(word)
                words_emojis.append(emojis[:5]) # 最多显示5个匹配的Emoji
            
            # 将原始文本内容也传递出去，用于生成文件名
            self.text_processed.emit(words, words_emojis, word_char_counts, text_content)
            self.finished.emit(True, f"文本处理完成，等待您选择Emoji。视频宽度将为 {total_char_count * emoji_core.CELL_SIZE}px。")

        except Exception as e:
            self.finished.emit(False, f"处理文本时发生错误: {e}")

    def generate_video(self, words, selected_emojis, word_char_counts, text_content):
        try:
            if not words or len(words) == 0:
                self.finished.emit(False, "错误：没有可用于生成视频的词语。")
                return

            self.update_status.emit("开始生成视频...")
            
            # 确保输出目录存在，如果不存在则创建
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                self.update_status.emit(f"输出目录 '{self.output_dir}' 不存在，已自动创建。")

            # 生成文件名：使用文本内容的前五个字，并去除非法字符
            safe_text = re.sub(r'[\\/*?:"<>|]', "", text_content[:5])
            if not safe_text: # 如果文本前五个字都是非法字符，则使用默认名
                safe_text = "output"
            output_file = os.path.join(self.output_dir, f"{safe_text}.mp4")
            
            # 模拟进度条
            total_steps = 100
            for i in range(total_steps):
                if not self.is_running:
                    self.finished.emit(False, "视频生成已取消。")
                    return
                self.video_progress.emit(i)
            
            # 调用核心函数生成视频，并指定输出文件路径
            emoji_core.create_emoji_video(
                words=words,
                selected_emojis=selected_emojis,
                word_char_counts=word_char_counts,
                duration_per_video=self.duration,
                output_file=output_file # 将构造好的路径传递给核心函数
            )
            
            self.video_progress.emit(100)
            self.finished.emit(True, f"成功！视频已保存为: {output_file}")

        except Exception as e:
            self.finished.emit(False, f"生成视频时发生错误: {e}")
    
    def stop(self):
        self.is_running = False

# --- GUI 主窗口 ---
class EmojiVideoMakerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Emoji 句子视频生成器 (多选填充版)")
        self.setGeometry(100, 100, 900, 700)
        self.setStyleSheet("font-family: 'Microsoft YaHei';")

        # --- 核心修改点 ---
        # 设置一个固定的输出文件目录，所有视频都将保存在这里
        # 使用原始字符串(r"...")来处理反斜杠，避免转义问题
        self.fixed_output_dir = r"Z:\2025\1120-hanshi\gif" 
        # --- 修改结束 ---

        self.file_path = None
        self.text_content = "" # 用于存储原始文本，以便生成文件名
        self.words = []
        self.words_emojis = []
        self.selected_emojis = [] 
        self.word_char_counts = []

        self.worker = None
        self.worker_thread = None

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        title_label = QLabel("Emoji 句子视频生成器 (多选填充版)")
        title_label.setFont(QFont("Microsoft YaHei", 26, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50;")
        main_layout.addWidget(title_label)

        control_layout = QHBoxLayout()
        control_layout.setSpacing(15)
        self.select_file_btn = QPushButton("1. 选择文本文件 (.txt)")
        self.select_file_btn.setFont(QFont("Microsoft YaHei", 12))
        self.select_file_btn.setFixedSize(220, 50)
        self.select_file_btn.setStyleSheet(self._get_button_style())
        self.select_file_btn.clicked.connect(self.select_file)
        control_layout.addWidget(self.select_file_btn)
        self.process_text_btn = QPushButton("2. 处理文本并匹配Emoji")
        self.process_text_btn.setFont(QFont("Microsoft YaHei", 12))
        self.process_text_btn.setFixedSize(250, 50)
        self.process_text_btn.setStyleSheet(self._get_button_style(disabled=True))
        self.process_text_btn.setEnabled(False)
        self.process_text_btn.clicked.connect(self.start_processing_text)
        control_layout.addWidget(self.process_text_btn)
        control_layout.addStretch()
        main_layout.addLayout(control_layout)

        # 在状态标签中提示用户输出路径
        self.status_label = QLabel(f"请选择一个文本文件开始。视频将自动保存到 '{self.fixed_output_dir}' 文件夹。")
        self.status_label.setFont(QFont("Microsoft YaHei", 11))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #7f8c8d; padding: 10px; background-color: #f8f9fa; border-radius: 5px;")
        main_layout.addWidget(self.status_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: 1px solid #bdc3c7; border-radius: 5px;")
        self.scroll_content = QWidget()
        self.emoji_selection_layout = QVBoxLayout(self.scroll_content)
        self.emoji_selection_layout.setSpacing(15)
        self.emoji_selection_layout.setContentsMargins(20, 20, 20, 20)
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

        generate_layout = QHBoxLayout()
        generate_layout.setSpacing(15)
        self.duration_label = QLabel("视频总时长 (秒):")
        self.duration_label.setFont(QFont("Microsoft YaHei", 12))
        self.duration_label.setAlignment(Qt.AlignVCenter)
        generate_layout.addWidget(self.duration_label)
        self.duration_spin = QSpinBox()
        self.duration_spin.setValue(emoji_core.DEFAULT_DURATION_SECONDS)
        self.duration_spin.setRange(1, 10)
        self.duration_spin.setFont(QFont("Microsoft YaHei", 12))
        self.duration_spin.setFixedSize(60, 40)
        self.duration_spin.setStyleSheet("QSpinBox { padding: 5px; border: 1px solid #bdc3c7; border-radius: 3px; }")
        generate_layout.addWidget(self.duration_spin)
        generate_layout.addStretch()
        self.generate_video_btn = QPushButton("3. 生成视频")
        self.generate_video_btn.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        self.generate_video_btn.setFixedSize(200, 60)
        self.generate_video_btn.setStyleSheet(self._get_button_style(color="#e74c3c", disabled=True))
        self.generate_video_btn.setEnabled(False)
        self.generate_video_btn.clicked.connect(self.start_generate_video)
        generate_layout.addWidget(self.generate_video_btn)
        main_layout.addLayout(generate_layout)

    def _get_button_style(self, color="#3498db", disabled=False):
        base_style = f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }}
            QPushButton:hover {{
                background-color: {self._darken_color(color, 0.1)};
            }}
        """
        if disabled:
            base_style += """
                QPushButton:disabled {
                    background-color: #bdc3c7;
                    color: #ecf0f1;
                }
            """
        return base_style
    
    def _darken_color(self, hex_color, factor):
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        r = int(r * (1 - factor))
        g = int(g * (1 - factor))
        b = int(b * (1 - factor))
        return f'#{r:02x}{g:02x}{b:02x}'

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文本文件", "", "Text Files (*.txt);;All Files (*)")
        if file_path:
            self.file_path = file_path
            self.select_file_btn.setText(f"已选择: {os.path.basename(file_path)}")
            self.process_text_btn.setEnabled(True)
            self.process_text_btn.setStyleSheet(self._get_button_style(color="#2ecc71"))
            self.status_label.setText(f"状态: 已选择文件 '{os.path.basename(file_path)}'。请点击'处理文本'。")
            self.reset_emoji_selection()

    def reset_emoji_selection(self):
        while self.emoji_selection_layout.count():
            child = self.emoji_selection_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        self.words = []
        self.words_emojis = []
        self.selected_emojis = []
        self.word_char_counts = []
        self.text_content = "" # 重置文本内容
        self.generate_video_btn.setEnabled(False)
        self.generate_video_btn.setStyleSheet(self._get_button_style(color="#e74c3c", disabled=True))

    def start_processing_text(self):
        if not self.file_path:
            QMessageBox.warning(self, "警告", "请先选择一个文本文件！")
            return
        self.process_text_btn.setEnabled(False)
        self.select_file_btn.setEnabled(False)
        self.process_text_btn.setStyleSheet(self._get_button_style(disabled=True))
        self.status_label.setText("状态: 正在初始化处理器...")
        self.reset_emoji_selection()

        # 创建worker时，将固定的输出目录传递过去
        self.worker = EmojiProcessorWorker(self.file_path, self.duration_spin.value(), self.fixed_output_dir)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.update_status.connect(self.update_status)
        self.worker.text_processed.connect(self.on_text_processed)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker_thread.started.connect(self.worker.process_text)
        self.worker_thread.start()

    def update_status(self, message):
        self.status_label.setText(f"状态: {message}")

    def on_text_processed(self, words, words_emojis, word_char_counts, text_content):
        self.words = words
        self.words_emojis = words_emojis
        self.word_char_counts = word_char_counts
        self.text_content = text_content # 保存原始文本
        self.selected_emojis = [[] for _ in words]

        for i, (word, emojis, char_count) in enumerate(zip(words, words_emojis, word_char_counts)):
            group_box = QGroupBox(f"词语: {word}（{char_count}字，占{char_count}个位置）- 可多选Emoji")
            group_box.setFont(QFont("Microsoft YaHei", 12))
            group_box.setStyleSheet("""
                QGroupBox { font-size: 14px; margin-top: 10px; }
                QGroupBox::title { color: #34495e; font-weight: bold; subcontrol-origin: margin; subcontrol-position: top left; padding: 0 10px; }
            """)
            h_layout = QHBoxLayout(group_box)
            h_layout.setSpacing(10)

            clear_btn = QPushButton("清空选择")
            clear_btn.setFont(QFont("Microsoft YaHei", 10))
            clear_btn.setFixedSize(90, 60)
            clear_btn.setCheckable(True)
            clear_btn.setChecked(True)
            clear_btn.setStyleSheet(self._get_checkbox_style(True))
            clear_btn.clicked.connect(lambda checked, idx=i, btn=clear_btn: self.on_clear_button_click(idx, btn))
            h_layout.addWidget(clear_btn)
            
            if not emojis:
                no_emoji_label = QLabel("❌ 未找到匹配的Emoji")
                no_emoji_label.setFont(QFont("Microsoft YaHei", 11))
                no_emoji_label.setStyleSheet("color: #e74c3c;")
                h_layout.addWidget(no_emoji_label)
            else:
                for emoji_code in emojis:
                    emoji_char = emoji_core.emoji_code_to_char.get(emoji_code, f"[{emoji_code}]")
                    btn = QPushButton(emoji_char)
                    btn.setFont(QFont("Segoe UI Emoji", 24))
                    btn.setFixedSize(60, 60)
                    btn.setCheckable(True)
                    btn.setStyleSheet(self._get_checkbox_style(False))
                    btn.clicked.connect(lambda checked, idx=i, code=emoji_code, btn=btn, clear_btn=clear_btn: self.on_emoji_button_click(idx, code, btn, clear_btn))
                    h_layout.addWidget(btn)
            
            h_layout.addStretch()
            self.emoji_selection_layout.addWidget(group_box)
        
        self.emoji_selection_layout.addStretch()
        self.generate_video_btn.setEnabled(True)
        self.generate_video_btn.setStyleSheet(self._get_button_style(color="#e74c3c"))

    def _get_checkbox_style(self, is_checked):
        border_color = "#e74c3c" if is_checked else "#bdc3c7"
        bg_color = "#fce4ec" if is_checked else "white"
        return f"""
            QPushButton {{ border: 2px solid {border_color}; border-radius: 8px; background-color: {bg_color}; }}
            QPushButton:hover {{ border-color: #3498db; }}
        """
    
    def on_clear_button_click(self, word_index, clear_btn):
        if clear_btn.isChecked():
            self.selected_emojis[word_index].clear()
            group_box = clear_btn.parent()
            for btn in group_box.findChildren(QPushButton):
                if btn != clear_btn:
                    btn.setChecked(False)
                    btn.setStyleSheet(self._get_checkbox_style(False))

    def on_emoji_button_click(self, word_index, emoji_code, emoji_btn, clear_btn):
        if emoji_btn.isChecked():
            self.selected_emojis[word_index].append(emoji_code)
            if clear_btn.isChecked():
                clear_btn.setChecked(False)
                clear_btn.setStyleSheet(self._get_checkbox_style(False))
        else:
            if emoji_code in self.selected_emojis[word_index]:
                self.selected_emojis[word_index].remove(emoji_code)
        
        if not self.selected_emojis[word_index]:
            clear_btn.setChecked(True)
            clear_btn.setStyleSheet(self._get_checkbox_style(True))
        
        emoji_btn.setStyleSheet(self._get_checkbox_style(emoji_btn.isChecked()))

    def on_processing_finished(self, success, message):
        self.status_label.setText(f"状态: {message}")
        self.process_text_btn.setEnabled(True)
        self.select_file_btn.setEnabled(True)
        self.process_text_btn.setStyleSheet(self._get_button_style(color="#2ecc71"))
        if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()

    def start_generate_video(self):
        any_selected = any(self.selected_emojis)
        if not any_selected:
            reply = QMessageBox.question(self, "确认生成", "您尚未选择任何Emoji，生成的视频将是全黑的。确定要继续吗？",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No: return

        # 构造将要保存的文件名并显示给用户
        safe_text = re.sub(r'[\\/*?:"<>|]', "", self.text_content[:5])
        if not safe_text:
            safe_text = "output"
        output_file = os.path.join(self.fixed_output_dir, f"{safe_text}.mp4")
        
        reply = QMessageBox.question(self, "确认生成", f"您确定要生成视频吗？\n总时长: {self.duration_spin.value()} 秒\n文件将保存为: {output_file}",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No: return

        self.generate_video_btn.setEnabled(False)
        self.generate_video_btn.setText("正在生成...")

        # 创建worker时，将固定的输出目录传递过去
        self.worker = EmojiProcessorWorker(self.file_path, self.duration_spin.value(), self.fixed_output_dir)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker.update_status.connect(self.update_status)
        self.worker.finished.connect(self.on_video_generated_finished)
        self.worker.video_progress.connect(self.update_video_progress)
        # 启动时，将原始文本内容传递给generate_video方法
        self.worker_thread.started.connect(lambda: self.worker.generate_video(self.words, self.selected_emojis, self.word_char_counts, self.text_content))
        self.worker_thread.start()

    def update_video_progress(self, value):
        self.status_label.setText(f"状态: 视频生成中... ({value}%)")

    def on_video_generated_finished(self, success, message):
        self.status_label.setText(f"状态: {message}")
        self.generate_video_btn.setEnabled(True)
        self.generate_video_btn.setText("3. 生成视频")
        if success: QMessageBox.information(self, "成功", message)
        if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker: self.worker.stop()
        if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = EmojiVideoMakerGUI()
    window.show()
    sys.exit(app.exec_())