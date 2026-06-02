#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
截图捕获模块
负责全屏截图和区域选择功能
"""

import sys
from PyQt5.QtWidgets import QApplication, QWidget, QRubberBand
from PyQt5.QtCore import Qt, QRect, pyqtSignal, QSize
from PyQt5.QtGui import QPainter, QPen, QColor, QPixmap, QScreen


class ScreenshotCaptureWindow(QWidget):
    """截图捕获窗口 - 用于用户拉框或点击选择区域"""
    
    # 信号：当用户完成选择时发出，包含截图和坐标信息
    capture_completed = pyqtSignal(object, object, tuple, str)  # (original_pixmap, marked_pixmap, (x, y, width, height), screenshot_type)
    
    def __init__(self):
        super().__init__()
        
        # 设置为全屏、无边框、置顶，必须加 Qt.Window 才能接收键盘事件
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # 获取主屏幕
        screen = QApplication.primaryScreen()
        self.screen_geometry = screen.geometry()
        
        # 设置窗口大小为整个屏幕
        self.setGeometry(self.screen_geometry)
        
        # 截图相关变量
        self.full_pixmap = None
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        self.origin = None
        self.current_rect = None
        
        # 鼠标状态
        self.is_selecting = False
        self.click_only = False  # 是否为纯点击（不拉框）
        
        # 选择状态
        self.has_selection = False  # 是否已完成选择
        self.selection_rect = None  # 保存的选区
        self.selection_type = None  # 保存的选择类型
        
        # 双框选择支持（用于拖拽动作）
        self.first_rect = None  # 第一个框
        self.second_rect = None  # 第二个框
        self.box_count = 0  # 已选择的框数量
        
        # 设置鼠标指针为十字
        self.setCursor(Qt.CrossCursor)

        # 捕获截图
        self.capture_screen()
        
    def capture_screen(self):
        """捕获整个屏幕"""
        screen = QApplication.primaryScreen()
        self.full_pixmap = screen.grabWindow(0)
        
        # 设置背景为半透明遮罩
        self.setStyleSheet("background-color: rgba(0, 0, 0, 100);")
    
    def showEvent(self, event):
        """窗口显示时自动获取键盘焦点"""
        super().showEvent(event)
        self.setFocus()
        self.activateWindow()
        
    def paintEvent(self, event):
        """绘制事件 - 显示截图和选区"""
        painter = QPainter(self)
        
        # 绘制全屏截图
        if self.full_pixmap:
            painter.drawPixmap(0, 0, self.full_pixmap)
        
        # 绘制半透明遮罩（除了选中区域）
        if self.current_rect or self.has_selection:
            # 创建遮罩
            mask = QPixmap(self.full_pixmap.size())
            mask.fill(QColor(0, 0, 0, 100))
            
            # 清除选中区域的遮罩
            painter_mask = QPainter(mask)
            painter_mask.setCompositionMode(QPainter.CompositionMode_Clear)
            
            # 清除第一个框的区域
            if self.first_rect:
                x, y, w, h = self.first_rect
                painter_mask.fillRect(QRect(x, y, w, h), Qt.transparent)
            
            # 清除第二个框的区域
            if self.second_rect:
                x, y, w, h = self.second_rect
                painter_mask.fillRect(QRect(x, y, w, h), Qt.transparent)
            
            # 如果没有双框，使用原有的单框逻辑
            if not self.first_rect and not self.second_rect:
                if self.has_selection and self.selection_rect:
                    x, y, w, h = self.selection_rect
                    painter_mask.fillRect(QRect(x, y, w, h), Qt.transparent)
                elif self.current_rect:
                    painter_mask.fillRect(self.current_rect, Qt.transparent)
            
            painter_mask.end()
            
            painter.drawPixmap(0, 0, mask)
            
            # 绘制选区边框
            pen = QPen(QColor(255, 0, 0), 2)
            painter.setPen(pen)
            
            # 绘制第一个框（已完成的）
            if self.first_rect:
                x, y, w, h = self.first_rect
                painter.drawRect(QRect(x, y, w, h))
            
            # 绘制第二个框（已完成的）
            if self.second_rect:
                x, y, w, h = self.second_rect
                painter.drawRect(QRect(x, y, w, h))
            
            # 绘制当前正在拉的框（橡皮筋）
            if self.current_rect and not self.click_only:
                painter.drawRect(self.current_rect)
            
            # 如果没有双框，使用原有的单框逻辑
            if not self.first_rect and not self.second_rect:
                if self.has_selection and self.selection_rect:
                    x, y, w, h = self.selection_rect
                    painter.drawRect(QRect(x, y, w, h))
                elif self.current_rect and not self.click_only:
                    painter.drawRect(self.current_rect)
        
        super().paintEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            self.is_selecting = True
            
            # 判断是点击还是开始拉框
            self.click_only = True
            
            # 初始化橡皮筋
            self.rubber_band.setGeometry(QRect(self.origin, QSize()))
            self.rubber_band.show()
            
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.is_selecting and self.origin:
            current = event.pos()
            
            # 如果移动距离超过阈值，认为是拉框而不是点击
            if abs(current.x() - self.origin.x()) > 5 or abs(current.y() - self.origin.y()) > 5:
                self.click_only = False
            
            if not self.click_only:
                # 更新橡皮筋矩形
                rect = QRect(self.origin, current).normalized()
                self.current_rect = rect
                self.rubber_band.setGeometry(rect)
                self.update()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.is_selecting:
            self.is_selecting = False
            
            if not self.click_only:
                if self.current_rect and self.current_rect.width() > 5 and self.current_rect.height() > 5:
                    self.handle_selection(self.current_rect, "drag")
            
            self.rubber_band.hide()
            self.current_rect = None
            self.update()
    
    def handle_selection(self, rect, selection_type):
        """处理用户选择 - 不关闭窗口，等待 Ctrl+S 确认"""
        # 计算相对于屏幕的坐标
        x = rect.x()
        y = rect.y()
        width = rect.width()
        height = rect.height()
        
        rect_info = (x, y, width, height)
        
        # 记录第一个框或第二个框
        if self.box_count == 0:
            self.first_rect = rect_info
            self.box_count = 1
            self.has_selection = True
            self.selection_rect = rect_info
            self.selection_type = selection_type
        elif self.box_count == 1:
            self.second_rect = rect_info
            self.box_count = 2
            # 双框模式，更新选择类型为 drag
            self.selection_type = "drag"
        
        # 隐藏橡皮筋
        self.rubber_band.hide()
        self.current_rect = None
        
        # 更新显示（绘制选区标记）
        self.update()
    
    def confirm_selection(self):
        """确认选择并发送信号"""
        if not self.has_selection or not self.selection_rect:
            if self.full_pixmap:
                original_pixmap = QPixmap(self.full_pixmap)
                marked_pixmap = QPixmap(self.full_pixmap)
                self.capture_completed.emit(
                    original_pixmap,
                    marked_pixmap,
                    (),
                    "fullscreen"
                )
            self.close()
            return
        
        if self.box_count == 2 and self.first_rect and self.second_rect:
            # 双框模式 - 拖拽动作
            # 返回两个框的中心点坐标
            first_center_x = self.first_rect[0] + self.first_rect[2] // 2
            first_center_y = self.first_rect[1] + self.first_rect[3] // 2
            second_center_x = self.second_rect[0] + self.second_rect[2] // 2
            second_center_y = self.second_rect[1] + self.second_rect[3] // 2
            
            # 使用第一个框作为 selection_rect（兼容性）
            x, y, width, height = self.first_rect
            
            # 返回整个屏幕的截图，并在上面绘制两个框
            if self.full_pixmap:
                # 保存原始截图（不带标记）
                original_pixmap = QPixmap(self.full_pixmap)
                
                # 创建带标记的截图副本（用于预览）
                marked_pixmap = QPixmap(self.full_pixmap)
                
                # 在截图上绘制两个框
                painter = QPainter(marked_pixmap)
                pen = QPen(QColor(255, 0, 0), 3)  # 红色，3像素宽
                painter.setPen(pen)
                
                # 绘制第一个框（起点）
                painter.drawRect(QRect(self.first_rect[0], self.first_rect[1], 
                                      self.first_rect[2], self.first_rect[3]))
                # 绘制第二个框（终点）
                painter.drawRect(QRect(self.second_rect[0], self.second_rect[1], 
                                      self.second_rect[2], self.second_rect[3]))
                
                # 绘制箭头连接两个框
                from PyQt5.QtGui import QPolygon
                arrow_start_x = first_center_x
                arrow_start_y = first_center_y
                arrow_end_x = second_center_x
                arrow_end_y = second_center_y
                
                # 计算箭头方向
                import math
                angle = math.atan2(arrow_end_y - arrow_start_y, arrow_end_x - arrow_start_x)
                arrow_length = 15
                arrow_angle = math.pi / 6
                
                # 箭头的两个侧点
                x1 = arrow_end_x - arrow_length * math.cos(angle - arrow_angle)
                y1 = arrow_end_y - arrow_length * math.sin(angle - arrow_angle)
                x2 = arrow_end_x - arrow_length * math.cos(angle + arrow_angle)
                y2 = arrow_end_y - arrow_length * math.sin(angle + arrow_angle)
                
                # 绘制箭头线
                painter.drawLine(arrow_start_x, arrow_start_y, arrow_end_x, arrow_end_y)
                # 绘制箭头头部
                painter.drawLine(arrow_end_x, arrow_end_y, int(x1), int(y1))
                painter.drawLine(arrow_end_x, arrow_end_y, int(x2), int(y2))
                
                painter.end()
                
                # 发送信号（包含双框信息）
                # rect_info 现在是一个元组，包含两个框的信息
                dual_rect_info = (self.first_rect, self.second_rect)
                self.capture_completed.emit(
                    original_pixmap,
                    marked_pixmap, 
                    dual_rect_info,
                    "drag"
                )
            
            # 关闭窗口
            self.close()
        else:
            # 单框模式 - 原有逻辑
            x, y, width, height = self.selection_rect
            
            # 返回整个屏幕的截图，并在上面绘制选区框或点击标记
            if self.full_pixmap:
                # 保存原始截图（不带标记）
                original_pixmap = QPixmap(self.full_pixmap)
                
                # 创建带标记的截图副本（用于预览）
                marked_pixmap = QPixmap(self.full_pixmap)
                
                # 在截图上绘制标识
                painter = QPainter(marked_pixmap)
                
                if self.selection_type == "click":
                    # 点击动作：绘制红色十字准星和圆点
                    center_x = x + width // 2
                    center_y = y + height // 2
                    
                    # 设置画笔 - 红色，3像素宽
                    pen = QPen(QColor(255, 0, 0), 3)
                    painter.setPen(pen)
                    
                    # 绘制十字线（长度为20像素）
                    cross_size = 20
                    painter.drawLine(center_x - cross_size, center_y, center_x + cross_size, center_y)  # 横线
                    painter.drawLine(center_x, center_y - cross_size, center_x, center_y + cross_size)  # 竖线
                    
                    # 绘制中心圆点
                    painter.setBrush(QColor(255, 0, 0))
                    painter.drawEllipse(center_x - 5, center_y - 5, 10, 10)
                    
                else:
                    # 拉框动作：绘制红色边框
                    pen = QPen(QColor(255, 0, 0), 3)  # 红色，3像素宽
                    painter.setPen(pen)
                    painter.drawRect(QRect(x, y, width, height))
                
                painter.end()
                
                # 发送信号（原始截图 + 带标记的截图 + 选区信息）
                self.capture_completed.emit(
                    original_pixmap,
                    marked_pixmap, 
                    self.selection_rect,
                    self.selection_type
                )
            
            # 关闭窗口
            self.close()
    
    def keyPressEvent(self, event):
        """键盘事件 - ESC 取消/清除，Ctrl+S(Meta+S) 确认"""
        if event.key() == Qt.Key_Escape:
            if self.box_count > 0:
                # 如果有选区，清除所有选区，允许重新选择
                self.has_selection = False
                self.selection_rect = None
                self.selection_type = None
                self.first_rect = None
                self.second_rect = None
                self.box_count = 0
                self.current_rect = None
                self.rubber_band.hide()
                self.update()
            else:
                # 如果没有选区，取消整个截图
                self.capture_completed.emit(None, None, (), "cancelled")
                self.close()
        elif event.key() == Qt.Key_S and (event.modifiers() & Qt.MetaModifier):
            self.confirm_selection()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScreenshotCaptureWindow()
    window.show()
    sys.exit(app.exec_())
