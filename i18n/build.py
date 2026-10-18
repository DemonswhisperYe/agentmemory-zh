#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成中文界面：PR 词典 + 补译词库 → DOM 翻译扫描器注入 0.9.30 界面"""
import glob, json, os, re

# 以脚本所在目录为基准，克隆到别处也能直接跑
BASE = os.path.dirname(os.path.abspath(__file__)) + "/"

# 1. 合并词条（PR 优先，补译补缺；后续文件的同词条不覆盖已有译文）
pairs = dict(json.load(open(BASE + "pairs-pr.json", encoding="utf-8")))
pr_n = len(pairs)
applied = 0
conflicts = []
# 补译文件按自然序号排序（supplement.tsv, supplement2.tsv, ... supplement15.tsv），
# 顺序决定同词条谁先胜出，因此不能直接字典序排（那样 supplement10 会排在 supplement9 前）
files = sorted(glob.glob(BASE + "supplement*.tsv"),
               key=lambda f: int(re.sub(r"\D", "", os.path.basename(f)) or 1))
for path in files:
    for ln in open(path, encoding="utf-8"):
        ln = ln.rstrip("\n")
        if not ln or "\t" not in ln:
            continue
        en, zh = ln.split("\t", 1)
        en, zh = en.strip(), zh.strip()
        if not en or not zh:
            continue
        if en not in pairs or pairs[en] == en:
            pairs[en] = zh
            applied += 1
        elif pairs[en] != zh:
            conflicts.append((en, os.path.basename(path), pairs[en], zh))
print("词条合计: %d（PR %d + 补译生效 %d）" % (len(pairs), pr_n, applied))
if conflicts:
    print("⚠ 同词条译文冲突 %d 条（保留先出现者，后续改动不会生效）:" % len(conflicts))
    for en, f, keep, drop in conflicts[:5]:
        print("   %r 保留 %r，忽略 %s 的 %r" % (en, keep, f, drop))
    if len(conflicts) > 5:
        print("   ……其余 %d 条" % (len(conflicts) - 5))

# 1b. 动态文案：数字占位键 + 正则模板
pairs_num = {}
for ln in open(BASE + "dyn3.tsv", encoding="utf-8"):
    ln = ln.rstrip("\n")
    if "\t" in ln:
        en, zh = ln.split("\t", 1)
        if en.strip() and zh.strip():
            pairs_num[en.strip()] = zh.strip()
patterns = json.load(open(BASE + "patterns.json", encoding="utf-8"))
print("动态词条: %d + 正则模板 %d" % (len(pairs_num), len(patterns)))

# 1c. 片段级词条：数字/分隔符拼接句里夹着的词条（如 "2,392 documents"、"· tier all"）。
# 只收长度 ≥4、含小写字母、非全大写标识符的词条；替换时再校验两侧词边界。
frag = sorted([k for k in pairs
               if len(k) >= 4 and re.search(r"[a-z]", k)
               and not re.fullmatch(r"[A-Z0-9 .,:_()/~+-]+", k)],
              key=len, reverse=True)
frag_src = "|".join(re.escape(k) for k in frag)
print("片段级词条: %d 条" % len(frag))

