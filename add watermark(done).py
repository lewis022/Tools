from PIL import Image
import os
import sys
import subprocess
import platform

try:
    from tkinter import Tk, filedialog, messagebox, Button, Frame
except ImportError:
    print("错误：需要Tkinter支持，请按以下方式安装：")
    print("Linux用户：sudo apt-get install python3-tk")
    sys.exit(1)


def open_folder(folder_path):
    """跨平台打开文件夹"""
    try:
        if platform.system() == "Windows":
            os.startfile(folder_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", folder_path])
        else:  # Linux
            subprocess.run(["xdg-open", folder_path])
    except Exception as e:
        print(f"打开文件夹失败: {e}")


def select_watermark_position():
    """创建一个窗口让用户选择水印位置"""
    position_value = [None]  # 使用列表存储选择的位置
    
    def on_position_selected(pos):
        position_value[0] = pos
        position_window.destroy()
    
    # 创建窗口
    position_window = Tk()
    position_window.title("选择水印位置")
    position_window.geometry("300x200")
    
    # 主框架
    frame = Frame(position_window)
    frame.pack(expand=True)
    
    # 创建按钮
    Button(frame, text="左上角", width=10, height=2, 
           command=lambda: on_position_selected("top_left")).grid(row=0, column=0, padx=10, pady=10)
    
    Button(frame, text="右上角", width=10, height=2,
           command=lambda: on_position_selected("top_right")).grid(row=0, column=1, padx=10, pady=10)
    
    Button(frame, text="左下角", width=10, height=2,
           command=lambda: on_position_selected("bottom_left")).grid(row=1, column=0, padx=10, pady=10)
    
    Button(frame, text="右下角", width=10, height=2,
           command=lambda: on_position_selected("bottom_right")).grid(row=1, column=1, padx=10, pady=10)
    
    position_window.mainloop()
    return position_value[0]


def add_watermark(input_folder, logo_path, position="bottom_right", margin=20, output_suffix='_watermarked'):
    """添加水印到图片
    
    参数:
    input_folder -- 包含图片的文件夹
    logo_path -- 水印图片路径
    position -- 水印位置: "top_left", "top_right", "bottom_left", "bottom_right"
    margin -- 水印到边缘的距离（像素）
    output_suffix -- 输出文件名后缀
    """
    try:
        logo = Image.open(logo_path).convert('RGBA')
    except Exception as e:
        print(f"无法加载商标图片：{e}")
        return

    supported_ext = ('.jpg', '.jpeg', '.png', '.gif', '.bmp')

    for filename in os.listdir(input_folder):
        if not filename.lower().endswith(supported_ext):
            continue

        file_path = os.path.join(input_folder, filename)

        try:
            with Image.open(file_path) as img:
                # 转换图片模式为RGBA
                img = img.convert('RGBA')
                
                # 创建一个与原图相同大小的新图层
                watermarked = Image.new('RGBA', img.size, (0, 0, 0, 0))
                
                # 调整logo大小，使其宽度为原图的1/4
                logo_width = img.size[0] // 4
                logo_height = int(logo_width * logo.size[1] / logo.size[0])
                logo_resized = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
                
                # 根据选择的位置计算logo位置
                if position == "top_right":
                    position_coords = (img.size[0] - logo_width - margin, margin)
                elif position == "bottom_right":
                    position_coords = (img.size[0] - logo_width - margin, img.size[1] - logo_height - margin)
                elif position == "top_left":
                    position_coords = (margin, margin)
                elif position == "bottom_left":
                    position_coords = (margin, img.size[1] - logo_height - margin)
                else:
                    # 默认右下角
                    position_coords = (img.size[0] - logo_width - margin, img.size[1] - logo_height - margin)
                
                # 将原图和logo合并
                watermarked.paste(img, (0, 0))
                watermarked.paste(logo_resized, position_coords, logo_resized)
                
                # 保存结果
                output_filename = os.path.splitext(filename)[0] + output_suffix + os.path.splitext(filename)[1]
                output_path = os.path.join(input_folder, output_filename)
                watermarked = watermarked.convert('RGB')
                watermarked.save(output_path, quality=95)
                print(f"已处理: {filename}")

        except Exception as e:
            print(f"处理 {filename} 时出错：{e}")


if __name__ == "__main__":
    # 选择图片文件夹
    root = Tk()
    root.withdraw()  # 隐藏主窗口
    
    input_folder = filedialog.askdirectory(title="选择图片文件夹")
    if not input_folder:
        print("未选择文件夹，程序退出")
        sys.exit()
    
    # 选择水印图片
    logo_path = filedialog.askopenfilename(
        title="选择商标图片",
        filetypes=[
            ("PNG图片", "*.png"),
            ("JPEG图片", "*.jpg *.jpeg"),
            ("GIF图片", "*.gif"),
            ("BMP图片", "*.bmp"),
            ("所有文件", "*.*")
        ]
    )
    if not logo_path:
        print("未选择商标图片，程序退出")
        sys.exit()
    
    root.destroy()  # 关闭主窗口
    
    # 选择水印位置
    position = select_watermark_position()
    if not position:
        print("未选择水印位置，程序退出")
        sys.exit()
    
    try:
        add_watermark(
            input_folder=input_folder,
            logo_path=logo_path,
            position=position,
            margin=30,
            output_suffix="_wm"
        )
        print("处理完成！")
        
        # 打开输出文件夹
        open_folder(input_folder)
    except Exception as e:
        print(f"发生未捕获错误：{str(e)}")