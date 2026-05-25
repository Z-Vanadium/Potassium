# Potassium — 多平台社交账号养号自动化框架

基于 **Playwright** 的浏览器自动化框架，在 **17 个国际平台** 上构建差异化的用户画像。每个账号拥有独立的浏览器上下文、唯一设备指纹、反检测补丁和拟人化行为。支持可插拔的按平台回调处理器架构，实现针对各网站 DOM 结构的精准内容交互。

---

## 快速开始

```bash
# 环境要求：Python 3.12+
pip install uv

# 克隆并安装
git clone git@github.com:Z-Vanadium/Potassium.git
cd Potassium
uv sync
uv run playwright install chromium

# 快速模式：17 个组合（每平台一个画像）
uv run python daily_farming.py --quick

# 全量模式：6 个画像 × 17 个平台 = 102 个组合
uv run python daily_farming.py
```

**或使用 Makefile（推荐）**：

```bash
# 一键：类型检查 → 运行养号 → 自动提交推送
make

# 分步操作
make install     # 安装依赖 + Chromium
make check       # 类型检查（0 error 才继续）
make run         # 快速模式（17 组合）
make run-full    # 全量模式（102 组合）
make push        # 自动 git add -A && commit && push
make clean       # 清理临时文件

# Windows 上没有 make？
# winget install GnuWin32.Make    或在 Git Bash 中使用
```

---

## 核心概念

| 概念 | 通俗解释 | 在本项目中的作用 |
|------|---------|-----------------|
| **Browser（浏览器）** | 一个 Chromium 进程 | 所有账号共享，只启动一次 |
| **Context（上下文）** | 浏览器中的独立隔间 | **每账号一个** — cookie、指纹、存储完全隔离 |
| **Page（页面）** | 一个标签页 | 每个 Context 可打开多个 Page |
| **指纹 (Fingerprint)** | 网站识别你设备的信号 | 每账号不同：UA、分辨率、WebGL、CPU 核数、时区 |
| **画像 (Profile)** | 一个完整的人设 | 兴趣、设备、行为参数、活跃模式 |
| **处理器 (Handler)** | 针对特定网站 DOM 的交互逻辑 | 知道每个网站的 HTML 结构，精准点击匹配内容的回调函数 |

**类比**：每个账号 = 不同的人,在不同的城市,用不同的电脑。

---

## 项目结构

```
├── config/
│   ├── settings.py          # 17 个平台配置、频控参数、浏览器默认值
│   └── profiles.py          # 6 个用户画像（人设定义）
├── core/
│   ├── stealth.py           # 反检测引擎（webdriver、plugins、CDP 泄露修补）
│   ├── fingerprint.py       # 每账号独立设备指纹
│   ├── human_behavior.py    # 拟人操作：打字、鼠标轨迹、滚动模拟
│   └── context_manager.py   # 浏览器上下文工厂 + 会话隔离
├── platforms/               # 按平台的 DOM 处理器（回调架构）
│   ├── base.py              # 抽象基类 PlatformHandler + 回调接口
│   ├── reddit.py            # Reddit：扫描 shreddit-post → 匹配 → 点击 → 投票
│   └── __init__.py          # 注册表：get_handler("reddit") 获取处理器
├── daily_farming.py         # 主自动化脚本：6×17 每日养号
├── main.py                  # 演示：反检测验证 + 指纹隔离检查
├── profiles/                # 持久化浏览器会话状态（自动保存）
└── evidence/                # 截图 + JSON 汇总报告（运行时输出）
```

---

## 6 个预设用户画像

| 画像 ID | 身份 | 设备 | 兴趣关键词 | 行为特征 |
|---------|------|------|-----------|---------|
| `tech_enthusiast` | 科技爱好者 | Windows / NVIDIA RTX 3060 | AI, Rust, 开源, 创业 | 快速浏览，点赞率 25%，每周发帖 |
| `food_blogger` | 美食博主 | iPhone | 食谱、烘焙、咖啡、意大利菜 | 慢速细看，点赞率 45%，表情多 |
| `traveler` | 旅行达人 | MacBook / M3 | 徒步、日本、巴塔哥尼亚、数字游民 | 正常速度，点赞率 35% |
| `college_student` | 大学生 | Windows / AMD RX 6600 | GRE、实习、寝室好物、歌单 | 极快浏览，点赞率 40%，每天 3-5 次上线 |
| `retiree` | 退休老人 | iPad / A12Z | 园艺、瑜伽、古典音乐、观鸟 | 逐字细读，点赞率 15%，转发率 25% |
| `teenager` | 未成年人 | Windows / AMD RX 6500XT | Fortnite、NBA、动漫、Valorant、梗图 | 飞快刷，点赞率 55%，表情刷屏，每天 2-4 小时 |

使用：`from config.profiles import TECH_ENTHUSIAST, RETIREE`

---

## 17 个国际平台

