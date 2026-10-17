#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成中文界面：PR 词典 + 补译词库 → DOM 翻译扫描器注入 0.9.30 界面"""
import json, os, re

BASE = os.path.dirname(os.path.abspath(__file__)) + os.sep

# 1. 合并词条（PR 优先，补译补缺）
pairs = dict(json.load(open(BASE + "pairs-pr.json", encoding="utf-8")))
added = 0
for name in ("supplement.tsv", "supplement2.tsv", "supplement3.tsv", "supplement4.tsv", "supplement5.tsv", "supplement6.tsv"):
    for ln in open(BASE + name, encoding="utf-8"):
        ln = ln.rstrip("\n")
        if not ln or "\t" not in ln:
            continue
        en, zh = ln.split("\t", 1)
        en, zh = en.strip(), zh.strip()
        if en and zh and (en not in pairs or pairs[en] == en):
            pairs[en] = zh
            added += 1
print("词条合计: %d（PR + 补译 %d）" % (len(pairs), added))

# 1b. 动态文案：数字占位键 + 正则模板
PH = "\u0001"
pairs_num = {}
for ln in open(BASE + "dyn3.tsv", encoding="utf-8"):
    ln = ln.rstrip("\n")
    if "\t" in ln:
        en, zh = ln.split("\t", 1)
        if en.strip() and zh.strip():
            pairs_num[en.strip()] = zh.strip()
patterns = json.load(open(BASE + "patterns.json", encoding="utf-8"))
print("动态词条: %d + 正则模板 %d" % (len(pairs_num), len(patterns)))

# 2. 生成翻译扫描器脚本块
pairs_json = json.dumps(pairs, ensure_ascii=False, separators=(",", ":"))
walker = '''
<script nonce="__AGENTMEMORY_VIEWER_NONCE__">
(function () {
  if (window.__amZhWalker) return; window.__amZhWalker = 1;
  var PAIRS = __PAIRS__;
  var PAIRS_NUM = __PAIRS_NUM__;
  var PATTERNS = __PATTERNS__;
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
      if (new RegExp(PATTERNS[i][0]).test(v)) return v.replace(new RegExp(PATTERNS[i][0]), PATTERNS[i][1]);
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
    return s.replace(/(\d+) seconds?/g, "$1 秒").replace(/(\d+) minutes?/g, "$1 分钟").replace(/(\d+) hours?/g, "$1 小时");
  }
  function fin(s) { return trDur(trDate(s)); }
  function trText(v) {
    var key = v.replace(/\s+/g, " ").trim();
    function lookup(k) {
      if (PAIRS[k] !== undefined) return PAIRS[k];
      if (PAIRS_LC[k.toLowerCase()] !== undefined) return PAIRS_LC[k.toLowerCase()];
      return null;
    }
    var zh = lookup(key);
    if (zh !== null) return fin(v.replace(key, zh));
    var nz = lookupNum(key);
    if (nz !== null) return fin(v.indexOf(key) >= 0 ? v.replace(key, nz) : nz);
    var pz = lookupPattern(key);
    if (pz !== null) return fin(v.indexOf(key) >= 0 ? v.replace(key, pz) : pz);
    var fd = fin(key);
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
    if (v.indexOf(k) >= 0) return fin(v.replace(k, zh));
    return lead + fin(zh) + suffix;
  }
  function trNode(n) {
    var v = n.nodeValue;
    if (!v || !v.trim() || !/[A-Za-z]{2}/.test(v)) return;
    var p = n.parentNode;
    if (p && p.nodeName && (p.nodeName === "SCRIPT" || p.nodeName === "STYLE")) return;
    var out = trText(v);
    if (out !== v) n.nodeValue = out;
  }
  var ATTRS = ["title", "aria-label", "placeholder", "alt", "data-title", "data-label"];
  function trEl(el) {
    if (!el || el.nodeType !== 1 || !el.getAttribute) return;
    for (var i = 0; i < ATTRS.length; i++) {
      var a = ATTRS[i];
      if (el.hasAttribute(a)) {
        var v = el.getAttribute(a);
        if (v && /[A-Za-z]{2}/.test(v)) {
          var out = trText(v);
          if (out !== v) el.setAttribute(a, out);
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

# 3. 注入 0.9.30 界面（不动原有内容，仅在 </body> 前追加）
src = open(BASE + "ours.html", encoding="utf-8").read()
assert "</body>" in src
out = src.replace("</body>", walker + "\n</body>", 1)
open(BASE + "viewer-zh.html", "w", encoding="utf-8").write(out)

# 4. 单独落盘脚本块供语法检查
js = re.search(r"<script nonce=\"__AGENTMEMORY_VIEWER_NONCE__\">\n\(function \(\) \{\n  if \(window\.__amZhWalker\)(.*?)</script>", out, re.S).group(1)
open(BASE + "walker-check.js", "w", encoding="utf-8").write("(function () {\n  if (window.__amZhWalker)" + js.replace("</script>", ""))

# 5. 覆盖率重估
todo = [l.rstrip("\n").split("\t", 1)[1] for l in open(BASE + "todo-translate.txt", encoding="utf-8") if "\t" in l]
hit = [t for t in todo if t in pairs]
print("原待补译 %d 条中已翻译: %d 条" % (len(todo), len(hit)))
print("输出: viewer-zh.html（%d 行）" % out.count("\n"))
