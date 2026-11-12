# Episode v1 数据契约

`episode.json` 是 AI 创作的输入；`timeline.json` 是程序生成的时间轴，禁止手工估计并填写时间字段。

顶层字段：

| 字段 | 规则 |
|---|---|
| version | 固定为 1 |
| ip, title, title_zh | IP 名称、英文标题、中文标题 |
| level | 默认 B1 |
| background | 相对 episode 目录的背景路径 |
| disclosure | 简短的原创同人、AI 配音/插画说明 |
| ending_title | 最长约 42 英文字符，片尾标题 |
| review_terms | 3 个正文 vocab.term 中的字符串 |
| prop | 可省略；当前只支持 lantern |
| characters | ID → 人物配置 |
| lines | 按播放顺序的对白/旁白/选择题 |

人物配置包含 `name`（英文显示名）、`zh`、`voice`（Edge 声线 ID）、`rate`（如 `-4%`）、`pitch`（如 `+0Hz`）、`color`（HEX）。在场角色还需要 `sprite` 和 `side: left/right`；旁白没有立绘。三人使用不同声线。不能用角色 ID 当成真实 TTS voice。

每段必须有 `id`（字母数字下划线短横线）、`speaker`、`en`、`zh`、`stage`（在场角色数组）、`act`（简短章节提示）。`tone` 可取 curious、playful、skeptical、quiet、gentle、warm、mysterious。可选 `vocab: {term,ipa,meaning,note}`；term 必须实际出现于英文对白。`sfx: lyre` 会生成三个很轻的合成拨弦音，同时令 lantern 道具开始上升；其他 IP 不要无意义地套用。

选择段额外字段：`type: choice`、`seconds: 7`、`answer: 0或1`、`options`（恰好两项，字段 en/zh/feedback）。选择问题本身使用 `en/zh`，由旁白读出，选项不朗读。

时间轴程序增加：`audio`、`words`、`speech_duration`、`start`、`audio_start`、`end`。`words` 来自真实 WordBoundary，单位秒，局部相对音频起点。渲染器以 `audio_start+word.start` 高亮。顶层 `duration` 包括片头和片尾。

限制：16:9，固定两名角色左右站位；不支持视频素材立绘、精确口型、多个背景自动切换或多结局。要扩展时先扩展数据契约、渲染器与验证，不要向 JSON 填无效字段后声称生效。
