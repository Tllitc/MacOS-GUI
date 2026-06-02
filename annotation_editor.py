#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标注编辑器模块
负责动作标注的编辑、分页显示、撤销等功能
"""

import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QLineEdit,
                             QComboBox, QTextEdit, QGroupBox, QFormLayout,
                             QStackedWidget, QMessageBox, QScrollArea,
                             QFrame, QSplitter, QTabWidget)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QFont, QPainter

from screenshot_capture import ScreenshotCaptureWindow
from data_manager import DataManager
from screen_recorder import ScreenRecorder


class StepEditorWidget(QWidget):
    """单个步骤的编辑界面"""

    def __init__(self, step_data=None, parent=None):
        super().__init__(parent)
        self.step_data = step_data or {}
        # 滚动测量相关变量
        self.scroll_references = []  # 存储参照物的Y坐标列表
        self.is_measuring_scroll = False  # 是否正在测量滚动
        # 按键组合相关变量
        self.current_keys_input = None  # 当前获得焦点的按键输入框
        self.init_ui()
        # 安装事件过滤器来监听键盘事件
        self.installEventFilter(self)

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 截图预览区域
        preview_group = QGroupBox("截图预览")
        preview_layout = QVBoxLayout()

        self.screenshot_label = QLabel("暂无截图")
        self.screenshot_label.setAlignment(Qt.AlignCenter)
        self.screenshot_label.setMinimumSize(400, 300)
        self.screenshot_label.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
        preview_layout.addWidget(self.screenshot_label)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # 动作信息表单
        form_group = QGroupBox("动作信息")
        form_layout = QFormLayout()

        # 步骤编号（只读）
        self.step_number_label = QLabel("")
        form_layout.addRow("步骤:", self.step_number_label)

        # 动作描述
        self.intent_input = QLineEdit()
        self.intent_input.setPlaceholderText("例如：左键单击网易有道翻译")
        form_layout.addRow("动作描述:", self.intent_input)

        # CoT (Chain of Thought) - 隐藏但保留字段
        self.cot_input = QTextEdit()
        self.cot_input.setPlaceholderText("为什么要这么做...")
        self.cot_input.setMaximumHeight(80)
        self.cot_input.hide()  # 隐藏CoT输入框
        cot_label = QLabel("CoT:")
        cot_label.hide()  # 隐藏标签
        form_layout.addRow(cot_label, self.cot_input)

        # 活动窗口 - 隐藏但保留字段
        self.active_window_input = QLineEdit()
        self.active_window_input.setPlaceholderText("例如：网易有道翻译、Desktop")
        self.active_window_input.hide()  # 隐藏活动窗口输入框
        active_window_label = QLabel("活动窗口:")
        active_window_label.hide()  # 隐藏标签
        form_layout.addRow(active_window_label, self.active_window_input)

        # UI 元素名称 - 隐藏但保留字段
        self.element_input = QLineEdit()
        self.element_input.setPlaceholderText("例如：输入框、按钮")
        self.element_input.hide()  # 隐藏UI元素输入框
        element_label = QLabel("UI元素:")
        element_label.hide()  # 隐藏标签
        form_layout.addRow(element_label, self.element_input)

        # 动作类型选择（中文显示，英文存储）
        self.action_type_combo = QComboBox()
        # 定义中英文映射
        self.action_type_mapping = {
            "左键单击": "left_click",
            "双击": "double_click",
            "三击": "triple_click",
            "右键单击": "right_click",
            "中键单击": "middle_click",
            "拖拽": "left_click_drag",
            "鼠标移动": "mouse_move",
            "滚动": "scroll",
            "文本输入": "type",
            "按键组合": "keys",
            "等待": "wait",
            "回答用户": "answer",
            "任务完成": "terminate",
            "打开app": "open_app",
            "打开网页": "open_url"
        }
        # 添加中文选项
        chinese_types = list(self.action_type_mapping.keys())
        self.action_type_combo.addItems(chinese_types)
        self.action_type_combo.currentTextChanged.connect(self.on_action_type_changed)
        form_layout.addRow("动作类型:", self.action_type_combo)

        # 动态参数区域
        self.params_widget = QWidget()
        self.params_layout = QFormLayout(self.params_widget)

        # 坐标输入（只读）- 支持单坐标和双坐标（拖拽）
        self.coord_x_input = QLineEdit()
        self.coord_x_input.setPlaceholderText("X 坐标")
        self.coord_x_input.setReadOnly(True)  # 设置为只读
        self.coord_y_input = QLineEdit()
        self.coord_y_input.setPlaceholderText("Y 坐标")
        self.coord_y_input.setReadOnly(True)  # 设置为只读
        coord_layout = QHBoxLayout()
        coord_layout.addWidget(self.coord_x_input)
        coord_layout.addWidget(self.coord_y_input)
        self.params_layout.addRow("坐标 [x, y]:", coord_layout)

        # 拖拽终点坐标（仅用于 left_click_drag）
        self.end_coord_x_input = QLineEdit()
        self.end_coord_x_input.setPlaceholderText("终点 X 坐标")
        self.end_coord_x_input.setReadOnly(True)
        self.end_coord_y_input = QLineEdit()
        self.end_coord_y_input.setPlaceholderText("终点 Y 坐标")
        self.end_coord_y_input.setReadOnly(True)
        end_coord_layout = QHBoxLayout()
        end_coord_layout.addWidget(self.end_coord_x_input)
        end_coord_layout.addWidget(self.end_coord_y_input)
        self.end_coord_row = self.params_layout.rowCount()
        self.params_layout.addRow("终点坐标 [x, y]:", end_coord_layout)

        # 文本输入（用于 type/answer）
        self.text_input = QTextEdit()
        self.text_input.setMaximumHeight(60)
        self.params_layout.addRow("文本 (text):", self.text_input)

        # 按键输入（用于 keys）- 四个文本框，中间用"+"连接
        self.keys_input_1 = QLineEdit()
        self.keys_input_1.setPlaceholderText("按键1")
        self.keys_input_1.setReadOnly(True)

        self.keys_input_2 = QLineEdit()
        self.keys_input_2.setPlaceholderText("按键2")
        self.keys_input_2.setReadOnly(True)

        self.keys_input_3 = QLineEdit()
        self.keys_input_3.setPlaceholderText("按键3")
        self.keys_input_3.setReadOnly(True)

        self.keys_input_4 = QLineEdit()
        self.keys_input_4.setPlaceholderText("按键4")
        self.keys_input_4.setReadOnly(True)

        # 创建水平布局，包含四个文本框和三个"+"符号
        keys_layout = QHBoxLayout()
        keys_layout.addWidget(self.keys_input_1)
        keys_layout.addWidget(QLabel("+"))
        keys_layout.addWidget(self.keys_input_2)
        keys_layout.addWidget(QLabel("+"))
        keys_layout.addWidget(self.keys_input_3)
        keys_layout.addWidget(QLabel("+"))
        keys_layout.addWidget(self.keys_input_4)

        self.params_layout.addRow("按键组合:", keys_layout)

        # 为四个按键输入框安装事件过滤器
        self.keys_input_1.installEventFilter(self)
        self.keys_input_2.installEventFilter(self)
        self.keys_input_3.installEventFilter(self)
        self.keys_input_4.installEventFilter(self)

        # 滚动像素（用于 scroll）
        self.pixels_input = QLineEdit()
        self.pixels_input.setPlaceholderText("正值向上，负值向下")
        self.pixels_input.setReadOnly(True)  # 设置为只读，通过按钮自动计算

        # 滚动测量按钮
        self.scroll_measure_btn = QPushButton("开始测量滚动距离")
        self.scroll_measure_btn.clicked.connect(self.start_scroll_measurement)
        self.scroll_measure_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; }")

        # 完成测量按钮
        self.scroll_finish_btn = QPushButton("完成测量")
        self.scroll_finish_btn.clicked.connect(self.finish_scroll_measurement)
        self.scroll_finish_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        self.scroll_finish_btn.hide()  # 初始隐藏

        scroll_layout = QHBoxLayout()
        scroll_layout.addWidget(self.pixels_input)
        scroll_layout.addWidget(self.scroll_measure_btn)
        scroll_layout.addWidget(self.scroll_finish_btn)
        self.params_layout.addRow("滚动像素:", scroll_layout)

        # 等待时间（用于 wait）
        self.wait_time_input = QLineEdit()
        self.wait_time_input.setPlaceholderText("单位：秒")
        self.params_layout.addRow("等待时间:", self.wait_time_input)

        # 终止状态（用于 terminate）- 隐藏但保留字段
        self.status_combo = QComboBox()
        self.status_combo.addItems(["success", "failure"])
        self.status_combo.hide()  # 隐藏状态选择框
        status_label = QLabel("状态:")
        status_label.hide()  # 隐藏标签
        self.params_layout.addRow(status_label, self.status_combo)

        form_layout.addRow("参数:", self.params_widget)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # 加载已有数据
        if self.step_data:
            self.load_data()

        # 初始隐藏不相关的参数
        self.on_action_type_changed(self.action_type_combo.currentText())

    def eventFilter(self, obj, event):
        """事件过滤器，用于捕获键盘事件和焦点事件"""
        from PyQt5.QtCore import QEvent

        # 处理焦点进入事件
        if event.type() == QEvent.FocusIn:
            # 如果是按键输入框获得焦点
            if obj in [self.keys_input_1, self.keys_input_2, self.keys_input_3, self.keys_input_4]:
                self.current_keys_input = obj
                return False  # 让焦点事件正常处理

        # 只处理按键按下事件
        if event.type() == QEvent.KeyPress:
            # 如果当前有焦点的按键输入框
            if self.current_keys_input is not None and obj == self.current_keys_input:
                # 获取按下的键
                key = event.key()
                key_name = self.get_key_name(key)

                if key_name:
                    # 将键名填入当前焦点的文本框
                    self.current_keys_input.setText(key_name.lower())
                    # 返回True表示事件已处理，不再传递
                    return True

        # 其他事件交给父类处理
        return super().eventFilter(obj, event)

    def get_key_name(self, key):
        """将Qt键码转换为键名"""
        from PyQt5.QtCore import Qt

        # 特殊键映射
        key_map = {
            Qt.Key_Meta: "meta",
            Qt.Key_Control: "ctrl",
            Qt.Key_Alt: "alt",
            Qt.Key_Shift: "shift",
            Qt.Key_Enter: "enter",
            Qt.Key_Return: "enter",
            Qt.Key_Tab: "tab",
            Qt.Key_Backspace: "backspace",
            Qt.Key_Delete: "delete",
            Qt.Key_Escape: "escape",
            Qt.Key_Space: "space",
            Qt.Key_Up: "up",
            Qt.Key_Down: "down",
            Qt.Key_Left: "left",
            Qt.Key_Right: "right",
            Qt.Key_Home: "home",
            Qt.Key_End: "end",
            Qt.Key_PageUp: "pageup",
            Qt.Key_PageDown: "pagedown",
            Qt.Key_Insert: "insert",
        }

        if key in key_map:
            return key_map[key]

        # 字母和数字键
        if Qt.Key_A <= key <= Qt.Key_Z:
            return chr(key).lower()
        elif Qt.Key_0 <= key <= Qt.Key_9:
            return chr(key)

        # F1-F12功能键
        if Qt.Key_F1 <= key <= Qt.Key_F12:
            return f"f{key - Qt.Key_F1 + 1}"

        return None

    def start_scroll_measurement(self):
        if self.is_measuring_scroll:
            self.start_reference_capture()
            return

        current_y = None
        try:
            y_text = self.coord_y_input.text().strip()
            if y_text:
                current_y = int(y_text)
        except:
            pass

        if current_y is None:
            QMessageBox.warning(self, "警告", "请先在屏幕上选择一个参照物并拉框！")
            return

        self.scroll_references = [current_y]
        self.is_measuring_scroll = True
        self.scroll_measure_btn.setText("继续测量")
        self.scroll_measure_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; }")
        self.scroll_finish_btn.show()

        QMessageBox.information(self, "滚动测量",
            f"已获取第一个参照物Y坐标: {current_y}\n\n" +
            "请在屏幕上滚动后，选择同一个参照物并拉框，\n" +
            "系统将自动计算滚动像素。\n\n" +
            "您可以多次选择来累积滚动距离。")

        self.start_reference_capture()

    def start_reference_capture(self):
        """启动参照物捕获窗口"""
        # 隐藏主窗口
        main_window = self.window()
        if main_window:
            main_window.hide()

        # 延迟一下确保窗口完全隐藏
        QTimer.singleShot(200, self.show_reference_capture_window)

    def show_reference_capture_window(self):
        """显示参照物捕获窗口"""
        from screenshot_capture import ScreenshotCaptureWindow
        self.reference_capture_window = ScreenshotCaptureWindow()
        self.reference_capture_window.capture_completed.connect(self.on_reference_captured)
        self.reference_capture_window.show()

    def on_reference_captured(self, original_pixmap, marked_pixmap, rect_info, selection_type):
        """参照物捕获完成回调"""
        # 检查是否被取消
        if selection_type == "cancelled":
            # 用户取消了截图，重新显示主窗口
            main_window = self.window()
            if main_window:
                main_window.show()
                main_window.activateWindow()
            return

        # 获取参照物的中心Y坐标
        if isinstance(rect_info, tuple) and len(rect_info) >= 2:
            y_center = rect_info[1] + rect_info[3] // 2
            self.scroll_references.append(y_center)

            # 计算滚动距离（至少有两个参照物）
            if len(self.scroll_references) >= 2:
                # 计算相邻参照物之间的高度差并累加
                total_pixels = 0
                for i in range(1, len(self.scroll_references)):
                    # 向下滚动时，Y坐标增加，所以用前一个减后一个
                    diff = self.scroll_references[i-1] - self.scroll_references[i]
                    total_pixels += diff

                # 更新像素输入框
                self.pixels_input.setText(str(total_pixels))

                # 显示完成测量按钮
                self.scroll_finish_btn.show()

                # 显示当前累计结果
                QMessageBox.information(self, "滚动测量",
                    f"已选择 {len(self.scroll_references)} 个参照物\n" +
                    f"当前累计滚动像素: {total_pixels}\n\n" +
                    "点击'继续测量'按钮可以继续添加参照物，\n" +
                    "或点击'完成测量'结束测量。")
            else:
                # 这种情况不应该发生，因为第一个参照物已经在start_scroll_measurement中设置
                QMessageBox.warning(self, "错误", "参照物数据异常！")

        # 重新显示主窗口
        main_window = self.window()
        if main_window:
            main_window.show()
            main_window.activateWindow()

    def finish_scroll_measurement(self):
        """完成滚动测量"""
        if len(self.scroll_references) < 2:
            QMessageBox.warning(self, "警告", "至少需要选择两个参照物才能计算滚动距离！")
            return

        # 保存参照物数量用于显示
        ref_count = len(self.scroll_references)

        self.is_measuring_scroll = False
        self.scroll_measure_btn.setText("开始测量滚动距离")
        self.scroll_measure_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; }")
        self.scroll_finish_btn.hide()  # 隐藏完成测量按钮

        # 计算最终的滚动像素
        total_pixels = 0
        for i in range(1, len(self.scroll_references)):
            diff = self.scroll_references[i-1] - self.scroll_references[i]
            total_pixels += diff

        self.pixels_input.setText(str(total_pixels))

        # 清空参照物列表，但保留pixels值
        self.scroll_references = []

        QMessageBox.information(self, "测量完成",
            f"滚动测量完成！\n" +
            f"总共选择了 {ref_count} 个参照物\n" +
            f"最终滚动像素: {total_pixels}")

    def on_action_type_changed(self, action_type_chinese):
        """根据动作类型显示/隐藏相关参数"""
        # 将中文转换为英文
        action_type = self.action_type_mapping.get(action_type_chinese, action_type_chinese)

        # 隐藏所有参数
        for i in range(self.params_layout.rowCount()):
            label_item = self.params_layout.itemAt(i, QFormLayout.LabelRole)
            field_item = self.params_layout.itemAt(i, QFormLayout.FieldRole)
            if label_item and label_item.widget():
                label_item.widget().hide()
            if field_item and field_item.widget():
                field_item.widget().hide()

        # 根据动作类型显示相关参数
        if action_type in ["left_click", "double_click", "triple_click",
                          "right_click", "middle_click", "mouse_move"]:
            self.show_params([0])  # 坐标
            # 隐藏滚动测量按钮
            self.scroll_measure_btn.hide()
            self.scroll_finish_btn.hide()
        elif action_type == "left_click_drag":
            self.show_params([0, 1])  # 起点坐标 + 终点坐标
            # 隐藏滚动测量按钮
            self.scroll_measure_btn.hide()
            self.scroll_finish_btn.hide()
        elif action_type in ["type", "open_app", "open_url"]:
            self.show_params([2])  # 文本
            # 隐藏滚动测量按钮
            self.scroll_measure_btn.hide()
            self.scroll_finish_btn.hide()
        elif action_type == "answer":
            # answer 动作需要显示 intent 和 text
            self.show_params([2])  # 文本
            # intent 输入框始终显示，不需要特殊处理
            # 隐藏滚动测量按钮
            self.scroll_measure_btn.hide()
            self.scroll_finish_btn.hide()
        elif action_type == "keys":
            self.show_params([3])  # 按键
            # 隐藏滚动测量按钮
            self.scroll_measure_btn.hide()
            self.scroll_finish_btn.hide()
        elif action_type == "scroll":
            self.show_params([4])  # 滚动像素
            # 显示滚动测量相关按钮
            self.scroll_measure_btn.show()
            if self.is_measuring_scroll and len(self.scroll_references) >= 2:
                self.scroll_finish_btn.show()
            else:
                self.scroll_finish_btn.hide()
        elif action_type == "wait":
            self.show_params([5])  # 等待时间
            # 隐藏滚动测量按钮
            self.scroll_measure_btn.hide()
            self.scroll_finish_btn.hide()
        elif action_type == "terminate":
            # terminate 不需要任何参数
            # 隐藏滚动测量按钮
            self.scroll_measure_btn.hide()
            self.scroll_finish_btn.hide()

    def show_params(self, indices):
        """显示指定索引的参数行"""
        for idx in indices:
            if idx < self.params_layout.rowCount():
                label_item = self.params_layout.itemAt(idx, QFormLayout.LabelRole)
                field_item = self.params_layout.itemAt(idx, QFormLayout.FieldRole)
                if label_item and label_item.widget():
                    label_item.widget().show()
                if field_item and field_item.widget():
                    field_item.widget().show()

    def set_screenshot(self, pixmap):
        """设置截图预览"""
        if pixmap and not pixmap.isNull():
            # 缩放图片以适应标签
            scaled_pixmap = pixmap.scaled(
                self.screenshot_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.screenshot_label.setPixmap(scaled_pixmap)
        else:
            self.screenshot_label.setText("暂无截图")

    def set_step_number(self, number):
        """设置步骤编号"""
        self.step_number_label.setText(str(number))

    def load_data(self):
        """加载已有的步骤数据"""
        if not self.step_data:
            return

        # 加载基本信息
        self.intent_input.setText(self.step_data.get("intent", ""))
        self.cot_input.setPlainText(self.step_data.get("CoT", ""))

        observation = self.step_data.get("observation", {})
        self.active_window_input.setText(observation.get("active_window", ""))

        # 加载动作信息
        actions = self.step_data.get("actions", [])
        if actions:
            action = actions[0]  # 简化处理，假设每个步骤只有一个动作
            action_type = action.get("action", "left_click")

            # 找到对应的中文显示
            index = self.action_type_combo.findText(
                next((k for k, v in self.action_type_mapping.items() if v == action_type), action_type)
            )
            if index >= 0:
                self.action_type_combo.setCurrentIndex(index)

            # 加载参数
            if "coordinate" in action:
                coord = action["coordinate"]
                if isinstance(coord, list):
                    if len(coord) >= 2:
                        # 单坐标格式 [x, y]
                        self.coord_x_input.setText(str(coord[0]))
                        self.coord_y_input.setText(str(coord[1]))
                    elif len(coord) == 4:
                        # 双坐标格式 [[x1, y1], [x2, y2]]
                        if isinstance(coord[0], list) and len(coord[0]) >= 2:
                            self.coord_x_input.setText(str(coord[0][0]))
                            self.coord_y_input.setText(str(coord[0][1]))
                        if isinstance(coord[1], list) and len(coord[1]) >= 2:
                            self.end_coord_x_input.setText(str(coord[1][0]))
                            self.end_coord_y_input.setText(str(coord[1][1]))

            if "text" in action:
                self.text_input.setPlainText(action["text"])

            # 加载按键组合
            if "keys" in action:
                keys = action["keys"]
                if isinstance(keys, list):
                    keys_inputs = [self.keys_input_1, self.keys_input_2, self.keys_input_3, self.keys_input_4]
                    for i, key in enumerate(keys):
                        if i < len(keys_inputs):
                            keys_inputs[i].setText(str(key))

            if "element" in action:
                self.element_input.setText(action["element"])

            # 加载滚动像素
            if "pixels" in action:
                self.pixels_input.setText(str(action["pixels"]))

    def get_data(self):
        """获取当前编辑的数据"""
        # 获取中文显示文本
        action_type_chinese = self.action_type_combo.currentText()
        # 转换为英文字段值
        action_type = self.action_type_mapping.get(action_type_chinese, action_type_chinese)

        # 构建动作对象
        action = {"action": action_type}

        # 添加坐标（open_app、open_url、terminate、answer、wait、scroll不需要坐标）
        if action_type not in ["open_app", "open_url", "terminate", "answer", "wait", "scroll"]:
            try:
                x = int(self.coord_x_input.text()) if self.coord_x_input.text() else 0
                y = int(self.coord_y_input.text()) if self.coord_y_input.text() else 0

                # 如果是拖拽动作，检查是否有终点坐标
                if action_type == "left_click_drag":
                    end_x = int(self.end_coord_x_input.text()) if self.end_coord_x_input.text() else x
                    end_y = int(self.end_coord_y_input.text()) if self.end_coord_y_input.text() else y
                    # 双坐标格式：[[x1, y1], [x2, y2]]
                    action["coordinate"] = [[x, y], [end_x, end_y]]
                else:
                    # 单坐标格式：[x, y]
                    action["coordinate"] = [x, y]
            except:
                if action_type == "left_click_drag":
                    action["coordinate"] = [[0, 0], [0, 0]]
                else:
                    action["coordinate"] = [0, 0]

        # 添加文本
        text = self.text_input.toPlainText().strip()
        if text and action_type in ["type", "answer", "open_app", "open_url"]:
            action["text"] = text

        # 添加按键组合（用于 keys 动作）
        if action_type == "keys":
            keys_list = []
            for keys_input in [self.keys_input_1, self.keys_input_2, self.keys_input_3, self.keys_input_4]:
                key_text = keys_input.text().strip()
                if key_text:
                    keys_list.append(key_text)
            if keys_list:
                action["keys"] = keys_list

        # 添加元素名称（所有动作都包含element字段，即使为空）
        element = self.element_input.text().strip()
        action["element"] = element

        # 特殊处理 scroll 动作 - 添加 pixels 字段
        if action_type == "scroll":
            pixels_text = self.pixels_input.text().strip()
            if pixels_text:
                try:
                    action["pixels"] = int(pixels_text)
                except ValueError:
                    action["pixels"] = 0
            else:
                action["pixels"] = 0

        # 特殊处理 terminate 动作
        if action_type == "terminate":
            action["status"] = "success"  # 默认 success
            # element 保持为空字符串

        # 构建完整步骤数据
        if action_type == "terminate":
            # terminate 动作不包含 intent 字段，而是使用 implement 字段
            data = {
                "implement": "任务已完成",
                "CoT": self.cot_input.toPlainText().strip(),
                "observation": {
                    "screenshot": "",  # 稍后由外部设置
                    "active_window": self.active_window_input.text().strip(),
                    "ui_tree_segment": ""
                },
                "actions": [action]
            }
        else:
            # 其他动作包含 intent 字段
            data = {
                "intent": self.intent_input.text().strip(),
                "CoT": self.cot_input.toPlainText().strip(),
                "observation": {
                    "screenshot": "",  # 稍后由外部设置
                    "active_window": self.active_window_input.text().strip(),
                    "ui_tree_segment": ""
                },
                "actions": [action]
            }

        return data


class AnnotationEditor(QMainWindow):
    """标注编辑器主窗口"""

    def __init__(self, data_manager, app_name, task_instruction, screen_info, app_type="", hotkey_listener=None):
        super().__init__()
        self.setWindowTitle(f"GUI 标注编辑器 - {app_name}")
        self.setGeometry(100, 100, 1200, 800)

        self.data_manager = data_manager
        self.app_name = app_name
        self.app_type = app_type  # 保存应用类型
        self.task_instruction = task_instruction
        self.screen_info = screen_info

        # 全局快捷键监听器
        self.hotkey_listener = hotkey_listener

        # 数据状态
        self.gui_number = None  # 整个任务共用一个 gui_number
        self.steps = []  # 步骤列表
        self.current_step_index = -1
        self.screenshot_counter = 0

        self.recorder = ScreenRecorder()

        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 设置窗口快捷键
        self.setup_shortcuts()

        # 顶部工具栏
        toolbar = QHBoxLayout()

        # 步骤导航
        prev_btn = QPushButton("← 上一步")
        prev_btn.clicked.connect(self.previous_step)
        toolbar.addWidget(prev_btn)

        self.step_indicator = QLabel("步骤: 0 / 0")
        self.step_indicator.setFont(QFont("Arial", 12))
        toolbar.addWidget(self.step_indicator)

        next_btn = QPushButton("下一步 →")
        next_btn.clicked.connect(self.next_step)
        toolbar.addWidget(next_btn)

        toolbar.addStretch()

        # 操作按钮
        self.undo_btn = QPushButton("撤销上一步")
        self.undo_btn.clicked.connect(self.undo_last_step)
        self.undo_btn.hide()  # 初始时隐藏，因为没有步骤
        toolbar.addWidget(self.undo_btn)

        recapture_btn = QPushButton("重新截图")
        recapture_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; }")
        recapture_btn.clicked.connect(self.recapture_current_step)
        toolbar.addWidget(recapture_btn)

        capture_btn = QPushButton("给下一步截图 (Cmd+Q)")
        capture_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; }")
        capture_btn.clicked.connect(self.start_capture)
        toolbar.addWidget(capture_btn)

        save_btn = QPushButton("确认")
        save_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; }")
        save_btn.clicked.connect(self.confirm_button_clicked)
        toolbar.addWidget(save_btn)

        main_layout.addLayout(toolbar)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # 步骤编辑区域（使用 StackWidget 实现分页）
        self.stack_widget = QStackedWidget()
        main_layout.addWidget(self.stack_widget)

        # 初始提示
        empty_widget = QWidget()
        empty_layout = QVBoxLayout(empty_widget)
        empty_label = QLabel("点击'给下一步截图'开始标注第一个步骤")
        empty_label.setAlignment(Qt.AlignCenter)
        empty_label.setStyleSheet("color: gray; font-size: 16px;")
        empty_layout.addWidget(empty_label)
        self.stack_widget.addWidget(empty_widget)

        # 底部状态栏
        status_bar = QHBoxLayout()
        self.status_label = QLabel("就绪 - 按 Cmd+Q 给下一步截图")
        status_bar.addWidget(self.status_label)
        main_layout.addLayout(status_bar)

        # 多轮任务支持
        self.rounds = []  # 存储所有轮次的数据
        self.current_round_index = 0  # 当前轮次索引

    def setup_shortcuts(self):
        """连接全局快捷键监听器的信号"""
        if self.hotkey_listener:
            # 连接全局快捷键信号
            self.hotkey_listener.screenshot_triggered.connect(self.start_capture)
            print("✅ 全局快捷键已连接到标注编辑器")
        else:
            print("⚠️ 未设置全局快捷键监听器")

    def start_recording(self):
        """开始屏幕录制"""
        if self.gui_number is None:
            self.gui_number = self.data_manager.get_next_gui_number()

        gui_dir = self.data_manager.create_gui_directory(self.gui_number)
        self.recorder.start(gui_dir, self.app_name)
        print(f"🔴 开始录制屏幕到: {gui_dir}")

    def recapture_current_step(self):
        """重新截取当前步骤的截图，如果没有步骤则开始第一个截图"""
        if self.current_step_index < 0 or self.current_step_index >= len(self.steps):
            # 没有步骤时，开始第一个截图
            self.start_capture()
            return

        # 隐藏主窗口
        self.hide()

        # 延迟一下确保窗口完全隐藏
        QTimer.singleShot(200, self.show_recapture_window)

    def show_recapture_window(self):
        """显示重新截图窗口"""
        self.capture_window = ScreenshotCaptureWindow()
        self.capture_window.capture_completed.connect(self.on_recapture_completed)
        self.capture_window.show()

    def on_recapture_completed(self, original_pixmap, marked_pixmap, rect_info, selection_type):
        """重新截图完成回调"""
        # 检查是否被取消
        if selection_type == "cancelled":
            # 用户取消了截图，重新显示主窗口
            self.restore_window()
            self.status_label.setText("重新截图已取消")
            return

        # 获取当前步骤
        current_step = self.steps[self.current_step_index]

        # 覆盖保存到原有的截图文件路径（覆盖而非新增）
        filename = current_step["screenshot_filename"]
        gui_dir = self.data_manager.create_gui_directory(self.gui_number)
        filepath = os.path.join(gui_dir, filename)

        success = original_pixmap.save(filepath, "PNG")

        if success:
            current_step["rect_info"] = rect_info
            current_step["selection_type"] = selection_type
            current_step["original_pixmap"] = original_pixmap

            editor = current_step["editor"]
            editor.set_screenshot(marked_pixmap)

            # 判断是否为双框模式（拖拽动作）
            if selection_type == "fullscreen":
                pass
            elif isinstance(rect_info, tuple) and len(rect_info) == 2 and isinstance(rect_info[0], tuple):
                # 双框模式 - 拖拽动作
                first_rect = rect_info[0]
                second_rect = rect_info[1]

                # 计算两个框的中心点
                start_x = first_rect[0] + first_rect[2] // 2
                start_y = first_rect[1] + first_rect[3] // 2
                end_x = second_rect[0] + second_rect[2] // 2
                end_y = second_rect[1] + second_rect[3] // 2

                # 设置起点坐标
                editor.coord_x_input.setText(str(start_x))
                editor.coord_y_input.setText(str(start_y))

                # 设置终点坐标
                editor.end_coord_x_input.setText(str(end_x))
                editor.end_coord_y_input.setText(str(end_y))

                # 自动选择"拖拽"动作
                drag_index = editor.action_type_combo.findText("拖拽")
                if drag_index >= 0:
                    editor.action_type_combo.setCurrentIndex(drag_index)
            elif len(rect_info) == 4:
                # 单框模式 - 原有逻辑
                center_x = rect_info[0] + rect_info[2] // 2
                center_y = rect_info[1] + rect_info[3] // 2
                editor.coord_x_input.setText(str(center_x))
                editor.coord_y_input.setText(str(center_y))

            # 显示主窗口
            self.restore_window()

            self.status_label.setText(f"已重新捕获截图 {filename}")
            # 更新撤销按钮可见性
            self.update_undo_button_visibility()
        else:
            QMessageBox.critical(self, "错误", "保存截图失败！")
            self.restore_window()

    def start_capture(self):
        """开始截图捕获"""
        # 隐藏主窗口
        self.hide()

        # 延迟一下确保窗口完全隐藏
        QTimer.singleShot(200, self.show_capture_window)

    def show_capture_window(self):
        """显示截图窗口"""
        self.capture_window = ScreenshotCaptureWindow()
        self.capture_window.capture_completed.connect(self.on_capture_completed)
        self.capture_window.show()

    def on_capture_completed(self, original_pixmap, marked_pixmap, rect_info, selection_type):
        """截图完成回调"""
        # 检查是否被取消
        if selection_type == "cancelled":
            # 用户取消了截图，重新显示主窗口
            self.restore_window()
            self.status_label.setText("截图已取消")
            return

        # 保存截图（整个任务共用一个 gui_number）
        if self.gui_number is None:
            self.gui_number = self.data_manager.get_next_gui_number()

        self.screenshot_counter += 1
        screenshot_number = f"{self.screenshot_counter:04d}"

        # 保存原始截图文件（不带标记）
        filepath = self.data_manager.save_screenshot(
            original_pixmap,
            self.app_name,
            self.gui_number,
            format="PNG"
        )

        if filepath:
            filename = os.path.basename(filepath)

            # 创建新的步骤编辑器
            step_editor = StepEditorWidget()
            # 预览图使用带标记的截图
            step_editor.set_screenshot(marked_pixmap)

            # 判断是否为双框模式（拖拽动作）
            if selection_type == "fullscreen":
                pass
            elif isinstance(rect_info, tuple) and len(rect_info) == 2 and isinstance(rect_info[0], tuple):
                # 双框模式 - 拖拽动作
                first_rect = rect_info[0]
                second_rect = rect_info[1]

                # 计算两个框的中心点
                start_x = first_rect[0] + first_rect[2] // 2
                start_y = first_rect[1] + first_rect[3] // 2
                end_x = second_rect[0] + second_rect[2] // 2
                end_y = second_rect[1] + second_rect[3] // 2

                # 设置起点坐标
                step_editor.coord_x_input.setText(str(start_x))
                step_editor.coord_y_input.setText(str(start_y))

                # 设置终点坐标
                step_editor.end_coord_x_input.setText(str(end_x))
                step_editor.end_coord_y_input.setText(str(end_y))

                # 自动选择"拖拽"动作
                drag_index = step_editor.action_type_combo.findText("拖拽")
                if drag_index >= 0:
                    step_editor.action_type_combo.setCurrentIndex(drag_index)

                selection_type = "drag"  # 确保选择类型为 drag
            elif len(rect_info) == 4:
                # 单框模式 - 原有逻辑
                center_x = rect_info[0] + rect_info[2] // 2
                center_y = rect_info[1] + rect_info[3] // 2
                step_editor.coord_x_input.setText(str(center_x))
                step_editor.coord_y_input.setText(str(center_y))

            # 添加到步骤列表
            self.steps.append({
                "editor": step_editor,
                "screenshot_filename": filename,
                "rect_info": rect_info,
                "selection_type": selection_type,
                "original_pixmap": original_pixmap  # 保存原始截图引用
            })

            # 添加到 stack widget
            self.stack_widget.addWidget(step_editor)
            self.current_step_index = len(self.steps) - 1
            self.stack_widget.setCurrentIndex(self.current_step_index + 1)  # +1 因为有空页面

            # 更新步骤编号
            step_num = self.get_current_step_number()
            step_editor.set_step_number(step_num)

            # 更新指示器
            self.update_step_indicator()

            # 显示主窗口
            self.restore_window()

            self.status_label.setText(f"已捕获截图 {filename}，请填写动作信息")
        else:
            QMessageBox.critical(self, "错误", "保存截图失败！")
            self.restore_window()

    def get_current_step_number(self):
        """获取当前步骤编号"""
        return len(self.steps) - 1

    def update_undo_button_visibility(self):
        """根据当前步骤位置更新撤销按钮的可见性"""
        # 只有当当前步骤是最后一步时才显示撤销按钮
        if len(self.steps) > 0 and self.current_step_index == len(self.steps) - 1:
            self.undo_btn.show()
        else:
            self.undo_btn.hide()

    def update_step_indicator(self):
        """更新步骤指示器"""
        total = len(self.steps)
        current = self.current_step_index + 1 if self.current_step_index >= 0 else 0
        self.step_indicator.setText(f"步骤: {current} / {total}")
        # 同时更新撤销按钮的可见性
        self.update_undo_button_visibility()

    def previous_step(self):
        """上一步"""
        if self.current_step_index > 0:
            self.current_step_index -= 1
            self.stack_widget.setCurrentIndex(self.current_step_index + 1)
            self.update_step_indicator()
            # 更新撤销按钮可见性
            self.update_undo_button_visibility()

    def next_step(self):
        """下一步"""
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            self.stack_widget.setCurrentIndex(self.current_step_index + 1)
            self.update_step_indicator()
            # 更新撤销按钮可见性
            self.update_undo_button_visibility()

    def undo_last_step(self):
        """撤销上一步"""
        if len(self.steps) > 0:
            reply = QMessageBox.question(
                self,
                "确认撤销",
                "确定要撤销最后一步吗？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                # 移除最后一个步骤
                removed = self.steps.pop()

                # 从 stack widget 移除
                widget = self.stack_widget.widget(self.stack_widget.count() - 1)
                self.stack_widget.removeWidget(widget)

                # 删除截图文件
                try:
                    gui_dir = os.path.join(self.data_manager.current_dir, f"gui_{self.gui_number}")
                    filepath = os.path.join(gui_dir, removed["screenshot_filename"])
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except Exception as e:
                    print(f"删除截图失败: {e}")

                # 更新计数器
                self.screenshot_counter -= 1

                # 调整当前索引
                if self.current_step_index >= len(self.steps):
                    self.current_step_index = len(self.steps) - 1

                if self.current_step_index >= 0:
                    self.stack_widget.setCurrentIndex(self.current_step_index + 1)

                self.update_step_indicator()
                # 更新撤销按钮可见性
                self.update_undo_button_visibility()
                self.status_label.setText("已撤销上一步")

    def hide_window(self):
        """隐藏窗口"""
        self.showMinimized()

    def confirm_button_clicked(self):
        if self.current_step_index >= 0 and self.current_step_index < len(self.steps):
            editor = self.steps[self.current_step_index]["editor"]
            action_type_chinese = editor.action_type_combo.currentText()
            action_type = editor.action_type_mapping.get(action_type_chinese, action_type_chinese)
            if action_type == "terminate":
                self.save_current_step()
                return
        self.hide_window()

    def restore_window(self):
        """恢复窗口显示（处理最小化状态）"""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def save_current_step(self):
        """保存当前步骤"""
        if self.current_step_index < 0 or self.current_step_index >= len(self.steps):
            QMessageBox.warning(self, "警告", "没有可保存的步骤！")
            return

        # 获取当前编辑器
        current_step = self.steps[self.current_step_index]
        editor = current_step["editor"]

        # 获取编辑数据
        step_data = editor.get_data()

        # 设置步骤编号（放在首部）
        step_num = self.get_current_step_number()
        step_data_with_step = {"step": step_num}
        step_data_with_step.update(step_data)
        step_data = step_data_with_step

        # 设置截图文件名
        step_data["observation"]["screenshot"] = current_step["screenshot_filename"]

        # 检查是否为 answer 动作
        actions = step_data.get("actions", [])
        if actions and actions[0].get("action") == "answer":
            # answer 动作：保存后直接开始新一轮任务
            current_step["data"] = step_data
            self.status_label.setText(f"步骤 {step_num} 已保存（回答用户）")

            # 保存当前轮次并直接开始新任务
            self.save_current_round()
            QTimer.singleShot(300, lambda: self.start_new_round(from_answer=True))
        elif actions and actions[0].get("action") == "terminate":
            # 任务完成动作
            current_step["data"] = step_data
            self.status_label.setText(f"步骤 {step_num} 已保存（任务完成）")

            # 默认结束任务，直接询问是否创建新的标注任务
            QTimer.singleShot(300, self.show_new_task_dialog)
        else:
            # 普通步骤
            current_step["data"] = step_data
            self.status_label.setText(f"步骤 {step_num} 已保存")

        # 更新指示器
        self.update_step_indicator()

    def show_terminate_dialog(self):
        """显示任务完成对话框"""
        # 确保主窗口在前台
        self.restore_window()

        reply = QMessageBox.question(
            self,
            "任务完成",
            "当前任务已完成。\n\n是否继续当前任务？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 保存当前轮次并开始新任务（同一 gui 文件夹）
            self.save_current_round()
            self.start_new_round()
        else:
            # 询问是否创建新的标注任务
            self.show_new_task_dialog()

    def save_current_round(self):
        """保存当前轮次的数据到 rounds 列表"""
        # 收集所有步骤数据
        trajectory = []
        for i, step in enumerate(self.steps):
            if "data" in step:
                trajectory.append(step["data"])
            else:
                # 如果步骤还没有保存，尝试从编辑器获取数据
                editor = step["editor"]
                step_data = editor.get_data()
                step_data["observation"]["screenshot"] = step["screenshot_filename"]
                # 将 step 字段放到首部
                step_data_with_step = {"step": i}
                step_data_with_step.update(step_data)
                step_data = step_data_with_step
                trajectory.append(step_data)

        # 添加到轮次列表（只保存 instruction 和 trajectory）
        self.rounds.append({
            "instruction": self.task_instruction,
            "trajectory": trajectory
        })

    def show_new_task_dialog(self):
        """显示是否创建新任务的对话框"""
        # 确保主窗口在前台
        self.restore_window()

        reply = QMessageBox.question(
            self,
            "创建新任务",
            "是否开始一个新的标注任务？\n\n是：创建新任务（gui_000002...）\n否：保存当前任务并退出",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 先保存当前任务的所有轮次
            self.finish_all_annotation()
            # 然后创建新任务
            self.create_new_task()
        else:
            # 保存当前任务并退出
            self.finish_all_annotation()

    def create_new_task(self):
        """创建新的标注任务（新的 gui 编号）"""
        from PyQt5.QtWidgets import QInputDialog

        # 确保主窗口在前台
        self.restore_window()

        new_instruction, ok = QInputDialog.getText(
            self,
            "新任务指令",
            "请输入新任务的第一个指令：",
            QLineEdit.Normal,
            ""
        )

        if ok and new_instruction.strip():
            # 清空所有轮次数据
            self.rounds = []

            # 更新任务指令
            self.task_instruction = new_instruction.strip()

            # 重置状态并获取新的 gui_number
            self.reset_for_new_task()
            self.gui_number = self.data_manager.get_next_gui_number()

            self.start_recording()

            self.status_label.setText(f"新任务开始 - 指令: {self.task_instruction}")
        else:
            # 用户取消了，关闭窗口
            self.close()

    def start_new_round(self, from_answer=False):
        """开始新一轮任务（同一 gui 文件夹内）
        :param from_answer: 是否从 answer 动作触发，如果是则取消时不保存退出
        """
        # 弹出对话框让用户输入新的 instruction
        from PyQt5.QtWidgets import QInputDialog

        # 确保主窗口在前台
        self.restore_window()

        new_instruction, ok = QInputDialog.getText(
            self,
            "新任务指令",
            "请输入下一个任务的指令：",
            QLineEdit.Normal,
            ""
        )

        if ok and new_instruction.strip():
            # 更新任务指令
            self.task_instruction = new_instruction.strip()

            # 重置状态（但保持 gui_number 不变，共用同一个文件夹）
            self.reset_for_new_task()

            self.status_label.setText(f"新任务开始 - 指令: {self.task_instruction}")
        else:
            # 用户取消了
            if from_answer:
                # 如果是从 answer 动作触发，只关闭弹窗，不保存退出
                self.status_label.setText("已取消新任务")
            else:
                # 否则完成所有标注
                self.finish_all_annotation()

    def finish_all_annotation(self):
        """完成所有轮次的标注并保存"""
        # 先保存当前轮次（如果有的话）
        if len(self.steps) > 0:
            self.save_current_round()

        # 保存所有轮次的数据
        if len(self.rounds) == 0:
            QMessageBox.warning(self, "警告", "没有可保存的数据！")
            return

        # 构建完整的 JSON 结构（包含平台信息）
        merged_data = self.data_manager.create_initial_json_structure(
            self.rounds[0].get("instruction", ""),  # 使用第一个指令作为示例
            self.screen_info,
            self.app_type  # 传入应用类型
        )

        video_filename = self.recorder.stop()
        if video_filename:
            merged_data["recording_video"] = video_filename
            print(f"⏹ 录制完成: {video_filename}")

        # 清空默认的 messages，重新构建
        merged_data["messages"] = []

        # 合并所有轮次到一个 messages 数组
        for round_data in self.rounds:
            # 添加 user 消息（instruction）
            merged_data["messages"].append({
                "role": "user",
                "instruction": round_data["instruction"]
            })

            # 添加 assistant 消息（trajectory）
            merged_data["messages"].append({
                "role": "assistant",
                "trajectory": round_data["trajectory"]
            })

        # 保存合并后的 JSON 文件
        filepath = self.data_manager.save_json_data(merged_data, self.gui_number)

        if filepath:
            QMessageBox.information(
                self,
                "保存成功",
                f"所有轮次数据已保存到:\n{filepath}"
            )
            self.close()
        else:
            QMessageBox.critical(self, "错误", "保存 JSON 失败！")

    def finish_annotation(self):
        """完成标注并保存（已废弃，由 show_terminate_dialog 替代）"""
        pass

    def reset_for_new_task(self):
        """重置状态以开始新任务（保持 gui_number 不变）"""
        self.steps = []
        self.current_step_index = -1
        self.screenshot_counter = 0
        # 注意：不重置 gui_number，整个任务共用同一个文件夹

        # 清空 stack widget（保留空页面）
        while self.stack_widget.count() > 1:
            widget = self.stack_widget.widget(1)
            self.stack_widget.removeWidget(widget)

        self.stack_widget.setCurrentIndex(0)
        self.update_step_indicator()
        # 隐藏撤销按钮
        self.undo_btn.hide()
        self.status_label.setText("就绪 - 按 Cmd+Q 给下一步截图")

    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.recorder.is_recording():
            self.recorder.stop()
        event.accept()
