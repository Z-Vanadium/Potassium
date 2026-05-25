# Potassium：社交账号养号自动化框架

一个基于 **Playwright** 的浏览器自动化框架，用于在多个社交平台（微博、小红书、抖音、B站、知乎等）模拟真实用户行为，构建差异化的用户画像。支持账户隔离、反指纹识别、拟人化操作和会话持久化。

---

## 目录

- [Potassium：社交账号养号自动化框架](#potassium社交账号养号自动化框架)
  - [目录](#目录)
  - [环境要求](#环境要求)
  - [快速开始](#快速开始)
    - [第一步：安装 Python](#第一步安装-python)
    - [第二步：安装 uv（Python 包管理器）](#第二步安装-uvpython-包管理器)
    - [第三步：下载项目并安装依赖](#第三步下载项目并安装依赖)
    - [第四步：运行演示](#第四步运行演示)
  - [概念解释](#概念解释)
  - [项目结构](#项目结构)
  - [核心模块详解](#核心模块详解)
    - [1. 反检测引擎 (stealth)](#1-反检测引擎-stealth)
    - [2. 指纹管理 (fingerprint)](#2-指纹管理-fingerprint)
    - [3. 用户画像 (profiles)](#3-用户画像-profiles)
    - [4. 会话管理 (context\_manager)](#4-会话管理-context_manager)
    - [5. 拟人化操作 (human\_behavior)](#5-拟人化操作-human_behavior)
  - [写一个自动化脚本](#写一个自动化脚本)
  - [配置说明](#配置说明)
    - [修改频控参数](#修改频控参数)
    - [配置代理](#配置代理)
    - [添加新平台](#添加新平台)
  - [常见问题](#常见问题)
    - [Q: 运行时提示 "BrowserContext.storage\_state: Target page, context or browser has been closed"](#q-运行时提示-browsercontextstorage_state-target-page-context-or-browser-has-been-closed)
    - [Q: 怎么让浏览器在后台运行（不弹窗）？](#q-怎么让浏览器在后台运行不弹窗)
    - [Q: 如何一次运行多个账号？](#q-如何一次运行多个账号)
    - [Q: 登录状态会过期吗？](#q-登录状态会过期吗)
    - [Q: 怎么知道反检测有没有生效？](#q-怎么知道反检测有没有生效)
    - [Q: 会不会被封号？](#q-会不会被封号)

---

## 环境要求

| 项目 | 最低要求 |
|------|----------|
| **Python** | 3.12 或更高 |
| **操作系统** | Windows / macOS / Linux |
| **浏览器** | 不需要手动安装（框架自动下载 Chromium） |
| **硬盘空间** | 约 500MB（Chromium 浏览器约 300MB） |
| **网络** | 需要能访问互联网（首次安装时下载依赖） |

> 本项目只支持 Chromium 浏览器。Firefox 和 WebKit 虽然 Playwright 支持，但反检测补丁只对 Chromium 有效。

---

## 快速开始

### 第一步：安装 Python

如果你还没有 Python，先去 [python.org](https://www.python.org/downloads/) 下载安装。安装时**一定要勾选"Add Python to PATH"**（把 Python 加到系统路径）。

安装完成后，打开**命令提示符**（按 `Win+R`，输入 `cmd`，回车），输入以下命令验证：

```bash
python --version
```

如果显示 `Python 3.12.x` 或更高版本，说明安装成功。

### 第二步：安装 uv（Python 包管理器）

在命令提示符中运行：

```bash
pip install uv
```

### 第三步：下载项目并安装依赖

```bash
# 进入项目目录
cd F:\study\osn\final

# 安装 Python 依赖
uv sync

# 下载 Chromium 浏览器（首次需要，约 300MB，之后不需要）
uv run playwright install chromium
```

### 第四步：运行演示

```bash
uv run python main.py
```

运行后你会看到：
- 浏览器自动启动（会弹出一个窗口）
- 打开知乎和 B站 页面
- 模拟滚动浏览
- 在 `profiles/` 目录下生成会话文件

**所有操作都是自动的，不需要你手动登录。**

---

## 概念解释

刚接触浏览器自动化，先理解这几个核心概念：

| 概念 | 通俗解释 | 在这个项目里的作用 |
|------|----------|-------------------|
| **Browser（浏览器）** | 整个 Chrome/Chromium 程序 | 框架启动一个共享的 Chromium，所有账号共用 |
| **Context（上下文）** | 浏览器里的一个"独立隔间" | **每个账号一个 Context**，各自的 cookie、登录状态、设备指纹完全隔离 |
| **Page（页面）** | 一个标签页 | 每个 Context 可以打开多个 Page，就跟你用浏览器一样 |
| **指纹 (Fingerprint)** | 网站用来识别你的设备信息 | 框架给每个账号分配不同的指纹（CPU 核数、屏幕分辨率、GPU 型号等），让网站以为是不同的人 |
| **用户画像 (Profile)** | 一个人的完整行为设定 | 包括他是什么身份（大学生/科技爱好者）、看什么内容、怎么互动 |

**类比**：就像你有两台不同的电脑，一台是 Window 台式机、一台是 MacBook，用不同的账号登录同一个网站。网站看到的是两个完全不同的人。框架就是帮你自动创建这些"虚拟电脑"和"虚拟人物"。

---

## 项目结构

```
final/
├── config/                 ← 配置文件
│   ├── settings.py         # 全局设置（平台列表、频控、代理等）
│   └── profiles.py         # 预设用户画像（科技爱好者、美食博主等）
│
├── core/                   ← 核心功能模块
│   ├── stealth.py          # 反检测引擎（让浏览器不像机器人）
│   ├── fingerprint.py       # 指纹管理器（设备信息伪装）
│   ├── human_behavior.py   # 拟人化操作（打字、鼠标、滚动）
│   └── context_manager.py  # 会话隔离管理器（最核心的文件）
│
├── profiles/              ← 会话存储（自动生成，不要手动改）
├── accounts/              ← 账号配置（JSON 文件，放各平台账号信息）
├── platforms/             ← 平台处理器（目前空，后续放各平台的自动化脚本）
├── main.py                ← 演示脚本
└── pyproject.toml         ← 项目元数据和依赖声明
```

---

## 核心模块详解

### 1. 反检测引擎 (stealth)

**文件**: `core/stealth.py`

**作用**：这是整个框架的"隐身衣"。没有它，你用 Playwright 打开浏览器，网站一眼就能看出你是机器人。

**它做了什么**：

| 检测点 | 未处理时 | 处理后 |
|--------|---------|--------|
| `navigator.webdriver` | `true`（暴露你是自动化工具） | `undefined`（看起来是普通浏览器） |
| `window.chrome` | 不存在 | 存在（正常 Chrome 都有这个对象） |
| `navigator.plugins` | 0 个插件（一看就是机器人） | 3 个假插件（Chrome PDF 查看器等） |
| User-Agent | 包含 `HeadlessChrome` | 普通 Chrome 的 UA |
| `navigator.mimeTypes` | 空 | 包含正常浏览器的 MIME 类型 |

**使用方式**：

你不需要手动调用它。当你通过 `ContextManager` 创建账号上下文时，反检测补丁会自动注入。

如果你想验证反检测是否生效：

```python
from core.stealth import verify_stealth

result = await verify_stealth(page)
print(result)
# 输出: {"webdriver": True, "chrome_runtime": True, "plugins": True, "ua_clean": True}
# 全部 True 说明反检测工作正常
```

---

### 2. 指纹管理 (fingerprint)

**文件**: `core/fingerprint.py`

**作用**：每个账号需要不同的"设备指纹"，让网站以为他们是不同的人、不同的电脑。否则同一台电脑登录多个账号，网站会关联它们然后封号。

**一个完整的指纹包含**：

```
用户A（科技爱好者）：            用户B（大学生）：
─────────────────────          ─────────────────────
Windows 台式机                  Windows 台式机
NVIDIA RTX 3060 显卡          AMD RX 6600 显卡
12 核 CPU                      8 核 CPU
1366×768 屏幕                 1536×864 屏幕
Chrome 浏览器                  Edge 浏览器
```

**微信/微博/抖音等平台会检测这些信息来判断你是不是同一个人**。

**使用方式**：

```python
from core.fingerprint import Fingerprint, generate_random_fingerprint

# 方式1：从用户画像自动生成
from config.profiles import TECH_ENTHUSIAST
fp = Fingerprint.from_profile(TECH_ENTHUSIAST)

# 方式2：随机生成一个（适合快速测试）
fp = generate_random_fingerprint()
```

---

### 3. 用户画像 (profiles)

**文件**: `config/profiles.py`

**作用**：定义一个人的完整画像——他是什么身份、用什么设备、关注什么内容、怎么互动。每个账号绑定一个画像。

**框架预设了 4 个画像**：

| 画像 ID | 名称 | 身份设定 | 关注内容 | 行为特征 |
|---------|------|---------|---------|---------|
| `tech_enthusiast` | 科技爱好者 | Windows 台式机 / NVIDIA | AI、开源、编程、芯片 | 快速浏览，偶尔评论，弹幕少 |
| `food_blogger` | 美食博主 | iPhone 手机 | 美食、探店、烘焙、奶茶 | 慢速细看，高频点赞，表情多 |
| `traveler` | 旅行达人 | MacBook Pro / M3 芯片 | 旅行、摄影、露营、民宿 | 正常速度，中等互动 |
| `college_student` | 大学生 | Windows 台式机 / AMD | 考研、游戏、动漫、美妆 | 快速刷，在线时间长，互动多 |

**创建自定义画像**：

```python
from config.profiles import UserProfile

my_profile = UserProfile(
    profile_id="sports_fan",
    display_name="体育迷",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
    viewport=(1920, 1080),
    locale="zh-CN",
    timezone="Asia/Shanghai",
    webgl_vendor="Google Inc. (NVIDIA)",
    webgl_renderer="ANGLE (NVIDIA GeForce RTX 4070 Direct3D11 ...)",
    platform="Win32",
    hardware_concurrency=16,
    device_memory=16,
    interests=["NBA", "中超", "欧冠", "F1", "网球"],
    typing_speed_min=50,
    typing_speed_max=100,
    scroll_style="fast",
    session_duration_min=10,
    session_duration_max=30,
    like_probability=0.35,
    comment_probability=0.08,
    post_frequency="daily",
    language="zh",
    emoji_usage="moderate",
)
```

**UserProfile 所有字段说明**：

| 分类 | 字段 | 类型 | 说明 |
|------|------|------|------|
| 身份 | `profile_id` | str | 唯一标识，如 `"tech_enthusiast"` |
| 身份 | `display_name` | str | 中文名称，如 `"科技爱好者"` |
| 设备 | `user_agent` | str | 浏览器 UA 字符串 |
| 设备 | `viewport` | (int, int) | 浏览器窗口大小，如 `(1366, 768)` |
| 设备 | `locale` | str | 语言地区，`"zh-CN"` 或 `"en-US"` |
| 设备 | `timezone` | str | 时区，如 `"Asia/Shanghai"` |
| 设备 | `webgl_vendor` | str | GPU 厂商，如 `"Google Inc. (NVIDIA)"` |
| 设备 | `webgl_renderer` | str | GPU 渲染器型号 |
| 设备 | `platform` | str | 操作系统，`"Win32"` 或 `"MacIntel"` |
| 设备 | `hardware_concurrency` | int | CPU 逻辑核心数，如 `8` |
| 设备 | `device_memory` | int | 内存大小（GB），如 `8` |
| 设备 | `is_mobile` | bool | 是否手机设备，`True`/`False` |
| 设备 | `has_touch` | bool | 是否触摸屏，`True`/`False` |
| 兴趣 | `interests` | list[str] | 关注的关键词列表 |
| 兴趣 | `suspend_keywords` | list[str] | 要避开的关键词列表 |
| 行为 | `typing_speed_min` | int | 最快打字速度（毫秒/字），如 `50` |
| 行为 | `typing_speed_max` | int | 最慢打字速度（毫秒/字），如 `150` |
| 行为 | `scroll_style` | str | 滚动风格：`"fast"` `"normal"` `"slow"` `"reader"` |
| 行为 | `reading_multiplier` | float | 阅读速度倍数，`1.0`=正常，`0.5`=快速扫 |
| 活跃 | `session_duration_min` | int | 最短在线时间（分钟） |
| 活跃 | `session_duration_max` | int | 最长在线时间（分钟） |
| 活跃 | `sessions_per_day_min` | int | 每天最少上线次数 |
| 活跃 | `sessions_per_day_max` | int | 每天最多上线次数 |
| 社交 | `like_probability` | float | 看内容后点赞的概率（0~1） |
| 社交 | `comment_probability` | float | 看内容后评论的概率（0~1） |
| 社交 | `follow_probability` | float | 看内容后关注的概率（0~1） |
| 社交 | `repost_probability` | float | 看内容后转发的概率（0~1） |
| 社交 | `post_frequency` | str | 发帖频率：`"daily"` `"weekly"` `"rare"` |
| 语言 | `language` | str | 语言：`"zh"`（中文）或 `"en"`（英文） |
| 语言 | `emoji_usage` | str | 表情使用量：`"none"` `"light"` `"moderate"` `"heavy"` |

---

### 4. 会话管理 (context_manager)

**文件**: `core/context_manager.py`

**作用**：这是框架的"大管家"。你不需要关心浏览器怎么启动、怎么给每个账号创建独立空间、怎么保存登录状态——这些它都帮你做了。

**核心类**：

- **`ContextManager`** — 浏览器启动器。创建账号上下文、管理生命周期。
- **`AccountContext`** — 单个账号的隔离环境。包含独立的 cookie、指纹、频控统计。

**基本用法**：

```python
from core.context_manager import ContextManager
from config.profiles import TECH_ENTHUSIAST

async with ContextManager() as manager:
    # 为"科技爱好者"在知乎创建一个账号上下文
    ctx = await manager.create_context(
        account_id="zhihu_tech_01",   # 账号 ID（自己起的名字）
        platform="zhihu",              # 平台（weibo/xiaohongshu/douyin/...）
        profile=TECH_ENTHUSIAST,       # 用户画像
    )

    # 打开一个新页面
    page = await ctx.new_page()

    # 导航到知乎
    await page.goto("https://www.zhihu.com")

    # 做你想做的事...

    # 关闭（会自动保存登录状态到 profiles/ 目录）
    await ctx.close()
```

**会话持久化说明**：

当你调用 `ctx.close()` 时，框架会自动把当前账号的 cookie 和 localStorage 保存到 `profiles/` 目录。下次再创建同名账号时，会自动恢复之前的登录状态，**不需要重新登录**。

```
profiles/
├── zhihu_tech_01_zhihu.json      ← "zhihu_tech_01" 在知乎的登录状态
├── weibo_food_01_weibo.json      ← "weibo_food_01" 在微博的登录状态
└── student_bilibili_01_bilibili.json
```

**频控功能**：

```python
# 检查是否可以点赞
if ctx.can_perform("likes"):
    await like_post(page)
    ctx.record_action("likes")  # 记录这次点赞
else:
    print("今天点赞次数已用完，跳过")

# 查看今天已经做了多少次操作
print(f"今天已点赞 {ctx.stats.likes} 次")
print(f"今天已评论 {ctx.stats.comments} 次")
```

---

### 5. 拟人化操作 (human_behavior)

**文件**: `core/human_behavior.py`

**作用**：提供一系列模拟真人操作的工具函数。直接用 Playwright 的 `page.type()` 或 `page.click()`，网站能看出是脚本。这些函数会加入随机延迟、鼠标轨迹、打字错误等"人味"。

**可用的函数**：

| 函数 | 作用 | 用法示例 |
|------|------|---------|
| `human_delay(min, max)` | 生成随机的等待时间 | `delay = human_delay(1, 5)` |
| `think_pause(min, max)` | 模拟思考停顿 | `await think_pause()` |
| `action_cooldown(min, max)` | 两次操作间的冷却 | `await action_cooldown(60, 180)` |
| `type_like_human(page, text)` | 模拟真人打字 | `await type_like_human(page, "你好，这个视频很好看！")` |
| `move_mouse_to(page, x, y)` | 贝塞尔曲线移动鼠标 | `await move_mouse_to(page, 500, 300)` |
| `click_like_human(page, selector)` | 模拟真人点击 | `await click_like_human(page, ".like-btn")` |
| `scroll_like_human(page, pixels)` | 模拟真人滚动 | `await scroll_like_human(page, 1000, style="normal")` |
| `random_scroll_behavior(page)` | 模拟一次完整浏览 | `await random_scroll_behavior(page, style="slow")` |

**打字模拟详解**：

```python
await type_like_human(
    page,
    text="这个视频真的很棒，学到了很多！",
    min_delay_ms=50,   # 每个字最少 50 毫秒
    max_delay_ms=150,  # 每个字最多 150 毫秒
)
```

这个函数会：
1. 一个字一个字地输入
2. 速度时快时慢（真人不会匀速打字）
3. 遇到标点符号会停顿（句号会停 0.1~0.35 秒）
4. 偶尔打错字然后删除重打（约 1.5% 概率）
5. 在词语之间偶尔犹豫（约 2% 概率）

---

## 写一个自动化脚本

下面是一个完整的例子：创建一个"美食博主"账号，在小红书上浏览内容、点赞、评论。

```python
import asyncio
from core.context_manager import ContextManager
from core.human_behavior import (
    think_pause,
    type_like_human,
    click_like_human,
    random_scroll_behavior,
    action_cooldown,
)
from config.profiles import FOOD_BLOGGER


async def browse_xiaohongshu():
    """以美食博主身份在小红书浏览和互动。"""

    async with ContextManager() as manager:
        # 1. 创建账号上下文
        ctx = await manager.create_context(
            account_id="food_xiaohongshu_01",
            platform="xiaohongshu",
            profile=FOOD_BLOGGER,
        )

        page = await ctx.new_page()

        try:
            # 2. 打开小红书首页
            await page.goto("https://www.xiaohongshu.com/explore")
            await think_pause(2, 4)  # 模拟刚打开时停顿

            # 3. 浏览首页推荐内容（模拟刷信息流）
            await random_scroll_behavior(page, style="slow")
            await think_pause()

            # 4. 点击搜索框，搜索感兴趣的内容
            await click_like_human(page, ".search-input")
            await type_like_human(page, "上海美食探店")
            await page.keyboard.press("Enter")
            await think_pause(3, 5)

            # 5. 浏览搜索结果，点进一篇笔记
            await random_scroll_behavior(page, style="normal")
            await click_like_human(page, ".note-item:first-child")

            # 6. 点赞这篇笔记
            await think_pause(2, 5)  # 先看一会儿
            if ctx.can_perform("likes"):
                await click_like_human(page, ".like-btn")
                ctx.record_action("likes")

            # 7. 写一条评论
            await think_pause(3, 8)  # 想一下要说什么
            await click_like_human(page, ".comment-input")
            await type_like_human(page, "看起来好好吃！具体地址在哪里呀？")
            await page.keyboard.press("Enter")
            ctx.record_action("comments")

            # 8. 操作间隔（防止被限流）
            await action_cooldown(120, 180)

        finally:
            # 9. 保存会话并关闭
            await ctx.close()


if __name__ == "__main__":
    asyncio.run(browse_xiaohongshu())
```

---

## 配置说明

### 修改频控参数

在 `config/settings.py` 中修改：

```python
# 每个平台每天的动作上限
@dataclass(frozen=True)
class PlatformConfig:
    daily_post_limit: int = 5       # 每天最多发 5 条帖子
    daily_like_limit: int = 20      # 每天最多点 20 个赞
    daily_comment_limit: int = 10   # 每天最多写 10 条评论
    daily_follow_limit: int = 5     # 每天最多关注 5 个人

# 所有账号合计每天最多 200 次操作
GLOBAL_DAILY_ACTION_CAP: int = 200

# 只在早 8 点到晚 11 点之间活动
ACTIVE_HOURS_START: int = 8
ACTIVE_HOURS_END: int = 23
```

### 配置代理

如果你需要为每个账号使用不同的 IP 地址（防止平台通过 IP 关联账号），在 `config/settings.py` 中设置：

```python
PROXY_SERVER = "http://username:password@proxy.example.com:8080"
```

代理会应用到所有账号上下文。

### 添加新平台

在 `config/settings.py` 中的 `PLATFORMS` 字典添加：

```python
PLATFORMS = {
    # ... 已有的平台 ...
    "douban": PlatformConfig(
        "douban", "豆瓣", "https://www.douban.com",
        "https://accounts.douban.com/passport/login",
        locale="zh-CN",
        daily_like_limit=10,
    ),
}
```

---

## 常见问题

### Q: 运行时提示 "BrowserContext.storage_state: Target page, context or browser has been closed"

**原因**：这是正常的。某些网站（如知乎）使用了单页应用架构，在浏览过程中会自己关闭旧的页面上下文。框架会自动处理这个异常，不影响功能。

### Q: 怎么让浏览器在后台运行（不弹窗）？

修改 `config/settings.py`：

```python
@dataclass(frozen=True)
class BrowserDefaults:
    headless: bool = True  # 改成 True
```

但注意：**headless 模式下反检测效果会减弱**，部分网站（尤其是国内平台）能检测出 headless 浏览器。如果不需要隐身，可以打开。

### Q: 如何一次运行多个账号？

```python
accounts = [
    {"id": "zhihu_tech_01",  "platform": "zhihu",        "profile": TECH_ENTHUSIAST},
    {"id": "zhihu_food_01",  "platform": "zhihu",        "profile": FOOD_BLOGGER},
    {"id": "bilibili_student_01", "platform": "bilibili", "profile": COLLEGE_STUDENT},
]

async with ContextManager() as manager:
    for acc in accounts:
        ctx = await manager.create_context(
            account_id=acc["id"],
            platform=acc["platform"],
            profile=acc["profile"],
        )
        # ... 各做各的操作 ...
```

所有账号共用同一个浏览器进程，但各自的 cookie 和指纹是完全隔离的。

### Q: 登录状态会过期吗？

会的。社交平台的 cookie 一般有效期几周到几个月。过期后需要重新登录。框架目前**不支持自动登录**（因为各平台登录方式不同，且涉及验证码和安全问题）。你需要：

1. 首次运行时，让框架打开浏览器
2. 手动扫码或输入密码登录
3. 关闭时框架会自动保存登录状态
4. 下次运行时自动恢复

### Q: 怎么知道反检测有没有生效？

框架内置了自检功能，运行演示脚本就能看到：

```
Stealth:  4/4 checks passed
  webdriver: PASS          ← 网站看不见你是机器人
  chrome_runtime: PASS     ← 浏览器特征正常
  plugins: PASS            ← 插件列表正常
  ua_clean: PASS           ← User-Agent 无泄露
```

也可以用在线检测工具手动验证：打开 [https://bot.sannysoft.com](https://bot.sannysoft.com) 看测试结果。

### Q: 会不会被封号？

这个框架**尽力降低封号风险**，但不能保证完全安全。以下建议能提高安全性：

- ✅ 使用 headful 模式（让浏览器窗口可见，`headless=False`）
- ✅ 设置合理的每日操作上限（发帖 3~5 条，点赞 20 以内）
- ✅ 操作间隔至少 1~3 分钟
- ✅ 坚持使用拟人化操作函数（不要用 Playwright 原生的 `page.click()`）
- ✅ 不同账号使用不同的指纹和画像
- ❌ 不要短时间内大量操作
- ❌ 不要所有账号都做一模一样的操作
- ❌ 不要 24 小时不间断运行

**免责声明**：使用自动化工具操作社交平台账号可能违反各平台的服务条款。本项目仅用于课程实验和学习目的。使用本项目产生的任何后果（包括但不限于账号封禁）由使用者自行承担。