# 2. 生成翻译扫描器脚本块
pairs_json = json.dumps(pairs, ensure_ascii=False, separators=(",", ":"))
walker = '''
<script nonce="__AGENTMEMORY_VIEWER_NONCE__">
(function () {
  if (window.__amZhWalker) return; window.__amZhWalker = 1;
  var PAIRS = __PAIRS__;
  var PAIRS_NUM = __PAIRS_NUM__;
  var PATTERNS = __PATTERNS__;
  for (var pi = 0; pi < PATTERNS.length; pi++) PATTERNS[pi][0] = new RegExp(PATTERNS[pi][0]);
  var PH = "\\u0001";
  var PAIRS_LC = {};
  for (var k in PAIRS) { if (PAIRS_LC[k.toLowerCase()] === undefined) PAIRS_LC[k.toLowerCase()] = PAIRS[k]; }
  function lookupNum(v) {
    var nums = [];
    var nk = v.replace(/\d[\d,.]*/g, function (m) { nums.push(m); return PH; });
    if (PAIRS_NUM[nk] === undefined) return null;
    var i = 0;
    return PAIRS_NUM[nk].replace(/\u0001/g, function () { return nums[i++] || ""; });
  }
  function lookupPattern(v) {
    for (var i = 0; i < PATTERNS.length; i++) {
      if (PATTERNS[i][0].test(v)) return v.replace(PATTERNS[i][0], PATTERNS[i][1]);
    }
    return null;
  }
  var loc = "en";
  try {
    var q = new URLSearchParams(location.search).get("lang");
    var s = localStorage.getItem("agentmemory-locale");
    loc = q || s || (navigator.languages && navigator.languages[0]) || navigator.language || "en";
  } catch (e) {}
  if (!/^zh/i.test(loc)) return;
  try { document.documentElement.lang = "zh-CN"; } catch (e) {}
  var WD = { Sun: "周日", Mon: "周一", Tue: "周二", Wed: "周三", Thu: "周四", Fri: "周五", Sat: "周六" };
  var MO = { Jan: "1月", Feb: "2月", Mar: "3月", Apr: "4月", May: "5月", Jun: "6月", Jul: "7月", Aug: "8月", Sep: "9月", Oct: "10月", Nov: "11月", Dec: "12月" };
  function trDate(s) {
    var m = s.match(/^([A-Z][a-z]{2}), ([A-Z][a-z]{2}) (\d{1,2}), (\d{4})$/);
    return (m && WD[m[1]] && MO[m[2]]) ? (m[4] + "年" + MO[m[2]] + m[3] + "日 " + WD[m[1]]) : s;
  }
  function trDur(s) {
    return s.replace(/(\d+) seconds?/g, "$1 秒").replace(/(\d+) minutes?/g, "$1 分钟").replace(/(\d+) hours?/g, "$1 小时")
      .replace(/(\d+) sec\\b/g, "$1 秒").replace(/(\d+) min\\b/g, "$1 分钟").replace(/(\d+) hrs?\\b/g, "$1 小时")
      .replace(/(\d+) days?\\b/g, "$1 天").replace(/(\d+) weeks?\\b/g, "$1 周")
      .replace(/(\d+) months?\\b/g, "$1 个月").replace(/(\d+) years?\\b/g, "$1 年")
      .replace(/(\d+)\s*(mo|y|w|d|h|m)\\b\s*(?:ago|前)/g, function (_, n, u) {
        var U = { mo: "个月", y: "年", w: "周", d: "天", h: "小时", m: "分钟" };
        return n + U[u] + "前";
      })
      .replace(/\\bjust now\\b/g, "刚刚").replace(/\\bago\\b/g, "前").replace(/\s+前/g, "前").replace(/\s+失败/g, "失败");
  }
  // 拼接句里残留的英文标点：仅在中文字符后改，不影响纯英文串
  function fixPunct(s) {
    if (!/[\u4e00-\u9fa5]/.test(s)) return s;
    return s.replace(/([\u4e00-\u9fa5])\s*,\s*/g, "$1，").replace(/，\s+/g, "，")
      .replace(/([\u4e00-\u9fa5])[ \t]+(?=[\u4e00-\u9fa5])/g, "$1")   // 中文之间不留空格
      .replace(/([\u4e00-\u9fa5])\.(\s|$)/g, "$1。$2");
  }
  function fin(s) { return fixPunct(trDur(trDate(s))); }
  // 组合句拆分："动词: 数量短语" 等拼接文本，两侧都能独立译出才拼回（否则整体保留）
  // 第三项分隔符前后相同：两侧都能独立译出时保留 " · " 原样拼接（不是恒等映射）
  var SEPS = [[": ", "："], [", ", "，" ], [" · ", " · "]];
  function compose(v) {
    if (v.length > 160) return null;
    for (var i = 0; i < SEPS.length; i++) {
      var sep = SEPS[i][0], out = SEPS[i][1];
      var p = v.indexOf(sep);
      if (p > 0 && p < v.length - sep.length) {
        var a = v.slice(0, p).trim(), b = v.slice(p + sep.length).trim();
        if (!a || !b) continue;
        var ta = trCore(a, true), tb = trCore(b, true);
        if (ta !== a && tb !== b) return ta + out + tb;
      }
    }
    return null;
  }
  // raw=true 时不做时长/日期替换：拼接句要先按词条和模板拆完，最后才动 ago/日期，
  // 否则 "not saved since start, unsaved changes since 9m ago" 会被提前改成半句中文，
  // 后续再无法按 ", " 拆分翻译。
  // i：页面里大小写不统一（"event loop" / "Event loop"），不区分大小写才能命中
  var FRAG_RE = new RegExp(__FRAG_SRC__, "gi");
  function trFrag(v) {
    if (!/\d/.test(v) || v.length > 240) return null;
    var hit = false;
    var out = v.replace(FRAG_RE, function (m, off) {
      var b = off === 0 ? "" : v.charAt(off - 1);
      var a = v.charAt(off + m.length);
      // 片段自带英文字母的一侧才校验词边界，避免替换单词内部片段；
      // 以标点开头的长词条（如 ". It does not run again."）仍可命中
      if (/[A-Za-z]/.test(m.charAt(0)) && /[A-Za-z]/.test(b)) return m;
      if (/[A-Za-z]/.test(m.charAt(m.length - 1)) && /[A-Za-z]/.test(a)) return m;
      var zh = PAIRS[m] !== undefined ? PAIRS[m] : PAIRS_LC[m.toLowerCase()];
      if (zh === undefined) return m;
      hit = true;
      return zh;
    });
    return hit ? out : null;
  }
  function trCore(v, raw) {
    var done = raw ? function (s) { return s; } : fin;
    var key = v.replace(/\s+/g, " ").trim();
    function lookup(k) {
      if (PAIRS[k] !== undefined) return PAIRS[k];
      // 以冒号结尾的标签词条常带尾随空格（"origin: " + 值），trim 后要能回查
      if (PAIRS[k + " "] !== undefined) return PAIRS[k + " "];
      if (PAIRS_LC[k.toLowerCase()] !== undefined) return PAIRS_LC[k.toLowerCase()];
      return null;
    }
    var zh = lookup(key);
    if (zh !== null) return done(v.replace(key, zh));
    var nz = lookupNum(key);
    if (nz !== null) return done(v.indexOf(key) >= 0 ? v.replace(key, nz) : nz);
    var pz = lookupPattern(key);
    if (pz !== null) return done(v.indexOf(key) >= 0 ? v.replace(key, pz) : pz);
    var fd = done(key);
    if (fd !== key) return v.indexOf(key) >= 0 ? v.replace(key, fd) : fd;
    var k = key, suffix = "", lead = "";
    var m1 = k.match(/^(.*?)(\\s*(?:→|…|\\.\\.\\.)\\s*)$/);
    if (m1) { k = m1[1]; suffix = m1[2]; }
    var m2 = k.match(/^(.*?)\\s*(\\(\\d+\\))$/);
    if (m2) { k = m2[1]; suffix = m2[2] + suffix; }
    var m3 = k.match(/^([\\s\\d.,%+~#|/()·-]+)(.+)$/);
    if (m3) { lead = m3[1]; k = m3[2].trim(); }
    if (!k) return v;
    zh = lookup(k);
    if (zh === null) zh = lookupNum(k);
    if (zh === null) return v;
    if (v.indexOf(k) >= 0) return done(v.replace(k, zh));
    return lead + done(zh) + suffix;
  }
  function trOnce(v) {
    var r = trCore(v, true);
    if (r !== v) return fin(r);
    // 片段级替换优先于拼接拆分：拼接句里任一半没收录时，片段替换仍能译出其余部分
    var fz = trFrag(v);
    if (fz !== null) return fin(fz);
    var key = v.replace(/\s+/g, " ").trim();
    var cz = compose(key);
    if (cz !== null) return fin(v.indexOf(key) >= 0 ? v.replace(key, cz) : cz);
    return fin(v);
  }
  // 数据区专用：整串与词条完全相等才译（"Saved a memory" 译，数据句子不译）
  function trExact(v, allowLabel) {
    var key = v.replace(/\s+/g, " ").trim();
    var zh = PAIRS[key];
    if (zh === undefined) zh = PAIRS[key + " "];
    if (zh === undefined) zh = PAIRS_LC[key.toLowerCase()];
    if (zh !== undefined) return zh;
    // "标签: 数据"（如 "Processed observations: 239 observations"）：只译冒号前的标签，
    // 后面的数据一个字符都不动
    var p = allowLabel ? key.indexOf(": ") : -1;
    if (p > 0 && key.length < 400) {
      var head = key.slice(0, p);
      var hz = PAIRS[head] !== undefined ? PAIRS[head] : PAIRS_LC[head.toLowerCase()];
      if (hz !== undefined) return hz + "：" + key.slice(p + 2);
    }
    return v;
  }
  // 反复套用规则直到稳定（最多 3 轮）：模板译完前半句后，后半句的片段还能再补一轮。
  // 结果缓存：页面实时刷新会反复渲染相同文案，同串直接复用
  var CACHE = Object.create(null), cacheN = 0;
  function trText(v) {
    var cacheable = v.length < 120;
    if (cacheable) { var c = CACHE[v]; if (c !== undefined) return c; }
    var cur = v;
    for (var i = 0; i < 3; i++) {
      var nxt = trOnce(cur);
      if (nxt === cur) break;
      cur = nxt;
      if (!/[A-Za-z]/.test(cur)) break;
    }
    if (cacheable && cacheN < 3000) { CACHE[v] = cur; cacheN++; }
    return cur;
  }
  // 代码区：整段不碰（工具入参、JSON、观测原文）
  var SKIP_SEL = "pre,code,textarea,script,style,kbd,samp,#mem-edit-text";
  // 数据区：只允许“整串精确等于某条 UI 词条”时翻译，其余一律原样。
  // 这样 feed 里的 "Saved a memory" 这类标签仍然是中文，而数据句子不会被片段替换改写。
  var DATA_SEL =
    ".mem-detail-content,.mem-excerpt,.mem-diff,.mem-head,.mem-chip," +
    ".feed-text,.ses-summary,.session-preview,.src-text,.obs-narrative,.obs-prompt," +
    ".gd-name,.gs-name,.tt-name,.layer-preview,.obs-item-title,.obs-item-sub,.ver-text," +
    ".session-project,.ses-id-mini,.entity-link,.tag,.kind-tag,.pf,.pm,.replay-event-label";
  function hit(n, sel) {
    if (!n) return false;
    // 元素自身也要检查（closest 包含自己）；文本节点从父元素开始
    var start = n.nodeType === 1 ? n : (n.parentElement || n.parentNode);
    return start && start.closest ? !!start.closest(sel) : false;
  }
  function inData(n) { return hit(n, DATA_SEL); }
  function inCode(n) { return hit(n, SKIP_SEL); }
  // 只有 feed 会出现 "标签: 数据" 结构（AUDIT_VERBS + 数据），据此放开标签前缀翻译
  var FEED_SEL = ".feed-text";
  function inFeed(n) { return hit(n, FEED_SEL); }
  function trNode(n) {
    var v = n.nodeValue;
    if (!v || !v.trim() || !/[A-Za-z]/.test(v)) return;
    if (n.__zhOut === v) return;
    if (inCode(n)) return;
    var out = inData(n) ? trExact(v, inFeed(n)) : trText(v);
    if (out !== v) { n.__zhOut = out; n.nodeValue = out; }
  }
  var ATTRS = ["title", "aria-label", "placeholder", "alt", "data-title", "data-label", "label"];
  function trEl(el) {
    if (!el || el.nodeType !== 1 || !el.getAttribute) return;
    if (inCode(el)) return;
    for (var i = 0; i < ATTRS.length; i++) {
      var a = ATTRS[i];
      if (el.hasAttribute(a)) {
        var v = el.getAttribute(a);
        if (v && /[A-Za-z]/.test(v)) {
          if (el["__zh_" + a] === v) continue;
          var out = inData(el) ? trExact(v) : trText(v);
          if (out !== v) { el["__zh_" + a] = out; el.setAttribute(a, out); }
        }
      }
    }
  }
  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { trNode(root); return; }
    if (root.nodeType === 1) {
      trEl(root);
      var we = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
      var e; while ((e = we.nextNode())) trEl(e);
      var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      var n; while ((n = w.nextNode())) trNode(n);
    }
  }
  function boot() {
    walk(document.documentElement);
    var mo = new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        var m = muts[i];
        if (m.type === "characterData") trNode(m.target);
        else if (m.type === "attributes") trEl(m.target);
        else { for (var j = 0; j < m.addedNodes.length; j++) walk(m.addedNodes[j]); }
      }
    });
    mo.observe(document.documentElement, {
      subtree: true, childList: true, characterData: true,
      attributes: true, attributeFilter: ATTRS
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
</script>
'''
walker = walker.replace("__PAIRS__", pairs_json)
walker = walker.replace("__PAIRS_NUM__", json.dumps(pairs_num, ensure_ascii=False, separators=(",", ":")))
walker = walker.replace("__PATTERNS__", json.dumps(patterns, ensure_ascii=False, separators=(",", ":")))
walker = walker.replace("__FRAG_SRC__", json.dumps(frag_src or "(?!)"))

# 3. 注入 0.9.30 界面（不动原有内容，仅在 </body> 前追加）
src = open(BASE + "ours.html", encoding="utf-8").read()
assert "</body>" in src
out = src.replace("</body>", walker + "\n</body>", 1)
open(BASE + "viewer-zh.html", "w", encoding="utf-8").write(out)

# 4. 单独落盘脚本块供语法检查
js = re.search(r"<script nonce=\"__AGENTMEMORY_VIEWER_NONCE__\">\n\(function \(\) \{\n  if \(window\.__amZhWalker\)(.*?)</script>", out, re.S).group(1)
open(BASE + "walker-check.js", "w", encoding="utf-8").write("(function () {\n  if (window.__amZhWalker)" + js.replace("</script>", ""))

print("输出: viewer-zh.html（%d 行）" % out.count("\n"))
