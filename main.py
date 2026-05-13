from DrissionPage import ChromiumPage, ChromiumOptions
from urllib.parse import urlparse, parse_qs, urlencode
import time
import os
import re


# ============================================================
# HathiTrust URL 解析与构造工具
# ============================================================

def parse_hathitrust_url(url: str) -> dict:
    """
    解析 HathiTrust 图像服务器 URL，提取所有关键参数。
    
    支持的 URL 格式:
      - 完整下载链接 (含 attachment/format/size/tracker)
      - 极简预览链接 (仅含 id 和 seq)
      - 阅读器页面链接 (如 /cgi/pt?id=xxx&seq=xxx)
    
    返回字典包含:
      - book_id: 书籍唯一标识符
      - seq: 页码序列号 (int)
      - size: 图像尺寸 (full / ppi:300 / 数字宽度 / None)
      - format: 图像格式 (如 image/jpeg / None)
      - attachment: 是否触发下载 (1/0 / None)
      - tracker: 追踪标识 (可忽略 / None)
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    result = {
        "book_id": params.get("id", [None])[0],
        "seq": None,
        "size": params.get("size", [None])[0],
        "format": params.get("format", [None])[0],
        "attachment": params.get("attachment", [None])[0],
        "tracker": params.get("tracker", [None])[0],
    }

    # seq 转为整数
    seq_raw = params.get("seq", [None])[0]
    if seq_raw is not None:
        try:
            result["seq"] = int(seq_raw)
        except ValueError:
            result["seq"] = seq_raw

    return result


def build_download_url(book_id: str, seq: int, size: str = "ppi:300",
                       fmt: str = "image/jpeg", attachment: int = 1) -> str:
    """
    根据参数构造 HathiTrust 图像下载 URL。
    
    参数:
      - book_id: 书籍 ID (如 keio.10812543530)
      - seq: 页码序列号 (从 1 开始)
      - size: 图像尺寸
          "ppi:300"  -> 300 PPI 高质量
          "full"     -> 服务器原始全尺寸
          数字字符串  -> 指定宽度像素 (如 "200")
      - fmt: 图像格式 (默认 image/jpeg)
      - attachment: 1=触发下载, 0=浏览器预览
    """
    base = "https://babel.hathitrust.org/cgi/imgsrv/image"
    params = {
        "id": book_id,
        "attachment": attachment,
        "format": fmt,
        "size": size,
        "seq": seq,
    }
    return f"{base}?{urlencode(params)}"


def build_preview_url(book_id: str, seq: int) -> str:
    """
    构造极简预览 URL (由服务器自动选择最优尺寸)。
    """
    return f"https://babel.hathitrust.org/cgi/imgsrv/image?id={book_id}&seq={seq}"


def extract_book_id_from_reader_url(url: str) -> str | None:
    """
    从 HathiTrust 阅读器页面 URL 中提取 book_id。
    例如: https://babel.hathitrust.org/cgi/pt?id=uc1.32106019930681&seq=1
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    return params.get("id", [None])[0]


def parse_input_to_config(user_input: str) -> dict:
    """
    智能解析用户输入，支持:
      1. 完整的 imgsrv 图像 URL -> 提取所有参数
      2. 阅读器页面 URL (/cgi/pt?id=...) -> 提取 book_id 和 seq
      3. 纯 book_id 字符串 (如 keio.10812543530) -> 仅设置 book_id
    
    返回配置字典。
    """
    user_input = user_input.strip()

    # 情况1 & 2: 是 URL
    if user_input.startswith("http"):
        info = parse_hathitrust_url(user_input)
        if info["book_id"]:
            return info
        # 尝试阅读器 URL
        book_id = extract_book_id_from_reader_url(user_input)
        if book_id:
            return {"book_id": book_id, "seq": None, "size": None,
                    "format": None, "attachment": None, "tracker": None}

    # 情况3: 纯 book_id (格式通常为 xxx.yyy)
    if re.match(r'^[\w]+\.[\w]+$', user_input):
        return {"book_id": user_input, "seq": None, "size": None,
                "format": None, "attachment": None, "tracker": None}

    return {}


def format_elapsed(seconds: float) -> str:
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


def test_proxy(proxy: str, timeout: float = 5.0):
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


# ============================================================
# 基础配置
# ============================================================

DEFAULT_PROXY = '127.0.0.1:7897'
SAVE_DIR = r"E:\2025\downloads"

# ============================================================
# 交互式输入
# ============================================================

print("=" * 50)
print("  HathiTrust 批量下载工具")
print("=" * 50)

