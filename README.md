# IP English Visual Novel

输入喜欢的 IP，制作分角色配音、人物进出场、英文逐词高亮和生词解释的视觉小说视频。**只交付一个 MP4。静态插画使用生图工具，其余制作全部通过代码完成，禁止调用视频生成模型或视频生成 API。**

## 安装与调用

在项目根目录运行（私有仓库需要先登录有访问权限的 GitHub 账号）：

```bash
gh repo clone kyanray-dev/ip-english-vn .agents/skills/ip-english-vn
```

在支持项目 skills、执行代码和生图的 AI 宿主中调用：

> 使用 ip-english-vn，IP：XX。

默认 B1、约 2 分钟、两名角色＋旁白、1080p。AI 负责规划剧情并整理内部数据；代码负责调用 TTS、对齐、逐帧合成、混音和编码。脚本、SDK 或命令行不能调用文生视频、图生视频、一键成片等服务。

支持两套代码绘制的界面：仙侠「青玉宣纸」使用云纹卷轴、玉牌和笔触高亮；「悬疑案卷」使用深色底、红色身份标签、琥珀色线索高亮与右侧语言档案，并配套案件片头、选择题和复习页。两套共用固定英文基线和自动排版，避免单词上下错位。可用 `scene_label` 设置地点与时间，`sprite_height` 保留儿童与成人的身高差。

用户只需输入 IP；内部 `ui_theme` 可设为 `auto`（默认）、`jade-paper` 或 `mystery`。自动模式识别柯南、福尔摩斯及侦探/推理关键词；其余保持青玉宣纸，显式指定优先。新增风格需实现并注册皮肤，不能仅填写一个新名称。详见 [界面规范](references/dialogue-ui.md)。

## 构建

要求 Python 3.10+、FFmpeg/ffprobe。渲染字体与许可证已包含。

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build.py examples/genshin/episode.json --out deliveries/genshin-video
```

唯一交付文件：

```text
deliveries/genshin-video/
└── episode.mp4
```

默认将中文对白绘入画面，并在同一 MP4 中嵌入可选中英字幕轨。需要纯英文对白画面时加 `--no-chinese`，仍只生成一个 `episode.mp4`。旧命令的 `--bilingual` 保留为兼容参数，不会再生成第二个视频。

不要把旧版包含其他附件的目录直接当作输出目录；程序会拒绝混杂输出，避免删除用户文件。新的构建在临时目录完成并通过验证后，才原子替换交付视频。

## 制作方式与内部文件

- 图像工具只制作静态背景和角色立绘。
- Python 调用 TTS 获取分角色语音与真实 WordBoundary；没有视频模型调用。
- Pillow 逐帧绘制人物、动画、字幕、词汇卡和思考题；NumPy 处理声音；FFmpeg 编码为 H.264/AAC。
- 必要的剧本、图片、逐句音频与时间轴可在 episode 目录缓存；临时 WAV、SRT 和验证阶段的视频自动清理。
- 不导出小说、词汇文件、独立字幕、封面、HTML 播放器、工程包、ZIP 或报告。验证信息只打印到终端，最终回复只给视频。

MP4 内的思考题倒计时后自动揭晓，属于固定播放路线。人物为程序化立绘动画，没有精确口型或多结局。随附原神样例缓存可以复用；新 IP 的剧情与图片由执行 skill 的 AI 制作。

## 验证

```bash
.venv/bin/python scripts/verify.py examples/genshin/timeline.json --out deliveries/genshin-video
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

验证涵盖脚本结构、语音有效性、逐词同步、音视频时长、字幕轨和单一视频交付。测试也检查主题自动选择与覆盖、两种风格的片头/对白/选择题/片尾、跨风格基线稳定、长句与词汇边界、多分辨率排版、中文字幕开关、纹理复现及失败时不会替换已有成片。自动检查不等于人工听审或所有 IP 的质量保证。

## 外部依赖

新配音通过 edge-tts 7.3.1 访问在线 TTS；已实现重试、逐句缓存、真实时间戳检查和原子写入。沿用宿主的受信任根证书，不关闭 TLS 校验。外部服务不可用时明确报错，不以静音或视频生成服务替代。

字体许可证在 `fonts/`，内部数据契约与创作规范在 `references/`。
