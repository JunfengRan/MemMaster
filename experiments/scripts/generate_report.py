from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAV = [
    ("index.html", "总览"),
    ("research.html", "调研"),
    ("architecture.html", "架构"),
    ("dataset.html", "数据集"),
    ("experiments.html", "实验"),
    ("results.html", "结果"),
    ("recommendation.html", "建议"),
]


def nav(current: str) -> str:
    links = []
    for href, label in NAV:
        cls = ' class="active"' if href == current else ""
        links.append(f'<a href="{href}"{cls}>{label}</a>')
    return " ".join(links)


def page(title: str, current: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title} · MemMaster</title>
  <link rel="stylesheet" href="styles.css"/>
</head>
<body>
<header>
  <strong>MemMaster</strong>
  <nav>{nav(current)}</nav>
</header>
<main>
{body}
</main>
<footer>MIT · 合成 ToB 数据 · 非华为生产业务</footer>
</body>
</html>
"""


def bar_row(label: str, value: float) -> str:
    pct = round(value * 100, 1)
    return f'<div class="row"><span>{label}</span><div class="bar"><i style="width:{pct}%"></i></div><b>{pct}%</b></div>'


def main() -> None:
    metrics = json.loads((ROOT / "experiments" / "runs" / "official" / "metrics.json").read_text(encoding="utf-8"))
    summary = metrics["summary"]
    rec = metrics["recommendation"]
    out = ROOT / "report" / "dist"
    out.mkdir(parents=True, exist_ok=True)
    (out / "styles.css").write_text(
        """
:root { font-family: "Segoe UI", sans-serif; color: #102033; background: #f4f1ea; }
body { margin: 0; }
header, footer { padding: 1rem 1.5rem; background: #13294b; color: #fff; }
header nav a { color: #d7e4ff; margin-right: 1rem; }
header nav a.active { color: #fff; font-weight: 700; }
main { max-width: 980px; margin: 0 auto; padding: 1.5rem; }
.card { background: #fff; border: 1px solid #d9d3c5; padding: 1rem 1.2rem; margin: 1rem 0; }
.row { display: grid; grid-template-columns: 90px 1fr 70px; gap: .6rem; align-items: center; margin: .4rem 0; }
.bar { background: #ece7dc; height: 12px; }
.bar i { display: block; height: 12px; background: #1f6feb; }
table { width: 100%; border-collapse: collapse; }
th, td { border-bottom: 1px solid #ddd; padding: .4rem; text-align: left; }
""",
        encoding="utf-8",
    )
    (out / "index.html").write_text(
        page(
            "总览",
            "index.html",
            f"""
<h1>华为 ToB 多源记忆插件技术验证</h1>
<div class="card">
<p>MemMaster 把邮件、会议纪要、IM、业务网页四类热插拔接口统一为不可变文本 ground truth，再用 lexical / hybrid / graph / push / Mem0-MemOS 改编方法进行对照。</p>
<p>空白组 E0 准确率 <b>{summary['E0']['task_success']*100:.0f}%</b>，说明题目依赖语料而非模型常识。推荐组 <b>{rec['winner']}</b>，task success {rec['task_success']*100:.0f}%。</p>
</div>
<div class="card">
<h2>总体准确率</h2>
{''.join(bar_row(gid, summary[gid]['task_success']) for gid in sorted(summary))}
</div>
""",
        ),
        encoding="utf-8",
    )
    (out / "research.html").write_text(
        page(
            "调研",
            "research.html",
            """
<h1>调研与方法拆解</h1>
<div class="card">
<p>证据目录见 <code>docs/research/method-catalog.json</code>。不整库接入 Mem0/MemOS/GraphRAG，只抽取可开关模块。</p>
<ul>
<li>Mem0：派生事实层，强制回源 span。</li>
<li>MemOS：双通道 + provenance，不做参数记忆。</li>
<li>Graphiti：valid/transaction time。</li>
<li>HippoRAG 2：PPR，跳过完整 OpenIE。</li>
<li>Proactive Memory：选择性 push，always-on 推迟。</li>
</ul>
</div>
""",
        ),
        encoding="utf-8",
    )
    (out / "architecture.html").write_text(
        page(
            "架构",
            "architecture.html",
            """
<h1>架构</h1>
<div class="card">
<p>TypeScript OpenCode 插件 + FastAPI sidecar。ConnectorRegistry 热插拔。SQLite FTS5 + 向量 + Graph-lite。增量更新经 staging 后原子切换 manifest。</p>
<p>调用链：Adapter.sync → CanonicalDocument → chunk/embed/graph → /v1/search 或 /v1/interventions → plugin tool/hook。</p>
</div>
""",
        ),
        encoding="utf-8",
    )
    (out / "dataset.html").write_text(
        page(
            "数据集",
            "dataset.html",
            """
<h1>合成数据集 tob-memory-v1</h1>
<div class="card">
<p>虚构客户 LumenGrid、项目星河-7。公开华为产品名 + 合成工单/日期/人员。20 题，四源各 5 题。Oracle 证据可达率 100%。</p>
<p>空白组 0 分：答案是订单号、租户 ID、变更单等，不在通用模型常识中。</p>
</div>
""",
        ),
        encoding="utf-8",
    )
    rows = "".join(
        f"<tr><td>{gid}</td><td>{summary[gid]['task_success']*100:.0f}%</td><td>{summary[gid]['constraint_fail']}</td></tr>"
        for gid in sorted(summary)
    )
    (out / "experiments.html").write_text(
        page(
            "实验",
            "experiments.html",
            f"""
<h1>十组预注册实验</h1>
<div class="card">
<p>配置在 <code>experiments/configs</code>，方法模块在 <code>experiments/methods</code>，脚本在 <code>experiments/scripts</code>。复跑：<code>python -m experiments run --config experiments/configs/E2.yaml</code></p>
<table><thead><tr><th>组</th><th>成功率</th><th>预算失败</th></tr></thead><tbody>{rows}</tbody></table>
</div>
""",
        ),
        encoding="utf-8",
    )
    (out / "results.html").write_text(
        page(
            "结果",
            "results.html",
            f"""
<h1>结果</h1>
<div class="card">
<p>后端：local-tool-agent（与插件相同的 search/push API 与预算）。E0=0%，E1 lexical=60%，E2 hybrid=95%。图/push/MemCube 在 20 题上未再净增 2 题，按预注册规则不证明额外复杂度。</p>
<p>分源（E2）：邮件 {summary['E2']['by_source']['mail']*100:.0f}% · 会议 {summary['E2']['by_source']['meeting']*100:.0f}% · IM {summary['E2']['by_source']['im']*100:.0f}% · 网页 {summary['E2']['by_source']['web']*100:.0f}%</p>
</div>
""",
        ),
        encoding="utf-8",
    )
    (out / "recommendation.html").write_text(
        page(
            "建议",
            "recommendation.html",
            f"""
<h1>最终建议</h1>
<div class="card">
<p>推荐 <b>{rec['winner']}</b>：BM25 + 向量 RRF 混合拉取。保留 Graph-lite、时间过滤、派生事实与选择性 push 作为可热插拔开关，待更长多跳语料再启用。</p>
<p>排序：{', '.join(f"{g} {s*100:.0f}%" for g,s in rec['ranked'])}</p>
</div>
""",
        ),
        encoding="utf-8",
    )
    print(out)


if __name__ == "__main__":
    main()
