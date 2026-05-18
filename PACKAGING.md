# HathiTrust Downloader 打包说明

本文档记录本项目当前可复现的 Windows EXE 打包方案，重点是减小体积、保持功能可用，以及处理常见错误。

## 当前推荐方案

推荐使用 PyInstaller + 干净虚拟环境打包。

当前实测结果：

- 原始方案：约 90 MB
- 优化后单文件：约 15.77 MB
- 输出文件：`dist\HathiTrust-Downloader-v2.0.1.exe`

主要优化点：

- 使用只包含必要依赖的 `.pack-venv`
- 排除明显无关的大型模块
- 使用 `--optimize 2`
- 保留 `customtkinter` 和 `DrissionPage`，保证 GUI 和浏览器控制功能可用

## 环境要求

建议使用 Python 3.10.x。当前测试使用：

```bat
C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe
```

如果该路径不存在，需要先安装 Python 3.10，并确认包含：

- pip
- Tcl/Tk
- venv

注意：旧环境 `E:\2025\venv` 已发现不可用，其 `pyvenv.cfg` 指向了不存在的基础解释器：

```text
C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe
```

如果继续使用旧 venv，可能出现：

```text
No Python at 'C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe'
```

因此不要再使用旧 `build.bat` 中的 `E:\2025\venv\Scripts\pyinstaller.exe`。

## 首次创建打包环境

在项目根目录执行：

```bat
C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe -m venv .pack-venv
.pack-venv\Scripts\python.exe -m pip install --upgrade pip pyinstaller customtkinter DrissionPage
```

如果网络慢，可以使用已有 pip 镜像源。当前机器 pip 实测使用阿里云源：

```text
https://mirrors.aliyun.com/pypi/simple/
```

## 推荐打包命令

可以直接运行：

```bat
build_optimized.bat
```

脚本会输出：

```text
dist\HathiTrust-Downloader-optimized-o2.exe
```

完整 PyInstaller 命令如下：

```bat
.pack-venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --optimize 2 ^
    --name HathiTrust-Downloader-optimized-o2 ^
    --add-data ".pack-venv\Lib\site-packages\customtkinter;customtkinter" ^
    --hidden-import DrissionPage ^
    --exclude-module pytest ^
    --exclude-module unittest ^
    --exclude-module doctest ^
    --exclude-module pydoc ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module matplotlib ^
    --exclude-module PIL ^
    --exclude-module PyQt5 ^
    --exclude-module PyQt6 ^
    --exclude-module PySide6 ^
    --exclude-module IPython ^
    --exclude-module jupyter ^
    --exclude-module notebook ^
    gui.py
```

## 为什么体积能降下来

原始打包方案依赖旧的大型 venv，里面包含大量本项目不需要的包。PyInstaller 分析时容易把无关依赖带进去。

优化方案使用 `.pack-venv`，只安装：

- `pyinstaller`
- `customtkinter`
- `DrissionPage`

再通过 `--exclude-module` 排除明显无关模块，避免误打包大型科学计算、绘图、Notebook、Qt 等依赖。

## onedir 分析命令

如果需要分析体积来源，可以先打 `onedir`：

```bat
.pack-venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed ^
    --name HathiTrust-Downloader-optimized ^
    --add-data ".pack-venv\Lib\site-packages\customtkinter;customtkinter" ^
    --hidden-import DrissionPage ^
    --exclude-module pytest ^
    --exclude-module unittest ^
    --exclude-module doctest ^
    --exclude-module pydoc ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module matplotlib ^
    --exclude-module PIL ^
    --exclude-module PyQt5 ^
    --exclude-module PyQt6 ^
    --exclude-module PySide6 ^
    --exclude-module IPython ^
    --exclude-module jupyter ^
    --exclude-module notebook ^
    gui.py
```

查看最大文件：

```powershell
Get-ChildItem dist\HathiTrust-Downloader-optimized -Recurse -File |
    Sort-Object Length -Descending |
    Select-Object -First 20 @{Name='MB';Expression={[math]::Round($_.Length/1MB,2)}},FullName
```

当前实测主要体积来自：

- `python310.dll`
- `lxml`
- `libcrypto`
- `tcl86t.dll`
- `tk86t.dll`
- `sqlite3.dll`
- `libssl`
- `customtkinter` 资源

