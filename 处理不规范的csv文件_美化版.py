import os
import sys
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import chardet
import subprocess
import logging
from datetime import datetime


class CSVImporter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.setup_logging()
        self.setup_ui()

    def setup_logging(self):
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"csv_importer_{timestamp}.log")

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("CSV导入工具启动")

    def setup_ui(self):
        self.config_win = tk.Toplevel()
        self.config_win.title("CSV导入工具")
        self.config_win.geometry("600x600")
        self.config_win.minsize(600, 600)
        try:
            self.config_win.iconbitmap("icon.ico")
        except:
            pass

        screen_width = self.config_win.winfo_screenwidth()
        screen_height = self.config_win.winfo_screenheight()
        x = (screen_width - 600) // 2
        y = (screen_height - 600) // 2
        self.config_win.geometry(f"600x600+{x}+{y}")

        file_frame = ttk.LabelFrame(self.config_win, text="文件选择", padding=5)
        file_frame.pack(fill=tk.X, padx=5, pady=5)

        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_frame, text="浏览", command=self.select_file).pack(side=tk.LEFT, padx=5)

        settings_frame = ttk.LabelFrame(self.config_win, text="导入设置", padding=5)
        settings_frame.pack(fill=tk.X, padx=5, pady=5)

        self.delimiter_var = tk.StringVar(value=',')
        ttk.Label(settings_frame, text="分隔符:").grid(row=0, column=0, padx=5, pady=5)
        self.delimiter_combo = ttk.Combobox(settings_frame, textvariable=self.delimiter_var,
                                        values=[',', ';', '\\t', '|', '其他'])
        self.delimiter_combo.grid(row=0, column=1)
        self.delimiter_combo.bind('<<ComboboxSelected>>', self.on_delimiter_change)

        self.custom_delimiter_var = tk.StringVar()
        self.custom_delimiter_entry = ttk.Entry(settings_frame, textvariable=self.custom_delimiter_var, width=3)
        self.custom_delimiter_entry.grid(row=0, column=2, padx=5)
        self.custom_delimiter_entry.grid_remove()

        self.quotechar_var = tk.StringVar(value='"')
        ttk.Label(settings_frame, text="文本限定符:").grid(row=1, column=0, padx=5, pady=5)
        ttk.Combobox(settings_frame, textvariable=self.quotechar_var,
                    values=['"', "'", "无"]).grid(row=1, column=1)

        preview_frame = ttk.LabelFrame(self.config_win, text="数据预览", padding=5)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        text_frame = ttk.Frame(preview_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.preview_text = tk.Text(text_frame, height=10, wrap=tk.NONE)

        v_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=v_scrollbar.set)

        h_scrollbar = ttk.Scrollbar(text_frame, orient="horizontal", command=self.preview_text.xview)
        self.preview_text.configure(xscrollcommand=h_scrollbar.set)

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

        v_scrollbar.configure(style="Thick.Vertical.TScrollbar")
        h_scrollbar.configure(style="Thick.Horizontal.TScrollbar")

        self.preview_text.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.config_win, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)

        button_frame = ttk.Frame(self.config_win)
        button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(button_frame, text="预览", command=self.preview_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="导入", command=self.import_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="退出", command=self.quit_app).pack(side=tk.RIGHT, padx=5)
    def select_file(self):
        try:
            file_path = filedialog.askopenfilename(
                title="选择CSV文件",
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )
            if file_path:
                self.file_path_var.set(file_path)
                self.logger.info(f"选择文件: {file_path}")
                self.detect_csv_format(file_path)
                self.preview_data()
        except Exception as e:
            self.logger.error(f"文件选择错误: {str(e)}", exc_info=True)
            messagebox.showerror("错误", f"文件选择时发生错误：\n{str(e)}")

    def detect_csv_format(self, file_path):
        try:
            self.logger.info(f"开始检测文件格式: {file_path}")
            encoding = self.detect_encoding(file_path)
            self.logger.info(f"检测到文件编码: {encoding}")

            with open(file_path, 'r', encoding=encoding) as f:
                sample = f.read(4096)

            dialect = csv.Sniffer().sniff(sample)
            self.logger.info(f"检测到CSV格式 - 分隔符: {repr(dialect.delimiter)}, 引号字符: {repr(dialect.quotechar)}")
            delimiter = dialect.delimiter
            if delimiter in [',', ';', '\t', '|']:
                if delimiter == '\t':
                    self.delimiter_var.set('\\t')
                else:
                    self.delimiter_var.set(delimiter)
            else:
                self.delimiter_var.set('其他')
                self.custom_delimiter_var.set(delimiter)
                self.custom_delimiter_entry.grid()
            quotechar = dialect.quotechar
            if quotechar in ['"', "'"]:
                self.quotechar_var.set(quotechar)
            else:
                self.quotechar_var.set('无')

            messagebox.showinfo("格式检测",
                                f"已自动检测CSV格式:\n分隔符: {repr(delimiter)}\n文本限定符: {repr(quotechar)}")
        except Exception as e:
            self.logger.error(f"CSV格式检测失败: {str(e)}", exc_info=True)
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

            self.logger.info(f"开始预览文件: {file_path}")
            encoding = self.detect_encoding(file_path)
            delimiter = self.get_delimiter()
            quotechar = self.quotechar_var.get()
            if quotechar == '无':
                quotechar = None

            self.logger.info(f"使用参数 - 编码: {encoding}, 分隔符: {repr(delimiter)}, 引号字符: {repr(quotechar)}")

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
            self.preview_text.insert(tk.END, f"检测到 {df.isnull().sum().sum()} 个空值\n\n")
            self.preview_text.insert(tk.END, f"各列数据类型:\n{df.dtypes}\n\n")

            self.logger.info("预览完成")

        except Exception as e:
            self.logger.error(f"预览数据错误: {str(e)}", exc_info=True)
            messagebox.showerror("错误", f"预览数据时发生错误：\n{str(e)}")

    def import_file(self):
        try:
            file_path = self.file_path_var.get()
            if not file_path:
                messagebox.showwarning("警告", "请先选择文件！")
                return

            self.logger.info(f"开始导入文件: {file_path}")
            encoding = self.detect_encoding(file_path)
            delimiter = self.get_delimiter()
            quotechar = self.quotechar_var.get()
            if quotechar == '无':
                quotechar = None

            self.logger.info(f"使用导入参数 - 编码: {encoding}, 分隔符: {repr(delimiter)}, 引号字符: {repr(quotechar)}")

            dir_name = os.path.dirname(file_path)
            base_name = os.path.basename(file_path)
            new_name = f"{os.path.splitext(base_name)[0]}_split out.xlsx"
            output_path = os.path.join(dir_name, new_name)

            if os.path.exists(output_path):
                self.logger.warning(f"输出文件已存在: {output_path}")
                if not messagebox.askyesno("确认", f"文件 {new_name} 已存在，是否覆盖？"):
                    self.logger.info("用户取消覆盖现有文件")
                    return

            chunks = pd.read_csv(
                file_path,
                encoding=encoding,
                delimiter=delimiter,
                quotechar=quotechar,
                engine='python',
                chunksize=50000
            )

            total_rows = sum(1 for _ in open(file_path, encoding=encoding))

            dfs = []
            processed_rows = 0

            for chunk in chunks:
                dfs.append(chunk)
                processed_rows += len(chunk)
                self.progress_var.set((processed_rows / total_rows) * 100)
                self.config_win.update()

            df = pd.concat(dfs, ignore_index=True)
            df.to_excel(output_path, index=False, engine='openpyxl')

            self.progress_var.set(0)
            self.logger.info(f"文件成功导入并保存到: {output_path}")

            if messagebox.askyesno("完成", f"文件已保存至：\n{output_path}\n是否打开文件？"):
                self.logger.info("用户选择打开输出文件")
                if os.name == 'nt':
                    os.startfile(output_path)
                else:
                    subprocess.call(('open', output_path))

        except Exception as e:
            self.logger.error(f"文件导入错误: {str(e)}", exc_info=True)
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