# 本地自用改动（不提交上游）

本仓库是 `rohitg00/agentmemory` 的 fork，`fnos-zh` 分支上除了**汉化工具链**，还有几处
**只给自己这台机器用**的改动。这份文件把它们单独列出来，避免和汉化混在一起看、
也避免以后同步上游时误判来源。

| 类别 | 位置 | 是否汉化相关 | 是否上游有 |
|---|---|---|---|
| 汉化工具链 | `i18n/`、`deploy/fnos/viewer-i18n-zh.html` | 是 | 否 |
| 飞牛 NAS 部署 | `deploy/fnos/` | 部分（viewer 是汉化产物） | 否 |
| pi 集成本地补丁 | `integrations/pi/index.ts` | 否 | 否 |

汉化本身的原理、词条规则、数据保护选择器见 [`i18n/README.md`](i18n/README.md)；
部署细节见 [`deploy/fnos/README.md`](deploy/fnos/README.md)。

---

## pi 集成本地补丁（`integrations/pi/index.ts`）

提交：`8545568`。代码里两处都打了 `LOCAL-PATCH(pi)` 注释，方便 `grep` 区分。

### 1. 连接配置从 `~/.pi/agent/agentmemory.env` 读

```
启动时读取 ~/.pi/agent/agentmemory.env 里的 AGENTMEMORY_URL / AGENTMEMORY_SECRET，
已有同名环境变量优先（不覆盖）；文件不存在或解析失败则静默跳过。
```

**为什么**：pi 守护进程的环境变量不好注入（父进程/服务管理器都碰不到），扩展原先只认
`process.env`，导致每次都要手动 export 才能连上。改成从权限 600 的自有配置文件读，
扩展变成自包含。

**风险**：静默失败。文件路径写错、SECRET 填错时没有任何提示，症状是"记忆不上报了"。
排查时先手工 `curl $AGENTMEMORY_URL/agentmemory/livez -H "Authorization: Bearer $AGENTMEMORY_SECRET"`
确认连通，再看扩展日志。

### 2. 会话结束时补一次延迟结晶

```
session_shutdown 里追加 POST crystals/auto  { olderThanDays: 7 }，超时 30s
```

**为什么**：结晶正常靠 agent 主动调 `memory_crystallize`，实际上很少被调用，已完成的工作
就一直不结晶。这里在退出时兜底扫一遍"完成超过 7 天、尚未结晶的行动"，对齐官方 opencode
插件的行为。

**风险**：这行是 `await`，服务端慢或在跑 LLM 凝练时，**pi 退出会被拖住最多 30 秒**。
嫌慢就把 `await` 改成 `void`（不等待）或把 `timeoutMs` 降到 5000。

### 与上游同步时

这两处都在上游文件 `integrations/pi/index.ts` 里，上游一改动这个文件就会冲突。冲突时
**认准 `LOCAL-PATCH(pi)` 注释**保留本地逻辑即可；`integrations/pi/` 之外的汉化与部署
改动都不在上游文件里（都是新增目录），不受影响。

> 结论：本人自用，不提上游。上游的 env 注入和结晶触发如果哪天跟这里行为一致了，
> 直接删掉这两个补丁段即可。
