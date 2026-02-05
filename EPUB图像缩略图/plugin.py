#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import tkinter as tk
from tkinter import ttk
from io import BytesIO

# 导入图像处理库 Pillow
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def run(bc):
    # 初始化主窗口
    root = tk.Tk()
    root.title("Sigil 0.9.10 图片浏览器")
    root.geometry("900x650")

    # 创建 Canvas 和 滚动条
    canvas = tk.Canvas(root, highlightthickness=0)
    v_scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
    scroll_frame = ttk.Frame(canvas)

    # 鼠标滚轮支持函数
    def _on_mousewheel(event):
        # 针对 Windows 的 delta 逻辑
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # 绑定滚轮（bind_all 确保在图片上方也能滚动）
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    # 针对 Linux 的滚轮绑定
    canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
    canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=v_scrollbar.set)

    # --- 资源获取与调试核心 ---
    img_list = []
    print("--- 启动 Manifest 扫描 ---")
    try:
        # 兼容 0.9.10 的迭代方式
        for item in bc.image_iter():
            # item 可能返回 (id, href) 或 (id, href, type)
            img_list.append(item[0])
    except Exception as e:
        print(u"无法获取图片列表: {0}".format(e))

    if not HAS_PIL:
        tk.Label(scroll_frame, text="错误: 未安装 Pillow 库", fg="red").pack(pady=20)
    elif not img_list:
        tk.Label(scroll_frame, text="未发现图像资源").pack(pady=20)
    else:
        cols = 4
        for i, img_id in enumerate(img_list):
            try:
                # 尝试读取二进制数据
                # 如果报错 'Id does not exist'，会在此处触发异常
                data = bc.readfile(img_id)
                
                img = Image.open(BytesIO(data))
                img.thumbnail((160, 160))
                photo = ImageTk.PhotoImage(img)

                # 正常显示容器
                f = tk.Frame(scroll_frame, bd=1, relief="sunken")
                f.grid(row=i // cols, column=i % cols, padx=10, pady=10)
                
                lbl_img = tk.Label(f, image=photo)
                lbl_img.image = photo 
                lbl_img.pack()
                
                # 文件名显示
                short_name = img_id if len(img_id) < 18 else img_id[:15] + "..."
                tk.Label(f, text=short_name, font=("Arial", 8)).pack()

            except Exception as e:
                # --- 调试方案：捕获并定位错误 ID ---
                error_info = u"ID: {0}".format(img_id, str(e))
                print(u"【疑似重复图片资源项】 " + error_info)
                
                # 在 GUI 界面绘制红色警告块
                f_err = tk.Frame(scroll_frame, bd=1, relief="solid", bg="#FFE4E1", width=160, height=180)
                f_err.grid(row=i // cols, column=i % cols, padx=10, pady=10)
                f_err.grid_propagate(False) # 固定大小
                
                tk.Label(f_err, text="读取失败", fg="red", bg="#FFE4E1", font=("Arial", 9, "bold")).pack(pady=10)
                tk.Label(f_err, text=img_id, bg="#FFE4E1", font=("Arial", 7), wraplength=140).pack()
                tk.Label(f_err, text="清单中不存在或路径无效", bg="#FFE4E1", font=("Arial", 7), fg="#555").pack(side="bottom", pady=5)

    v_scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    root.lift()
    root.focus_force()
    root.mainloop()

    print("--- 扫描结束 ---")
    return 0