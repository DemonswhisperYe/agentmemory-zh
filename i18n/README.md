# i18n — agentmemory 管理界面简体中文汉化工具链

> 本目录**只含汉化**。仓库里另有只给自己用的改动（pi 集成本地补丁、飞牛部署），
> 见 [`../LOCAL-PATCHES.md`](../LOCAL-PATCHES.md)，两者不要混看。

原理：**不改原代码**，在原版 `dist/viewer/index.html` 末尾注入一段 DOM 翻译扫描器
（`window.__amZhWalker`），运行时对文本节点/属性逐层尝试：整句精确匹配 → 数字归一化
→ 正则模板 → 片段级替换（句子里夹着的词条）→ 分隔符拼接 → 时长/日期格式化，
并用 MutationObserver 覆盖动态渲染。

## 文件

| 文件 | 作用 |
|---|---|
| `ours.html` | 0.9.30 原版界面（构建输入，取自 npm 包 `dist/viewer/index.html`） |
| `pairs-pr.json` | 社区 PR 词典（约 316 条，含原样占位条目） |
| `supplement.tsv` ~ `supplement16.tsv` | 补译词条（约 1200 条，构建时自动 glob，按序号顺序合并） |
| `dyn3.tsv` | 数字占位动态词条（`N` 归一成 `\u0001` 后匹配） |
| `patterns.json` | 正则模板词条（非数字动态串） |
| `build.py` | 合并词典 → 注入扫描器 → 输出 `viewer-zh.html` |
| `scan2.py` | 宽容扫描器：升级新版本后查漏未汉化文案 |
| `inventory.py` | 文案盘点（需要 PR 版界面 `theirs.html`，未随仓库分发） |
| `test-walker.cjs` | 翻译层自检（68 项断言，`node test-walker.cjs`） |

合并规则：**补译词条优先**于社区词典里的原样占位条目（`en → en`）；同一词条出现在多个
补译文件里时**先出现的生效**，后出现的若译文不同会在构建输出里打印冲突清单（防止改了没反应）。

## 数据保护（重要）

代理自己产生的内容**不能被翻译**，否则等于篡改数据。扫描器分两级：

| 级别 | 选择器 | 行为 |
|---|---|---|
| 代码区 | `pre, code, textarea, script, style, kbd, samp, #mem-edit-text` | 整段不碰（工具入参、JSON、观测原文） |
| 数据区 | `.mem-detail-content, .mem-excerpt, .mem-diff, .mem-head, .mem-chip, .feed-text, .ses-summary, .session-preview, .src-text, .obs-narrative, .obs-prompt, .obs-item-title, .obs-item-sub, .gd-name, .gs-name, .tt-name, .layer-preview, .ver-text, .session-project, .ses-id-mini, .entity-link, .tag, .kind-tag, .pf, .pm, .replay-event-label` | 只允许**整串等于某条 UI 词条**时翻译（`Saved a memory` 译，`Fixed 3 bugs and moved 2 files` 不译）；`.feed-text` 额外允许 `标签: 数据` 的前缀翻译，数据部分原样 |

界面升级后 class 名可能变化，**必须重新核对这两张选择器表**，否则数据会被误译。

## 构建

```bash
python3 build.py                                   # 输出 viewer-zh.html
node test-walker.cjs                               # 跑自检（改动翻译层后必跑）
cp viewer-zh.html ../deploy/fnos/viewer-i18n-zh.html   # 部署目录里的是成品
```

校验成品与线上是否一致：容器内 `md5sum .../dist/viewer/index.html` 应与
`deploy/fnos/viewer-i18n-zh.html` 相同（服务端会替换 nonce 与版本占位符，HTTP 取回的
页面需归一化后再比）。

## 升级新版本

1. 从新版 npm 包提取 `dist/viewer/index.html` 覆盖 `ours.html`；
2. `python3 scan2.py` 生成未汉化候选清单（宽容匹配，含数字/模板/超长句）；
3. 人工审一遍候选（数据正文、路径、ID、命令、URL 保留英文），补进 `supplement*.tsv`
   或 `dyn3.tsv`（数字占位）/ `patterns.json`（正则）；
4. `python3 build.py`，用无头浏览器逐页签复扫验证。

## 翻译取舍

- 保留英文：数据内容（记忆/观测正文、图谱实体名）、文件路径、ID、命令、环境变量名、
  版本号、品牌名、URL；
- 技术值（如 `pending`/`done` 等状态值）在叙述句里保留原文，与界面徽标一致；
- 星期/月份跟随浏览器语言，顶栏日期已强制中文。

已知边界：词条是整句精确匹配，被内联 help 图标切碎的句子按**碎片**各存一条；
带变量的句子走数字占位或正则模板。若新版本出现第三类拼接形态，需扩展扫描器回退层。
