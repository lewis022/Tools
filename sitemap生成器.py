import requests
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from queue import Queue
from threading import Thread


class WebSitemapGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("网络Sitemap生成器")
        self.root.geometry("600x500")

        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # URL输入
        ttk.Label(self.main_frame, text="网站URL:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_entry = ttk.Entry(self.main_frame, width=50)
        self.url_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)
        self.url_entry.insert(0, "https://")

        # 爬取深度
        ttk.Label(self.main_frame, text="爬取深度:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.depth_spinbox = ttk.Spinbox(self.main_frame, from_=1, to=5, width=5)
        self.depth_spinbox.grid(row=1, column=1, sticky=tk.W, padx=5)
        self.depth_spinbox.set(2)

        # 输出文件名
        ttk.Label(self.main_frame, text="输出文件名:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.output_entry = ttk.Entry(self.main_frame, width=50)
        self.output_entry.grid(row=2, column=1, sticky=tk.EW, padx=5)
        self.output_entry.insert(0, "web_sitemap.html")

        # 标题设置
        ttk.Label(self.main_frame, text="网页标题:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.title_entry = ttk.Entry(self.main_frame, width=50)
        self.title_entry.grid(row=3, column=1, sticky=tk.EW, padx=5)
        self.title_entry.insert(0, "网站地图")

        # 生成按钮
        self.generate_button = ttk.Button(self.main_frame, text="生成Sitemap", command=self.start_generation)
        self.generate_button.grid(row=4, column=1, pady=10)

        # 停止按钮
        self.stop_button = ttk.Button(self.main_frame, text="停止", state=tk.DISABLED, command=self.stop_generation)
        self.stop_button.grid(row=4, column=0, pady=10)

        # 进度条
        self.progress = ttk.Progressbar(self.main_frame, orient=tk.HORIZONTAL, length=400, mode='determinate')
        self.progress.grid(row=5, column=0, columnspan=2, pady=10)

        # 日志输出
        ttk.Label(self.main_frame, text="爬取进度:").grid(row=6, column=0, sticky=tk.W, pady=5)
        self.log_text = tk.Text(self.main_frame, height=12, width=70)
        self.log_text.grid(row=7, column=0, columnspan=2, sticky=tk.EW)
        self.log_text.config(state=tk.DISABLED)

        # 配置网格权重
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(7, weight=1)

        # 爬取控制变量
        self.crawling = False
        self.visited_urls = set()
        self.domain = ""
        self.max_depth = 0
        self.total_pages = 0
        self.processed_pages = 0
        self.queue = Queue()
        self.thread = None

    def log_message(self, message):
        """在日志区域添加消息"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def get_links(self, url, depth):
        """获取页面所有链接"""
        if not self.crawling or depth > self.max_depth:
            return []

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            links = set()

            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)
                parsed_url = urlparse(absolute_url)

                # 只处理同域名下的链接
                if parsed_url.netloc == self.domain and not any(
                        absolute_url.endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.zip']
                ):
                    links.add(absolute_url)

            return list(links)

        except Exception as e:
            self.log_message(f"获取 {url} 链接失败: {str(e)}")
            return []

    def crawl_website(self):
        """爬取网站"""
        while not self.queue.empty() and self.crawling:
            url, depth = self.queue.get()

            if url in self.visited_urls:
                self.queue.task_done()
                continue

            self.visited_urls.add(url)
            self.processed_pages += 1
            progress = (self.processed_pages / self.total_pages) * 100 if self.total_pages > 0 else 0
            self.progress["value"] = progress
            self.log_message(f"处理中: {url} (深度 {depth})")

            links = self.get_links(url, depth)
            new_links = [link for link in links if link not in self.visited_urls]

            if depth < self.max_depth:
                for link in new_links:
                    self.queue.put((link, depth + 1))
                    self.total_pages += 1

            self.queue.task_done()
            self.root.update_idletasks()

        if self.crawling:
            self.generate_sitemap()

    def generate_sitemap(self):
        """生成sitemap HTML文件"""
        try:
            output_file = self.output_entry.get()
            title = self.title_entry.get()

            html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; }}
        h1 {{ color: #333; }}
        ul {{ list-style-type: none; padding-left: 20px; }}
        li {{ margin: 5px 0; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .last-updated {{ color: #999; font-size: 0.9em; }}
        .stats {{ background: #f5f5f5; padding: 10px; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="last-updated">最后更新: {current_time}</p>
    <div class="stats">
        总页面数: {total_pages} | 爬取深度: {max_depth} | 域名: {domain}
    </div>
    <ul>
{content}
    </ul>
</body>
</html>"""

            content = []
            for url in sorted(self.visited_urls):
                content.append(f'        <li><a href="{url}">{url}</a></li>')

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_template.format(
                    title=title,
                    current_time=current_time,
                    total_pages=len(self.visited_urls),
                    max_depth=self.max_depth,
                    domain=self.domain,
                    content="\n".join(content)
                ))

            self.log_message(f"成功生成网站地图: {output_file}")
            messagebox.showinfo("完成", f"网站地图已生成: {output_file}")

        except Exception as e:
            self.log_message(f"生成网站地图时出错: {str(e)}")
            messagebox.showerror("错误", f"生成网站地图时出错: {str(e)}")

        finally:
            self.stop_generation()

    def start_generation(self):
        """开始生成sitemap"""
        url = self.url_entry.get().strip()
        if not url or not url.startswith(('http://', 'https://')):
            messagebox.showerror("错误", "请输入有效的URL (以http://或https://开头)")
            return

        try:
            parsed_url = urlparse(url)
            self.domain = parsed_url.netloc
            self.max_depth = int(self.depth_spinbox.get())
            self.visited_urls = set()
            self.total_pages = 1
            self.processed_pages = 0

            self.queue = Queue()
            self.queue.put((url, 0))

            self.crawling = True
            self.generate_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.progress["value"] = 0

            self.log_message(f"开始爬取: {url}")
            self.log_message(f"最大深度: {self.max_depth}")
            self.log_message(f"域名: {self.domain}")

            self.thread = Thread(target=self.crawl_website)
            self.thread.daemon = True
            self.thread.start()

        except Exception as e:
            messagebox.showerror("错误", f"初始化爬取时出错: {str(e)}")

    def stop_generation(self):
        """停止生成sitemap"""
        self.crawling = False
        self.generate_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.log_message("爬取已停止")


if __name__ == "__main__":
    root = tk.Tk()
    app = WebSitemapGenerator(root)
    root.mainloop()
