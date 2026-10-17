# i18n — agentmemory 管理界面简体中文汉化工具链

原理：**不改原代码**，在原版 `dist/viewer/index.html` 末尾注入一段 DOM 翻译扫描器
（`window.__amZhWalker`），运行时对文本节点/属性做整句精确匹配 + 三层回退
（数字归一化、正则模板、时长/日期格式化），并用 MutationObserver 覆盖动态渲染。

## 文件

| 文件 | 作用 |
|---|---|
| `ours.html` | 0.9.30 原版界面（构建输入，取自 npm 包 `dist/viewer/index.html`） |
| `pairs-pr.json` | 社区 PR 词典（约 316 条，含原样占位条目） |
| `supplement.tsv` ~ `supplement6.tsv` | 补译词条（约 1000+ 条） |
| `dyn3.tsv` | 数字占位动态词条（`N` 归一成 `\u0001` 后匹配） |
| `patterns.json` | 正则模板词条（非数字动态串） |
| `build.py` | 合并词典 → 注入扫描器 → 输出 `viewer-zh.html` |
| `scan2.py` | 宽容扫描器：升级新版本后查漏未汉化文案 |
| `inventory.py` | 文案盘点（需要 PR 版界面 `theirs.html`，未随仓库分发） |

合并规则：**补译词条优先**于社区词典里的原样占位条目（`en → en`）。

## 构建

```bash
python3 build.py                                   # 输出 viewer-zh.html
cp viewer-zh.html ../deploy/fnos/viewer-i18n-zh.html   # 部署目录里的是成品
```

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
