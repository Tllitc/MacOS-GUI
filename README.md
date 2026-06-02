# macOS GUI 采集标注工具

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-macOS-lightgrey.svg)
![GUI](https://img.shields.io/badge/GUI-PyQt5-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

一款基于 **Python 3 + PyQt5** 开发的 macOS 平台 GUI 操作轨迹采集与标注工具。支持全屏截图、区域选择、多动作类型标注、屏幕录制、全局快捷键，并输出结构化的 JSON 数据，适用于 GUI Agent 训练数据的采集工作流。

## 目录

- [功能特性](#功能特性)
- [系统要求](#系统要求)
- [安装](#安装)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
  - [任务初始化](#任务初始化)
  - [截图捕获](#截图捕获)
  - [动作标注](#动作标注)
  - [多轮对话支持](#多轮对话支持)
  - [完成与导出](#完成与导出)
- [动作类型说明](#动作类型说明)
- [快捷键](#快捷键)
- [数据格式](#数据格式)
  - [目录结构](#目录结构)
  - [JSON 结构](#json-结构)
- [项目架构](#项目架构)
  - [模块说明](#模块说明)
  - [核心类说明](#核心类说明)
- [常见问题](#常见问题)
- [许可证](#许可证)

## 功能特性

- 🖥️ **全屏截图 + 区域选择** — 支持点击选点、拖拽拉框、双框拖拽（起点→终点）
- 🏷️ **15 种动作类型** — 涵盖点击、拖拽、输入、滚动、按键组合、等待、回答、打开应用等
- 🧠 **智能滚动测量** — 通过参照物多次框选，自动累加计算滚动像素距离
- ⌨️ **按键组合捕获** — 直接在输入框中按下对应键盘按键，自动记录键名
- 📹 **屏幕录制** — 使用 `screencapture` 命令录制操作过程视频
- 🔄 **多轮对话** — 支持同一任务内多轮 user/assistant 消息交替，answer 动作自动开启新轮次
- 🔢 **灵活编号** — answer 后步骤编号从 1 重新计数，截图文件编号全局递增
- 🌐 **全局快捷键** — Cmd+Q 截图、Cmd+S 保存，基于 pynput + 独立子进程架构
- 📁 **标准化数据输出** — 目录结构 `gui_000001/`，JSON 格式含 platform、screen_size、messages 等字段
- ↩️ **步骤管理** — 支持前后翻页、撤销上一步、重新截图、步骤编号编辑
- 🎨 **可定制分类** — 内置 11 种软件类型（社交、电商、办公、浏览器等）

## 系统要求

| 组件     | 要求                      |
| -------- | ------------------------- |
| 操作系统 | macOS 10.13+              |
| Python   | 3.7+                      |
| GUI 框架 | PyQt5                     |
| 快捷键   | pynput（需辅助功能权限）  |
| 权限     | 屏幕录制权限 + 辅助功能权限 |

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/macos-gui-annotation-tool.git
cd macos-gui-annotation-tool
```

### 2. 创建虚拟环境（推荐）

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install PyQt5 pynput
```

### 4. 授予系统权限

首次运行前，请确保在 **系统设置 > 隐私与安全性** 中授予以下权限：
- **屏幕录制** — 允许终端（Terminal）或你所用的 Python 解释器
- **辅助功能** — 允许终端（Terminal）或你所用的 Python 解释器（全局快捷键需要）

## 快速开始

```bash
python main.py
```

程序启动后：
1. **选择存储母目录** — 所有标注数据将保存在此目录下
2. **填写软件名称** — 如"网易有道翻译"、"微信"、"Safari"
3. **选择软件类型** — 从下拉框中选择对应的分类
4. **点击"开始标注"** — 输入第一个任务指令，即可开始采集

## 使用指南

### 任务初始化

| 字段         | 说明                                                              |
| ------------ | ----------------------------------------------------------------- |
| 存储目录     | 所有 `gui_XXXXXX` 文件夹的父目录                                   |
| 软件名称     | 被采集应用的名称，会用于文件名生成                                |
| 软件类型     | 11 种预置类型之一，影响 JSON 中 `task_type` 字段                  |

点击"开始标注"后会弹出对话框询问第一个任务指令（例如："打开翻译功能并翻译一段英文"）。

### 截图捕获

点击 **"给下一步截图 (Cmd+Q)"** 按钮或按下全局快捷键，主窗口自动隐藏，进入全屏截图模式：

| 操作方式         | 说明                                                              |
| ---------------- | ----------------------------------------------------------------- |
| **单击**         | 点击屏幕上某个点，记录该点坐标，截图类型为 `click`                |
| **拉框**         | 按住鼠标左键拖拽选择矩形区域，截图类型为 `drag`                   |
| **双框（拖拽）** | 拉第一个框 → 按 `ESC` 清除选区 → 拉第二个框，再用 Cmd+S 确认     |

**截图标记说明：**
- 点击动作：绘制红色十字准星 + 中心圆点
- 拉框动作：绘制红色矩形边框
- 双框拖拽：绘制两个红色矩形 + 箭头连接

完成选择后按 **Cmd+S** 确认截图，或按 **ESC** 取消。

### 动作标注

截图返回后，在右侧表单中填写动作信息：

| 字段       | 说明                                                              |
| ---------- | ----------------------------------------------------------------- |
| 动作描述   | 该动作的目的，如"左键单击网易有道翻译"                            |
| 动作类型   | 从 15 种类型中选择（中文显示，内部存储为英文 key）                |
| 坐标 [x,y] | 自动根据截图选区中心点填充（只读）                                |
| 文本       | type / answer / open_app / open_url 动作时显示                   |
| 按键组合   | keys 动作时显示，点击输入框后直接按键即可捕获键名                  |
| 滚动像素   | scroll 动作时显示，支持智能测量                                   |

**滚动距离智能测量：**
1. 先截图框选参照物（如某个按钮）
2. 选择动作类型为"滚动"
3. 点击"开始测量滚动距离"记录第一个参照物
4. 滚动页面后，再次截图框选**同一个参照物**
5. 重复可累积测量，点击"完成测量"结束

### 多轮对话支持

工具支持在一个任务文件夹中采集多轮 user/assistant 对话：

- **answer 动作**：保存后自动弹出对话框询问下一轮指令，步骤编号重新从 1 开始
- **terminate 动作**：标记任务完成，弹出选项询问是否继续新任务或创建新任务文件夹
- 所有轮次保存在同一个 JSON 文件的 `messages` 数组中

### 完成与导出

点击 **"完成标注"** 或保存 terminate 步骤后：
1. 屏幕录制自动停止
2. 所有轮次数据合并为一个 JSON 文件
3. 截图文件保持原始命名
4. 弹出选项：继续新任务（新 `gui_` 编号）或退出

## 动作类型说明

| 中文显示   | 英文 Key          | 说明                     | 需要参数           |
| ---------- | ----------------- | ------------------------ | ------------------ |
| 左键单击   | `left_click`      | 鼠标左键单击             | 坐标               |
| 双击       | `double_click`    | 鼠标左键双击             | 坐标               |
| 三击       | `triple_click`    | 鼠标左键三击             | 坐标               |
| 右键单击   | `right_click`     | 鼠标右键单击             | 坐标               |
| 中键单击   | `middle_click`    | 鼠标中键单击             | 坐标               |
| 拖拽       | `left_click_drag` | 鼠标左键拖拽（起点→终点）| 起点坐标 + 终点坐标 |
| 鼠标移动   | `mouse_move`      | 鼠标移动到指定位置       | 坐标               |
| 滚动       | `scroll`          | 滚轮滚动                 | 滚动像素           |
| 文本输入   | `type`            | 键盘输入文本             | 文本内容           |
| 按键组合   | `keys`            | 键盘组合键               | 按键列表           |
| 等待       | `wait`            | 等待指定时间             | 等待时间（秒）     |
| 回答用户   | `answer`          | 回答用户问题             | 文本内容           |
| 任务完成   | `terminate`       | 终止当前任务             | 无                 |
| 打开app    | `open_app`        | 打开指定应用程序         | 应用名称           |
| 打开网页   | `open_url`        | 打开指定网页             | URL                |

## 快捷键

| 快捷键   | 功能                               | 作用范围   |
| -------- | ---------------------------------- | ---------- |
| Cmd+Q    | 隐藏窗口并进入截图模式             | 全局       |
| Cmd+S    | 确认截图 / 确认选区（截图模式下）  | 全局       |
| Cmd+S    | 保存当前步骤                       | 编辑窗口   |
| ESC      | 取消当前截图 / 清除选区            | 截图窗口   |

## 数据格式

### 目录结构

```
<存储母目录>/
└── gui_000001/                         # GUI 编号文件夹
    ├── gui_000001.json                 # 标注数据
    ├── macOS_微信_2025-01-01_10h30_00.png
    ├── macOS_微信_2025-01-01_10h30_15.png
    ├── macOS_微信_2025-01-01_10h30_30.mp4  # 录制视频
    └── ...
```

### JSON 结构

```json
{
  "platform": "macOS-15.0",
  "system": "macOS 15.0",
  "screen_size": [1440, 900],
  "task_type": "MacOS-社交",
  "recording_video": "macOS_微信_2025-01-01_10h30_30.mp4",
  "messages": [
    {
      "role": "user",
      "instruction": "打开翻译功能并翻译一段英文"
    },
    {
      "role": "assistant",
      "trajectory": [
        {
          "step": 0,
          "intent": "左键单击翻译图标",
          "CoT": "需要先点击翻译图标进入翻译界面",
          "observation": {
            "screenshot": "macOS_微信_2025-01-01_10h30_00.png",
            "active_window": "微信",
            "ui_tree_segment": ""
          },
          "actions": [
            {
              "action": "left_click",
              "coordinate": [100, 200],
              "element": "翻译图标"
            }
          ]
        }
      ]
    },
    {
      "role": "user",
      "instruction": "把翻译结果复制到剪贴板"
    },
    {
      "role": "assistant",
      "trajectory": [
        {
          "step": 1,
          "intent": "右键单击翻译结果区域",
          "CoT": "弹出右键菜单选择复制",
          "observation": {
            "screenshot": "macOS_微信_2025-01-01_10h30_15.png",
            "active_window": "微信",
            "ui_tree_segment": ""
          },
          "actions": [
            {
              "action": "right_click",
              "coordinate": [300, 400],
              "element": "翻译结果区域"
            }
          ]
        }
      ]
    }
  ]
}
```

**字段说明：**

| 字段                        | 说明                            |
| --------------------------- | ------------------------------- |
| `platform`                  | 操作系统版本信息                |
| `system`                    | 系统名称 + 版本                 |
| `screen_size`               | 屏幕分辨率 [宽, 高]             |
| `task_type`                 | 任务类型（平台-分类）           |
| `recording_video`           | 录制视频文件名                  |
| `messages`                  | 多轮对话消息数组                |
| `messages[].role`           | `user` 或 `assistant`          |
| `messages[].instruction`    | 用户指令（role=user 时）        |
| `messages[].trajectory`     | 轨迹步骤数组（role=assistant 时）|
| `trajectory[].step`         | 步骤编号                        |
| `trajectory[].intent`       | 动作描述（terminate 时使用 `implement`） |
| `trajectory[].CoT`          | 思维链（Chain of Thought）      |
| `trajectory[].observation`  | 观察信息（截图、活动窗口等）    |
| `trajectory[].actions`      | 动作数组                        |

## 项目架构

### 模块说明

```
MacosProject/
├── main.py                  # 程序入口，任务初始化窗口，全局快捷键子进程管理
├── annotation_editor.py     # 标注编辑器核心，步骤管理、多轮对话、JSON 生成
├── screenshot_capture.py    # 全屏截图窗口，区域选择（点击/拉框/双框拖拽）
├── data_manager.py          # 数据管理层，目录创建、文件保存、JSON 结构初始化
├── screen_recorder.py       # macOS 原生 screencapture 屏幕录制封装
├── hotkey_listener.py       # 全局快捷键独立模块（pynput HotKey 封装）
├── logo.ico                 # 应用图标
└── README.md                # 项目文档
```

### 核心类说明

| 类名                          | 所在文件                 | 职责                                               |
| ----------------------------- | ------------------------ | -------------------------------------------------- |
| `InitTaskWindow`              | `main.py`                | 任务初始化窗口，配置存储目录、软件信息              |
| `GlobalHotkeyListener`        | `main.py`                | 基于 multiprocessing 子进程的全局快捷键管理器       |
| `AnnotationEditor`            | `annotation_editor.py`   | 标注编辑器主窗口，步骤分页、多轮、保存/导出         |
| `StepEditorWidget`            | `annotation_editor.py`   | 单个步骤编辑面板，动作表单、截图预览、滚动测量      |
| `ScreenshotCaptureWindow`     | `screenshot_capture.py`  | 全屏截图窗口，支持单击/拉框/双框拖拽选择            |
| `DataManager`                 | `data_manager.py`        | 目录编号管理、截图/JSON 保存、屏幕信息获取          |
| `ScreenRecorder`              | `screen_recorder.py`     | 调用 `screencapture -v` 录制并管理录制进程          |

**数据流概览：**

```
[InitTaskWindow]  ──(配置参数)──→  [AnnotationEditor]
                                       │
                        ┌──────────────┼──────────────┐
                        ▼              ▼              ▼
               [ScreenshotCapture]  [StepEditor]  [ScreenRecorder]
                        │              │
                        ▼              ▼
                   [DataManager]  ──→  文件系统 (gui_XXXXXX/)
```

## 常见问题

### Q: 截图时看不到其他应用程序窗口？
**A:** 确保已为终端（Terminal）或 Python 解释器授予**屏幕录制权限**：
> 系统设置 → 隐私与安全性 → 隐私 → 屏幕录制 → 勾选终端

### Q: 全局快捷键 (Cmd+Q / Cmd+S) 不生效？
**A:** 需要授予**辅助功能权限**：
> 系统设置 → 隐私与安全性 → 隐私 → 辅助功能 → 勾选终端

同时确保已安装 `pynput` 库：`pip install pynput`

### Q: 提示"全局快捷键子进程已退出"？
**A:** 检查终端是否被授予辅助功能权限。如果授权后仍不生效，尝试重启终端或重启应用。

### Q: 如何修改已有的标注数据？
**A:** 当前版本暂不支持加载已有 JSON 进行编辑，建议在标注过程中使用"上一步/下一步"和"重新截图"功能进行调整。

### Q: answer 和 terminate 有什么区别？
**A:**
- **answer**：表示回答用户问题，保存后自动进入下一轮对话（同一个 `gui_` 文件夹）
- **terminate**：表示整个采集任务完成，保存后弹出对话框决定是否创建新任务（新 `gui_` 文件夹）

### Q: 视频录制文件在哪里？
**A:** 录制文件保存在对应 `gui_XXXXXX` 文件夹内，文件名格式为 `macOS_{软件名称}_{时间戳}.mp4`，通过 `recording_video` 字段记录在 JSON 中。

## 许可证

本项目基于 [MIT License](LICENSE) 开源。

---

如有问题或建议，欢迎提交 [Issue](https://github.com/your-username/macos-gui-annotation-tool/issues) 或 Pull Request。
