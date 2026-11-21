import sys
import os
import time
import random
import json
import ctypes
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGroupBox, QLabel, QSpinBox, 
                             QComboBox, QPushButton, QCheckBox, QTextEdit,
                             QMessageBox, QSlider, QTabWidget, QGridLayout, QFrame,
                             QProgressBar, QSystemTrayIcon, QMenu, QAction,
                             QTextBrowser)  
from PyQt5.QtCore import (Qt, QThread, pyqtSignal, QTimer, QSettings, 
                          QPoint, QRect, QDate, QCoreApplication)
from PyQt5.QtGui import (QIcon, QFont, QPalette, QColor, QTextCursor,
                         QCloseEvent, QMouseEvent)
import win32api
import win32con
import win32gui

# 尝试导入Windows任务栏相关模块
try:
    from PyQt5.QtWinExtras import QWinTaskbarButton, QWinTaskbarProgress
    HAS_WIN_EXTRAS = True
    print("✓ PyQt5.QtWinExtras 模块可用 - 支持任务栏进度条")
except ImportError as e:
    HAS_WIN_EXTRAS = False
    print(f"✗ PyQt5.QtWinExtras 模块不可用 - 任务栏进度条功能将禁用: {e}")

class ProjectInfo:
    """项目信息元数据（集中管理所有项目相关信息）"""
    VERSION = "3.0.1"
    BUILD_DATE = "2026-02-26"
    # from datetime import datetime
    # BUILD_DATE = datetime.now().strftime("%Y-%m-%d")  # 修改为动态获取当前日期
    AUTHOR = "杜玛"
    LICENSE = "MIT"
    COPYRIGHT = "© 永久 杜玛"
    URL = "https://github.com/duma520"
    MAINTAINER_EMAIL = "不提供"
    NAME = "鼠标抖动模拟器"
    DESCRIPTION = """鼠标抖动模拟器
主要功能：
1. 定时移动鼠标防止系统休眠
2. 支持8个方向移动（含对角线）
3. 可自定义移动间隔、方向和距离
4. 实时显示运行状态和进度
5. 支持Windows任务栏进度条显示
6. 系统托盘图标支持
7. 自动保存和加载设置
8. 详细的运行统计信息
9. 多线程处理，界面无卡顿
10. 适应各种分辨率显示
"""


    VERSION_HISTORY = {
        "1.0.0": "初始版本 - 基本鼠标移动功能",
        "2.2.0": "增加8方向移动和统计功能",
        "3.0.0": "增加任务栏进度条和系统托盘",
        "3.0.1": "修复已知问题，优化用户体验"
    }
    HELP_TEXT = """
基本操作指南：
1. 设置移动间隔（5-3600秒）
2. 选择移动方向（随机或指定方向）
3. 设置移动距离（1-10像素）
4. 点击"开始运行"按钮启动
5. 程序会在后台定时移动鼠标
6. 可随时暂停或停止运行
7. 最小化到系统托盘可后台运行

高级功能：
- 任务栏进度条：显示下次移动倒计时
- 系统托盘：最小化到托盘，右键菜单控制
- 自动启动：启动时自动运行
- 详细统计：记录各方向移动次数
- 运行日志：记录所有操作事件

注意事项：
- 移动距离为1像素，肉眼难以察觉
- 每次移动后会立即返回原位
- 对正常使用电脑无影响
- 关闭窗口可选择退出或最小化到托盘
"""


    @classmethod
    def get_metadata(cls) -> dict:
        """获取主要元数据字典"""
        return {
            'version': cls.VERSION,
            'author': cls.AUTHOR,
            'license': cls.LICENSE,
            'url': cls.URL
        }


    @classmethod
    def get_header(cls) -> str:
        """生成标准化的项目头信息"""
        return f"{cls.NAME} {cls.VERSION} | {cls.LICENSE} License | {cls.URL}"



    @classmethod
    def get_about_info(cls):
        """获取ABOUT信息字典"""
        return {
            "name": cls.NAME,
            "version": cls.VERSION,
            "build_date": cls.BUILD_DATE,
            "author": cls.AUTHOR,
            "license": cls.LICENSE,
            "copyright": cls.COPYRIGHT,
            "url": cls.URL,
            "description": cls.DESCRIPTION,
            "features": [
                "定时移动鼠标防止系统休眠",
                "支持8个方向移动（含对角线）",
                "Windows任务栏进度条显示",
                "系统托盘图标支持",
                "详细的运行统计信息",
                "自动保存和加载设置"
            ]
        }



