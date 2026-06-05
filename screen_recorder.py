#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
屏幕录制模块
使用 macOS 原生 screencapture 命令录制屏幕
"""

import os
import signal
import subprocess
import time
from datetime import datetime


class ScreenRecorder:
    """macOS 屏幕录制器（基于 screencapture）"""

    def __init__(self):
        self.process = None
        self.output_path = None
        self.video_filename = None

    def start(self, output_dir, app_name):
        if self.process is not None:
            self.stop()

        timestamp = datetime.now().strftime("%Y-%m-%d_%Hh%M_%S")
        self.video_filename = f"macOS_{app_name}_{timestamp}.mp4"
        self.output_path = os.path.join(output_dir, self.video_filename)

        cmd = [
            "screencapture",
            "-v",
            self.output_path
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return True
        except Exception as e:
            print(f"启动录制失败: {e}")
            return False

    def stop(self):
        if self.process is None:
            return None

        # 通过 stdin 发送换行符通知 screencapture 停止录制
        try:
            self.process.stdin.write(b"\n")
            self.process.stdin.flush()
        except Exception:
            pass

        # 优先等待进程自然退出，给 screencapture 充足时间写入 moov atom
        try:
            self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            # 发送 SIGINT（比 SIGKILL 温和，screencapture 有机会清理资源）
            try:
                self.process.send_signal(signal.SIGINT)
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # 最后手段才用 SIGKILL，此时元数据丢失不可避免
                self.process.kill()
                self.process.wait()

        stderr_output = ""
        try:
            stderr_output = self.process.stderr.read().decode(errors="replace")
        except Exception:
            pass

        self.process = None

        # 等待文件系统刷新，确保 moov atom 完全写入磁盘
        time.sleep(1.0)

        if self.output_path and os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 0:
            return self.video_filename

        print(f"录制失败，视频文件未生成或为空: {self.output_path}")
        if stderr_output:
            print(f"stderr: {stderr_output}")
        return None

    def is_recording(self):
        return self.process is not None and self.process.poll() is None
