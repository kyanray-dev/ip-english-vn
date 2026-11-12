# IP English Visual Novel

输入一个 IP，由支持技能、文件执行和图像生成的 AI 宿主完成原创英文短篇、配音、视觉小说视频与交互播放器。

## 从 GitHub 安装

在你的项目根目录运行（私有仓库需要先登录有访问权限的 GitHub 账号）：

```bash
gh repo clone kyanray-dev/ip-english-vn .agents/skills/ip-english-vn
```

随后在支持项目 skills 的 AI 宿主中调用 `ip-english-vn`，输入喜欢的 IP。仓库包含完整 skill、制作程序、字体许可证以及原神样例的素材、配音与时间轴。生成的视频和临时文件不进入 Git 历史。

## 使用 skill

将整个 `ip-english-vn` 文件夹放进宿主的 skills 目录，入口是 `SKILL.md`。Codex 项目可用 `.agents/skills/ip-english-vn/`。不同宿主的技能安装目录不同；ZIP 不会自动安装插件或获得新的模型能力。

调用示例：

> 使用 ip-english-vn，IP：原神。

默认 B1、约 2 分钟、两名角色＋旁白、1080p。AI 负责生成内容及图片，脚本负责配音、同步、渲染和验收。单独运行 Python 不能从一个 IP 名称凭空生成全部故事与插画。

## 复现已完成样片

要求 Python 3.10+、FFmpeg/ffprobe；FFmpeg 双语烧录需 libass。正片的字体已包含，并附字体许可证。

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build.py examples/genshin/episode.json --out deliveries/genshin --bilingual
```

已附该集配音及 WordBoundary 缓存，因此相同文本、声线和语速会复用已有音频。修改对白时才调用在线 TTS。新 IP 的故事与图片由执行 skill 的 AI 制作，不能只改 episode.ip。

## 产物

| 文件 | 用途 |
|---|---|
| episode.mp4 | 英文高亮＋中文词汇卡，内嵌可选中/英字幕轨 |
| episode-bilingual.mp4 | 中文对白已烧录，适合直接观看和上传 |
| index.html | 本地交互播放器：线索选择、反馈、字幕开关、逐句重听 |
| serve.py | 支持 Range 的本地启动服务，运行 `python serve.py` |
| novel-english.txt / novel-bilingual.txt | 英文故事、双语文本 |
| subtitles.en.srt / subtitles.zh.srt | 独立字幕 |
| vocabulary.json | 生词与释义 |
| qa-report.json | 媒体、时长、逐词与结构检查 |

HTML 的选项提供不同反馈后汇合主线；MP4 固定播放正确路线。没有精确口型、动态表情或多结局。此次为 139.62 秒的完整短篇样片，非长篇小说全本。

## 测试

```bash
.venv/bin/python scripts/verify.py examples/genshin/timeline.json --out deliveries/genshin
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

可选浏览器测试另装 `playwright==1.65.1` 并提供 `/usr/bin/chromium`。先运行 `python scripts/serve.py --directory deliveries/genshin --port 8001`，再运行 `python tests/browser_qa.py --out deliveries/genshin`。这些测试验证功能和媒体结构，不等于对配音表演或所有 IP 泛化能力的保证。

## 外部依赖和失败处理

配音使用 edge-tts 7.3.1 提供的在线合成访问方式；第三方服务存在变更风险。已实现 3 次重试、单句缓存、原子写入、真实词时间戳校验。失败不会输出伪成功或静音成片。宿主的 SSL_CERT_FILE / REQUESTS_CA_BUNDLE 受信任根证书设置会被沿用，不关闭 TLS 校验。

插画源文件保留，字体许可证位于 fonts/。参考分析、数据契约、导演规范位于 references/。
