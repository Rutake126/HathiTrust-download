from DrissionPage import ChromiumPage, ChromiumOptions
import time
import os
#第5行到第9行代码参数自行修改
PROXY_ADDR = '127.0.0.1:7897'
SAVE_DIR = r"E:\2025\downloads"
BOOK_ID = "keio.10810310333"
START_SEQ = 10
END_SEQ = 13 # 修改为实际页数，左闭右开
URL_TEMPLATE = "https://babel.hathitrust.org/cgi/imgsrv/image?id={book_id}&format=image/jpeg&size=ppi:300&seq={seq}"

# --- 主要修改在这里 ---
# 创建浏览器配置对象
options = ChromiumOptions()

# 设置代理
options.set_argument(f'--proxy-server=http://{PROXY_ADDR}')

# 设置无头模式 (False 表示有界面，True 表示无界面)
options.headless(False)

# 设置下载路径和其他实验性选项
options.set_pref("download.default_directory", SAVE_DIR)  # 设置默认下载目录
options.set_pref("download.prompt_for_download", False) # 不弹出保存对话框
options.set_pref("download.directory_upgrade", True)
options.set_pref("safebrowsing.enabled", True)

# 使用配置创建页面对象
page = ChromiumPage(options)
# --- 修改结束 ---

# 确保保存目录存在
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

for seq in range(START_SEQ, END_SEQ + 1):
    url = URL_TEMPLATE.format(book_id=BOOK_ID, seq=seq)
    filename = f"seq_{seq}.jpg"
    print(f"⬇ 正在触发下载: {filename}")

    page.get(url)
    time.sleep(2)  # 等待图片加载

    # 自动生成下载链接并点击
    page.run_js(
        f"""
        var a = document.createElement('a');
        a.href = window.location.href;
        a.download = '{filename}';
        document.body.appendChild(a);
        a.click();
        a.remove();
        """
    )
    time.sleep(1)  # 避免连续触发过快

print("下载已完成！")

# 建议在脚本结束时关闭浏览器
page.quit()
