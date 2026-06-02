#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全局快捷键监听模块
使用 pynput 库监听全局键盘事件
支持 macOS Ctrl 键组合
"""

from pynput import keyboard
import threading


class GlobalHotkeyListener:
    """全局快捷键监听器 - 使用 pynput HotKey"""
    
    def __init__(self, on_ctrl_q=None, on_ctrl_s=None):
        """
        初始化快捷键监听器
        :param on_ctrl_q: Ctrl+Q 回调函数（macOS上为 Ctrl+Q）
        :param on_ctrl_s: Ctrl+S 回调函数（macOS上为 Ctrl+S）
        """
        self.on_ctrl_q = on_ctrl_q
        self.on_ctrl_s = on_ctrl_s
        
        # 定义热键映射
        self.hotkeys = {}
        
        # 创建热键
        if on_ctrl_q:
            # macOS: Ctrl+Q, 其他平台: Ctrl+Q
            hotkey_q = keyboard.HotKey(
                keyboard.HotKey.parse('<cmd>+q'),
                on_ctrl_q
            )
            self.hotkeys['ctrl_q'] = hotkey_q
            
        if on_ctrl_s:
            # macOS: Ctrl+S, 其他平台: Ctrl+S
            hotkey_s = keyboard.HotKey(
                keyboard.HotKey.parse('<cmd>+s'),
                on_ctrl_s
            )
            self.hotkeys['ctrl_s'] = hotkey_s
        
        # 创建监听器
        self.listener = None
        self.create_listener()
        
    def create_listener(self):
        """创建键盘监听器"""
        # 使用 pynput 的 Listener 和 HotKey
        def on_press(key):
            for hotkey in self.hotkeys.values():
                hotkey.press(self.canonical(key))
                
        def on_release(key):
            for hotkey in self.hotkeys.values():
                hotkey.release(self.canonical(key))
                
            # ESC 键退出
            if key == keyboard.Key.esc:
                return False
        
        self.listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release
        )
        
    def canonical(self, key):
        """标准化按键"""
        try:
            return self.listener.canonical(key)
        except:
            return key
        
    def start(self):
        """启动监听器"""
        if self.listener:
            self.listener.start()
            print("✅ 全局快捷键监听器已启动")
            print("   - Ctrl+Q: 开始截图")
            print("   - Ctrl+S: 保存步骤")
            print("   - ESC: 退出监听")
            
    def stop(self):
        """停止监听器"""
        if self.listener:
            self.listener.stop()
            print("⏹ 全局快捷键监听器已停止")


# 测试代码
if __name__ == "__main__":
    def handle_ctrl_q():
        print("🔥 检测到 Ctrl+Q - 开始截图")
        
    def handle_ctrl_s():
        print("💾 检测到 Ctrl+S - 保存步骤")
        
    listener = GlobalHotkeyListener(on_ctrl_q=handle_ctrl_q, on_ctrl_s=handle_ctrl_s)
    listener.start()
    
    try:
        # 等待监听器结束（按ESC退出）
        listener.listener.join()
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        listener.stop()
        print("程序退出")
