import os
import time
from DrissionPage import ChromiumPage, ChromiumOptions

BOOK_ID = 'nyp.33433082168125' #书籍id，自行更换
BASE_DIR = r'E:\2025\downloads'  # 下载目录,自行更换
PROXY_ADDR = '127.0.0.1:7890'     # 可自定义代理地址


def build_url(book_id, seq):
    return f'https://babel.hathitrust.org/cgi/imgsrv/image?id={book_id}&attachment=1&tracker=D1&format=image/jpeg&size=ppi:300&seq={seq}'


def setup_browser(use_proxy=False):
    options = ChromiumOptions()
    options.headless = False  # 打开可见浏览器
    if use_proxy:
        options.set_argument(f'--proxy-server=http://{PROXY_ADDR}')
        print(f'🔌 使用代理：{PROXY_ADDR}')
    else:
        print('🌐 不使用代理')
    return ChromiumPage(options)


def ensure_download_dir():
    path = BASE_DIR
    os.makedirs(path, exist_ok=True)
    print(f'📁 文件将保存到：{path}')
    return path


def wait_for_download(download_path, before_files):
    timeout = 30  # 最多等待30秒
    for _ in range(timeout):
        after_files = set(os.listdir(download_path))
        new_files = after_files - before_files
        if new_files:
            return new_files
        time.sleep(1)
    return set()


def main():
    # 下载设置
    mode = input("请选择下载方式：1. 全本下载  2. 自定义页码（输入1或2）: ").strip()
    if mode == '2':
        start, end = map(int, input("请输入起始页码和结束页码（例如 1 10）：").strip().split())
    else:
        start, end = 1, 386  # 默认最多下载500页

    use_proxy = input("是否启用代理？(y/n)：").strip().lower() == 'y'
    browser = setup_browser(use_proxy)
    download_dir = ensure_download_dir()

    # 设置浏览器下载路径
    browser.set.download_path(download_dir)

    for seq in range(start, end + 1):
        print(f'⬇ 正在下载第 {seq} 页...')
        url = build_url(BOOK_ID, seq)

        before = set(os.listdir(download_dir))
        browser.get(url)
        new_files = wait_for_download(download_dir, before)

        if new_files:
            print(f'✅ 第 {seq} 页下载完成：{list(new_files)[0]}')
        else:
            print(f'⚠️ 第 {seq} 页下载失败或超时。')

    browser.quit()
    print('🎉 所有页面处理完成！')


if __name__ == '__main__':
    main()
    
