#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宽容版全量扫描：捞出所有未翻译英文（含数字/模板符/长句/小写词）"""
import re, json, collections

BASE = "/root/pi-cwd-20260804/agentmemory-deploy/i18n/"
src = open(BASE + "ours.html", encoding="utf-8").read()

pairs = dict(json.load(open(BASE + "pairs-pr.json", encoding="utf-8")))
for ln in open(BASE + "supplement.tsv", encoding="utf-8"):
    ln = ln.rstrip("\n")
    if "\t" in ln:
        en, zh = ln.split("\t", 1)
        if en.strip() and zh.strip() and (en.strip() not in pairs or pairs[en.strip()] == en.strip()):
            pairs[en.strip()] = zh.strip()
norm = {k.strip().lower() for k in pairs}

def covered(t):
    k = re.sub(r"\s+", " ", t).strip()
    return k in pairs or k.lower() in norm

def codey(t):
    s = t.strip()
    if not s: return True
    if re.match(r"^(https?://|/|~/|\./|-{1,2}[a-z])", s): return True          # URL/路径/命令行参数
    if re.search(r"curl |=>|\(\)|;|::|===|<script|</|\{\{|localStorage|document\.|window\.", s): return True
    if re.match(r"^[a-z_$][\w$]*(\.[\w$]+)+$", s): return True                 # obj.field / a.b.c
    if re.match(r"^[a-zA-Z0-9_$\-#./:]+$", s) and " " not in s: return True    # 纯标识符
    if re.match(r"^[\d\s.,:%\-+/#()×·]+$", s): return True                     # 纯数字/符号
    return False

cands = collections.Counter(); where = {}
# 1) HTML 文本节点（不限长度）
for m in re.finditer(r">([^<>]{2,600})<", src):
    t = m.group(1)
    if re.search(r"[A-Za-z]{2}", t) and not codey(t) and not covered(t):
        k = re.sub(r"\s+", " ", t).strip()
        cands[k] += 1; where.setdefault(k, "html")
# 2) 属性文案
for m in re.finditer(r"(?:title|aria-label|placeholder|alt|data-label|data-title)=\"([^\"]{2,400})\"", src):
    t = m.group(1)
    if re.search(r"[A-Za-z]{2}", t) and not codey(t) and not covered(t):
        k = re.sub(r"\s+", " ", t).strip()
        cands[k] += 1; where.setdefault(k, "attr")
# 3) JS 字符串/模板串（含 ${}），模板串归一化
for m in re.finditer(r"""(['"`])((?:[^'"`\\]|\\.){2,600}?)\1""", src):
    q, t = m.group(1), m.group(2)
    if not re.search(r"[A-Za-z]{2}", t): continue
    if q == "`":
        t2 = re.sub(r"\$\{[^}]*\}", "${}", t)           # 变量归一
    else:
        t2 = t
    if codey(t2) or covered(t2) or covered(t): continue
    k = re.sub(r"\s+", " ", t2).strip()
    if len(k) < 2: continue
    cands[k] += 1; where.setdefault(k, "js-tpl" if q == "`" else "js")

out = open(BASE + "todo2.txt", "w", encoding="utf-8")
for t, n in cands.most_common():
    out.write("%d\t%s\t%s\n" % (n, where[t], t))
out.close()
print("未覆盖候选: %d 条 → todo2.txt" % len(cands))
byz = collections.Counter(where[t] for t in cands)
print("分布:", dict(byz))
