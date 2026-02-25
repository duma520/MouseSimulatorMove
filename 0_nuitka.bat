@echo off
chcp 65001 >nul
cls

echo 清理旧文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo 开始打包（简化版）...
REM 使用最简参数，移除所有中文描述
nuitka --standalone ^
       --windows-icon-from-ico=icon.ico ^
       --enable-plugin=pyqt5 ^
       --include-qt-plugins=all ^
       --windows-console-mode=disable ^
       --output-dir=build ^
       --mingw64 ^
       MouseSimulatorMove.py

if %errorlevel% equ 0 (
    echo 打包成功！
) else (
    echo 打包失败，请检查错误。
)
pause