class MouseSimulatorThread(QThread):
    """鼠标模拟线程"""
    update_status = pyqtSignal(str)
    update_count = pyqtSignal(int)
    update_next_time = pyqtSignal(str)
    update_direction = pyqtSignal(str)
    update_progress_value = pyqtSignal(int)  # 新增：进度值信号
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_paused = False
        self.interval = 60  # 默认60秒
        self.direction = "random"  # random, up, down, left, right, upleft, upright, downleft, downright
        self.move_distance = 1  # 移动像素
        self.count = 0
        self.next_move_time = 0
        
    def set_params(self, interval, direction, move_distance):
        """设置参数"""
        self.interval = interval
        self.direction = direction
        self.move_distance = move_distance
        
    def run(self):
        """线程运行主函数"""
        self.is_running = True
        self.is_paused = False
        self.count = 0
        
        while self.is_running:
            try:
                if not self.is_paused:
                    # 获取当前鼠标位置
                    current_x, current_y = win32api.GetCursorPos()
                    
                    # 确定移动方向
                    if self.direction == "random":
                        dir_choice = random.choice(["up", "down", "left", "right", 
                                                    "upleft", "upright", "downleft", "downright"])
                    else:
                        dir_choice = self.direction
                    
                    # 计算新位置（支持对角线移动）
                    new_x, new_y = current_x, current_y
                    
                    # 上下移动
                    if "up" in dir_choice:
                        new_y = current_y - self.move_distance
                    elif "down" in dir_choice:
                        new_y = current_y + self.move_distance
                    
                    # 左右移动（包括对角线）
                    if "left" in dir_choice:
                        new_x = current_x - self.move_distance
                    elif "right" in dir_choice:
                        new_x = current_x + self.move_distance
                    
                    # 纯上下左右（不移对角线）
                    if dir_choice == "up":
                        new_y = current_y - self.move_distance
                    elif dir_choice == "down":
                        new_y = current_y + self.move_distance
                    elif dir_choice == "left":
                        new_x = current_x - self.move_distance
                    elif dir_choice == "right":
                        new_x = current_x + self.move_distance
                    
                    # 移动鼠标
                    win32api.SetCursorPos((new_x, new_y))
                    time.sleep(0.05)  # 短暂延迟，确保移动完成
                    win32api.SetCursorPos((current_x, current_y))
                    
                    # 更新计数
                    self.count += 1
                    self.update_count.emit(self.count)
                    
                    # 更新方向信息
                    dir_names = {
                        "up": "↑ 上", 
                        "down": "↓ 下", 
                        "left": "← 左", 
                        "right": "→ 右",
                        "upleft": "↖ 左上", 
                        "upright": "↗ 右上", 
                        "downleft": "↙ 左下", 
                        "downright": "↘ 右下"
                    }
                    self.update_direction.emit(dir_names.get(dir_choice, dir_choice))
                    
                    # 更新状态
                    current_time = datetime.now().strftime("%H:%M:%S")
                    self.update_status.emit(f"已执行操作 - {current_time}")
                    
                    # 计算下一次移动时间
                    self.next_move_time = time.time() + self.interval
                    next_time_str = datetime.fromtimestamp(
                        self.next_move_time).strftime("%H:%M:%S")
                    self.update_next_time.emit(next_time_str)
                    
                    # 重置进度条
                    self.update_progress_value.emit(0)
                
                # 等待间隔时间，同时更新进度
                start_wait = time.time()
                while self.is_running and time.time() - start_wait < self.interval:
                    if self.is_paused:
                        time.sleep(0.1)
                    else:
                        # 计算并发送进度
                        elapsed = time.time() - start_wait
                        progress = int((elapsed / self.interval) * 100)
                        self.update_progress_value.emit(min(progress, 99))
                        time.sleep(0.1)
                        
            except Exception as e:
                self.update_status.emit(f"错误: {str(e)}")
                time.sleep(1)
    
    def stop(self):
        """停止线程"""
        self.is_running = False
        
    def pause(self):
        """暂停"""
        self.is_paused = True
        
    def resume(self):
        """恢复"""
        self.is_paused = False

class SettingsManager:
    """设置管理器"""
    def __init__(self):
        self.settings_file = "mouse_simulator_settings.json"
        self.default_settings = {
            "interval": 60,
            "direction": "random",
            "move_distance": 1,
            "auto_start": False,
            "show_notifications": True,
            "show_taskbar_progress": True,  # 新增：任务栏进度条显示选项
            "window_geometry": None,
            "window_state": None
        }
        
    def load_settings(self):
        """加载设置"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # 确保所有默认键都存在
                    for key, value in self.default_settings.items():
                        if key not in settings:
                            settings[key] = value
                    return settings
        except Exception as e:
            print(f"加载设置失败: {e}")
        
        return self.default_settings.copy()
    
    def save_settings(self, settings):
        """保存设置"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存设置失败: {e}")
            return False

