"""
HathiTrust 批量下载工具 - GUI 版本
左右分栏布局：左侧设置面板 + 右侧日志与预览
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import time
import os
import re
from urllib.parse import urlparse, parse_qs, urlencode


# ============================================================
# HathiTrust URL 解析与构造工具
# ============================================================

def parse_hathitrust_url(url: str) -> dict:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    return {"book_id": params.get("id", [None])[0]}


def build_download_url(book_id: str, seq: int, size: str = "ppi:300",
                       fmt: str = "image/jpeg", attachment: int = 1) -> str:
    base = "https://babel.hathitrust.org/cgi/imgsrv/image"
    params = {
        "id": book_id,
        "attachment": attachment,
        "format": fmt,
        "size": size,
        "seq": seq,
    }
    return f"{base}?{urlencode(params)}"


def parse_input_to_config(user_input: str) -> dict:
    user_input = user_input.strip()
    if user_input.startswith("http"):
        info = parse_hathitrust_url(user_input)
        if info["book_id"]:
            return info
    if re.match(r'^[\w]+\.[\w]+$', user_input):
        return {"book_id": user_input}
    return {}


# ============================================================
# 主题配置
# ============================================================

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

COLORS = {
    "bg": "#F5F5F7",
    "card": "#FFFFFF",
    "accent": "#007AFF",
    "accent_hover": "#0056CC",
    "success": "#34C759",
    "warning": "#FF9500",
    "error": "#E8291E",
    "text_primary": "#1D1D1F",
    "text_secondary": "#86868B",
    "border": "#E5E5EA",
    "input_bg": "#F2F2F7",
    "progress_bg": "#E5E5EA",
    "log_bg": "#1E1E1E",
    "log_text": "#D4D4D4",
}


# ============================================================
# GUI 应用
# ============================================================

class HathiTrustApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("HathiTrust Downloader")
        self.geometry("1060x560")
        self.minsize(900, 520)
        self.configure(fg_color=COLORS["bg"])

        self.is_downloading = False
        self.should_stop = False
        self.is_paused = False

        self._build_ui()

    def _build_ui(self):
        # 顶部标题栏
        self._build_titlebar()

        # 主体：左右分栏
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        # 左侧面板
        self._build_left_panel(body)

        # 右侧面板
        self._build_right_panel(body)

    # ============================================================
    # 标题栏
    # ============================================================

    def _build_titlebar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent", height=56)
        bar.pack(fill="x", padx=24, pady=(16, 10))
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar, text="📚 HathiTrust Downloader",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(side="left", anchor="w")

        ctk.CTkLabel(
            bar, text="v2.0",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        ).pack(side="left", padx=(10, 0), anchor="w")

    # ============================================================
    # 左侧设置面板
    # ============================================================

    def _build_left_panel(self, parent):
        left = ctk.CTkFrame(parent, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # 链接输入
        self._build_url_section(left)


        # 下载设置
        self._build_download_settings(left)

        # 代理设置
        self._build_proxy_section(left)

        # 操作按钮
        self._build_buttons(left)

    def _build_url_section(self, parent):
        card = self._card(parent, "下载链接")

        self.url_entry = ctk.CTkEntry(
            card,
            placeholder_text="粘贴链接或输入 Book ID",
            height=34, corner_radius=7,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"], border_width=1,
            font=ctk.CTkFont(size=12)
        )
        self.url_entry.pack(fill="x", pady=(0, 6))

        # 右键菜单：复制、粘贴、剪切
        self._add_context_menu(self.url_entry)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x")

        self.book_id_label = ctk.CTkLabel(
            row, text="未解析",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"]
        )
        self.book_id_label.pack(side="left")

        ctk.CTkButton(
            row, text="解析", width=52, height=26,
            corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            command=self._parse_url
        ).pack(side="right")

    def _build_download_settings(self, parent):
        card = self._card(parent, "下载设置")

        # 页码范围
        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(row1, text="页码范围", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS["text_primary"]).pack(side="left")

        self.end_entry = ctk.CTkEntry(
            row1, placeholder_text="结束", width=66, height=28,
            corner_radius=6, fg_color=COLORS["input_bg"],
            border_color=COLORS["border"], border_width=1,
            font=ctk.CTkFont(size=12), justify="center"
        )
        self.end_entry.pack(side="right")

        ctk.CTkLabel(row1, text="—", font=ctk.CTkFont(size=13),
                     text_color=COLORS["text_secondary"]).pack(side="right", padx=5)

        self.start_entry = ctk.CTkEntry(
            row1, placeholder_text="起始", width=66, height=28,
            corner_radius=6, fg_color=COLORS["input_bg"],
            border_color=COLORS["border"], border_width=1,
            font=ctk.CTkFont(size=12), justify="center"
        )
        self.start_entry.pack(side="right")

        # PPI 质量
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(row2, text="下载质量 (PPI)", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS["text_primary"]).pack(side="left")

        self.quality_var = ctk.StringVar(value="300")
        quality_seg = ctk.CTkSegmentedButton(
            row2, values=["300", "600"],
            variable=self.quality_var,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["input_bg"],
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"],
            unselected_color=COLORS["input_bg"],
            corner_radius=6, height=28, width=110
        )
        quality_seg.pack(side="right")

        # 下载间隔
        row4 = ctk.CTkFrame(card, fg_color="transparent")
        row4.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(row4, text="下载间隔 (秒)", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS["text_primary"]).pack(side="left")

        self.interval_entry = ctk.CTkEntry(
            row4, width=56, height=28,
            corner_radius=6, fg_color=COLORS["input_bg"],
            border_color=COLORS["border"], border_width=1,
            font=ctk.CTkFont(size=12), justify="center"
        )
        self.interval_entry.insert(0, "3")
        self.interval_entry.pack(side="right")

        # 重试设置: 次数 + 间隔
        row5 = ctk.CTkFrame(card, fg_color="transparent")
        row5.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(row5, text="重试设置 (次/秒)", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS["text_primary"]).pack(side="left")

        self.retry_interval_entry = ctk.CTkEntry(
            row5, width=56, height=28,
            corner_radius=6, fg_color=COLORS["input_bg"],
            border_color=COLORS["border"], border_width=1,
            font=ctk.CTkFont(size=12), justify="center"
        )
        self.retry_interval_entry.insert(0, "5")
        self.retry_interval_entry.pack(side="right")

        self.retry_count_entry = ctk.CTkEntry(
            row5, width=56, height=28,
            corner_radius=6, fg_color=COLORS["input_bg"],
            border_color=COLORS["border"], border_width=1,
            font=ctk.CTkFont(size=12), justify="center"
        )
        self.retry_count_entry.insert(0, "3")
        self.retry_count_entry.pack(side="right", padx=(0, 6))

        # 保存目录
        row3 = ctk.CTkFrame(card, fg_color="transparent")
        row3.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(row3, text="保存目录", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS["text_primary"]).pack(side="left")

        ctk.CTkButton(
            row3, text="📁", width=28, height=24,
            corner_radius=5, fg_color=COLORS["input_bg"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=12),
            command=self._browse_folder
        ).pack(side="right")

        self.save_dir_var = ctk.StringVar(value=r"E:\2025\downloads")
        self.save_dir_entry = ctk.CTkEntry(
            card, textvariable=self.save_dir_var,
            height=28, corner_radius=6,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"], border_width=1,
            font=ctk.CTkFont(size=11)
        )
        self.save_dir_entry.pack(fill="x")

    def _build_proxy_section(self, parent):
        card = self._card(parent, "代理")

        # 第一行: 标签 + 切换按钮 (右对齐，与"解析"按钮风格一致)
        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(row1, text="启用代理", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=COLORS["text_primary"]).pack(side="left")

        self.proxy_enabled = True
        self.proxy_toggle_btn = ctk.CTkButton(
            row1, text="已开启", width=52, height=26,
            corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            text_color="white",
            command=self._toggle_proxy
        )
        self.proxy_toggle_btn.pack(side="right")

        # 第二行: 代理地址输入框
        self.proxy_entry = ctk.CTkEntry(
            card, placeholder_text="127.0.0.1:7897",
            height=28, corner_radius=6,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["border"], border_width=1,
            font=ctk.CTkFont(size=11)
        )
        self.proxy_entry.insert(0, "127.0.0.1:7897")
        self.proxy_entry.pack(fill="x")

    def _build_buttons(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(6, 0))

        # 开始 + 暂停 + 重置 并排
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x")

        self.start_btn = ctk.CTkButton(
            btn_row, text="▶  开始下载", height=38,
            corner_radius=9,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._start_download
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.pause_btn = ctk.CTkButton(
            btn_row, text="暂停", height=38, width=80,
            corner_radius=9,
            fg_color=COLORS["input_bg"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=12),
            border_width=1,
            border_color=COLORS["border"],
            state="disabled",
            command=self._toggle_pause
        )
        self.pause_btn.pack(side="left", padx=(0, 6))

        self.reset_btn = ctk.CTkButton(
            btn_row, text="重置", height=38, width=80,
            corner_radius=9,
            fg_color=COLORS["input_bg"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=12),
            border_width=1,
            border_color=COLORS["border"],
            command=self._reset_defaults
        )
        self.reset_btn.pack(side="right")

    # ============================================================
    # 右侧日志面板
    # ============================================================

    def _build_right_panel(self, parent):
        right = ctk.CTkFrame(
            parent, fg_color=COLORS["card"],
            corner_radius=14, border_width=1,
            border_color=COLORS["border"]
        )
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # 内部容器
        inner = ctk.CTkFrame(right, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=16, pady=16)

        # 标题 + 进度
        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            header, text="进度日志",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(side="left")

        self.progress_label = ctk.CTkLabel(
            header, text="就绪",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"]
        )
        self.progress_label.pack(side="right")

        # 进度条
        self.progress_bar = ctk.CTkProgressBar(
            inner, height=5, corner_radius=3,
            fg_color=COLORS["progress_bg"],
            progress_color=COLORS["accent"]
        )
        self.progress_bar.pack(fill="x", pady=(0, 12))
        self.progress_bar.set(0)

        # URL 模板预览
        self.url_preview_label = ctk.CTkLabel(
            inner, text="URL 模板将在开始下载后显示",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color=COLORS["text_secondary"],
            wraplength=450, justify="left"
        )
        self.url_preview_label.pack(anchor="w", pady=(0, 8))

        # 日志区域 (深色终端风格)
        self.log_text = ctk.CTkTextbox(
            inner, corner_radius=10,
            fg_color=COLORS["log_bg"],
            border_color="#333333",
            border_width=1,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=COLORS["log_text"]
        )
        self.log_text.pack(fill="both", expand=True)

        # 日志右键菜单：复制全部 / 复制选中
        self._add_log_context_menu(self.log_text)

        # 统计栏
        stats = ctk.CTkFrame(inner, fg_color="transparent", height=28)
        stats.pack(fill="x", pady=(8, 0))

        self.stats_label = ctk.CTkLabel(
            stats, text="已下载: 0  |  失败: 0  |  跳过: 0",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"]
        )
        self.stats_label.pack(side="left")

        self.clear_btn = ctk.CTkButton(
            stats, text="清空日志", height=26, width=80,
            corner_radius=6,
            fg_color=COLORS["input_bg"],
            hover_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            font=ctk.CTkFont(size=11),
            command=self._clear_log
        )
        self.clear_btn.pack(side="right")

    # ============================================================
    # 辅助方法
    # ============================================================

    def _card(self, parent, title: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent, fg_color=COLORS["card"],
            corner_radius=10, border_width=1,
            border_color=COLORS["border"]
        )
        card.pack(fill="x", pady=(0, 8))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=12, pady=10)

        ctk.CTkLabel(
            inner, text=title,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(0, 6))

        return inner

    def _add_context_menu(self, entry_widget):
        """为输入框添加右键菜单（复制、粘贴、剪切）"""
        import tkinter as tk

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="剪切", command=lambda: self._ctx_cut(entry_widget))
        menu.add_command(label="复制", command=lambda: self._ctx_copy(entry_widget))
        menu.add_command(label="粘贴", command=lambda: self._ctx_paste(entry_widget))

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        # 绑定到内部的 tkinter Entry 组件
        entry_widget.bind("<Button-3>", show_menu)

    def _ctx_cut(self, entry_widget):
        try:
            if entry_widget.selection_get():
                self.clipboard_clear()
                self.clipboard_append(entry_widget.selection_get())
                entry_widget.delete("sel.first", "sel.last")
        except Exception:
            pass

    def _ctx_copy(self, entry_widget):
        try:
            if entry_widget.selection_get():
                self.clipboard_clear()
                self.clipboard_append(entry_widget.selection_get())
        except Exception:
            pass

    def _ctx_paste(self, entry_widget):
        try:
            text = self.clipboard_get()
            try:
                entry_widget.delete("sel.first", "sel.last")
            except Exception:
                pass
            entry_widget.insert("insert", text)
        except Exception:
            pass

    def _format_elapsed(self, seconds: float) -> str:
        """将秒数格式化为可读的时间字符串"""
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            m, s = divmod(seconds, 60)
            return f"{m}分{s}秒"
        else:
            h, remainder = divmod(seconds, 3600)
            m, s = divmod(remainder, 60)
            return f"{h}时{m}分{s}秒"

    def _test_proxy(self, proxy: str, timeout: float = 5.0):
        """
        通过代理访问 Google 的连通性检测端点，验证代理是否真的工作。
        使用 generate_204（响应 204 No Content），国内无代理无法访问。
        返回 (是否成功, 描述信息)
        """
        import urllib.request
        import urllib.error
        import socket

        proxy_url = f"http://{proxy}"
        proxy_handler = urllib.request.ProxyHandler({
            "http": proxy_url,
            "https": proxy_url,
        })
        opener = urllib.request.build_opener(proxy_handler)

        target = "https://www.google.com/generate_204"
        start = time.time()
        try:
            req = urllib.request.Request(target, headers={"User-Agent": "Mozilla/5.0"})
            with opener.open(req, timeout=timeout) as resp:
                elapsed_ms = int((time.time() - start) * 1000)
                if resp.status == 204:
                    return True, f"延迟 {elapsed_ms}ms"
                return False, f"目标返回状态码 {resp.status}"
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            return False, f"连接失败: {reason}"
        except socket.timeout:
            return False, f"超时 (>{timeout}s)"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    def _add_log_context_menu(self, textbox):
        """为日志文本框添加右键菜单（复制选中、复制全部）"""
        import tkinter as tk

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="复制选中", command=lambda: self._log_copy_selection(textbox))
        menu.add_command(label="复制全部日志", command=lambda: self._log_copy_all(textbox))

        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        textbox.bind("<Button-3>", show_menu)

    def _log_copy_selection(self, textbox):
        try:
            text = textbox.get("sel.first", "sel.last")
            if text:
                self.clipboard_clear()
                self.clipboard_append(text)
        except Exception:
            pass

    def _log_copy_all(self, textbox):
        text = textbox.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def _toggle_proxy(self):
        self.proxy_enabled = not self.proxy_enabled
        if self.proxy_enabled:
            self.proxy_toggle_btn.configure(
                text="已开启",
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                text_color="white"
            )
            self.proxy_entry.configure(state="normal")
        else:
            self.proxy_toggle_btn.configure(
                text="已关闭",
                fg_color=COLORS["input_bg"],
                hover_color=COLORS["border"],
                text_color=COLORS["text_secondary"]
            )
            self.proxy_entry.configure(state="disabled")

    def _browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.save_dir_var.set(folder)

    def _parse_url(self):
        user_input = self.url_entry.get().strip()
        if not user_input:
            self.book_id_label.configure(text="⚠ 请输入链接", text_color=COLORS["warning"])
            return
        config = parse_input_to_config(user_input)
        if config and config.get("book_id"):
            self.book_id_label.configure(
                text=f"✅ {config['book_id']}", text_color=COLORS["success"])
        else:
            self.book_id_label.configure(
                text="❌ 无法解析", text_color=COLORS["error"])

    def _clear_log(self):
        self.log_text.delete("1.0", "end")
        self.stats_label.configure(text="已下载: 0  |  失败: 0  |  跳过: 0")
        self.progress_bar.set(0)
        self.progress_label.configure(text="就绪")

    def _log(self, message: str):
        self.after(0, lambda: self._append_log(message))

    def _append_log(self, message: str):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def _update_progress(self, value: float):
        self.after(0, lambda: self.progress_bar.set(value))

    def _update_progress_label(self, text: str):
        self.after(0, lambda: self.progress_label.configure(text=text))

    def _update_stats(self, downloaded: int, failed: int, skipped: int):
        self.after(0, lambda: self.stats_label.configure(
            text=f"已下载: {downloaded}  |  失败: {failed}  |  跳过: {skipped}"))

    def _update_url_preview(self, text: str):
        self.after(0, lambda: self.url_preview_label.configure(text=text))

    # ============================================================
    # 输入验证
    # ============================================================

    def _validate_inputs(self) -> dict | None:
        user_input = self.url_entry.get().strip()
        config = parse_input_to_config(user_input)
        if not config or not config.get("book_id"):
            messagebox.showerror("错误", "请输入有效的 HathiTrust 链接或 Book ID\n\n点击「解析」按钮检查")
            return None

        start_text = self.start_entry.get().strip()
        end_text = self.end_entry.get().strip()
        if not start_text or not end_text:
            messagebox.showerror("错误", "请输入起始和结束页码")
            return None

        try:
            start_seq = int(start_text.replace(",", ""))
            end_seq = int(end_text.replace(",", ""))
        except ValueError:
            messagebox.showerror("错误", "页码必须为数字")
            return None

        if start_seq > end_seq:
            messagebox.showerror("错误", "起始页码不能大于结束页码")
            return None

        ppi = self.quality_var.get()
        size = f"ppi:{ppi}"

        proxy = None
        if self.proxy_enabled:
            proxy = self.proxy_entry.get().strip() or "127.0.0.1:7897"

        save_dir = self.save_dir_var.get().strip()
        if not save_dir:
            messagebox.showerror("错误", "请选择保存目录")
            return None

        try:
            interval = float(self.interval_entry.get().strip() or "3")
        except ValueError:
            interval = 3.0

        try:
            retry_count = int(self.retry_count_entry.get().strip() or "3")
        except ValueError:
            retry_count = 3

        try:
            retry_interval = float(self.retry_interval_entry.get().strip() or "5")
        except ValueError:
            retry_interval = 5.0

        return {
            "book_id": config["book_id"],
            "start_seq": start_seq,
            "end_seq": end_seq,
            "size": size,
            "proxy": proxy,
            "save_dir": save_dir,
            "interval": interval,
            "retry_count": retry_count,
            "retry_interval": retry_interval,
        }

    # ============================================================
    # 下载逻辑
    # ============================================================

    def _start_download(self):
        params = self._validate_inputs()
        if not params:
            return

        self.is_downloading = True
        self.should_stop = False
        self.is_paused = False
        self.start_btn.configure(state="disabled")
        self.pause_btn.configure(state="normal", text="暂停",
                                 fg_color=COLORS["input_bg"],
                                 hover_color=COLORS["border"],
                                 text_color=COLORS["text_primary"])
        self.log_text.delete("1.0", "end")
        self.progress_bar.set(0)

        thread = threading.Thread(target=self._download_worker, args=(params,), daemon=True)
        thread.start()

    def _toggle_pause(self):
        """暂停/继续切换 - 类似音乐播放键"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.configure(
                text="继续",
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                text_color="#FFFFFF"
            )
            self._update_progress_label("已暂停")
            self._log("已暂停")
        else:
            self.pause_btn.configure(
                text="暂停",
                fg_color=COLORS["input_bg"],
                hover_color=COLORS["border"],
                text_color=COLORS["text_primary"]
            )
            self._log("继续下载")

    def _reset_defaults(self):
        """恢复所有设置为默认值"""
        # 正在下载且未暂停时，提示用户先暂停或等待完成
        if self.is_downloading and not self.is_paused:
            messagebox.showwarning("提示", "下载进行中，请先暂停后再重置")
            return

        # 暂停状态下点击重置，先停止下载线程
        if self.is_downloading and self.is_paused:
            self.should_stop = True
            self.is_paused = False  # 解除暂停让线程能跳出等待循环并退出
            self._log("⏹ 用户重置，已停止下载")

        # 链接相关
        self.url_entry.delete(0, "end")
        self.book_id_label.configure(text="未解析", text_color=COLORS["text_secondary"])

        # 下载设置
        self.start_entry.delete(0, "end")
        self.end_entry.delete(0, "end")
        self.quality_var.set("300")
        self.interval_entry.delete(0, "end")
        self.interval_entry.insert(0, "3")
        self.retry_count_entry.delete(0, "end")
        self.retry_count_entry.insert(0, "3")
        self.retry_interval_entry.delete(0, "end")
        self.retry_interval_entry.insert(0, "5")
        self.save_dir_var.set(r"E:\2025\downloads")

        # 代理
        if not self.proxy_enabled:
            self._toggle_proxy()
        self.proxy_entry.configure(state="normal")
        self.proxy_entry.delete(0, "end")
        self.proxy_entry.insert(0, "127.0.0.1:7897")

        # 日志与进度
        self._clear_log()
        self.url_preview_label.configure(
            text="URL 模板将在开始下载后显示",
            text_color=COLORS["text_secondary"]
        )

    def _download_worker(self, params: dict):
        downloaded = 0
        failed = 0
        skipped = 0
        start_time = time.time()

        try:
            from DrissionPage import ChromiumPage, ChromiumOptions

            book_id = params["book_id"]
            start_seq = params["start_seq"]
            end_seq = params["end_seq"]
            size = params["size"]
            proxy = params["proxy"]
            save_dir = params["save_dir"]
            interval = params["interval"]
            retry_interval = params["retry_interval"]
            retry_count = params["retry_count"]
            total = end_seq - start_seq + 1

            # 显示 URL 模板
            template_url = build_download_url(book_id, seq=1, size=size)
            self._update_url_preview(f"模板: {template_url.replace('seq=1', 'seq=%PAGE%')}")

            # 以书籍 ID 命名子文件夹（替换 Windows 不允许的字符）
            os.makedirs(save_dir, exist_ok=True)
            safe_book_id = re.sub(r'[\\/:*?"<>|]', '_', book_id)
            book_folder = os.path.join(save_dir, safe_book_id)
            os.makedirs(book_folder, exist_ok=True)

            self._log(f"📖 Book ID: {book_id}")
            self._log(f"📁 保存至: {book_folder}")
            self._log(f"📄 范围: {start_seq} → {end_seq} (共 {total} 页)")
            self._log(f"🖼 质量: {size}")
            self._log(f"🌐 代理: {proxy or '直连'}")
            self._log(f"⏱ 下载间隔: {interval}s  |  重试: {retry_count} 次 × {retry_interval}s")
            self._log("─" * 36)

            # 启用代理时，先测试代理是否可用
            if proxy:
                self._update_progress_label("测试代理连接...")
                self._log("🔍 正在测试代理连接...")
                ok, msg = self._test_proxy(proxy)
                if not ok:
                    self._log(f"❌ 代理测试失败: {msg}")
                    self._log("   请检查代理是否启动，或关闭代理使用直连")
                    self._update_progress_label("代理不可用")
                    return
                self._log(f"✅ 代理可用 ({msg})")

            self._update_progress_label("初始化浏览器...")

            options = ChromiumOptions()
            if proxy:
                options.set_argument(f'--proxy-server=http://{proxy}')
            options.headless(False)
            options.set_pref("download.default_directory", book_folder)
            options.set_pref("download.prompt_for_download", False)

            page = ChromiumPage(options)
            page.get("https://babel.hathitrust.org/")
            page.wait.load_start()

            self._log("✅ 浏览器就绪，开始下载\n")

            for i, seq in enumerate(range(start_seq, end_seq + 1)):
                # 暂停检测 - 循环等待直到恢复或停止
                while self.is_paused and not self.should_stop:
                    time.sleep(0.3)

                if self.should_stop:
                    self._log("\n⏹ 用户停止")
                    break

                url = build_download_url(book_id, seq, size=size)
                filename = f"seq{seq:04d}.jpg"
                filepath = os.path.join(book_folder, filename)

                progress = (i + 1) / total
                self._update_progress(progress)
                self._update_progress_label(f"{i + 1}/{total} — {filename}")

                # 检查文件是否已存在且为有效 JPEG，若是则跳过
                if os.path.exists(filepath):
                    try:
                        existing_size = os.path.getsize(filepath)
                        if existing_size > 0:
                            with open(filepath, 'rb') as f:
                                header = f.read(3)
                            if header == b'\xff\xd8\xff':
                                self._log(f"  ⏭ {filename} 已存在 ({existing_size // 1024} KB)，跳过")
                                skipped += 1
                                self._update_stats(downloaded, failed, skipped)
                                time.sleep(0.1)
                                continue
                    except Exception:
                        pass  # 文件损坏或读取失败，重新下载

                # 使用 JS fetch + Blob 触发浏览器保存
                # （DrissionPage 的 run_js 不会等待 Promise 完成，只能 fire-and-forget）
                js_code = f"""
                fetch('{url}')
                  .then(response => {{
                    if (!response.ok) throw new Error('HTTP ' + response.status);
                    return response.blob();
                  }})
                  .then(blob => {{
                    const blobUrl = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = blobUrl;
                    a.download = '{filename}';
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(blobUrl);
                    a.remove();
                  }})
                  .catch(e => console.error('下载失败:', e));
                """

                # 尝试下载，失败后按重试参数重试
                # 判定成功标准：文件出现在磁盘上且非空，且不是 .crdownload 临时文件
                success = False
                last_error = ""

                for attempt in range(retry_count + 1):
                    if self.should_stop:
                        break

                    # 删除旧文件（如果之前重试残留）
                    if os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                        except Exception:
                            pass

                    try:
                        page.run_js(js_code)
                    except Exception as ex:
                        last_error = f"上下文丢失: {ex}"
                        self._log(f"  ↻ 页面上下文丢失，恢复中...")
                        try:
                            page.get("https://babel.hathitrust.org/")
                            page.wait.load_start()
                            time.sleep(2)
                        except Exception:
                            pass
                        if attempt < retry_count:
                            time.sleep(retry_interval)
                        continue

                    # 等待文件出现（最多等待 interval + 5 秒，每 0.3s 检查一次）
                    wait_total = max(interval, 1.0) + 5.0
                    waited = 0.0
                    file_ready = False
                    while waited < wait_total:
                        if self.should_stop:
                            break
                        # 浏览器下载中的临时文件
                        crdownload = filepath + ".crdownload"
                        if os.path.exists(filepath) and not os.path.exists(crdownload):
                            try:
                                size_bytes = os.path.getsize(filepath)
                                if size_bytes > 0:
                                    file_ready = True
                                    break
                            except OSError:
                                pass
                        time.sleep(0.3)
                        waited += 0.3

                    if file_ready:
                        size_bytes = os.path.getsize(filepath)
                        # 校验 JPEG 魔数
                        try:
                            with open(filepath, 'rb') as f:
                                header = f.read(3)
                            if header != b'\xff\xd8\xff':
                                last_error = f"非 JPEG 数据 ({size_bytes} 字节)"
                                if attempt < retry_count:
                                    self._log(f"  ↻ {filename} 第 {attempt + 1} 次失败: {last_error}，{retry_interval}s 后重试")
                                    time.sleep(retry_interval)
                                continue
                        except Exception as ex:
                            last_error = f"读取校验失败: {ex}"
                            if attempt < retry_count:
                                time.sleep(retry_interval)
                            continue

                        if attempt == 0:
                            self._log(f"  ✓ {filename} ({size_bytes // 1024} KB)")
                        else:
                            self._log(f"  ✓ {filename} ({size_bytes // 1024} KB, 第 {attempt + 1} 次尝试成功)")
                        downloaded += 1
                        success = True
                        break
                    else:
                        last_error = f"文件未出现 (等待 {wait_total:.0f}s)"
                        if attempt < retry_count:
                            self._log(f"  ↻ {filename} 第 {attempt + 1} 次失败: {last_error}，{retry_interval}s 后重试")
                            time.sleep(retry_interval)

                if not success and not self.should_stop:
                    self._log(f"  ❌ {filename} 重试 {retry_count} 次后仍失败 ({last_error})，跳过")
                    skipped += 1

                self._update_stats(downloaded, failed, skipped)
                # 间隔已经隐含在等待文件出现的过程中，仅短暂喘息
                time.sleep(0.5)

            page.quit()

            elapsed = time.time() - start_time
            elapsed_str = self._format_elapsed(elapsed)

            if not self.should_stop:
                self._log(f"\n{'═' * 36}")
                self._log(f"✅ 完成! 成功 {downloaded}, 失败 {failed}, 跳过 {skipped}, 耗时 {elapsed_str}")
                self._update_progress_label("下载完成")
                self._update_progress(1.0)
            else:
                self._log(f"\n耗时 {elapsed_str}")
                self._update_progress_label("已停止")

        except Exception as e:
            self._log(f"\n❌ 错误: {str(e)}")
            self._update_progress_label("出错了")
        finally:
            self.is_downloading = False
            self.is_paused = False
            self.after(0, lambda: self.start_btn.configure(state="normal"))
            self.after(0, lambda: self.pause_btn.configure(
                state="disabled", text="暂停",
                fg_color=COLORS["input_bg"],
                hover_color=COLORS["border"],
                text_color=COLORS["text_primary"]))


# ============================================================
# 启动
# ============================================================

if __name__ == "__main__":
    app = HathiTrustApp()
    app.mainloop()
