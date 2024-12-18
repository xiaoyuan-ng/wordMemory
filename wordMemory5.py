import tkinter as tk
from tkinter import messagebox
import pyttsx3
import threading
import random
import time
import os
import csv
from tkinter import font as tkFont

class WordDisplayApp:
    def __init__(self, root, csv_path):
        self.root = root
        self.root.title("单词显示器")
        self.root.configure(bg='black')
        self.root.geometry("1000x700")  # 设置窗口大小

        # 初始化 pyttsx3 引擎
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)  # 设置语速

        # 加载CSV文件
        self.words_dict = self.load_csv(csv_path)

        # 创建输入区域
        self.input_frame = tk.Frame(self.root, bg='black')
        self.input_frame.pack(pady=10)

        self.word_label = tk.Label(self.input_frame, text="单词:", fg='white', bg='black', font=("Arial", 14))
        self.word_label.grid(row=0, column=0, padx=5)

        self.word_entry = tk.Entry(self.input_frame, font=("Arial", 14), width=30)
        self.word_entry.grid(row=0, column=1, padx=5)

        self.add_button = tk.Button(self.input_frame, text="添加单词", command=self.add_word, bg='grey', fg='white', font=("Arial", 12))
        self.add_button.grid(row=0, column=2, padx=5)

        self.stop_button = tk.Button(self.root, text="停止", command=self.stop_display, bg='red', fg='white', font=("Arial", 12))
        self.stop_button.pack(pady=10)

        # 创建画布用于显示单词
        self.canvas = tk.Canvas(self.root, bg='black', width=980, height=600)
        self.canvas.pack()

        # 存储当前显示的单词信息
        self.current_words = []

        # 存储已占用的区域
        self.occupied_areas = []

        # 控制生成和显示单词的标志
        self.is_running = False
        self.current_word = ""
        self.current_meaning = ""

        # 控制发音线程
        self.speech_thread = None
        self.speech_stop_event = threading.Event()

    def load_csv(self, csv_path):
        """
        加载CSV文件并返回一个字典，包含英文单词和对应的中文释义。
        """
        if not os.path.exists(csv_path):
            messagebox.showerror("文件缺失", f"未找到文件：{csv_path}")
            return {}

        words_dict = {}
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) < 2:
                        continue
                    english_word, chinese_meaning = row
                    words_dict[english_word.strip().lower()] = chinese_meaning.strip()
            print(f"成功加载CSV文件，共包含 {len(words_dict)} 个单词。")
        except Exception as e:
            messagebox.showerror("文件加载错误", f"加载CSV时出错：{e}")
        return words_dict

    def add_word(self):
        word = self.word_entry.get().strip()

        if not word:
            messagebox.showwarning("输入错误", "请输入单词。")
            return

        if self.is_running:
            messagebox.showwarning("正在运行", "请先停止当前单词的显示再添加新单词。")
            return

        # 获取中文释义
        meaning = self.words_dict.get(word.lower())
        if not meaning:
            messagebox.showwarning("翻译失败", f"无法获取单词 '{word}' 的中文释义。")
            return

        self.current_word = word
        self.current_meaning = meaning
        self.is_running = True

        # 禁用输入框和添加按钮
        self.word_entry.config(state='disabled')
        self.add_button.config(state='disabled')

        # 启动单词生成和发音线程
        self.display_thread = threading.Thread(target=self.generate_words, daemon=True)
        self.display_thread.start()

        self.speech_stop_event.clear()
        self.speech_thread = threading.Thread(target=self.speak_word_continuously, daemon=True)
        self.speech_thread.start()

        # 清空输入框
        self.word_entry.delete(0, tk.END)

    def speak_word_continuously(self):
        while not self.speech_stop_event.is_set():
            self.engine.say(self.current_word)
            self.engine.runAndWait()
            time.sleep(0.1)

    def generate_words(self):
        while self.is_running:
            self.root.after(0, self.display_text, self.current_word, self.current_meaning)
            time.sleep(0.5)
        print("单词生成线程已停止。")

    def display_text(self, word, meaning):
        if not self.is_running:
            return

        font_size = random.randint(20, 40)
        word_font = tkFont.Font(family="Arial", size=font_size, weight="bold")
        meaning_font = tkFont.Font(family="Arial", size=14)

        self.canvas.update_idletasks()

        # 计算文本宽度和高度
        temp_text = self.canvas.create_text(0, 0, text=word, font=word_font, anchor='nw')
        bbox_word = self.canvas.bbox(temp_text)
        self.canvas.delete(temp_text)

        temp_text = self.canvas.create_text(0, 0, text=meaning, font=meaning_font, anchor='nw')
        bbox_meaning = self.canvas.bbox(temp_text)
        self.canvas.delete(temp_text)

        text_width = max(bbox_word[2] - bbox_word[0], bbox_meaning[2] - bbox_meaning[0]) + 10
        text_height = (bbox_word[3] - bbox_word[1]) + (bbox_meaning[3] - bbox_meaning[1]) + 20

        max_attempts = 100
        for _ in range(max_attempts):
            x = random.randint(10, self.canvas.winfo_width() - text_width - 10)
            y = random.randint(10, self.canvas.winfo_height() - text_height - 10)
            new_area = (x, y, x + text_width, y + text_height)

            if not self.check_overlap(new_area):
                self.occupied_areas.append(new_area)
                break
        else:
            print("无法找到不重叠的位置来显示单词。")
            return  # 放弃显示这个单词

        word_id = self.canvas.create_text(x, y, anchor='nw', text=word, fill=self.random_color(), font=word_font)
        meaning_id = self.canvas.create_text(x, y + (bbox_word[3] - bbox_word[1]) + 5, anchor='nw', text=meaning, fill=self.random_color(), font=meaning_font)

        self.current_words.append((word_id, meaning_id, new_area))
        self.root.after(5000, lambda: self.remove_word(word_id, meaning_id, new_area))

    def check_overlap(self, new_area):
        """
        检查新区域是否与已占用的区域重叠
        new_area: (x1, y1, x2, y2)
        """
        for area in self.occupied_areas:
            # 判断两个矩形是否重叠
            if not (new_area[2] < area[0] or new_area[0] > area[2] or
                    new_area[3] < area[1] or new_area[1] > area[3]):
                return True
        return False

    def remove_word(self, word_id, meaning_id, area):
        self.canvas.delete(word_id)
        self.canvas.delete(meaning_id)
        try:
            self.occupied_areas.remove(area)
        except ValueError:
            pass  # 如果区域已经被移除，不做处理

    def stop_display(self):
        if not self.is_running:
            return

        self.is_running = False
        self.speech_stop_event.set()
        self.canvas.delete("all")
        self.word_entry.config(state='normal')
        self.add_button.config(state='normal')
        self.current_words.clear()
        self.occupied_areas.clear()

    def random_color(self):
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))


if __name__ == "__main__":
    csv_path = "cleaned_toefl_words.csv"  # 替换为你的CSV文件路径
    root = tk.Tk()
    app = WordDisplayApp(root, csv_path)
    root.mainloop()
