# MemMaster

面向华为 ToB **模拟场景** 的 OpenCode 本地记忆插件。把邮件、会议纪要、IM、业务网页四类可热插拔接口统一成**不可变文本 ground truth**，再用混合检索、轻量图、派生事实和选择性 push 做召回。

本仓库是技术验证：**数据全部合成**，项目/客户/工单均为虚构；产品名来自公开资料。不是华为生产系统，也不包含真实客户数据。

## 快速开始

```bash
npm ci
npm run validate
python -m pip install -r requirements.txt
python datasets/tob-memory-v1/build_corpus.py
python -m pytest tests -q
python -m experiments compare
```

打开离线报告：[report/dist/index.html](report/dist/index.html)

记忆服务：

```bash
python -m memmaster --help
# 或
python -m uvicorn memmaster.api:app --app-dir services/memory/src --port 8787
```

OpenCode 插件入口：`apps/opencode-plugin/index.ts`，评测时 workspace 禁止 read/glob/bash。模型标识使用已配置的 `deepseek/deepseek-v4-flash`。

## 架构要点

- TypeScript 插件只负责 tool / hook；Python sidecar 负责接入、索引、检索。
- Connector 通过 `memmaster.sources` 注册，mock 四种格式可替换。
- 索引：SQLite FTS5 + 本地向量（默认 hashing，可设 `MEMMASTER_EMBEDDER=bge-m3`）+ Graph-lite PPR。
- 增量更新：cursor + content hash + staging + manifest 原子切换，删除走 tombstone。

## 实验

预注册最多 10 组，配置与脚本全部在 `experiments/`。默认锁定 E0–E9。

正式协议：每个问题一个全新 OpenCode session，用户消息只有题目，**不指定调用哪个工具**。E1–E9 同时提供邮件/会议/IM/网页四个可选检索工具；E0 无记忆工具。排序：完成率降序，再按平均上下文长度、完成时间、工具次数升序。

```bash
python -m uvicorn memmaster.api:app --app-dir services/memory/src --port 8787
python -m experiments compare --backend opencode
```

单组复跑：

```bash
python -m experiments run --config experiments/configs/E2.yaml --backend opencode
```

检索天花板（强制检索，非正式）：`--backend oracle`。推迟组见 `experiments/deferred/`。


## SDD

```bash
node tooling/sdd/cli.mjs init 2026-08-20-memmaster-abc12 --workflow delivery --slug memmaster
node tooling/sdd/cli.mjs advance
```

改编自 [JunfengRan/dev-env](https://github.com/JunfengRan/dev-env)（MIT）。

## 许可

MIT。第三方声明见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
