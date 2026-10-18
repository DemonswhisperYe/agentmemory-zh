// 中文翻译层自检：node i18n/test-walker.js
// 用 walker-check.js 在假 DOM 里跑 trText，覆盖截图残留句、幂等性和技术标识符不被误译
const fs = require("fs");
const path = require("path");
const dir = __dirname;

const hook = 'else { if (window.__amZhTest) { window.__tr = trText; window.__node = trNode; window.__el = trEl; } else boot(); }';
const src = fs.readFileSync(path.join(dir, "walker-check.js"), "utf8").replace("else boot();", hook);
fs.writeFileSync("/tmp/walk-test.js", src);

global.window = { __amZhTest: 1 };
global.document = { readyState: "complete", documentElement: {}, addEventListener() {} };
global.localStorage = { getItem: () => "zh-CN" };
global.navigator = { languages: ["zh-CN"], language: "zh-CN" };
global.location = { search: "" };
require("/tmp/walk-test.js");
const tr = window.__tr;
const trNode = window.__node;

// 造一个带祖先链的文本节点，用来验证代码/数据容器里的内容不被翻译。
// 祖先可写成 "div"、"div.mem-detail-content" 或 "#mem-edit-text"
function trInDom(text, ancestors) {
  const node = { nodeType: 3, nodeValue: text };
  let parent = null;
  for (let i = ancestors.length - 1; i >= 0; i--) {
    const spec = ancestors[i];
    const [tag, cls] = spec.split(".");
    const id = tag.startsWith("#") ? tag.slice(1) : "";
    const el = {
      nodeType: 1,
      nodeName: (id ? "DIV" : tag.toUpperCase()),
      className: cls || "",
      id: id,
      __parent: parent,
      getAttribute: () => null,
      hasAttribute: () => false,
    };
    el.closest = (sel) => {
      const parts = sel.split(",").map((x) => x.trim());
      for (let p = el; p; p = p.__parent) {
        for (const part of parts) {
          if (part.startsWith("#") && p.id === part.slice(1)) return p;
          if (part.startsWith(".") && (" " + p.className + " ").indexOf(" " + part.slice(1) + " ") >= 0) return p;
          if (!part.startsWith(".") && !part.startsWith("#") && p.nodeName === part.toUpperCase()) return p;
        }
      }
      return null;
    };
    parent = el;
  }
  node.parentNode = node.parentElement = parent;
  trNode(node);
  return node.nodeValue;
}

const cases = [
  ["· showing the 500 most connected", "· 仅显示连接最多的 500 个"],
  ["2,392 documents", "2,392 个文档"],
  ["1,515 vectors", "1,515 个向量"],
  ["14 vector changes", "14 条向量变更"],
  ["7,320 nodes · 12,594 edges", "7,320 节点 · 12,594 边"],
  ["not saved since start, unsaved changes since 9m ago", "启动后未保存，自 9分钟前起有未保存更改"],
  ["Snapshot rebuilt 2h ago.", "快照已重建 2小时前。"],
  ["0 records trimmed, 0 ids removed, finished 5d ago. It does not run again.",
   "0 条记录已裁剪，0 个 ID 已移除，完成于 5天前。它不会再次运行。"],
  ["1h ago · tier all", "1小时前 · 层级：全部"],
  ["checked 41 facts and 12 procedures", "检查 41 条事实和 12 个程序"],
  ["4 new procedures from 13 patterns", "4 条新流程来自 13 条模式"],
  ["5 new insights", "5 条新洞察"],
  ["Run consolidation now", "立即运行整合"],
  ["configured", "已配置"],
  ["event loop 0.1 ms behind", "事件循环 0.1 毫秒滞后"],   // 页面小写，词条大写
  ["Event loop 0.1 ms behind", "事件循环 0.1 毫秒滞后"],
  ["Running…", "运行中…"],
];

// 必须原样保留：模型名、环境变量、工具名
const keep = ["OpenAI", "AGENTMEMORY_LLM_TIMEOUT_MS", "memory_save", "ANTHROPIC_API_KEY",
              "should_bump_version_check", "uvicorn", "SELECT * FROM actions;"];

let fail = 0;
for (const [en, want] of cases) {
  const got = tr(en);
  const ok = got === want;
  if (!ok) fail++;
  console.log((ok ? "PASS " : "FAIL ") + JSON.stringify(en) + " -> " + JSON.stringify(got) + (ok ? "" : "  期望 " + JSON.stringify(want)));
}
for (const en of keep) {
  const got = tr(en);
  const ok = got === en;
  if (!ok) fail++;
  console.log((ok ? "PASS " : "FAIL ") + "保留 " + JSON.stringify(en) + (ok ? "" : " -> " + JSON.stringify(got)));
}

// 幂等性：同一节点被 MutationObserver 二次处理时不得继续变形
const extra = ["2,392 documents", "1h ago · tier all", "Run consolidation now",
               "0 records trimmed, 0 ids removed, finished 5d ago. It does not run again.",
               "failed: OpenAI API request timed out after 60000ms"];
for (const en of extra) {
  const once = tr(en), twice = tr(once);
  const ok = once === twice;
  if (!ok) fail++;
  console.log((ok ? "PASS " : "FAIL ") + "幂等 " + JSON.stringify(once) + (ok ? "" : " -> " + JSON.stringify(twice)));
}