| 分类 | 平台 | 键值 | 网址 |
|------|------|------|------|
| 社交 | Pinterest | `pinterest` | pinterest.com |
| 社交 | Tumblr | `tumblr` | tumblr.com |
| 社交 | Reddit | `reddit` | reddit.com |
| 社交 | Quora | `quora` | quora.com |
| 社交 | X / Twitter | `twitter` | x.com |
| 社交 | LinkedIn | `linkedin` | linkedin.com |
| 直播 | Twitch | `twitch` | twitch.tv |
| 电商 | Amazon | `amazon` | amazon.com |
| 电商 | eBay | `ebay` | ebay.com |
| 电商 | AliExpress | `aliexpress` | aliexpress.com |
| 电商 | Walmart | `walmart` | walmart.com |
| 电商 | Shopee | `shopee` | shopee.sg |
| 旅行 | Booking.com | `booking` | booking.com |
| 旅行 | Expedia | `expedia` | expedia.com |
| 旅行 | Agoda | `agoda` | agoda.com |
| 流媒体 | Spotify | `spotify` | open.spotify.com |
| 流媒体 | YouTube | `youtube` | youtube.com |

---

## 回调式处理器架构

每个平台可以有专属的处理器（回调函数），它知道该网站的具体 DOM 结构。处理器根据画像兴趣找到匹配内容，然后点击、投票、评论。

### 工作原理

```python
from platforms import get_handler

handler = get_handler("reddit")  # 返回 RedditHandler 实例，无处理器时返回 None

if handler:
    # 可选：设置回调函数
    handler.on_content_found = lambda item: print(f"发现: {item.title}")
    handler.on_interact = lambda item, action: print(f"已点赞: {action.liked}")

    # 浏览 + 互动
    result = await handler.browse(page, profile, account_ctx)
    # → 找到匹配画像兴趣的帖子 → 点击 → 点赞 → 返回汇总
else:
    # 没有处理器时回退到通用搜索+滚动
    ...
```

### 已实现处理器：Reddit

```
RedditHandler (platforms/reddit.py)
│
├── before_browse()     → 根据画像兴趣导航到 r/Python、r/Baking 等匹配子版
├── find_content()      → 扫描 <shreddit-post> 元素，提取标题，与 profile.interests 打分
├── should_engage()     → 相关性 ≥ 0.5 才考虑；实际概率 = like_probability + 相关性 × 0.4
└── interact()          → 点击标题 → 加载帖子 → 滚动阅读（profile.reading_multiplier）
                           → 随机点赞（profile.like_probability）
                           → 随机评论（profile.comment_probability）
                           → 返回信息流
```

### 如何新增处理器

```python
# platforms/amazon.py
from platforms.base import PlatformHandler, register_handler

@register_handler("amazon")
class AmazonHandler(PlatformHandler):
    def _get_selectors(self):
        return {"product_card": "[data-component-type='s-search-result']",
                "product_title": "h2 a span"}

    async def find_content(self, page, profile):
        ...  # 扫描商品卡片,匹配标题与 profile.interests

    async def interact(self, page, item, profile):
        ...  # 点击商品 → 查看详情 → 随机加入心愿单
```

然后在 `platforms/__init__.py` 中加一行 `from platforms import amazon`。`@register_handler` 装饰器会自动注册。

---

## 抽象处理器接口

```python
class PlatformHandler(ABC):
    # ── 子类必须实现 ──
    async def find_content(self, page, profile) -> list[ContentItem]: ...
    async def interact(self, page, item, profile) -> ActionResult: ...
    def _get_selectors(self) -> dict[str, str]: ...

    # ── 可选钩子 ──
    async def before_browse(self, page, profile): ...       # 浏览前：导航、cookie 同意等
    async def after_browse(self, page, profile, result): ... # 浏览后：清理、日志
    def should_engage(self, item, profile) -> bool: ...      # 是否与匹配内容互动（骰子判定）

    # ── 回调函数（调用方设置） ──
    on_content_found: ContentCallback | None   # 发现匹配内容时触发
    on_interact: ActionResultCallback | None   # 每次互动后触发

    # ── 编排器 ──
    async def browse(self, page, profile, ctx, max_interactions=5) -> BrowseResult: ...

    # ── 共享工具方法 ──
    @staticmethod match_interests(text, interests) -> list[tuple[str, float]]  # 文本与兴趣打分
    @staticmethod safe_click(page, selector) -> bool                            # 安全点击
    @staticmethod safe_get_text(page, selector) -> str                          # 安全提取文本
```

---

## 核心模块

### 反检测引擎 (`core/stealth.py`)

每次导航前自动注入，修补以下检测点：

- `navigator.webdriver` → `undefined`
- `window.chrome` → 存在且看起来是原生对象
- `navigator.plugins` → 3 个伪插件（Chrome PDF 查看器等）
- `navigator.mimeTypes` → 正常浏览器的 MIME 类型
- iframe contentWindow 检测 → 拦截
- CDP `Runtime.enable` 痕迹 → 隐藏

### 拟人化操作 (`core/human_behavior.py`)