# --- 代理设置 ---
print("\n🌐 代理设置:")
print("  1. 开启代理 (默认)")
print("  2. 关闭代理 (直连)")
proxy_choice = input("选择 (默认 1): ").strip()

PROXY_ADDR = None
if proxy_choice != "2":
    proxy_input = input(f"  代理地址 (默认 {DEFAULT_PROXY}): ").strip()
    PROXY_ADDR = proxy_input if proxy_input else DEFAULT_PROXY
    print(f"  ✅ 代理已开启: {PROXY_ADDR}")
else:
    print("  ✅ 代理已关闭，使用直连")

# --- 链接输入 (只提取 book_id) ---
print()
print("支持输入格式:")
print("  1. 阅读器链接: https://babel.hathitrust.org/cgi/pt?id=keio.10812543530&seq=2")
print("  2. 图像链接:   https://babel.hathitrust.org/cgi/imgsrv/image?id=xxx&seq=1")
print("  3. 纯 book_id: keio.10812543530")
print()

USER_INPUT = input("请粘贴 HathiTrust 链接或输入 book_id: ").strip()

if not USER_INPUT:
    print("❌ 输入为空，退出。")
    exit(1)

config = parse_input_to_config(USER_INPUT)
if not config or not config.get("book_id"):
    print("❌ 无法解析输入，请提供有效的 HathiTrust URL 或 book_id")
    exit(1)

BOOK_ID = config["book_id"]
print(f"\n✅ 成功提取 Book ID: {BOOK_ID}")

# --- 下载质量 (PPI) ---
print("\n🖼 下载质量:")
print("  1. 300 PPI — 默认质量")
print("  2. 600 PPI — 高质量")
ppi_choice = input("选择 (默认 1): ").strip()
if ppi_choice == "2":
    DOWNLOAD_SIZE = "ppi:600"
else:
    DOWNLOAD_SIZE = "ppi:300"

# --- 页码范围 (支持 "1-172" 格式) ---
print()
range_input = input("📄 下载页码范围 (如 1-172): ").strip()

# 解析范围输入
range_match = re.match(r'^(\d+)\s*[-~到]\s*(\d+)$', range_input.replace(',', ''))
if range_match:
    START_SEQ = int(range_match.group(1))
    END_SEQ = int(range_match.group(2))
elif range_input.isdigit():
    # 只输入了一个数字，当作单页下载
    START_SEQ = int(range_input)
    END_SEQ = START_SEQ
else:
    print("❌ 页码格式错误，请使用如 1-172 的格式")
    exit(1)

if START_SEQ > END_SEQ:
    print("❌ 起始页码不能大于结束页码")
    exit(1)

# --- 下载间隔 ---
interval_input = input("⏱ 下载间隔秒数 (默认 3): ").strip()
try:
    INTERVAL = float(interval_input) if interval_input else 3.0
except ValueError:
    INTERVAL = 3.0

# --- 重试设置 ---
retry_count_input = input("🔄 重试次数 (默认 3): ").strip()
try:
    RETRY_COUNT = int(retry_count_input) if retry_count_input else 3
except ValueError:
    RETRY_COUNT = 3

retry_interval_input = input("🔄 重试间隔秒数 (默认 5): ").strip()
try:
    RETRY_INTERVAL = float(retry_interval_input) if retry_interval_input else 5.0
except ValueError:
    RETRY_INTERVAL = 5.0

# --- 确保目录存在，以书籍 ID 命名子文件夹（替换 Windows 不允许的字符）---
os.makedirs(SAVE_DIR, exist_ok=True)
SAFE_BOOK_ID = re.sub(r'[\\/:*?"<>|]', '_', BOOK_ID)
BOOK_FOLDER = os.path.join(SAVE_DIR, SAFE_BOOK_ID)
os.makedirs(BOOK_FOLDER, exist_ok=True)

# --- 确认信息 ---
TOTAL = END_SEQ - START_SEQ + 1
print()
print(f"📖 Book ID:  {BOOK_ID}")
print(f"📄 页码范围: {START_SEQ} - {END_SEQ} (共 {TOTAL} 页)")
print(f"🖼 下载质量: {DOWNLOAD_SIZE}")
print(f"📁 保存目录: {BOOK_FOLDER}")
print(f"⏱ 下载间隔: {INTERVAL}s  |  重试: {RETRY_COUNT} 次 × {RETRY_INTERVAL}s")
print("-" * 50)

# ============================================================
# 代理可用性预检
# ============================================================

