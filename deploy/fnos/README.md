# deploy/fnos — 飞牛 NAS 单容器部署

把 agentmemory 跑成一个 Docker 容器（REST/MCP :3111、流式 :3112、管理界面 :3113），
基于官方 `deploy/coolify` 思路，额外做了四件事：

1. **中文分词补装**：官方 `npm install --omit=optional` 会跳过 `@node-rs/jieba`，
   中文检索退化成整句分词。镜像里补装 jieba + tiny-segmenter（不装大体积 transformers）。
2. **CSP 放行局域网**：官方 connect-src 只允许 localhost 的 WebSocket，手机/其他机器
   访问界面会卡在 CONNECTING。构建时给 CSP 补上本机地址。
3. **提示词语言补丁**（`patch-prompt-lang.mjs`）：官方 14 条 LLM 提示词全是英文且没有
   语言约束，中文会话会被重写成英文摘要/图谱实体。补丁给每条提示词追加一句"跟随输入
   语言"的规则，逻辑不变。
4. **中文界面**：`viewer-i18n-zh.html` 是在原版界面上注入 DOM 翻译层的成品（工具链见
   `../../i18n/`），不改原代码。

## 用法

```bash
cp agentmemory.env.example agentmemory.env   # 填 LLM / 向量模型配置
# 改掉文件里的 192.168.1.100（示例 IP）和 sk-REPLACE_WITH_YOUR_LLM_KEY
docker compose up -d --build
```

- 管理界面 `http://<NAS>:3113`；对外开放时必须配 `AGENTMEMORY_SECRET`（首启自动生成到
  `/data/.hmac`，也可自己指定）和 `VIEWER_ALLOWED_HOSTS`（防 DNS 重绑定）。
- Agent/MCP 接入口 `http://<NAS>:3111`，需要 `Authorization: Bearer <secret>`。
- **提供方识别只认挂载进容器的 `~/.agentmemory/.env` 文件**（compose 里已挂
  `agentmemory.env`），进程环境变量只作为兜底。
- `AGENTMEMORY_EMBEDDING_DIMENSIONS` 必须显式声明向量维度，否则按默认 1536 算导致
  与实际模型（如 dmeta-768）维度不匹配。

## 版本升级

1. 改 `docker-compose.yml` 里的 `AGENTMEMORY_VERSION`（`III_VERSION` 与
   `III_SDK_VERSION` 必须是同一 release，Dockerfile 有护栏校验）；
2. `docker compose up -d --build`；
3. 升级后如果界面文案变了，按 `../../i18n/README.md` 的升级流程补译。

> 安全提示：局域网 HTTP + Bearer 明文传密钥只适合单人内网。跨网段使用请先上 HTTPS
> 或 SSH 隧道（官方对非回环地址的带认证 REST 调用也要求 HTTPS）。