| 函数 | 作用 |
|------|------|
| `human_delay(min, max)` | Gamma 分布随机等待 |
| `type_like_human(page, text)` | 模拟真人打字（含打错+纠正） |
| `move_mouse_to(page, x, y)` | 贝塞尔曲线鼠标移动 |
| `click_like_human(page, selector)` | 移动到元素内随机位置 → 点击 |
| `scroll_like_human(page, px, style)` | 按阅读风格滚动（含停顿+回看） |
| `random_scroll_behavior(page, style)` | 模拟一次完整的信息流浏览 |

### 会话隔离 (`core/context_manager.py`)

```python
async with ContextManager() as manager:
    ctx = await manager.create_context(
        account_id="tech_reddit_01",
        platform="reddit",
        profile=TECH_ENTHUSIAST,
    )
    page = await ctx.new_page()
    # ... 浏览、互动 ...
    await ctx.close()  # 自动保存 cookie 到 profiles/
```

每个 `AccountContext` 自动跟踪：操作计数、频控状态、会话时长。

### 强制登录机制 (`FORCE_LOGIN`)

**默认开启**：所有 17 个平台在自动浏览前都会等待手动登录。配置项在 `config/settings.py`：

```python
FORCE_LOGIN = True             # 默认 True：所有平台强制等待手动登录
LOGIN_TIMEOUT_SECONDS = 300    # 每平台最多等 5 分钟
```

关闭后仅对检测到登录墙的平台暂停：

```python
FORCE_LOGIN = False            # 仅检测到登录墙的平台才等待
```

### 登录检测流程（4 层级联）

```
handler.before_browse()
    └── wait_for_login()
            │
            ├── 1. 特定选择器检测（9 个平台有专用检测器）
            │      logged_in 选择器可见 → 已登录，继续
            │      login_wall 选择器可见 → 需要登录
            │
            ├── 2. FORCE_LOGIN=True？→ 无论有无检测器，都要求登录
            │
            ├── 3. 跳转到登录页 → 终端打印提示
            │      "MANUAL LOGIN REQUIRED — 请在浏览器窗口中手动登录"
            │
            └── 4. 每 3 秒轮询，4 种策略检测完成：
                   ├── logged_in 选择器出现
                   ├── login_wall 消失
                   ├── URL 不再含 "login"/"signin"（通用兜底）
                   └── 页面内容分析（无登录关键词 + 内容丰富）
                   
                   完成后自动恢复自动化浏览
```

**已配置专用检测器的平台（9/17）**：

| 平台 | 登录墙检测 | 已登录检测 |
|------|-----------|-----------|
| Twitter | login button | `article[data-testid="tweet"]` |
| LinkedIn | login form | `div.global-nav__me` |
| Amazon | signin tooltip | account list span |
| eBay | signin link | user menu |
| AliExpress | login modal | user-account div |
| Spotify | login button | user widget |
| Shopee | login popup | navbar username |
| Expedia | signin button | account menu |
| Agoda | signin link | user avatar |

其余 8 个平台（Pinterest, Tumblr, Reddit, Quora, Twitch, Walmart, Booking, YouTube）在 `FORCE_LOGIN=True` 时使用 URL 跳转 + 页面内容策略通用检测。

---

## 配置说明

### 频控参数 (`config/settings.py`)

```python
GLOBAL_DAILY_ACTION_CAP = 500       # 所有账号合计每天最多 500 次操作
ACTIVE_HOURS_START = 8              # 早上 8 点开始
ACTIVE_HOURS_END = 23               # 晚上 11 点结束

FORCE_LOGIN = True                  # 所有平台强制等待手动登录
LOGIN_TIMEOUT_SECONDS = 300         # 登录等待超时（秒）

# 每个平台可独立设置（示例）：
PlatformConfig(daily_like_limit=30, daily_comment_limit=8, ...)
```

### 代理设置

```python
PROXY_SERVER = "http://user:pass@proxy.example.com:8080"
```

### 新增平台

1. 在 `config/settings.py` 的 `PlatformName` 类型中添加
2. 在 `PLATFORMS` 字典中添加 `PlatformConfig` 条目
3. 在 `platform_category()` 映射中添加
4. （可选）创建 `platforms/{key}.py` 处理器

---

## 运行证据

每次运行自动生成：

- `evidence/screenshots/{画像}/{平台}/` — 每次会话的前/后截图
- `evidence/summary.json` — 每个组合的状态、耗时、搜索词等完整记录

---

## 常见问题

**如何证明浏览行为被平台记录了？**  即使未登录，平台也会通过 cookie 追踪你的页面浏览、搜索关键词、滚动深度和停留时间。框架将这些 cookie 保存在 `profiles/` 目录，多次重复会话会建立持久的匿名用户画像。

**无头模式能用吗？** 能用但反检测效果减弱。默认 `headless=False`（可见浏览器窗口），以保证最佳的隐身效果。

**如何登录？** 首次运行时框架会打开可见浏览器窗口，手动扫码或输入密码登录；关闭时框架自动保存登录态。下次运行自动恢复。

**会被封号吗？** 存在风险。降低风险的策略：使用有头模式、遵守每日上限、操作分散在不同时段、不同账号使用不同指纹、不要 24 小时不间断运行。本项目仅用于课程实验和学习目的。