// 代码/原始数据：pre、code、textarea 内一律原样保留（工具入参、JSON、观测原文、接口路径）
const dataCases = [
  ['{"status":"ok","files":3,"rows":120}', ["pre", "details", "body", "html"]],
  ['SELECT * FROM files WHERE id = 5', ["pre", "div", "body", "html"]],
  ['curl -X POST http://10.0.0.5:3111/agentmemory/remember', ["pre", "div", "body", "html"]],
  ['AGENTMEMORY_SECRET', ["code", "p", "body", "html"]],
  ['git log --oneline -5 --stat files', ["textarea", "body", "html"]],
  // 代理自己产生的数据：拼上后缀后带数字，以前会被片段替换误伤
  ['Agent saved 5 memories and 2 lessons', ["div.mem-detail-content", "div", "body"]],
  ['Cross-system structured memory batch import via REST (8 steps)', ["div.mem-detail-content", "div", "body"]],
];
// 数据容器内的同类文本必须原样保留
const dataClasses = ["mem-detail-content", "mem-excerpt", "mem-diff", "feed-text",
  "ses-summary", "session-preview", "src-text", "obs-narrative", "obs-prompt",
  "gd-name", "gs-name", "tt-name", "mem-chip", "mem-head", "layer-preview",
  "obs-item-title", "obs-item-sub", "ver-text", "session-project", "tag",
  "kind-tag", "replay-event-label"];
for (const cls of dataClasses) {
  const text = "Fixed 3 bugs in the save path and moved 2 files";
  const got = trInDom(text, ["." + cls, "div", "body", "html"]);
  if (got !== text) { fail++; console.log("FAIL 数据容器 ." + cls + " -> " + JSON.stringify(got)); continue; }
  const ok = got === text;
  if (!ok) fail++;
  console.log((ok ? "PASS " : "FAIL ") + "数据容器 ." + cls + (ok ? "" : " -> " + JSON.stringify(got)));
}
for (const [en, anc] of dataCases) {
  const got = trInDom(en, anc);
  const ok = got === en;
  if (!ok) fail++;
  console.log((ok ? "PASS " : "FAIL ") + "不译代码 " + JSON.stringify(en) + (ok ? "" : " -> " + JSON.stringify(got)));
}
// 属性（title/aria-label）同样要守数据区：数据元素的属性只做整串精确匹配
function attrInDom(value, ancestors) {
  const attrs = { title: value };
  const node = {
    nodeType: 1, className: "", getAttribute: (k) => attrs[k],
    hasAttribute: (k) => k in attrs, setAttribute: (k, v) => { attrs[k] = v; },
  };
  let parent = null;
  for (let i = ancestors.length - 1; i >= 0; i--) {
    const [tag, cls] = ancestors[i].split(".");
    const el = { nodeType: 1, nodeName: tag.toUpperCase(), className: cls || "", __parent: parent };
    el.closest = (sel) => closestOf(el, sel);
    parent = el;
  }
  node.closest = (sel) => closestOf(node, sel);
  node.__parent = parent;
  window.__el(node);
  return attrs.title;
}
function closestOf(start, sel) {
  const parts = sel.split(",").map((x) => x.trim());
  for (let p = start; p; p = p.__parent) {
    for (const part of parts) {
      if (part.startsWith(".") && (" " + p.className + " ").indexOf(" " + part.slice(1) + " ") >= 0) return p;
      if (!part.startsWith(".") && !part.startsWith("#") && p.nodeName === part.toUpperCase()) return p;
    }
  }
  return null;
}
// 非 feed 的数据容器不做标签前缀翻译（避免改到数据开头）
{
  const got = trInDom("Saved a memory: Fixed 3 bugs and moved 2 files", ["div.mem-detail-content", "div", "body"]);
  const ok = got === "Saved a memory: Fixed 3 bugs and moved 2 files";
  if (!ok) fail++;
  console.log((ok ? "PASS " : "FAIL ") + "非 feed 数据区不改标签前缀" + (ok ? "" : " -> " + JSON.stringify(got)));
}
for (const [val, anc, want, label] of [
  ["Fixed 3 bugs and moved 2 files", [".mem-chip", "div", "body"], "Fixed 3 bugs and moved 2 files", "数据属性不译"],
  ["Delete", [".mem-chip", "div", "body"], "删除", "数据区属性标签仍译"],
  ["Event loop 0.1 ms behind", ["span", "div", "body"], "事件循环 0.1 毫秒滞后", "普通属性译"],
  ["Content-Type", ["pre", "div", "body"], "Content-Type", "代码属性不译"],
]) {
  const got = attrInDom(val, anc);
  const ok = got === want;
  if (!ok) fail++;
  console.log((ok ? "PASS " : "FAIL ") + label + " " + JSON.stringify(val) + (ok ? "" : " -> " + JSON.stringify(got)));
}

// 数据容器里“整串等于 UI 词条”的标签仍要翻译（feed 里的动作名）
for (const [en, zh] of [["Saved a memory", "保存了记忆"], ["Recalled lessons", "召回了经验"],
                        ["Ran consolidation", "运行了整合"],
                        // "标签: 数据" 只译标签，数据原样（仅 feed）
                        ["Processed observations: 239 observations", "已处理观测：239 observations"]]) {
  const got = trInDom(en, ["span.feed-text", "div", "body", "html"]);
  const ok = got === zh;
  if (!ok) fail++;
  console.log((ok ? "PASS " : "FAIL ") + "数据区标签 " + JSON.stringify(en) + " -> " + JSON.stringify(got));
}

// 同样的文本在普通元素里仍要翻译，证明保护没有过度
{
  const got = trInDom("configured", ["span", "div", "body", "html"]);
  const ok = got === "已配置";
  if (!ok) fail++;
  console.log((ok ? "PASS " : "FAIL ") + "普通节点仍译 " + JSON.stringify(got));
}

console.log(fail === 0 ? "\n全部通过" : "\n失败 " + fail + " 项");
process.exit(fail === 0 ? 0 : 1);
