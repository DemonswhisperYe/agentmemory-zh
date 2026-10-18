// 让 LLM 生成的记忆跟随输入语言。
//
// 背景：agentmemory 的"记忆"不是原文，是 LLM 把观测/会话重写成的结构化摘要，
// 而官方 14 条提示词全是英文且没有任何语言约束 —— LLM 的语言倾向是对齐提示词，
// 于是中文会话被重写成英文标题/事实/叙述，图谱实体名也变英文。
// 这里给每条提示词的首句后追加一句语言规则，逻辑不变，只加约束。
//
// 构建时运行（见 Dockerfile），锚点缺失会直接让构建失败，避免上游改版后静默失效。
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const DIST =
  process.env.PATCH_DIST || "/opt/agentmemory/node_modules/@agentmemory/agentmemory/dist";

const RULE =
  " IMPORTANT LANGUAGE RULE: write every free-text value you output (title, subtitle, facts, " +
  "narrative, concepts, decisions, procedures, steps, insight text, property values, summaries) " +
  "in Simplified Chinese regardless of the input language. Never translate file paths, commands, " +
  "code, identifiers, URLs, version strings or established English technical terms; copy them " +
  "exactly as they appear in the input. For entity names use the exact name from the source. " +
  "Keys you invent yourself (such as property keys) must also be in Simplified Chinese, " +
  "for example 部署环境 or 待解决问题. Keep the XML tag names and the enumerated type " +
  "values exactly as specified in English.";

const ANCHORS = [
  "You are a memory compression engine for an AI coding agent.",
  "You are a session summarizer for an AI coding agent's memory system.",
  "You are merging multiple partial summaries of the SAME coding session into one final session summary.",
  "You are a memory consolidation engine.",
  "You are a procedural memory extractor.",
  "You are a knowledge graph extraction engine.",
  "You are a higher-order reasoning engine.",
  "You are a contextual enrichment engine.",
  "You are a query expansion engine for a memory retrieval system.",
  "You are a skill extraction engine.",
  "You are a temporal knowledge extraction engine.",
  "You are a workflow summarizer.",
  "You are summarizing a completed chain of agent actions into a compact digest.",
  "Describe what this image shows in the context of software development.",
];

const files = readdirSync(DIST).filter((f) => f.endsWith(".mjs"));
if (files.length === 0) {
  console.error(`patch-prompt-lang: ${DIST} 下没有 .mjs 文件，路径不对`);
  process.exit(1);
}

const found = new Set();
let patched = 0;
let schemaPatched = 0;
for (const file of files) {
  const path = join(DIST, file);
  const before = readFileSync(path, "utf8");
  let after = before;
  for (const anchor of ANCHORS) {
    if (!after.includes(anchor)) continue;
    found.add(anchor);
    if (after.includes(anchor + RULE)) continue; // 幂等
    after = after.split(anchor).join(anchor + RULE);
    patched += 1;
  }
  // 自由键的 few-shot：把占位符 key="key" 换成中文键示例（示例比规则更有效）
  if (after.includes('<property key="key">')) {
    after = after.replace(
      /(\n[ \t]*)<property key="key">value<\/property>/g,
      (_m, indent) =>
        indent + '<property key="部署环境">NAS 上的容器</property>' +
        indent + '<property key="待解决问题">连续失败阈值的误报率校准</property>',
    );
    if (!after.includes('部署环境')) {
      console.error("patch-prompt-lang: property 示例替换失败");
      process.exit(1);
    }
    schemaPatched += 1;
  }
  if (after !== before) writeFileSync(path, after);
}

const missing = ANCHORS.filter((a) => !found.has(a));
if (missing.length > 0) {
  console.error(
    `patch-prompt-lang: ${missing.length} 个锚点未找到（上游提示词可能已改动）：\n  ` +
      missing.join("\n  "),
  );
  process.exit(1);
}

if (schemaPatched === 0) {
  console.error("patch-prompt-lang: 未找到 <property key=\"key\"> 示例，上游 schema 可能已改动");
  process.exit(1);
}
console.log(
  `patch-prompt-lang: 自由键示例替换 ${schemaPatched} 个文件；追加语言规则 ${patched} 处，覆盖 ${found.size}/${ANCHORS.length} 条提示词，扫描 ${files.length} 个文件`,
);