if PROXY_ADDR:
    print(f"\n🔍 正在测试代理 {PROXY_ADDR} 是否可用...")
    ok, msg = test_proxy(PROXY_ADDR)
    if not ok:
        print(f"❌ 代理测试失败: {msg}")
        print("   请检查代理是否启动，或重新运行选择「关闭代理」")
        exit(1)
    print(f"✅ 代理可用 ({msg})")

# ============================================================
# 浏览器配置
# ============================================================

options = ChromiumOptions()
if PROXY_ADDR:
    options.set_argument(f'--proxy-server=http://{PROXY_ADDR}')
options.headless(False)
options.set_pref("download.default_directory", BOOK_FOLDER)
options.set_pref("download.prompt_for_download", False)

page = ChromiumPage(options)

# 先访问一个空白页作为稳定的 JS 执行环境
page.get("https://babel.hathitrust.org/")
page.wait.load_start()

# ============================================================
# 下载逻辑
# ============================================================

downloaded = 0
failed = 0
skipped = 0
start_time = time.time()

for i, seq in enumerate(range(START_SEQ, END_SEQ + 1)):
    # 使用正确的 URL 模板构造下载链接
    url = build_download_url(BOOK_ID, seq, size=DOWNLOAD_SIZE)
    filename = f"seq{seq:04d}.jpg"
    filepath = os.path.join(BOOK_FOLDER, filename)

    # 检查文件是否已存在且为有效 JPEG，若是则跳过
    if os.path.exists(filepath):
        try:
            existing_size = os.path.getsize(filepath)
            if existing_size > 0:
                with open(filepath, 'rb') as f:
                    header = f.read(3)
                if header == b'\xff\xd8\xff':
                    print(f"⏭ [{i + 1}/{TOTAL}] {filename} 已存在 ({existing_size // 1024} KB)，跳过")
                    skipped += 1
                    continue
        except Exception:
            pass  # 文件损坏或读取失败，重新下载

    print(f"⬇ [{i + 1}/{TOTAL}] 正在下载: {filename}")

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
    # 判定成功标准：文件出现在磁盘上且非空，且通过 JPEG 魔数校验
    success = False
    last_error = ""

    for attempt in range(RETRY_COUNT + 1):
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
            print(f"  ↻ 页面上下文丢失，恢复中...")
            try:
                page.get("https://babel.hathitrust.org/")
                page.wait.load_start()
                time.sleep(2)
            except Exception:
                pass
            if attempt < RETRY_COUNT:
                time.sleep(RETRY_INTERVAL)
            continue

        # 等待文件出现（最多等待 INTERVAL + 5 秒）
        wait_total = max(INTERVAL, 1.0) + 5.0
        waited = 0.0
        file_ready = False
        while waited < wait_total:
            crdownload = filepath + ".crdownload"
            if os.path.exists(filepath) and not os.path.exists(crdownload):
                try:
                    if os.path.getsize(filepath) > 0:
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
                    if attempt < RETRY_COUNT:
                        print(f"  ↻ {filename} 第 {attempt + 1} 次失败: {last_error}，{RETRY_INTERVAL}s 后重试")
                        time.sleep(RETRY_INTERVAL)
                    continue
            except Exception as ex:
                last_error = f"读取校验失败: {ex}"
                if attempt < RETRY_COUNT:
                    time.sleep(RETRY_INTERVAL)
                continue

            if attempt == 0:
                print(f"  ✓ {filename} ({size_bytes // 1024} KB)")
            else:
                print(f"  ✓ {filename} ({size_bytes // 1024} KB, 第 {attempt + 1} 次尝试成功)")
            downloaded += 1
            success = True
            break
        else:
            last_error = f"文件未出现 (等待 {wait_total:.0f}s)"
            if attempt < RETRY_COUNT:
                print(f"  ↻ {filename} 第 {attempt + 1} 次失败: {last_error}，{RETRY_INTERVAL}s 后重试")
                time.sleep(RETRY_INTERVAL)

    if not success:
        print(f"  ❌ {filename} 重试 {RETRY_COUNT} 次后仍失败 ({last_error})，跳过")
        skipped += 1

    # 短暂喘息（实际节流由等待文件出现承担）
    time.sleep(0.5)

page.quit()

# ============================================================
# 下载总结
# ============================================================

elapsed = time.time() - start_time
elapsed_str = format_elapsed(elapsed)

print()
print("═" * 50)
print(f"✅ 下载完成! 成功 {downloaded}, 失败 {failed}, 跳过 {skipped}, 耗时 {elapsed_str}")
print("═" * 50)