class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()
        self.settings = self.settings_manager.load_settings()
        self.mouse_thread = MouseSimulatorThread()
        
        # 任务栏进度条相关
        self.taskbar_button = None
        self.taskbar_progress = None
        
        self.init_ui()
        self.load_settings_to_ui()
        self.setup_signals()
        
        # 检查图标文件
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))
        
        # 定时更新进度显示
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_progress)
        self.update_timer.start(1000)  # 每秒更新
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"{ProjectInfo.NAME} {ProjectInfo.VERSION} (Build: {ProjectInfo.BUILD_DATE})")
        self.setMinimumSize(550, 700)
        
        # 设置应用样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QPushButton#stopBtn {
                background-color: #f44336;
            }
            QPushButton#stopBtn:hover {
                background-color: #da190b;
            }
            QPushButton#pauseBtn {
                background-color: #ff9800;
            }
            QPushButton#pauseBtn:hover {
                background-color: #e68900;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 3px;
                font-family: Consolas, monospace;
            }
            QSpinBox, QComboBox {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 3px;
                min-height: 20px;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 3px;
            }
            QTabBar::tab {
                padding: 8px 15px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border: 1px solid #cccccc;
                border-bottom: none;
            }
        """)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建标签页
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # 主控制标签页
        control_tab = QWidget()
        tabs.addTab(control_tab, "⚙️ 主控制")
        
        # 统计标签页
        stats_tab = QWidget()
        tabs.addTab(stats_tab, "📊 统计信息")
        
        # 关于标签页
        about_tab = QWidget()
        tabs.addTab(about_tab, "ℹ️ 关于")
        
        # 设置主控制标签页布局
        control_layout = QVBoxLayout(control_tab)
        control_layout.setSpacing(10)
        
        # 参数设置组
        param_group = QGroupBox("参数设置")
        param_layout = QGridLayout(param_group)
        param_layout.setVerticalSpacing(10)
        param_layout.setHorizontalSpacing(15)
        
        # 间隔时间
        param_layout.addWidget(QLabel("移动间隔:"), 0, 0)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(5, 3600)
        self.interval_spin.setValue(self.settings.get("interval", 60))
        self.interval_spin.setSuffix(" 秒")
        self.interval_spin.setToolTip("设置鼠标移动的时间间隔（5-3600秒）")
        self.interval_spin.setMinimumWidth(120)
        param_layout.addWidget(self.interval_spin, 0, 1)
        
        # 移动方向 - 增加到8个方向
        param_layout.addWidget(QLabel("移动方向:"), 1, 0)
        self.direction_combo = QComboBox()
        self.direction_combo.addItems([
            "随机方向", 
            "向上 ↑", 
            "向下 ↓", 
            "向左 ←", 
            "向右 →",
            "左上 ↖", 
            "右上 ↗", 
            "左下 ↙", 
            "右下 ↘"
        ])
        self.direction_combo.setCurrentText(self.get_direction_text())
        self.direction_combo.setToolTip("选择鼠标移动的方向（支持8个方向）")
        self.direction_combo.setMinimumWidth(120)
        param_layout.addWidget(self.direction_combo, 1, 1)
        
        # 移动距离
        param_layout.addWidget(QLabel("移动距离:"), 2, 0)
        self.distance_spin = QSpinBox()
        self.distance_spin.setRange(1, 10)
        self.distance_spin.setValue(self.settings.get("move_distance", 1))
        self.distance_spin.setSuffix(" 像素")
        self.distance_spin.setToolTip("设置鼠标每次移动的像素距离（1-10像素）")
        self.distance_spin.setMinimumWidth(120)
        param_layout.addWidget(self.distance_spin, 2, 1)
        
        control_layout.addWidget(param_group)
        
        # 状态显示组
        status_group = QGroupBox("运行状态")
        status_layout = QGridLayout(status_group)
        status_layout.setVerticalSpacing(10)
        status_layout.setHorizontalSpacing(15)
        
        # 当前状态
        status_layout.addWidget(QLabel("当前状态:"), 0, 0)
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666666; font-weight: bold; font-size: 12px;")
        status_layout.addWidget(self.status_label, 0, 1)
        
        # 操作计数
        status_layout.addWidget(QLabel("已执行操作:"), 1, 0)
        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("color: #4CAF50; font-weight: bold; font-size: 14px;")
        status_layout.addWidget(self.count_label, 1, 1)
        
        # 最后方向
        status_layout.addWidget(QLabel("最后方向:"), 2, 0)
        self.last_direction_label = QLabel("-")
        self.last_direction_label.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.last_direction_label, 2, 1)
        
        # 下次移动
        status_layout.addWidget(QLabel("下次移动:"), 3, 0)
        self.next_time_label = QLabel("-")
        self.next_time_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        status_layout.addWidget(self.next_time_label, 3, 1)
        
        control_layout.addWidget(status_group)
        
        # 进度条组
        progress_group = QGroupBox("进度")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p% - 距离下次移动还有 %v 秒")
        progress_layout.addWidget(self.progress_bar)
        
        control_layout.addWidget(progress_group)
        
        # 控制按钮组
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.start_btn = QPushButton("▶ 开始运行")
        self.start_btn.clicked.connect(self.start_simulation)
        button_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("⏸️ 暂停")
        self.pause_btn.setObjectName("pauseBtn")
        self.pause_btn.clicked.connect(self.pause_simulation)
        self.pause_btn.setEnabled(False)
        button_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("■ 停止")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.clicked.connect(self.stop_simulation)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        control_layout.addLayout(button_layout)
        
        # 日志显示
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        clear_log_btn = QPushButton("清除日志")
        clear_log_btn.clicked.connect(self.clear_log)
        clear_log_btn.setMaximumWidth(100)
        log_layout.addWidget(clear_log_btn, alignment=Qt.AlignRight)
        
        control_layout.addWidget(log_group)
        
        # 统计标签页布局
        stats_layout = QVBoxLayout(stats_tab)
        stats_layout.setSpacing(15)
        
        # 统计信息 - 增加到8个方向的统计
        stats_group = QGroupBox("详细统计")
        stats_grid = QGridLayout(stats_group)
        stats_grid.setVerticalSpacing(10)
        stats_grid.setHorizontalSpacing(20)
        
        # 总运行次数
        stats_grid.addWidget(QLabel("总运行次数:"), 0, 0)
        self.total_count_label = QLabel("0")
        self.total_count_label.setStyleSheet("font-weight: bold; color: #4CAF50;")
        stats_grid.addWidget(self.total_count_label, 0, 1)
        
        # 方向统计 - 第一列
        stats_grid.addWidget(QLabel("向上移动:"), 1, 0)
        self.up_count_label = QLabel("0")
        self.up_count_label.setStyleSheet("color: #666;")
        stats_grid.addWidget(self.up_count_label, 1, 1)
        
        stats_grid.addWidget(QLabel("向下移动:"), 2, 0)
        self.down_count_label = QLabel("0")
        self.down_count_label.setStyleSheet("color: #666;")
        stats_grid.addWidget(self.down_count_label, 2, 1)
        
        stats_grid.addWidget(QLabel("向左移动:"), 3, 0)
        self.left_count_label = QLabel("0")
        self.left_count_label.setStyleSheet("color: #666;")
        stats_grid.addWidget(self.left_count_label, 3, 1)
        
        stats_grid.addWidget(QLabel("向右移动:"), 4, 0)
        self.right_count_label = QLabel("0")
        self.right_count_label.setStyleSheet("color: #666;")
        stats_grid.addWidget(self.right_count_label, 4, 1)
        
        # 方向统计 - 第二列（对角线）
        stats_grid.addWidget(QLabel("左上移动:"), 1, 2)
        self.upleft_count_label = QLabel("0")
        self.upleft_count_label.setStyleSheet("color: #666;")
        stats_grid.addWidget(self.upleft_count_label, 1, 3)
        
        stats_grid.addWidget(QLabel("右上移动:"), 2, 2)
        self.upright_count_label = QLabel("0")
        self.upright_count_label.setStyleSheet("color: #666;")
        stats_grid.addWidget(self.upright_count_label, 2, 3)
        
        stats_grid.addWidget(QLabel("左下移动:"), 3, 2)
        self.downleft_count_label = QLabel("0")
        self.downleft_count_label.setStyleSheet("color: #666;")
        stats_grid.addWidget(self.downleft_count_label, 3, 3)
        
        stats_grid.addWidget(QLabel("右下移动:"), 4, 2)
        self.downright_count_label = QLabel("0")
        self.downright_count_label.setStyleSheet("color: #666;")
        stats_grid.addWidget(self.downright_count_label, 4, 3)
        
        # 运行时间
        stats_grid.addWidget(QLabel("运行时间:"), 5, 0)
        self.runtime_label = QLabel("0分钟")
        self.runtime_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        stats_grid.addWidget(self.runtime_label, 5, 1)
        
        stats_layout.addWidget(stats_group)
        
        # 重置统计按钮
        reset_stats_btn = QPushButton("重置统计")
        reset_stats_btn.clicked.connect(self.reset_stats)
        reset_stats_btn.setMaximumWidth(120)
        stats_layout.addWidget(reset_stats_btn, alignment=Qt.AlignCenter)
        
        stats_layout.addStretch()
        
        # 关于标签页布局
        about_layout = QVBoxLayout(about_tab)

        about_text = QTextBrowser()
        about_text.setReadOnly(True)
        about_text.setStyleSheet("background-color: white;")

        # 获取项目信息
        project_info = ProjectInfo.get_about_info()

        # 生成版本历史HTML
        version_history_html = ""
        for version, description in ProjectInfo.VERSION_HISTORY.items():
            version_history_html += f"<li><b>{version}</b>: {description}</li>"

        # 生成功能列表HTML
        features_html = ""
        for feature in project_info["features"]:
            features_html += f"<li>{feature}</li>"

        # 设置HTML内容
        about_text.setHtml(f"""
        <div style='padding: 20px; font-family: "Microsoft YaHei", Arial, sans-serif;'>
            <h1 style='color: #4CAF50; text-align: center; margin-bottom: 5px;'>{project_info['name']}</h1>
            <p style='color: #666; text-align: center; font-size: 14px; margin-top: 0;'>
                版本 {project_info['version']} | 构建日期 {project_info['build_date']}
            </p>
            
            <div style='background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;'>
                <p style='color: #555; line-height: 1.6; white-space: pre-line;'>{project_info['description']}</p>
            </div>
            
            <div style='display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0;'>
                <div style='flex: 1; min-width: 250px;'>
                    <h3 style='color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 5px;'>📋 项目信息</h3>
                    <table style='width: 100%; border-collapse: collapse; color: #555;'>
                        <tr>
                            <td style='padding: 6px 0; font-weight: bold; width: 80px;'>作者:</td>
                            <td style='padding: 6px 0;'>{project_info['author']}</td>
                        </tr>
                        <tr>
                            <td style='padding: 6px 0; font-weight: bold;'>许可证:</td>
                            <td style='padding: 6px 0;'>{project_info['license']}</td>
                        </tr>
                        <tr>
                            <td style='padding: 6px 0; font-weight: bold;'>版权:</td>
                            <td style='padding: 6px 0;'>{project_info['copyright']}</td>
                        </tr>
                        <tr>
                            <td style='padding: 6px 0; font-weight: bold;'>网址:</td>
                            <td style='padding: 6px 0;'>
                                <a href="{project_info['url']}" style='color: #2196F3; text-decoration: none;'>
                                    {project_info['url']}
                                </a>
                            </td>
                        </tr>
                    </table>
                </div>
                
                <div style='flex: 1; min-width: 250px;'>
                    <h3 style='color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 5px;'>✨ 主要功能</h3>
                    <ul style='color: #555; padding-left: 20px; margin-top: 5px;'>
                        {features_html}
                    </ul>
                </div>
            </div>
            
            <div style='margin: 20px 0;'>
                <h3 style='color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 5px;'>📜 版本历史</h3>
                <ul style='color: #555; padding-left: 20px;'>
                    {version_history_html}
                </ul>
            </div>
            
            <div style='margin: 20px 0;'>
                <h3 style='color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 5px;'>📖 使用帮助</h3>
                <div style='color: #555; line-height: 1.6; white-space: pre-line; padding: 10px; background-color: #f8f9fa; border-radius: 5px;'>
                    {ProjectInfo.HELP_TEXT}
                </div>
            </div>
            
            <div style='text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;'>
                <p style='color: #999; font-size: 12px;'>
                    {project_info['copyright']}<br>
                    {project_info['name']} {project_info['version']} - {project_info['build_date']}<br>
                    基于 {project_info['license']} 许可证发布
                </p>
            </div>
        </div>
        """)

        # 设置链接可点击
        about_text.setOpenExternalLinks(True)
        about_layout.addWidget(about_text)
        
        # 底部设置区域
        bottom_frame = QFrame()
        bottom_frame.setFrameStyle(QFrame.StyledPanel)
        bottom_frame.setStyleSheet("QFrame { background-color: #e8e8e8; border-radius: 3px; }")
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(10, 8, 10, 8)
        
        self.auto_start_cb = QCheckBox("启动时自动运行")
        self.auto_start_cb.setChecked(self.settings.get("auto_start", False))
        self.auto_start_cb.setStyleSheet("QCheckBox { color: #333; }")
        bottom_layout.addWidget(self.auto_start_cb)
        
        self.notify_cb = QCheckBox("显示通知")
        self.notify_cb.setChecked(self.settings.get("show_notifications", True))
        self.notify_cb.setStyleSheet("QCheckBox { color: #333; }")
        bottom_layout.addWidget(self.notify_cb)
        
        # 任务栏进度条选项
        self.taskbar_progress_cb = QCheckBox("任务栏进度条")
        self.taskbar_progress_cb.setChecked(self.settings.get("show_taskbar_progress", True))
        self.taskbar_progress_cb.setStyleSheet("QCheckBox { color: #333; }")
        self.taskbar_progress_cb.toggled.connect(self.toggle_taskbar_progress)
        
        # 如果系统不支持任务栏进度条，禁用复选框
        if not HAS_WIN_EXTRAS:
            self.taskbar_progress_cb.setEnabled(False)
            self.taskbar_progress_cb.setToolTip("当前系统不支持任务栏进度条或缺少PyQt5.QtWinExtras模块")
        
        bottom_layout.addWidget(self.taskbar_progress_cb)
        
        bottom_layout.addStretch()
        
        # 版本信息
        version_label = QLabel(f"v{ProjectInfo.VERSION}")
        version_label.setStyleSheet("color: #999; font-size: 10px;")
        version_label.setToolTip(f"构建日期: {ProjectInfo.BUILD_DATE}")
        bottom_layout.addWidget(version_label)
        
        main_layout.addWidget(bottom_frame)
        
        # 初始化计数变量（增加到8个方向）
        self.direction_counts = {
            "up": 0, "down": 0, "left": 0, "right": 0,
            "upleft": 0, "upright": 0, "downleft": 0, "downright": 0
        }
        self.start_time = None
        self.total_runtime = 0
        
    def center_on_screen(self):
        """将窗口居中显示"""
        screen = QApplication.primaryScreen().availableGeometry()
        window = self.frameGeometry()
        window.moveCenter(screen.center())
        self.move(window.topLeft())
        
    def get_direction_text(self):
        """获取方向文本"""
        direction_map = {
            "random": "随机方向",
            "up": "向上 ↑",
            "down": "向下 ↓",
            "left": "向左 ←",
            "right": "向右 →",
            "upleft": "左上 ↖",
            "upright": "右上 ↗",
            "downleft": "左下 ↙",
            "downright": "右下 ↘"
        }
        return direction_map.get(self.settings.get("direction", "random"), "随机方向")
        
    def setup_signals(self):
        """设置信号连接"""
        self.mouse_thread.update_status.connect(self.update_status)
        self.mouse_thread.update_count.connect(self.update_count)
        self.mouse_thread.update_next_time.connect(self.update_next_time)
        self.mouse_thread.update_direction.connect(self.update_last_direction)
        self.mouse_thread.update_progress_value.connect(self.update_taskbar_progress)
        
    def load_settings_to_ui(self):
        """加载设置到UI"""
        self.interval_spin.setValue(self.settings.get("interval", 60))
        self.distance_spin.setValue(self.settings.get("move_distance", 1))
        
        direction = self.settings.get("direction", "random")
        direction_map = {
            "random": "随机方向",
            "up": "向上 ↑",
            "down": "向下 ↓",
            "left": "向左 ←",
            "right": "向右 →",
            "upleft": "左上 ↖",
            "upright": "右上 ↗",
            "downleft": "左下 ↙",
            "downright": "右下 ↘"
        }
        self.direction_combo.setCurrentText(direction_map.get(direction, "随机方向"))
        
    def save_ui_settings(self):
        """保存UI设置"""
        direction_map = {
            "随机方向": "random",
            "向上 ↑": "up",
            "向下 ↓": "down",
            "向左 ←": "left",
            "向右 →": "right",
            "左上 ↖": "upleft",
            "右上 ↗": "upright",
            "左下 ↙": "downleft",
            "右下 ↘": "downright"
        }
        
        # 保存窗口几何信息
        geometry = self.saveGeometry()
        
        self.settings.update({
            "interval": self.interval_spin.value(),
            "direction": direction_map.get(self.direction_combo.currentText(), "random"),
            "move_distance": self.distance_spin.value(),
            "auto_start": self.auto_start_cb.isChecked(),
            "show_notifications": self.notify_cb.isChecked(),
            "show_taskbar_progress": self.taskbar_progress_cb.isChecked(),
            "window_geometry": geometry.toBase64().data().decode() if geometry else None,
            "window_state": self.saveState().toBase64().data().decode() if self.saveState() else None
        })
        
        self.settings_manager.save_settings(self.settings)
        
    def init_taskbar_progress(self):
        """初始化任务栏进度条"""
        if not HAS_WIN_EXTRAS or not self.taskbar_progress_cb.isChecked():
            return
            
        self.log_message("正在初始化任务栏进度条...")
        
        try:
            # 创建任务栏按钮
            self.taskbar_button = QWinTaskbarButton(self)
            
            # 获取进度条对象
            self.taskbar_progress = self.taskbar_button.progress()
            
            # 初始状态
            self.taskbar_progress.setVisible(False)
            self.taskbar_progress.setRange(0, 100)
            self.taskbar_progress.setValue(0)
            
            self.log_message("✓ 任务栏进度条初始化完成")
            
            # 窗口显示后设置窗口句柄关联
            QTimer.singleShot(500, self.setup_window_handle)
            
        except Exception as e:
            self.log_message(f"✗ 任务栏进度条初始化失败: {e}")
            self.taskbar_button = None
            self.taskbar_progress = None
            
    def setup_window_handle(self):
        """设置窗口句柄关联"""
        if not self.taskbar_button or not self.taskbar_progress_cb.isChecked():
            return
            
        try:
            # 获取窗口句柄
            window_handle = self.windowHandle()
            if window_handle:
                # 设置关联
                self.taskbar_button.setWindow(window_handle)
                self.log_message("✓ 任务栏进度条窗口句柄已关联")
        except Exception as e:
            self.log_message(f"✗ 设置窗口句柄失败: {e}")
            
    def show_taskbar_progress(self):
        """显示任务栏进度条"""
        if self.taskbar_progress and self.taskbar_progress_cb.isChecked():
            try:
                self.taskbar_progress.setVisible(True)
                self.taskbar_progress.resume()
            except Exception as e:
                self.log_message(f"✗ 显示任务栏进度条失败: {e}")
                
    def hide_taskbar_progress(self):
        """隐藏任务栏进度条"""
        if self.taskbar_progress:
            try:
                self.taskbar_progress.setVisible(False)
                self.taskbar_progress.stop()
            except Exception as e:
                pass  # 隐藏失败不影响主要功能
                
    def update_taskbar_progress(self, value):
        """更新任务栏进度条"""
        if self.taskbar_progress and self.taskbar_progress_cb.isChecked():
            try:
                if not self.taskbar_progress.isVisible():
                    self.taskbar_progress.setVisible(True)
                self.taskbar_progress.setValue(value)
            except Exception:
                pass  # 更新失败不影响主要功能
                
    def toggle_taskbar_progress(self, checked):
        """切换任务栏进度条显示"""
        if checked:
            if not self.taskbar_button:
                self.init_taskbar_progress()
            elif self.mouse_thread.is_running and not self.mouse_thread.is_paused:
                self.show_taskbar_progress()
        else:
            self.hide_taskbar_progress()
            
    def start_simulation(self):
        """开始模拟"""
        # 保存设置
        self.save_ui_settings()
        
        # 初始化任务栏进度条（如果需要）
        if self.taskbar_progress_cb.isChecked() and not self.taskbar_button:
            self.init_taskbar_progress()
        
        # 获取参数
        direction_map = {
            "随机方向": "random",
            "向上 ↑": "up",
            "向下 ↓": "down",
            "向左 ←": "left",
            "向右 →": "right",
            "左上 ↖": "upleft",
            "右上 ↗": "upright",
            "左下 ↙": "downleft",
            "右下 ↘": "downright"
        }
        
        interval = self.interval_spin.value()
        direction = direction_map.get(self.direction_combo.currentText(), "random")
        distance = self.distance_spin.value()
        
        # 设置线程参数
        self.mouse_thread.set_params(interval, direction, distance)
        
        # 启动线程
        if not self.mouse_thread.isRunning():
            self.mouse_thread.start()
            self.start_time = time.time()
            
        # 更新按钮状态
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        # 显示任务栏进度条
        self.show_taskbar_progress()
        
        self.log_message("▶ 开始运行")
        self.update_status("运行中")
        
        # 显示通知
        if self.notify_cb.isChecked():
            self.statusBar().showMessage("程序开始运行", 3000)
        
    def pause_simulation(self):
        """暂停模拟"""
        if self.mouse_thread.is_running:
            if self.mouse_thread.is_paused:
                self.mouse_thread.resume()
                self.pause_btn.setText("⏸️ 暂停")
                self.log_message("▶ 恢复运行")
                # 恢复时显示进度条
                self.show_taskbar_progress()
                if self.notify_cb.isChecked():
                    self.statusBar().showMessage("恢复运行", 2000)
            else:
                self.mouse_thread.pause()
                self.pause_btn.setText("▶ 继续")
                self.log_message("⏸️ 暂停运行")
                # 暂停时隐藏进度条
                self.hide_taskbar_progress()
                if self.notify_cb.isChecked():
                    self.statusBar().showMessage("已暂停", 2000)
        
    def stop_simulation(self):
        """停止模拟"""
        if self.mouse_thread.isRunning():
            self.mouse_thread.stop()
            self.mouse_thread.wait()
            
        # 更新按钮状态
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.pause_btn.setText("⏸️ 暂停")
        
        # 隐藏任务栏进度条
        self.hide_taskbar_progress()
        
        self.progress_bar.setValue(0)
        self.log_message("⏹️ 停止运行")
        self.update_status("已停止")
        
        # 更新运行时间
        if self.start_time:
            self.total_runtime += int(time.time() - self.start_time)
            self.start_time = None
            
        if self.notify_cb.isChecked():
            self.statusBar().showMessage("已停止运行", 3000)
        
    def update_status(self, status):
        """更新状态显示"""
        self.status_label.setText(status)
        
    def update_count(self, count):
        """更新计数"""
        self.count_label.setText(str(count))
        self.total_count_label.setText(str(count))
        
    def update_next_time(self, next_time):
        """更新下次移动时间"""
        self.next_time_label.setText(next_time)
        
    def update_last_direction(self, direction):
        """更新最后移动方向"""
        self.last_direction_label.setText(direction)
        
        # 更新方向统计（8个方向）
        if "↑ 上" in direction:
            self.direction_counts["up"] += 1
            self.up_count_label.setText(str(self.direction_counts["up"]))
        elif "↓ 下" in direction:
            self.direction_counts["down"] += 1
            self.down_count_label.setText(str(self.direction_counts["down"]))
        elif "← 左" in direction:
            self.direction_counts["left"] += 1
            self.left_count_label.setText(str(self.direction_counts["left"]))
        elif "→ 右" in direction:
            self.direction_counts["right"] += 1
            self.right_count_label.setText(str(self.direction_counts["right"]))
        elif "↖ 左上" in direction:
            self.direction_counts["upleft"] += 1
            self.upleft_count_label.setText(str(self.direction_counts["upleft"]))
        elif "↗ 右上" in direction:
            self.direction_counts["upright"] += 1
            self.upright_count_label.setText(str(self.direction_counts["upright"]))
        elif "↙ 左下" in direction:
            self.direction_counts["downleft"] += 1
            self.downleft_count_label.setText(str(self.direction_counts["downleft"]))
        elif "↘ 右下" in direction:
            self.direction_counts["downright"] += 1
            self.downright_count_label.setText(str(self.direction_counts["downright"]))
            
    def update_progress(self):
        """更新进度条"""
        if self.mouse_thread.is_running and not self.mouse_thread.is_paused:
            if self.mouse_thread.next_move_time > 0:
                current_time = time.time()
                remaining = self.mouse_thread.next_move_time - current_time
                total = self.mouse_thread.interval
                
                if remaining > 0:
                    progress = int((1 - remaining / total) * 100)
                    self.progress_bar.setValue(progress)
                    # 设置进度条格式
                    remaining_seconds = int(max(0, remaining))
                    self.progress_bar.setFormat(f"%p% - 剩余 {remaining_seconds} 秒")
                else:
                    self.progress_bar.setValue(0)
                    
        # 更新运行时间
        if self.start_time:
            runtime = int(time.time() - self.start_time) + self.total_runtime
            minutes = runtime // 60
            seconds = runtime % 60
            self.runtime_label.setText(f"{minutes}分{seconds}秒")
            
    def log_message(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # 自动滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
        
    def clear_log(self):
        """清除日志"""
        self.log_text.clear()
        self.log_message("日志已清除")
        
    def reset_stats(self):
        """重置统计"""
        self.direction_counts = {
            "up": 0, "down": 0, "left": 0, "right": 0,
            "upleft": 0, "upright": 0, "downleft": 0, "downright": 0
        }
        self.up_count_label.setText("0")
        self.down_count_label.setText("0")
        self.left_count_label.setText("0")
        self.right_count_label.setText("0")
        self.upleft_count_label.setText("0")
        self.upright_count_label.setText("0")
        self.downleft_count_label.setText("0")
        self.downright_count_label.setText("0")
        self.total_runtime = 0
        self.runtime_label.setText("0分钟")
        self.log_message("统计已重置")
        
        if self.notify_cb.isChecked():
            self.statusBar().showMessage("统计已重置", 2000)
        
    def showEvent(self, event):
        """显示事件"""
        super().showEvent(event)
        
        # 初始化任务栏进度条（如果需要）
        if self.taskbar_progress_cb.isChecked() and not self.taskbar_button:
            self.init_taskbar_progress()
        
        # 如果设置了自动启动
        if self.auto_start_cb.isChecked() and not self.mouse_thread.isRunning():
            QTimer.singleShot(500, self.start_simulation)
            
    def closeEvent(self, event: QCloseEvent):
        """关闭事件"""
        reply = QMessageBox.question(
            self, 
            "确认退出", 
            "确定要退出程序吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.quit_app()
            event.accept()
        else:
            event.ignore()
            
    def quit_app(self):
        """退出应用"""
        # 停止模拟
        if self.mouse_thread.isRunning():
            self.mouse_thread.stop()
            self.mouse_thread.wait()
            
        # 隐藏任务栏进度条
        self.hide_taskbar_progress()
        
        # 保存设置
        self.save_ui_settings()
        
        # 退出应用
        QApplication.quit()
        
    def resizeEvent(self, event):
        """调整窗口大小事件"""
        super().resizeEvent(event)
        # 可以在这里处理窗口大小变化

def main():
    """主函数"""
    # 设置DPI感知（适应高分辨率）
    try:
        # Windows 8.1 及以上版本
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        try:
            # Windows Vista 及以上版本
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass
    
    app = QApplication(sys.argv)
    
    # 设置应用程序元数据（使用ProjectInfo类中的信息）
    app.setApplicationName(ProjectInfo.NAME)
    app.setApplicationDisplayName(f"{ProjectInfo.NAME} {ProjectInfo.VERSION}")
    app.setApplicationVersion(ProjectInfo.VERSION)
    app.setOrganizationName("MouseSimulator")
    app.setOrganizationDomain(ProjectInfo.URL.replace("https://", ""))
    
    # 设置窗口图标（如果存在）
    icon_path = "icon.ico"
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # 设置应用字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    # 创建主窗口
    window = MainWindow()
    
    # 恢复窗口位置
    if "window_geometry" in window.settings and window.settings["window_geometry"]:
        try:
            geometry_data = bytes.fromhex(window.settings["window_geometry"])
            window.restoreGeometry(geometry_data)
        except:
            window.resize(550, 700)
            window.center_on_screen()
    else:
        window.resize(550, 700)
        window.center_on_screen()
    
    # 恢复窗口状态
    if "window_state" in window.settings and window.settings["window_state"]:
        try:
            state_data = bytes.fromhex(window.settings["window_state"])
            window.restoreState(state_data)
        except:
            pass
    
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()