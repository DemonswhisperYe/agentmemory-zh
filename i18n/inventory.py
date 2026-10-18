#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""i18n 盘点：PR 字典对提取 + 0.9.30 界面文案清单 + 匹配统计"""
import re, json, collections, sys

BASE = "/root/pi-cwd-20260804/agentmemory-deploy/i18n/"

# ---------- 1. 从 PR 版提取 I18N_STRINGS（en + zh-CN） ----------
src = open(BASE + "theirs.html", encoding="utf-8").read()
lines = src.split("\n")
section = None
en, zh = {}, {}
entry_re = re.compile(r"^\s*'([\w.\-]+)':\s*'((?:[^'\\]|\\.)*)'\s*,?\s*$")
for ln in lines:
    if re.match(r"^\s*en:\s*\{\s*$", ln):
        section = "en"; continue
    if re.match(r"^\s*'zh-CN':\s*\{\s*$", ln):
        section = "zh"; continue
    if re.match(r"^\s*\},?\s*$", ln):
        section = None; continue
    if section:
        m = entry_re.match(ln)
        if m:
            key, val = m.group(1), m.group(2).replace("\\'", "'")
            (en if section == "en" else zh)[key] = val

pairs = {}
for k in en:
    if k in zh and en[k] and zh[k]:
        # 只收不含变量占位符的纯文本（DOM 文本匹配模式）
        if "{" not in en[k]:
            pairs[en[k]] = zh[k]
print("PR 字典: en词条=%d zh词条=%d 可用于文本匹配=%d" % (len(en), len(zh), len(pairs)))
json.dump(pairs, open(BASE + "pairs-pr.json", "w"), ensure_ascii=False, indent=0)

# ---------- 2. 从 0.9.30 界面提取英文文案 ----------
s = open(BASE + "ours.html", encoding="utf-8").read()
cand = collections.Counter()

STOP = {"esc", "true", "false", "null", "undefined", "div", "span", "button", "input", "label", "class", "type", "json", "api", "ok", "id", "cli", "mcp", "url", "http", "https", "get", "post", "put", "delete", "en", "zh", "lang", "new", "name", "value", "text", "title", "data", "test", "run", "all", "none", "auto", "self", "node", "key", "var", "let", "const", "function", "return"}

def plausible(t):
    t = t.strip()
    if len(t) < 2 or len(t) > 70: return False
    if not re.search(r"[A-Za-z]{2}", t): return False
    if re.search(r"[{}<>\\$`|=;:+()\[\]/#&@]", t): return False
    if re.match(r"^[\d\s.,:%\-+/#()]+$", t): return False
    if re.search(r"[a-z][A-Z]", t): return False          # camelCase
    if re.search(r"[a-z]+[-_][a-z0-9]+", t): return False  # btn-danger / mem_filer
    if re.search(r"[_]|\d", t): return False              # 下划线 / 含数字
    if re.match(r"^(https?|www)", t): return False
    if t.isupper() and len(t) < 4: return False
    if "\t" in t or "  " in t: return False
    words = re.findall(r"[A-Za-z']+", t)
    if not words: return False
    if len(words) == 1:
        w = words[0]
        if w.lower() in STOP: return False
        if not (w[0].isupper() and len(w) >= 4): return False   # 单词只收首字母大写的实词
    if t.lower() in STOP: return False
    return True

# HTML 文本节点
for m in re.finditer(r">([^<>]{2,80})<", s):
    t = m.group(1)
    if plausible(t) and re.search(r"[A-Za-z]{2}", t):
        cand[t.strip()] += 1
# 属性文案
for m in re.finditer(r"(?:title|aria-label|placeholder|alt|data-label|data-title)=\"([^\"]{2,80})\"", s):
    t = m.group(1)
    if plausible(t):
        cand[t.strip()] += 1
# JS 字符串（含空格的句子/多词，或首字母大写的实词）
for m in re.finditer(r"""(['"])((?:[^'"\\\n]|\\.){2,70}?)\1""", s):
    t = m.group(2)
    if plausible(t) and re.search(r"[A-Za-z]{2}", t):
        if (" " in t) or (t[0].isupper() and len(t) > 3):
            cand[t.strip()] += 1

print("界面文案候选: %d 条（去重）" % len(cand))

# ---------- 3. 匹配统计 ----------
norm = {k.strip().lower(): v for k, v in pairs.items()}
hit = miss = 0
missed = []
for t, n in cand.most_common():
    if t in pairs or t.lower() in norm:
        hit += n
    else:
        miss += n
        missed.append((n, t))
print("按出现次数: 已覆盖=%d 未覆盖=%d 覆盖率=%.0f%%" % (hit, miss, 100*hit/max(1, hit+miss)))

with open(BASE + "todo-translate.txt", "w", encoding="utf-8") as f:
    for n, t in missed:
        f.write("%d\t%s\n" % (n, t))
print("待补译清单 → todo-translate.txt（%d 条）" % len(missed))
