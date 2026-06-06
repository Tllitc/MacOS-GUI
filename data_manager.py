#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据管理模块
负责数据目录创建、文件保存、JSON 格式化管理等
"""

import os
import json
import platform
import subprocess
from datetime import datetime


class DataManager:
    """数据管理器"""
    
    def __init__(self, base_dir=None):
        """
        初始化数据管理器
        :param base_dir: 基础目录，gui 文件夹将直接创建在此目录下
        """
        if base_dir is None:
            base_dir = os.getcwd()
        self.base_dir = base_dir
        self.current_dir = base_dir
        
    def create_task_directory(self, platform_name, app_type, app_name):
        """
        设置任务目录为 base_dir，gui_编号 文件夹将直接创建在此目录下
        :param platform_name: 平台名称 (mac, windows, ios, android) - 保留参数兼容性
        :param app_type: 软件类型 (社交、电商等) - 保留参数兼容性
        :param app_name: 具体软件名称 - 保留参数兼容性
        :return: True if success, False otherwise
        """
        try:
            os.makedirs(self.base_dir, exist_ok=True)
            self.current_dir = self.base_dir
            return True
        except Exception as e:
            print(f"设置任务目录失败: {e}")
            return False
    
    def get_next_gui_number(self):
        """
        获取下一个 GUI 编号（六位数字）
        :return: 例如 "000001"
        """
        # 在应用目录下查找所有 gui_ 文件夹
        gui_dirs = [d for d in os.listdir(self.current_dir) 
                   if os.path.isdir(os.path.join(self.current_dir, d)) and d.startswith("gui_")]
        
        if not gui_dirs:
            return "000001"
        
        # 提取现有编号
        numbers = []
        for d in gui_dirs:
            try:
                num_str = d.replace("gui_", "")
                numbers.append(int(num_str))
            except:
                continue
        
        if numbers:
            next_num = max(numbers) + 1
        else:
            next_num = 1
        
        return f"{next_num:06d}"
    
    def create_gui_directory(self, gui_number):
        """
        创建 GUI 编号文件夹
        :param gui_number: GUI 编号，例如 "000001"
        :return: GUI 文件夹路径
        """
        gui_dir_name = f"gui_{gui_number}"
        gui_dir_path = os.path.join(self.current_dir, gui_dir_name)
        os.makedirs(gui_dir_path, exist_ok=True)
        return gui_dir_path
    
    def get_next_screenshot_number(self, gui_number, gui_dir=None):
        """
        获取下一个截图编号
        :param gui_number: GUI 编号，例如 "000001"
        :param gui_dir: GUI 文件夹路径，如果为 None 则使用 current_dir
        :return: 例如 "0001"
        """
        if gui_dir is None:
            gui_dir = os.path.join(self.current_dir, f"gui_{gui_number}")
        
        prefix = f"gui_{gui_number}_"
        screenshot_files = [f for f in os.listdir(gui_dir) 
                          if f.startswith(prefix) and f.endswith((".png", ".jpg"))]
        
        if not screenshot_files:
            return "0001"
        
        # 提取现有编号
        numbers = []
        for f in screenshot_files:
            try:
                num_str = f.replace(prefix, "").split(".")[0]
                numbers.append(int(num_str))
            except:
                continue
        
        if numbers:
            next_num = max(numbers) + 1
        else:
            next_num = 1
        
        return f"{next_num:04d}"
    
    def save_screenshot(self, image_data, app_name, gui_number, format="PNG"):
        """
        保存截图文件到对应的 gui_编号文件夹
        :param image_data: PIL Image 对象或字节数据
        :param app_name: 应用名称
        :param gui_number: GUI 编号
        :param format: 图片格式 (PNG 或 JPG)
        :return: 文件路径
        """
        # 创建或获取 GUI 文件夹
        gui_dir = self.create_gui_directory(gui_number)
        
        ext = "png" if format == "PNG" else "jpg"
        # 生成基于时间的文件名: macOS_appname_YYYY-MM-DD_HHhMM_SS.ext
        timestamp = datetime.now().strftime("%Y-%m-%d_%Hh%M_%S")
        filename = f"macOS_{app_name}_{timestamp}.{ext}"
        filepath = os.path.join(gui_dir, filename)
        
        try:
            if hasattr(image_data, 'save'):
                # PIL Image 对象
                if format == "JPG":
                    image_data.save(filepath, "JPEG", quality=95)
                else:
                    image_data.save(filepath, "PNG")
            else:
                # 字节数据
                with open(filepath, 'wb') as f:
                    f.write(image_data)
            
            return filepath
        except Exception as e:
            print(f"保存截图失败: {e}")
            return None
    
    def save_json_data(self, data, gui_number):
        """
        保存 JSON 数据文件到对应的 gui_编号文件夹
        :param data: 字典数据
        :param gui_number: GUI 编号
        :return: 文件路径
        """
        # 创建或获取 GUI 文件夹
        gui_dir = self.create_gui_directory(gui_number)
        
        filename = f"gui_{gui_number}.json"
        filepath = os.path.join(gui_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return filepath
        except Exception as e:
            print(f"保存 JSON 失败: {e}")
            return None
    
    def load_json_data(self, gui_number):
        """
        加载 JSON 数据文件
        :param gui_number: GUI 编号
        :return: 字典数据或 None
        """
        filename = f"gui_{gui_number}.json"
        filepath = os.path.join(self.current_dir, filename)
        
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载 JSON 失败: {e}")
        
        return None
    
    def save_coords_json(self, coords_data, gui_number):
        """
        保存拉框坐标信息到独立的 JSON 文件
        :param coords_data: 坐标数据列表，每个元素包含 step/action/vertices/center
        :param gui_number: GUI 编号
        :return: 文件路径或 None (失败时)
        """
        gui_dir = self.create_gui_directory(gui_number)
        filename = f"gui_{gui_number}_coords.json"
        filepath = os.path.join(gui_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(coords_data, f, ensure_ascii=False, indent=2)
            return filepath
        except Exception as e:
            print(f"保存坐标 JSON 失败: {e}")
            return None
    
    def get_screen_info(self):
        """
        获取屏幕信息
        :return: 包含平台、系统、屏幕尺寸的字典
        """
        try:
            # 获取屏幕分辨率（macOS）
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType'],
                capture_output=True,
                text=True
            )
            
            screen_size = [1440, 900]  # 默认值
            for line in result.stdout.split('\n'):
                if 'Resolution' in line:
                    # 解析类似 "Resolution: 1440 x 900 Retina"
                    parts = line.split(':')
                    if len(parts) > 1:
                        res_str = parts[1].strip()
                        dims = res_str.split('x')
                        if len(dims) >= 2:
                            try:
                                width = int(dims[0].strip())
                                height = int(dims[1].split()[0].strip())
                                screen_size = [width, height]
                            except:
                                pass
                    break
            
            # 获取系统信息
            system_version = platform.mac_ver()[0]  # macOS 版本
            platform_info = platform.platform()
            
            return {
                "platform": platform_info,
                "system": f"macOS {system_version}",
                "screen_size": screen_size
            }
        except Exception as e:
            print(f"获取屏幕信息失败: {e}")
            return {
                "platform": "MacBook",
                "system": "macOS",
                "screen_size": [1440, 900]
            }
    
    def create_initial_json_structure(self, task_instruction, screen_info, app_type=""):
        """
        创建初始 JSON 数据结构
        :param task_instruction: 任务指令
        :param screen_info: 屏幕信息
        :param app_type: 应用类型（用于构建 task_type）
        :return: JSON 数据字典
        """
        # 构建 task_type: 平台名称-应用类型
        platform_name = screen_info.get("system", "macOS")
        if app_type:
            task_type = f"MacOS-{app_type}"
        else:
            task_type = platform_name
        
        return {
            "platform": screen_info.get("platform", "MacBook"),
            "system": screen_info.get("system", "macOS"),
            "screen_size": screen_info.get("screen_size", [1440, 900]),
            "task_type": task_type,
            "recording_video": "",
            "messages": [
                {
                    "role": "user",
                    "instruction": task_instruction
                },
                {
                    "role": "assistant",
                    "trajectory": []
                }
            ]
        }
