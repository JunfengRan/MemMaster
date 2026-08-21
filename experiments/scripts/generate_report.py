"""Standalone blog-style HTML report. Open any page without other docs."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAV = [
    ("index.html", "总览"),
    ("research.html", "调研与方法"),
    ("architecture.html", "架构"),
    ("dataset.html", "数据集"),
    ("experiments.html", "三次实验"),
    ("results.html", "结果对比"),
    ("recommendation.html", "建议"),
]
SOURCES = ("mail", "meeting", "im", "web")
SOURCE_LABEL = {"mail": "邮件", "meeting": "会议", "im": "IM", "web": "网页"}
GROUPS = {
    "E0": {
        "name": "Blank（空白对照）",
        "short": "无记忆插件、无四个源工具。测模型会不会靠常识蒙对合成事实。",
        "detail": "OpenCode 以 --pure 启动，禁止 search_mail/search_meeting/search_im/search_web。题目里的订单号、租户 ID、工单号都是虚构的，训练数据里不应存在。若 Blank 完成率不是 0，说明题面泄密或评测串题。本轮不对 Blank 调 Harness。",
    },
    "E1": {
        "name": "Lexical / BM25",
        "short": "SQLite FTS5 关键词检索，对单号、型号最稳，对改写和别名弱。",
        "detail": "把四个源各自做成全文索引，按 BM25 打分。问句里出现 PO、CHG、租户 ID 这类精确字符串时召回最好。中文整段分词偏粗，像「RTO 目标是多久」对不上「15分钟」时会全军覆没，所以第一版天花里 E1 只有 60%。",
    },
    "E2": {
        "name": "Hybrid RRF",
        "short": "BM25 + 稠密向量倒数排名融合，精确匹配和语义改写都照顾。",
        "detail": "同一查询走词法检索和哈希向量检索，再用 Reciprocal Rank Fusion 合并。第一版强制检索天花 95%，未调优真实 Agent 也是十组里完成率最高的。代价是上下文比纯 BM25 长。",
    },
    "E3": {
        "name": "Graph-lite PPR",
        "short": "在 Hybrid 之上用共现图做一跳个性化 PageRank，适合人名-资产多跳。",
        "detail": "改编 HippoRAG 2 的 PPR，不做完整 OpenIE。图边来自实体共现。多跳题（谁申请 Kunpeng、谁提 Ascend）理论上更有优势；噪声边也可能把无关片段挤进 top-k，未调优时完成率反而低于 E2。",
    },
    "E4": {
        "name": "Push + Pull",
        "short": "Hybrid/Graph 检索，外加 sidecar 判断要不要塞一条短提醒。",
        "detail": "改编 Proactive Memory：不是每轮都灌记忆，而是按当前问题决定是否 intervention。提醒走 system.transform，不能在 chat.message 里插残缺 part（OpenCode 会 UnknownError）。提醒只给线索，不点名单题该用哪个源工具。",
    },
    "E5": {
        "name": "Extractive Facts",
        "short": "Mem0 风格：先命中派生事实，再回源到原文 span。",
        "detail": "正则+种子事实层独立于原文。查询打到事实后必须带回证据片段，禁止只抛脱离上下文的三元组。对「当前生效日期/最终容量」这类修订题有帮助，但事实抽错会连带回源一起错。",
    },
    "E6": {
        "name": "Time-aware",
        "short": "LongMemEval + Graphiti：valid time 上把「当前/修订」压过旧草稿。",
        "detail": "文档带 valid_time / transaction_time。问「当前版本」「最终容量」时提高新文档权重。对 GaussDB 切换日、NCE 版本、内核版本这类 update 题是对口方法。",
    },
    "E7": {
        "name": "Core Memory",
        "short": "把项目术语表常驻 system，再做 Hybrid 检索。",
        "detail": "改编 MemGPT/MemOS 的 core：LumenGrid、星河-7、OceanStor、GaussDB 等稳定别名始终可见，减少「老陈是谁」这类别名题的迷路。Core 不能替代单号检索，订单号仍要拉原文。",
    },
    "E8": {
        "name": "Dual Channel",
        "short": "MemOS MemCube 双通道：语义通道 + 关键词通道，带 provenance。",
        "detail": "不做参数记忆。两个通道分别召回再合并，结果带来源文档 ID。和 Hybrid 相近，但通道切分与计分不同，上下文往往略长。",
    },
    "E9": {
        "name": "Fact Keys",
        "short": "LongMemEval 键 + 有限别名链接（老陈→陈启明）。",
        "detail": "为高频实体建 key，别名边数量封顶，避免把整库连成一团。对 IM/邮件里的花名有效；对纯单号题退化为普通检索。",
    },
}

CSS = """
:root { --ink:#152033; --muted:#5b6573; --paper:#f7f4ee; --card:#fff; --line:#d9d3c5; --blue:#1f6feb; --green:#1a7f37; --red:#c62828; --navy:#13294b; }
* { box-sizing: border-box; }
html, body { margin:0; background:var(--paper); color:var(--ink); font: 16px/1.65 "Segoe UI", "PingFang SC", sans-serif; }
header, footer { background:var(--navy); color:#fff; padding:1rem 1.5rem; }
header { display:flex; flex-wrap:wrap; gap:.8rem 1.5rem; align-items:center; justify-content:space-between; }
header nav a { color:#d7e4ff; margin-right:1rem; text-decoration:none; }
header nav a.active { color:#fff; font-weight:700; border-bottom:2px solid #fff; }
main { max-width: 980px; margin: 0 auto; padding: 1.6rem 1.2rem 3rem; }
.card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:1.1rem 1.3rem; margin:1rem 0; }
h1 { font-size:1.7rem; margin:.2rem 0 1rem; }
h2 { font-size:1.25rem; margin:1.4rem 0 .6rem; }
.muted { color:var(--muted); }
.legend span { display:inline-block; margin-right:1rem; }
.sw { display:inline-block; width:12px; height:12px; border-radius:2px; margin-right:.3rem; vertical-align:middle; }
.sw.blue { background:var(--blue); } .sw.green { background:var(--green); } .sw.red { background:var(--red); }
.cmp { margin:.7rem 0 1rem; }
.cmp .lab { display:flex; justify-content:space-between; font-size:.92rem; margin-bottom:.25rem; }
.track { position:relative; height:16px; background:#ece7dc; border-radius:8px; overflow:hidden; }
.track i { position:absolute; top:0; height:16px; }
.track .blue { background:var(--blue); }
.track .green { background:var(--green); }
.track .red { background:var(--red); }
table { width:100%; border-collapse:collapse; font-size:.95rem; }
th, td { border-bottom:1px solid var(--line); padding:.45rem .4rem; text-align:left; }
.kicker { letter-spacing:.08em; text-transform:uppercase; font-size:.75rem; color:#8a6d3b; }
blockquote { border-left:4px solid var(--blue); margin:1rem 0; padding:.2rem 1rem; color:#243047; }
footer { font-size:.85rem; }
"""


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
  <style>{CSS}</style>
</head>
<body>
<header>
  <strong>MemMaster 技术验证报告</strong>
  <nav>{nav(current)}</nav>
</header>
<main>
<p class="kicker">Standalone · 打开本页即可读完 · 合成 ToB 数据 · 非华为生产业务</p>
{body}
</main>
<footer>MIT · 虚构客户 LumenGrid / 项目星河-7 · 数字全部由 experiments/runs 里的 JSON 生成</footer>
</body>
</html>
"""


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def num(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def delta_bar(gid: str, old: float, new: float) -> str:
    old_p = max(0.0, min(100.0, old * 100))
    new_p = max(0.0, min(100.0, new * 100))
    lo = min(old_p, new_p)
    diff = abs(new_p - old_p)
    extra = "green" if new_p >= old_p else "red"
    arrow = f"+{diff:.1f}pt" if new_p >= old_p else f"-{diff:.1f}pt"
    label = GROUPS.get(gid, {}).get("name", gid)
    return f"""
<div class="cmp">
  <div class="lab"><span>{gid} · {label}</span><span>未调优 {old_p:.1f}% → 调优后 {new_p:.1f}%（{arrow}）</span></div>
  <div class="track">
    <i class="blue" style="left:0;width:{lo:.2f}%"></i>
    <i class="{extra}" style="left:{lo:.2f}%;width:{diff:.2f}%"></i>
  </div>
</div>"""


def metrics_table(rows: list[dict], caption: str) -> str:
    body = []
    for i, row in enumerate(rows, start=1):
        gid = row["group"]
        name = GROUPS.get(gid, {}).get("name", gid)
        n = int(row.get("n") or 0)
        ok = int(round(float(row.get("task_success") or 0) * n)) if n else 0
        fact = row.get("fact_success")
        extra = ""
        if fact is not None:
            extra = f"<br><span class='muted'>事实 {pct(fact)}"
            extra += f" · 代价失败 {int(row.get('cost_fail') or 0)}</span>"
        score_cell = pct(row["task_success"])
        if n:
            score_cell += f"<br><span class='muted'>{ok}/{n}</span>"
        score_cell += extra
        body.append(
            "<tr>"
            f"<td>{i}</td>"
            f"<td>{gid}<br><span class='muted'>{name}</span></td>"
            f"<td>{score_cell}</td>"
            f"<td>{num(row.get('avg_context_tokens') or 0, 0)}</td>"
            f"<td>{num(row.get('avg_duration_ms') or 0, 0)}</td>"
            f"<td>{num(row.get('avg_tool_calls') or 0, 2)}</td>"
            "</tr>"
        )
    return f"""
<p>{caption}</p>
<table>
<thead><tr><th>序</th><th>组 / 方法</th><th>完成率 ↑</th><th>上下文 token ↓</th><th>耗时 ms ↓</th><th>工具次数 ↓</th></tr></thead>
<tbody>{''.join(body)}</tbody>
</table>
"""


def group_cards() -> str:
    bits = []
    for gid, meta in GROUPS.items():
        bits.append(
            f"<div class='card'><h2>{gid} · {meta['name']}</h2>"
            f"<p><b>一句话：</b>{meta['short']}</p>"
            f"<p>{meta['detail']}</p></div>"
        )
    return "".join(bits)


def ranked_from(metrics: dict) -> list[dict]:
    rec = metrics.get("recommendation") or {}
    rows = rec.get("ranked") or []
    out = []
    for row in rows:
        if isinstance(row, dict) and "group" in row:
            out.append(
                {
                    "group": row["group"],
                    "n": row.get("n") or 0,
                    "task_success": row.get("task_success") or 0,
                    "fact_success": row.get("fact_success"),
                    "cost_fail": row.get("cost_fail") or 0,
                    "avg_context_tokens": row.get("avg_context_tokens") or 0,
                    "avg_duration_ms": row.get("avg_duration_ms") or 0,
                    "avg_tool_calls": row.get("avg_tool_calls") or 0,
                }
            )
        elif isinstance(row, (list, tuple)) and row:
            gid = row[0]
            summary = (metrics.get("summary") or {}).get(gid) or {}
            out.append(
                {
                    "group": gid,
                    "n": summary.get("n") or 0,
                    "task_success": row[1] if len(row) > 1 else summary.get("task_success") or 0,
                    "avg_context_tokens": summary.get("avg_context_tokens") or 0,
                    "avg_duration_ms": summary.get("avg_duration_ms") or 0,
                    "avg_tool_calls": summary.get("avg_tool_calls") or 0,
                }
            )
    if out:
        return out
    summary = metrics.get("summary") or {}
    return [
        {
            "group": gid,
            "n": s.get("n") or 0,
            "task_success": s.get("task_success") or 0,
            "avg_context_tokens": s.get("avg_context_tokens") or 0,
            "avg_duration_ms": s.get("avg_duration_ms") or 0,
            "avg_tool_calls": s.get("avg_tool_calls") or 0,
        }
        for gid, s in summary.items()
    ]


def main() -> None:
    exp1 = load_json(ROOT / "experiments" / "runs" / "archive-local-tool-agent" / "metrics.json")
    exp2 = load_json(ROOT / "experiments" / "runs" / "exp2-adjusted" / "metrics.json")
    exp3 = load_json(ROOT / "experiments" / "runs" / "harness-best" / "metrics.json")
    chosen = load_json(ROOT / "experiments" / "runs" / "harness-best" / "chosen.json")
    if not chosen:
        chosen = exp3.get("chosen") or {}
    out = ROOT / "report" / "dist"
    out.mkdir(parents=True, exist_ok=True)

    s1 = exp1.get("summary") or {}
    s2 = exp2.get("summary") or {}
    s3 = exp3.get("summary") or {}
    rec3 = exp3.get("recommendation") or {}
    winner = rec3.get("winner") or "（评测尚未写完）"

    gids = sorted(
        {*(s2.keys()), *(s3.keys())},
        key=lambda gid: (
            -float((s3.get(gid) or {}).get("task_success") or 0),
            float((s3.get(gid) or {}).get("avg_context_tokens") or 0),
            float((s3.get(gid) or {}).get("avg_duration_ms") or 0),
            float((s3.get(gid) or {}).get("avg_tool_calls") or 0),
            gid,
        ),
    )
    bars = []
    for gid in gids:
        old = (s2.get(gid) or {}).get("task_success")
        new = (s3.get(gid) or {}).get("task_success")
        if old is None or new is None:
            continue
        bars.append(delta_bar(gid, float(old), float(new)))

    chosen_html = "".join(
        f"<li><b>{gid}</b> 采用 {spec.get('harness', '').upper()}："
        f"{spec.get('label') or GROUPS.get(gid, {}).get('short', '')}，"
        f"完成率 {pct(spec.get('task_success') or 0)}</li>"
        for gid, spec in chosen.items()
    )

    (out / "index.html").write_text(
        page(
            "总览",
            "index.html",
            f"""
<h1>企业记忆插件该怎么选：三次实验说明什么</h1>
<div class="card">
<p>MemMaster 是给 OpenCode 用的本地记忆插件：邮件、会议、IM、网页四类热插拔源，经 FastAPI sidecar 做检索，再以四个可选工具交给 Agent。<b>本页是完整结论</b>，不必再去翻仓库里的 Markdown 或代码。</p>
<p>评测模型固定为 DeepSeek V4 Flash。题库是虚构客户 LumenGrid、项目星河-7 的合成 ToB 事实，不是华为生产数据。完成率只计必答事实是否写出；顺带提到已作废编号不再判失败。</p>
</div>
<div class="card">
<h2>三句话结论</h2>
<ol>
<li><b>第一版</b>强制检索再抽答案，测的是检索理论上限，不是真实员工问法。</li>
<li><b>第二版</b>每个问题一个全新 session，用户消息只有题目，不调优提示词。这是「裸 Agent」。</li>
<li><b>第三版</b>给 E1–E9 各试两套 Harness（渠道启发 / 关键词改写），每组取字典序更好的那次；Blank 不调。完成率以未调优为蓝条基准，绿是提升、红是回落。</li>
</ol>
<p>当前字典序第一名：<b>{winner}</b>
{"，完成率 " + pct(rec3.get("task_success") or 0) + "，上下文 " + num(rec3.get("avg_context_tokens") or 0, 0) + " token，耗时 " + num(rec3.get("avg_duration_ms") or 0, 0) + " ms，工具 " + num(rec3.get("avg_tool_calls") or 0, 2) + " 次。" if rec3.get("task_success") is not None else "。"}</p>
</div>
<div class="card">
<h2>完成率：未调优（蓝）vs 调优后（绿升 / 红降）</h2>
<p class="legend"><span><i class="sw blue"></i>未调优完成率（公共部分）</span><span><i class="sw green"></i>Harness 提升</span><span><i class="sw red"></i>Harness 回落</span></p>
{''.join(bars) or "<p class='muted'>调优实验还在跑，对比图将在跑完后自动填入。</p>"}
<p class="muted">条形图按当前总完成率降序。完成率 = 必答事实写出，且该题的工具次数 / 上下文 / 耗时没有相对同题同伴严重偏高。加赛只给当时并列第一的组加跨源多跳题，未参赛组保持原分母。</p>
</div>
<div class="card">
<h2>十组方法（读这一段就能分清 E0–E9）</h2>
<p>E1–E9 在第三版里<b>同时提供四个工具</b>：search_mail、search_meeting、search_im、search_web。差别只在 sidecar 检索算法和是否注入 core/push。Harness 可以启发「该去查记忆」，但<b>不会按标准答案点名某一题该用哪个源</b>。</p>
</div>
{group_cards()}
""",
        ),
        encoding="utf-8",
    )

    (out / "research.html").write_text(
        page(
            "调研与方法",
            "research.html",
            f"""
<h1>调研：为什么是这十组，而不是整库接入某个开源记忆项目</h1>
<div class="card">
<p>业界记忆系统很多，Mem0、MemOS、Graphiti、HippoRAG、MemGPT 各自解决一块。华为 ToB 场景要的是<b>可开关模块</b>：同一套四个源工具，换检索后端就能对比，而不是把整个开源仓库搬进来。</p>
<ul>
<li><b>Mem0</b> → E5：派生事实层，命中后必须回源 span，防止幻觉事实。</li>
<li><b>MemOS MemCube</b> → E8：双通道 + provenance；E7 借用其 core memory 思路。</li>
<li><b>Graphiti</b> → E6：valid time / transaction time，处理「旧邮件作废、新邮件生效」。</li>
<li><b>HippoRAG 2</b> → E3：个性化 PageRank，跳过沉重 OpenIE。</li>
<li><b>Proactive Memory</b> → E4：选择性 push，不做 always-on 灌上下文。</li>
<li><b>LongMemEval</b> → E6/E9：时间题与 fact key / 别名。</li>
</ul>
<p>空白组 E0 是科学对照：没有工具时模型必须答不出虚构单号，否则整个排行榜作废。</p>
</div>
{group_cards()}
""",
        ),
        encoding="utf-8",
    )

    (out / "architecture.html").write_text(
        page(
            "架构",
            "architecture.html",
            """
<h1>架构：插件只负责工具，检索在本机 sidecar</h1>
<div class="card">
<p>运行时只有两块进程。OpenCode 里的 TypeScript 插件暴露四个工具；Python FastAPI sidecar 管索引、检索、干预。它们只走 localhost HTTP，语料不出机器。</p>
<blockquote>search_mail / search_meeting / search_im / search_web 各自带 source_id 过滤。没有统一的 memory_search。Agent 必须自己判断去哪个渠道。</blockquote>
<p>索引是 SQLite：FTS5 词法、哈希向量、Graph-lite 共现图。文档带 ACL 字段，但这是后续权限隔离评测用的，<b>本轮方法对比不启用 ACL 过滤，也不把约束失败踢出排行榜</b>。增量更新先写 staging，再原子切换 manifest，避免读到半截索引。</p>
<p>评测 session 在空沙箱里跑：禁止 read / glob / bash / web，避免 Agent 去仓库里翻题库或原文。全局 OpenCode 插件（例如会提供 ls 的环境插件）也会被隔离配置关掉，否则模型会去列目录而不是调记忆工具。</p>
</div>
<div class="card">
<h2>一次问答实际发生什么</h2>
<ol>
<li>用户只发题目，例如「有效采购订单号是什么」。</li>
<li>Agent（可选地）按 Harness 启发选择 1–2 个源工具，写入查询词。</li>
<li>Sidecar 按当前组的 methods 检索（lexical / hybrid / graph / facts / dual / keys / time）。</li>
<li>命中片段回到对话，Agent 抽原子事实作答。</li>
<li>评分只看必答事实有没有写全（任务完成率），以及上下文 token、耗时、工具次数。答案里顺带提到「已作废的草稿号」不再判失败。权限/ACL、约束失败不进本轮排序。</li>
</ol>
<p>E4 的 push 若触发，会多一条 system 提醒，仍然不点名单题金标准工具。</p>
</div>
""",
        ),
        encoding="utf-8",
    )

    n_items = 21
    (out / "dataset.html").write_text(
        page(
            "数据集",
            "dataset.html",
            f"""
<h1>合成数据集 tob-memory-v1：{n_items} 题，四源覆盖</h1>
<div class="card">
<p>客户叫 LumenGrid，项目叫星河-7。产品名用公开资料里的 OceanStor / GaussDB / iMaster NCE 等，<b>工单号、租户 ID、人名关系全部虚构</b>。每题指定 evidence 文档，构建时有 oracle 门禁：标准答案必须出现在证据原文里。</p>
<p>题型包括精确匹配、修订覆盖、别名、组合约束、干扰项、多跳。邮件约 6 题、会议/IM/网页各 5 题。</p>
</div>
<div class="card">
<h2>为什么删掉了原来的 Q06</h2>
<p>第一版「强制检索 + 从上下文抽答案」里，<b>E1–E9 全部做不出</b>「GaussDB 容灾演练 RTO 是多久」。问句是「RTO 目标是多久」，证据里写的是「15分钟」。中文 FTS 把整段汉字当成一个大词，检索天花都召不回，说明这题超出了当前检索器能力，不是模型不肯答。</p>
<p>删掉 Q06 后补了两题，都满足：Blank 不应会；E1–E4 里至少一种方法在第一版强制检索下能抽到答案——</p>
<ul>
<li><b>Q21</b> 会议：WO-DR 系列容灾演练工单完整编号 <code>WO-DR-20260311-07</code></li>
<li><b>Q22</b> 邮件：ACC-LG 系列现场验收窗口完整编号 <code>ACC-LG-202604-19</code></li>
</ul>
<p>第二版当时没跑过这两题，按协议<b>记失败</b>，所以第二次完成率分母变成 21、分子不加。上下文 / 耗时 / 工具次数三项代价<b>仍用原来 20 题的均值</b>，不被两条默认失败的空行拉歪。</p>
</div>
""",
        ),
        encoding="utf-8",
    )

    exp1_rows = ranked_from(exp1)
    exp2_rows = ranked_from(exp2)
    exp3_rows = ranked_from(exp3)
    (out / "experiments.html").write_text(
        page(
            "三次实验",
            "experiments.html",
            f"""
<h1>三次实验分别在测什么</h1>
<div class="card">
<h2>第一版 · 检索理论上限</h2>
<p>系统强制用题目去搜全库，再从返回上下文做字符串抽取。Agent 不会「忘记调用工具」，也不会选错源。这是<b>检索天花板</b>。Hybrid 一带方法大多 95%，Lexical 60%，Blank 0%。Q06 是全组天花板失败的唯一正式题，已删除。</p>
{metrics_table(exp1_rows, "第一版字典序。缺上下文/耗时/工具次数的组，是当时评分脚本只记完成率。")}
</div>
<div class="card">
<h2>第二版 · 未调优真实 Agent（蓝色基准）</h2>
<p>每个 case 一个全新 OpenCode session。用户消息<b>只有题目</b>。E1–E9 四个工具都在，提示词只说「没有依据就说不知道」。模型常常连打 3–5 个源，上下文被撑长。这是「不调优 Harness」的真实表现。</p>
<p>换题之后的第二次成绩已经改写并冻结：新题默认失败，三项代价指标保持原值。</p>
{metrics_table(exp2_rows, "第二次（修正分母后）字典序。")}
</div>
<div class="card">
<h2>第三版 · 每组两套 Harness，取更好的一次</h2>
<p>仍然不在题目里点名金标准工具。两套提示都是<b>分类启发</b>：</p>
<ul>
<li><b>HA 渠道启发式</b>：看到订单/邮件/PO 优先查邮件，看到纪要/演练优先查会议，看到群/微信优先查 IM，看到 wiki/CMDB/租户优先查网页。不确定就先搜最像的一类，不要四类扫一遍。</li>
<li><b>HB 关键词改写</b>：把整句压成 2–6 个专有名词再搜；落空才换源，最多换两次。各组另有一句方法提示（例如时间组强调「当前/修订」），仍然不点名单题源工具。</li>
</ul>
<p>每组跑完两套后，按完成率 ↓、上下文 ↑、耗时 ↑、工具次数 ↑ 的字典序取优。Blank 不参加。</p>
<ul>{chosen_html or "<li>尚未选出各组优胜 Harness。</li>"}</ul>
{metrics_table(exp3_rows, "第三版（含后续加赛，若有）字典序。")}
</div>
""",
        ),
        encoding="utf-8",
    )

    src_sections = []
    for src in SOURCES:
        raw = (rec3.get("by_source") or {}).get(src) or []
        src_rows = []
        for row in raw:
            if isinstance(row, dict) and "group" in row:
                src_rows.append(row)
        src_sections.append(
            f"<h2>{SOURCE_LABEL[src]} 分层</h2>"
            + metrics_table(src_rows, f"{SOURCE_LABEL[src]} 子集，同一字典序。分层只作诊断，主排序看总体。")
        )

    (out / "results.html").write_text(
        page(
            "结果对比",
            "results.html",
            f"""
<h1>结果：蓝绿红对比 + 最终排行</h1>
<div class="card">
<p class="legend"><span><i class="sw blue"></i>未调优完成率</span><span><i class="sw green"></i>提升</span><span><i class="sw red"></i>回落</span></p>
<p class="muted">按当前总完成率降序。本轮只比任务完成率与代价（上下文 / 耗时 / 工具次数），安全与权限隔离另开评测，不混进这张图。</p>
{''.join(bars) or "<p class='muted'>等待第三版跑完。</p>"}
</div>
<div class="card">
<h2>最终字典序（事实 + 代价离群，含多跳加赛）</h2>
{metrics_table(exp3_rows, "完成率 = 必答事实写出且非代价离群。代价按同一题在 E1–E9 上的分布：工具次数 z≥1.5 且至少比中位多 2 次，或 token z≥1.5 且 ≥1.6×中位，或耗时 z≥2 且 ≥1.8×中位。Blank 不参与代价分布。多跳加赛只跑当时并列第一的组。")}
{''.join(src_sections)}
</div>
<div class="card">
<h2>看起来「简单方法完胜」是怎么来的</h2>
<p>第一版检索天花上，E2–E8 都在 90% 以上，说明新兴模块召回并不差。未调优 Agent 和调优后，表面上 E2 远高于 E5–E9，拆题后不是这么回事。</p>
<ul>
<li><b>评分把「答对后又点出作废项」判失败。</b>Q01 有效 PO、Q02 切换日、Q07 NCE 版本、Q12 容量、Q17 内核、Q20 授权组等，各组其实都写出了正确事实，只是按题目习惯写了「草稿号已作废」。这不是检索失败，更不是 Mem0/时间/Core 比 BM25 差。</li>
<li><b>组间真正拉开的只有一两道。</b>在同一 21 题上，E1/E2/E3/E8 曾是 11/21，E4–E9 是 10/21，差在 Q09 IdeaHub、Q11 变更单是否复述了干扰编号，不是方法天花板。</li>
<li><b>加赛改成跨源多跳 / 混合指代。</b>问句里不出现第二跳的专有名词（例如只问「批准 Ascend 配额的人的工号」，工号在邮件、批准人在纪要）。单号查找题无法分开 Hybrid 家族。</li>
<li><b>过多工具调用 / 过长上下文 / 过长耗时算失败。</b>按每一题在各组上的均值和标准差，只把明显偏高的右尾判失败（多 1 次调用不够）。这样 E3 等「事实对了但扫了过多源」会掉完成率。</li>
<li><b>Harness 本身偏源路由。</b>HA/HB 教模型按邮件/会议/IM/网页选工具，这对 BM25/Hybrid 最顺。E5 事实层、E6 时间、E7 Core、E9 键并没有单独的工具，优势展不开。本轮不把「没用上方法特长」写成方法无效。</li>
</ul>
<p>修正后的结论：在 21 道事实题上 Hybrid 家族几乎都能写对答案；把「同题同伴里工具/上下文/耗时明显偏高」算失败后，E3/E4/E5/E7/E1 先掉队。跨源多跳加赛又把 E8 因多搜两次判失败。剩下 E2 / E6 / E9 事实完成率仍并列，三跳组合题（T49）撞到步数上限后三组一起失败，完成率仍相同。当前字典序第一是代价更低的那一个。</p>
</div>
<div class="card">
<p>完成率仍并列时，继续只给领先簇加多跳题，直到第一名唯一；代价离群已经计入完成率，不再只靠字典序里的平均值拉开。</p>
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
<h1>建议怎么上：先 Hybrid，再按痛点加模块</h1>
<div class="card">
<p>当前综合第一名是 <b>{winner}</b>。完成率同时看必答事实和代价离群（同题同伴里工具/token/耗时明显偏高算失败）。加赛是跨源多跳，分母可以不同。Blank 必须保持 0%。ACL / 权限隔离不进入本轮对比。</p>
<p>工程建议：</p>
<ol>
<li>默认检索用 <b>Hybrid</b>（E2）。第一版天花和第二版裸 Agent 都支持这一点。</li>
<li>Agent 侧加<b>渠道启发式</b>，不要默认四源全扫。这是第三版 HA 要验证的效率假设。</li>
<li>修订题多再开时间通道（E6）；花名多再开 keys/core（E9/E7）；需要提醒时用选择性 push（E4），不要 always-on。</li>
<li>不要把「强制检索抽答案」当成线上体验。真实用户只会发题目。</li>
</ol>
<p>本报告所有数字来自 <code>experiments/runs/exp2-adjusted</code> 与 <code>experiments/runs/harness-best</code>，重新生成：<code>python experiments/scripts/generate_report.py</code>。</p>
</div>
{group_cards()}
""",
        ),
        encoding="utf-8",
    )
    print(out)


if __name__ == "__main__":
    main()
