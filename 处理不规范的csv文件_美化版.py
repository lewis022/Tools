import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import chardet
import pandas as pd
import os
import subprocess
import sys
import csv


class CSVImporter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.setup_ui()

    def setup_ui(self):
        self.config_win = tk.Toplevel()
        self.config_win.title("CSV导入工具")
        self.config_win.geometry("600x600")
        self.config_win.minsize(600, 600)  # 设置最小窗口尺寸
        try:
            self.config_win.iconbitmap("icon.ico")  # 如果有图标的话
        except:
            pass

        # 居中显示窗口
        screen_width = self.config_win.winfo_screenwidth()
        screen_height = self.config_win.winfo_screenheight()
        x = (screen_width - 600) // 2
        y = (screen_height - 600) // 2
        self.config_win.geometry(f"600x600+{x}+{y}")

        # 文件选择框
        file_frame = ttk.LabelFrame(self.config_win, text="文件选择", padding=5)
        file_frame.pack(fill=tk.X, padx=5, pady=5)

        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="浏览", command=self.select_file).pack(side=tk.LEFT, padx=5)

        # 导入设置
        settings_frame = ttk.LabelFrame(self.config_win, text="导入设置", padding=5)
        settings_frame.pack(fill=tk.X, padx=5, pady=5)

        # 分隔符选择
        self.delimiter_var = tk.StringVar(value=',')
        ttk.Label(settings_frame, text="分隔符:").grid(row=0, column=0, padx=5, pady=5)
        self.delimiter_combo = ttk.Combobox(settings_frame, textvariable=self.delimiter_var,
                                            values=[',', ';', '\\t', '|', '其他'])
        self.delimiter_combo.grid(row=0, column=1)
        self.delimiter_combo.bind('<<ComboboxSelected>>', self.on_delimiter_change)

        # 自定义分隔符
        self.custom_delimiter_var = tk.StringVar()
        self.custom_delimiter_entry = ttk.Entry(settings_frame, textvariable=self.custom_delimiter_var, width=3)
        self.custom_delimiter_entry.grid(row=0, column=2, padx=5)
        self.custom_delimiter_entry.grid_remove()

        # 文本限定符
        self.quotechar_var = tk.StringVar(value='"')
        ttk.Label(settings_frame, text="文本限定符:").grid(row=1, column=0, padx=5, pady=5)
        ttk.Combobox(settings_frame, textvariable=self.quotechar_var,
                     values=['"', "'", "无"]).grid(row=1, column=1)

        # 预览区域
        preview_frame = ttk.LabelFrame(self.config_win, text="数据预览", padding=5)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 创建带有自定义滚动条的文本区域
        text_frame = ttk.Frame(preview_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        # 创建文本框和滚动条
        self.preview_text = tk.Text(text_frame, height=10, wrap=tk.NONE)

        # 创建垂直滚动条，应用醒目的样式
        v_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=v_scrollbar.set)

        # 创建水平滚动条，应用醒目的样式
        h_scrollbar = ttk.Scrollbar(text_frame, orient="horizontal", command=self.preview_text.xview)
        self.preview_text.configure(xscrollcommand=h_scrollbar.set)

        # 修改滚动条样式部分代码（替换原来的样式设置部分）
        style = ttk.Style()
        style.configure("Thick.Vertical.TScrollbar",
               thickness=20,
               arrowsize=20,
               background="#4CAF50",
               troughcolor="#e1e1e1",
               borderwidth=2,
               relief="raised")
        style.configure("Thick.Horizontal.TScrollbar",
               thickness=20,
               arrowsize=20,
               background="#4CAF50",
               troughcolor="#e1e1e1",
               borderwidth=2,
               relief="raised")

        # 修改滚动条配置部分
        v_scrollbar.configure(style="Thick.Vertical.TScrollbar")
        h_scrollbar.configure(style="Thick.Horizontal.TScrollbar")

        # 使用网格布局放置组件
        self.preview_text.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        # 配置网格权重，使文本区域可扩展
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.config_win, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)

        # 按钮区域
        button_frame = ttk.Frame(self.config_win)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(button_frame, text="预览", command=self.preview_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="导入", command=self.import_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="退出", command=self.quit_app).pack(side=tk.RIGHT, padx=5)

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="选择CSV文件",
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
            # 自动检测分隔符和文本限定符
            self.detect_csv_format(file_path)
            self.preview_data()

    def detect_csv_format(self, file_path):
        try:
            # 检测文件编码
            encoding = self.detect_encoding(file_path)
            # 读取文件前几行
            with open(file_path, 'r', encoding=encoding) as f:
                sample = f.read(4096)  # 读取前4KB数据

            # 使用csv模块的Sniffer来推测分隔符和引号字符
            dialect = csv.Sniffer().sniff(sample)

            # 设置界面上的值
            # 分隔符设置
            delimiter = dialect.delimiter
            if delimiter in [',', ';', '\t', '|']:
                if delimiter == '\t':
                    self.delimiter_var.set('\\t')
                else:
                    self.delimiter_var.set(delimiter)
            else:
                self.delimiter_var.set('其他')
                self.custom_delimiter_var.set(delimiter)
                self.custom_delimiter_entry.grid()  # 显示自定义分隔符输入框
            # 引号字符设置
            quotechar = dialect.quotechar
            if quotechar in ['"', "'"]:
                self.quotechar_var.set(quotechar)
            else:
                self.quotechar_var.set('无')

            messagebox.showinfo("格式检测",
                                f"已自动检测CSV格式:\n分隔符: {repr(delimiter)}\n文本限定符: {repr(quotechar)}")

        except Exception as e:
            messagebox.showwarning("检测失败", f"无法自动检测CSV格式，使用默认值。\n错误: {str(e)}")

    def on_delimiter_change(self, event=None):
        if self.delimiter_var.get() == '其他':
            self.custom_delimiter_entry.grid()
        else:
            self.custom_delimiter_entry.grid_remove()

    def get_delimiter(self):
        delimiter = self.delimiter_var.get()
        if delimiter == '其他':
            delimiter = self.custom_delimiter_var.get()
        elif delimiter == '\\t':
            delimiter = '\t'
        return delimiter

    def preview_data(self):
        try:
            file_path = self.file_path_var.get()
            if not file_path:
                messagebox.showwarning("警告", "请先选择文件！")
                return

            encoding = self.detect_encoding(file_path)
            delimiter = self.get_delimiter()
            quotechar = self.quotechar_var.get()
            if quotechar == '无':
                quotechar = None

            # 只读取前20行用于预览
            df = pd.read_csv(
                file_path,
                encoding=encoding,
                delimiter=delimiter,
                quotechar=quotechar,
                engine='python',
                nrows=21
            )

            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, df.to_string())

        except Exception as e:
            messagebox.showerror("错误", f"预览数据时发生错误：\n{str(e)}")

    def import_file(self):
        try:
            file_path = self.file_path_var.get()
            if not file_path:
                messagebox.showwarning("警告", "请先选择文件！")
                return

            encoding = self.detect_encoding(file_path)
            delimiter = self.get_delimiter()
            quotechar = self.quotechar_var.get()
            if quotechar == '无':
                quotechar = None

            # 生成输出路径
            dir_name = os.path.dirname(file_path)
            base_name = os.path.basename(file_path)
            new_name = f"{os.path.splitext(base_name)[0]}_split out.xlsx"
            output_path = os.path.join(dir_name, new_name)

            # 检查文件是否已存在
            if os.path.exists(output_path):
                if not messagebox.askyesno("确认", f"文件 {new_name} 已存在，是否覆盖？"):
                    return

            # 读取CSV文件并显示进度
            chunks = pd.read_csv(
                file_path,
                encoding=encoding,
                delimiter=delimiter,
                quotechar=quotechar,
                engine='python',
                chunksize=50000
            # 获取总行数用于进度计算
            )

            # 获取总行数用于进度计算
            total_rows = sum(1 for _ in open(file_path, encoding=encoding))

            dfs = []
            processed_rows = 0

            for chunk in chunks:
                dfs.append(chunk)
                processed_rows += len(chunk)
                self.progress_var.set((processed_rows / total_rows) * 100)
                self.config_win.update()

            df = pd.concat(dfs, ignore_index=True)

            # 保存Excel文件
            df.to_excel(output_path, index=False, engine='openpyxl')

            # 完成后重置进度条
            self.progress_var.set(0)

            if messagebox.askyesno("完成", f"文件已保存至：\n{output_path}\n是否打开文件？"):
                if os.name == 'nt':
                    os.startfile(output_path)
                else:
                    subprocess.call(('open', output_path))

        except Exception as e:
            messagebox.showerror("错误", f"导入文件时发生错误：\n{str(e)}")

    @staticmethod
    def detect_encoding(file_path):
        with open(file_path, 'rb') as f:
            result = chardet.detect(f.read())
        return result['encoding']

    def quit_app(self):
        self.config_win.destroy()
        self.root.destroy()
        sys.exit(0)


def main():
    app = CSVImporter()
    app.root.mainloop()


if __name__ == "__main__":
    main()