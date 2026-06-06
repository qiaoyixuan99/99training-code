@echo off
chcp 65001 >nul
:: ============================================================
:: Git 自动提交监视器 — Windows 启动脚本
:: 用法：
::   双击运行 → 在后台启动监视器
::   放到 shell:startup → 开机自动启动
:: ============================================================

cd /d "%~dp0.."

echo.
echo ╔══════════════════════════════════════════════╗
echo ║   Git 自动同步系统 — 启动监视器             ║
echo ╚══════════════════════════════════════════════╝
echo.
echo   仓库路径: %cd%
echo   检查间隔: 120 秒（每 2 分钟）
echo.

:: 使用 pythonw 在后台运行（无命令行窗口，不弹窗）
where pythonw >nul 2>&1
if %errorlevel%==0 (
    echo   模式: 后台静默运行
    start "" pythonw "%~dp0auto_commit_watcher.py" --interval 120
) else (
    echo   [错误] 未找到 pythonw.exe，请安装 Python 后重试
    pause
    exit /b 1
)

echo   监视器已在后台启动！
echo   查看状态: python auto-sync\auto_commit_watcher.py --status
echo   停止方法: 任务管理器中结束 python.exe/pythonw.exe
echo.
pause
