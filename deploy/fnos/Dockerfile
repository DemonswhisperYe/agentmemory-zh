ARG III_VERSION=0.22.1

FROM iiidev/iii:${III_VERSION} AS iii-image

FROM node:22-slim

ARG AGENTMEMORY_VERSION=0.9.30
ARG III_VERSION=0.22.1
ARG III_SDK_VERSION=0.22.1

RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
 && apt-get update \
 && apt-get install -y --no-install-recommends openssl ca-certificates tini gosu curl \
 && rm -rf /var/lib/apt/lists/*

COPY --from=iii-image /app/iii /usr/local/bin/iii
RUN iii --version 2>&1 | grep -qF "${III_VERSION}" \
 || { echo "the iiidev/iii:${III_VERSION} image does not contain iii ${III_VERSION}" >&2; exit 1; }

WORKDIR /opt/agentmemory
RUN [ "${III_VERSION}" = "${III_SDK_VERSION}" ] \
 || { echo "III_VERSION=${III_VERSION} and III_SDK_VERSION=${III_SDK_VERSION} must be the same release" >&2; exit 1; }
RUN printf '{"name":"agentmemory-deploy","version":"1.0.0","private":true,"overrides":{"iii-sdk":"%s"}}\n' "${III_SDK_VERSION}" > package.json \
 && npm install "@agentmemory/agentmemory@${AGENTMEMORY_VERSION}" --omit=optional --no-fund --no-audit \
 && ln -s /opt/agentmemory/node_modules/.bin/agentmemory /usr/local/bin/agentmemory

# 补装中日文分词（官方 --omit=optional 会把 @node-rs/jieba 一起跳过，
# 中文检索会退化成整句分词；这里只补 jieba/tiny-segmenter，不装大体积的 transformers）
RUN npm install @node-rs/jieba@^2.0.1 tiny-segmenter@^0.2.0 --no-fund --no-audit

ENV AGENTMEMORY_III_VERSION=${III_VERSION} \
    TINI_SUBREAPER=1

# 放行局域网访问：官方 CSP 的 connect-src 只允许 localhost 的 WebSocket，
# 手机/其他机器访问时实时数据流会被拦（界面卡 CONNECTING）。给 CSP 补上本机地址。
RUN sed -i 's|wss://127\.0\.0\.1:\*|wss://127.0.0.1:* ws://192.168.1.100:* wss://192.168.1.100:* http://192.168.1.100:*|g' \
    /opt/agentmemory/node_modules/@agentmemory/agentmemory/dist/*.mjs

# 让 LLM 生成的记忆跟随输入语言：官方 14 条提示词（compression/summary/consolidation/
# graph/reflect/enrich/query-expansion/skill/temporal/workflow/crystallize/vision）全是英文，
# 且没有任何语言约束，LLM 会按提示词语言输出，中文会话被重写成英文摘要。
COPY --chmod=0644 patch-prompt-lang.mjs /tmp/patch-prompt-lang.mjs
RUN node /tmp/patch-prompt-lang.mjs && rm /tmp/patch-prompt-lang.mjs

# 中文界面：保留 0.9.30 原版界面，追加中文翻译层
# （PR #1388 词典 317 条 + 自补译 525 条，DOM 扫描式翻译，不改原代码）
COPY --chmod=0644 viewer-i18n-zh.html /opt/agentmemory/node_modules/@agentmemory/agentmemory/dist/viewer/index.html

COPY --chmod=0755 entrypoint.sh /usr/local/bin/agentmemory-entrypoint.sh

EXPOSE 3111 3112 3113

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -fsS http://127.0.0.1:3111/agentmemory/livez || exit 1

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/agentmemory-entrypoint.sh"]
