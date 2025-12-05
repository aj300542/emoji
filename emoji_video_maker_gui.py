import sys
import os
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QScrollArea, QGroupBox, QMessageBox, QSpinBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject

# 导入核心逻辑模块
import emoji_core

# --- 后台工作线程 ---
class EmojiProcessorWorker(QObject):
    update_status = pyqtSignal(str)
    text_processed = pyqtSignal(list, list, list, str)
    finished = pyqtSignal(bool, str)
    video_progress = pyqtSignal(int)

    def __init__(self, file_path, duration, output_dir):
        super().__init__()
        self.file_path = file_path
        self.duration = duration
        self.output_dir = output_dir
        self.is_running = True

    def process_text(self):
        try:
            self.update_status.emit("正在读取文本文件...")
            with open(self.file_path, 'r', encoding='utf-8') as f:
                text_content = f.read().strip()
            if not text_content:
                self.finished.emit(False, "错误：选择的文本文件为空。")
                return

            self.update_status.emit("正在对文本进行智能分词...")
            words = emoji_core.tokenize_text(text_content)
            if not words:
                self.finished.emit(False, "错误：文本中未找到有效词语。")
                return
            
            word_char_counts = [len(word) for word in words]
            total_char_count = sum(word_char_counts)
            self.update_status.emit(f"分词完成（总字数：{total_char_count}），正在为每个词匹配Emoji...")
            
            words_emojis = []
            for word in words:
                emojis = emoji_core.search_emoji(word)
                words_emojis.append(emojis)
            
            self.text_processed.emit(words, words_emojis, word_char_counts, text_content)
            self.finished.emit(True, f"文本处理完成，等待您选择Emoji。视频宽度将为 {total_char_count * emoji_core.CELL_SIZE}px。")

        except Exception as e:
            self.finished.emit(False, f"处理文本时发生错误: {e}")

    def generate_video(self, words, selected_emojis, word_char_counts, text_content):
        try:
            if not words:
                self.finished.emit(False, "错误：没有可用于生成视频的词语。")
                return

            self.update_status.emit("开始生成视频...")
            
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                self.update_status.emit(f"输出目录 '{self.output_dir}' 不存在，已自动创建。")

            safe_text = re.sub(r'[\\/*?:"<>|]', "", text_content[:5])
            if not safe_text:
                safe_text = "output"
            output_file = os.path.join(self.output_dir, f"{safe_text}.mp4")
            
            # 模拟进度条
            total_steps = 100
            for i in range(total_steps):
                if not self.is_running:
                    self.finished.emit(False, "视频生成已取消。")
                    return
                self.video_progress.emit(i)
            
            emoji_core.create_emoji_video(
                words=words,
                selected_emojis=selected_emojis,
                word_char_counts=word_char_counts,
                duration_per_video=self.duration,
                output_file=output_file
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
        self.setWindowTitle("Emoji 句子视频生成器 (智能分词版)")
        self.setGeometry(100, 100, 900, 700)
        self.setStyleSheet("font-family: 'Microsoft YaHei';")

        # 默认输出目录
        self.fixed_output_dir = r"Z:\2025\1120-hanshi\gif"
        if not os.path.exists(self.fixed_output_dir):
            os.makedirs(self.fixed_output_dir)

        # 数据模型
        self.file_path = None
        self.text_content = ""
        self.words = []
        self.words_emojis = []
        self.selected_emojis = [] 
        self.word_char_counts = []
        # 新增：存储每个词语对应的Emoji按钮列表（关键优化：直接映射，避免查找）
        self.emoji_buttons = []  # 结构：[[btn1, btn2...], [btn1, btn2...]] 对应每个词语

        # 线程相关
        self.worker = None
        self.worker_thread = None

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title_label = QLabel("Emoji 句子视频生成器 (智能分词版)")
        title_label.setFont(QFont("Microsoft YaHei", 26, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50;")
        main_layout.addWidget(title_label)

        # 控制按钮区
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

        # 状态显示区
        self.status_label = QLabel(f"请选择一个文本文件开始。视频将自动保存到 '{self.fixed_output_dir}'。")
        self.status_label.setFont(QFont("Microsoft YaHei", 11))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #7f8c8d; padding: 10px; background-color: #f8f9fa; border-radius: 5px;")
        main_layout.addWidget(self.status_label)

        # Emoji选择滚动区
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: 1px solid #bdc3c7; border-radius: 5px;")
        self.scroll_content = QWidget()
        self.emoji_selection_layout = QVBoxLayout(self.scroll_content)
        self.emoji_selection_layout.setSpacing(15)
        self.emoji_selection_layout.setContentsMargins(20, 20, 20, 20)
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)  # 占据主要空间

        # 视频生成控制区
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
        """重置Emoji选择区域（包括数据模型和UI）"""
        # 清空布局
        while self.emoji_selection_layout.count():
            child = self.emoji_selection_layout.takeAt(0)
            if child.widget(): 
                child.widget().deleteLater()
        # 重置数据模型
        self.words = []
        self.words_emojis = []
        self.selected_emojis = []
        self.word_char_counts = []
        self.emoji_buttons = []  # 清空按钮映射列表
        self.text_content = ""
        
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

        # 创建并启动线程
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
        """文本处理完成后，更新UI以显示Emoji选择（关键优化：存储按钮映射）"""
        self.words = words
        self.words_emojis = words_emojis
        self.word_char_counts = word_char_counts
        self.text_content = text_content
        self.selected_emojis = [[] for _ in words]
        self.emoji_buttons = [[] for _ in words]  # 初始化按钮映射列表

        for i, (word, emojis, char_count) in enumerate(zip(words, words_emojis, word_char_counts)):
            # 创建GroupBox（设置唯一标识，便于调试）
            group_box = QGroupBox(f"词语: {word}（{char_count}字，占{char_count}个位置）- 可多选Emoji")
            group_box.setFont(QFont("Microsoft YaHei", 12))
            group_box.setStyleSheet("""
                QGroupBox { font-size: 14px; margin-top: 10px; }
                QGroupBox::title { color: #34495e; font-weight: bold; subcontrol-origin: margin; subcontrol-position: top left; padding: 0 10px; }
            """)
            
            group_main_layout = QVBoxLayout(group_box)
            
            # 清空选择按钮行
            clear_btn_layout = QHBoxLayout()
            clear_btn = QPushButton("清空选择")
            clear_btn.setFont(QFont("Microsoft YaHei", 8))
            clear_btn.setFixedSize(45, 30)
            clear_btn.setCheckable(True)
            clear_btn.setChecked(True)
            clear_btn.setStyleSheet("""
                QPushButton {
                    border: 2px solid #e74c3c;
                    border-radius: 3px;
                    background-color: #fce4ec;
                    color: #c0392b;
                    padding: 0px;
                }
                QPushButton:hover {
                    border-color: #3498db;
                }
                QPushButton:checked {
                    border-color: #2ecc71;
                    background-color: #e8f5e9;
                    color: #27ae60;
                }
            """)
            # 绑定清空事件（直接传递词语索引，避免查找）
            clear_btn.clicked.connect(lambda checked, idx=i, btn=clear_btn: self.on_clear_button_click(idx, btn))
            clear_btn_layout.addWidget(clear_btn)
            clear_btn_layout.addStretch()
            group_main_layout.addLayout(clear_btn_layout)
            
            # Emoji滚动区域
            emoji_scroll_area = QScrollArea()
            emoji_scroll_area.setWidgetResizable(True)
            emoji_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            emoji_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            emoji_scroll_area.setFixedHeight(80)
            
            emoji_container_widget = QWidget()
            emoji_h_layout = QHBoxLayout(emoji_container_widget)
            emoji_h_layout.setSpacing(10)
            emoji_h_layout.setContentsMargins(0, 5, 0, 5)
            
            if not emojis:
                no_emoji_label = QLabel("❌ 未找到匹配的Emoji")
                no_emoji_label.setFont(QFont("Microsoft YaHei", 11))
                no_emoji_label.setStyleSheet("color: #e74c3c; padding: 25px;")
                emoji_h_layout.addWidget(no_emoji_label)
            else:
                # 存储当前词语的Emoji按钮（关键优化：直接映射，无需后续查找）
                current_emoji_buttons = []
                for emoji_code in emojis:
                    emoji_char = emoji_core.emoji_code_to_char.get(emoji_code, f"[{emoji_code}]")
                    btn = QPushButton(emoji_char)
                    btn.setFont(QFont("Segoe UI Emoji", 24))
                    btn.setFixedSize(60, 60)
                    btn.setCheckable(True)
                    btn.setStyleSheet(self._get_checkbox_style(False))
                    # 绑定Emoji选择事件
                    btn.clicked.connect(lambda checked, idx=i, code=emoji_code, btn=btn, clear_btn=clear_btn: self.on_emoji_button_click(idx, code, btn, clear_btn))
                    emoji_h_layout.addWidget(btn)
                    current_emoji_buttons.append(btn)
                # 保存当前词语的按钮列表
                self.emoji_buttons[i] = current_emoji_buttons
            
            emoji_h_layout.addStretch()
            emoji_scroll_area.setWidget(emoji_container_widget)
            group_main_layout.addWidget(emoji_scroll_area)
            
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
            QPushButton:checked {{ border-color: #e74c3c; background-color: #fce4ec; }}  # 明确选中状态样式
        """
    
    # --- 彻底修复的清空按钮点击事件 ---
    def on_clear_button_click(self, word_index, clear_btn):
        """清空某个词的所有Emoji选择（关键优化：直接使用按钮映射，隔离信号干扰）"""
        if clear_btn.isChecked():
            # 1. 清空后台数据模型（确保数据同步）
            self.selected_emojis[word_index].clear()
            
            # 2. 直接获取当前词语的所有Emoji按钮（无需查找，100%可靠）
            current_emoji_buttons = self.emoji_buttons[word_index]
            if not current_emoji_buttons:
                return
            
            # 3. 隔离信号干扰：暂时断开Emoji按钮的点击信号（避免设置状态时触发信号覆盖）
            for btn in current_emoji_buttons:
                btn.blockSignals(True)
            
            # 4. 强制同步UI状态：设置所有按钮为未选中，并更新样式表
            for btn in current_emoji_buttons:
                btn.setChecked(False)
                btn.setStyleSheet(self._get_checkbox_style(False))
                btn.update()  # 强制刷新按钮UI
            
            # 5. 恢复信号连接（确保后续操作正常）
            for btn in current_emoji_buttons:
                btn.blockSignals(False)
            
            # 6. 强制刷新整个UI，确保视觉效果立即更新
            QApplication.processEvents()

    def on_emoji_button_click(self, word_index, emoji_code, emoji_btn, clear_btn):
        """处理Emoji按钮的点击事件（同步数据模型和清空按钮状态）"""
        if emoji_btn.isChecked():
            # 选中Emoji：添加到数据模型，取消清空按钮的选中状态
            self.selected_emojis[word_index].append(emoji_code)
            if clear_btn.isChecked():
                clear_btn.setChecked(False)
            emoji_btn.setStyleSheet(self._get_checkbox_style(True))
        else:
            # 取消选中Emoji：从数据模型移除
            if emoji_code in self.selected_emojis[word_index]:
                self.selected_emojis[word_index].remove(emoji_code)
            emoji_btn.setStyleSheet(self._get_checkbox_style(False))
        
        # 如果当前词语没有选中任何Emoji，自动勾选清空按钮
        if not self.selected_emojis[word_index]:
            clear_btn.setChecked(True)

    def on_processing_finished(self, success, message):
        """文本处理线程结束后的回调"""
        self.status_label.setText(f"状态: {message}")
        self.process_text_btn.setEnabled(True)
        self.select_file_btn.setEnabled(True)
        self.process_text_btn.setStyleSheet(self._get_button_style(color="#2ecc71"))
        
        # 清理线程
        if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()

    def start_generate_video(self):
        """开始生成视频"""
        any_selected = any(self.selected_emojis)
        if not any_selected:
            reply = QMessageBox.question(self, "确认生成", "您尚未选择任何Emoji，生成的视频将是全黑的。确定要继续吗？",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No: 
                return

        safe_text = re.sub(r'[\\/*?:"<>|]', "", self.text_content[:5])
        if not safe_text:
            safe_text = "output"
        output_file = os.path.join(self.fixed_output_dir, f"{safe_text}.mp4")
        
        reply = QMessageBox.question(self, "确认生成", f"您确定要生成视频吗？\n总时长: {self.duration_spin.value()} 秒\n文件将保存为: {output_file}",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No: 
            return

        self.generate_video_btn.setEnabled(False)
        self.generate_video_btn.setText("正在生成...")

        # 创建并启动视频生成线程
        self.worker = EmojiProcessorWorker(self.file_path, self.duration_spin.value(), self.fixed_output_dir)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        
        self.worker.update_status.connect(self.update_status)
        self.worker.finished.connect(self.on_video_generated_finished)
        self.worker.video_progress.connect(self.update_video_progress)
        self.worker_thread.started.connect(lambda: self.worker.generate_video(self.words, self.selected_emojis, self.word_char_counts, self.text_content))
        
        self.worker_thread.start()

    def update_video_progress(self, value):
        """更新视频生成进度"""
        self.status_label.setText(f"状态: 视频生成中... ({value}%)")

    def on_video_generated_finished(self, success, message):
        """视频生成线程结束后的回调"""
        self.status_label.setText(f"状态: {message}")
        self.generate_video_btn.setEnabled(True)
        self.generate_video_btn.setText("3. 生成视频")
        
        if success:
            QMessageBox.information(self, "成功", message)
        
        # 清理线程
        if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()

    def closeEvent(self, event):
        """关闭窗口时停止所有后台线程"""
        if hasattr(self, 'worker') and self.worker:
            self.worker.stop()
        if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = EmojiVideoMakerGUI()
    window.show()
    sys.exit(app.exec_())