这些大多来自 Python 运行时、Tk GUI、HTTPS、DrissionPage 依赖链，不能随意删除。

## 验证打包结果

打包后建议做一个基础启动测试：

```powershell
$p = Start-Process -FilePath "E:\2025\HathiTrust-download-main\HathiTrust-download-main\dist\HathiTrust-Downloader-optimized-o2.exe" -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 5
if ($p.HasExited) { "EXITED $($p.ExitCode)" } else { "RUNNING"; Stop-Process -Id $p.Id }
```

如果输出：

```text
RUNNING
```

说明 GUI 主程序可以启动，至少没有立即崩溃。

下载流程仍需要人工测试，因为它依赖：

- 网络
- HathiTrust 页面状态
- Chrome/Chromium 环境
- DrissionPage 浏览器连接

## 常见错误处理

### 1. No Python at ...

错误示例：

```text
No Python at 'C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe'
```

原因：

- venv 的基础 Python 被移动或卸载
- 旧 venv 不再可用

处理：

```bat
C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe -m venv .pack-venv
.pack-venv\Scripts\python.exe -m pip install --upgrade pip pyinstaller customtkinter DrissionPage
```

如果 `C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe` 不存在，先重新安装 Python 3.10。

### 2. PermissionError: WinError 5 拒绝访问

错误示例：

```text
PermissionError: [WinError 5] 拒绝访问。: 'dist\HathiTrust-Downloader-optimized-o2.exe'
```

常见原因：

- 目标 exe 正在运行
- Windows Defender 或杀软正在扫描
- 资源管理器或其它工具占用了文件

处理：

1. 关闭正在运行的 `HathiTrust-Downloader-optimized-o2.exe`
2. 等待几秒再重新打包
3. 如果仍失败，查看进程：

```powershell
Get-Process | Where-Object { $_.ProcessName -like 'HathiTrust-Downloader*' } |
    Select-Object Id,ProcessName,Path
```

必要时手动结束对应进程。

`build_optimized.bat` 已包含同名进程检测，检测到程序正在运行时会提示先关闭。

### 3. exe 第一次运行失败，第二次运行正常

存在这种可能，通常不是体积优化本身导致，而是首次运行初始化造成。

可能原因：

- PyInstaller `onefile` 首次需要解压到临时目录
- 杀软扫描新 exe 或临时解压文件
- DrissionPage 首次初始化浏览器配置
- Chrome 用户数据目录、Cookie、缓存首次建立
- 首次网络 DNS/TLS/证书链请求较慢
- HathiTrust 页面或浏览器会话首次连接不稳定

建议处理方向：

- 在代码中为网络请求增加 2-3 次自动重试
- 启动下载前预热 DrissionPage/Chrome
- 给首次浏览器连接设置更长超时
- 将首次运行失败信息写得更明确，提示用户稍后重试

### 4. PyInstaller 入口脚本异常

如果运行：

```bat
.pack-venv\Scripts\pyinstaller.exe
```

出现 Python 路径异常，可以改用：

```bat
.pack-venv\Scripts\python.exe -m PyInstaller
```

当前推荐脚本就是使用 `python.exe -m PyInstaller`。

## 后续继续减体积的方向

当前 15.77 MB 已经比较理想。如果还要继续减小，可以考虑：

- 将 `customtkinter` 改成原生 `tkinter`
- 检查 `DrissionPage` 是否可以延迟安装或外部化
- 为项目写更精细的 PyInstaller hook，排除 DrissionPage 中确实不用的子模块
- 尝试 Nuitka，但构建复杂度会提高，体积不一定更小

不要盲目删除以下组件：

- `tk86t.dll`
- `tcl86t.dll`
- `python310.dll`
- `libssl`
- `libcrypto`
- `lxml`

这些组件很可能是 GUI、HTTPS 或 DrissionPage 正常运行所需。

## 推荐维护方式

日常修改代码后：

```bat
build_optimized.bat
```

如果 `.pack-venv` 损坏或迁移到新机器：

```bat
C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe -m venv .pack-venv
.pack-venv\Scripts\python.exe -m pip install --upgrade pip pyinstaller customtkinter DrissionPage
build_optimized.bat
```

如果换了 Python 安装路径，需要同步修改 `build_optimized.bat` 中提示信息，但打包命令本身只依赖 `.pack-venv\Scripts\python.exe`。
