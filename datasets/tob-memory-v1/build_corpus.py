"""Build the synthetic Xinghe-7 / LumenGrid corpus. Not Huawei real business data."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent
NOTICE = "【合成数据 / NOT Huawei production data】LumenGrid 星河-7 技术验证语料。"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def eml(stem, date, subject, frm, to, body, cc=""):
    cc_line = f"Cc: {cc}\n" if cc else ""
    return f"""From: {frm}
To: {to}
{cc_line}Subject: {subject}
Date: {date}
Message-ID: <{stem}@lumengrid.example>
MIME-Version: 1.0
Content-Type: text/plain; charset=utf-8

{NOTICE}

{body}
"""


def build() -> None:
    mail = ROOT / "corpus" / "mail"
    # Q-mail-01 PO
    write(
        mail / "2026-03-18-po.eml",
        eml(
            "po044",
            "Wed, 18 Mar 2026 09:12:00 +0800",
            "星河-7 OceanStor Dorado 8000 合同确认",
            "周敏 <zhou.min@lumengrid.example>",
            "陈启明 <chen.qiming@huawei.example>",
            """陈总：
OceanStor Dorado 8000 集中式全闪存用于星河-7 生产存储。采购订单号 PO-XH7-20260318-044，含 4 控 + 智能压缩。
请勿与草稿单 PO-XH7-20260301-009 混淆，009 已作废。
金额条款见附件（本验证集不提供金额）。
周敏
商业经理""",
            cc="刘芳 <liu.fang@huawei.example>",
        ),
    )
    # Q-mail-02 delivery date update
    write(
        mail / "2026-02-02-gaussdb-plan.eml",
        eml(
            "gdb-plan",
            "Mon, 02 Feb 2026 11:00:00 +0800",
            "GaussDB 生产切换计划（初版）",
            "王磊 <wang.lei@huawei.example>",
            "陈启明 <chen.qiming@huawei.example>",
            """初版承诺 GaussDB 主集群切换窗口为 2026-04-12。
该日期已被后续修订邮件作废，请归档不要执行。""",
        ),
    )
    write(
        mail / "2026-03-28-gaussdb-amend.eml",
        eml(
            "gdb-amend",
            "Sat, 28 Mar 2026 16:40:00 +0800",
            "【修订】GaussDB 生产切换窗口",
            "王磊 <wang.lei@huawei.example>",
            "陈启明 <chen.qiming@huawei.example>",
            """修订：因 LumenGrid 侧电力窗口调整，GaussDB 主集群切换改到 2026-05-06 02:00-06:00 CST。
旧日期 2026-04-12 作废。备集群仍在 HCS 可用区 AZ-B。""",
        ),
    )
    # Q-mail-03 rejected SKU
    write(
        mail / "2026-03-05-sku.eml",
        eml(
            "sku",
            "Thu, 05 Mar 2026 14:22:00 +0800",
            "OceanStor 选型结论",
            "刘芳 <liu.fang@huawei.example>",
            "周敏 <zhou.min@lumengrid.example>",
            """结论：生产采用 Dorado 8000。Dorado 5000 方案被否决，原因是前端端口数量不足。
请市场同事不要再推 5000 清单。""",
        ),
    )
    # Q-mail-04 penalty
    write(
        mail / "2026-03-20-penalty.eml",
        eml(
            "penalty",
            "Fri, 20 Mar 2026 10:05:00 +0800",
            "星河-7 交付延误罚则确认",
            "周敏 <zhou.min@lumengrid.example>",
            "陈启明 <chen.qiming@huawei.example>",
            """罚则：OceanStor 主体到货相对 PO-XH7-20260318-044 约定日期每延误 1 个自然日，按合同总额千分之三计。
宽限期 3 日，从第 4 日开始起算。本邮件取代 2 月口头“不罚款”讨论。""",
        ),
    )
    # Q-mail-05 alias 老陈
    write(
        mail / "2026-03-22-alias.eml",
        eml(
            "alias",
            "Sun, 22 Mar 2026 08:31:00 +0800",
            "现场接口人确认",
            "陈启明 <chen.qiming@huawei.example>",
            "周敏 <zhou.min@lumengrid.example>",
            """请将华为侧项目经理接口人写为陈启明。现场微信群里叫我“老陈”即可。
工号 HW-PM-7712。不要写陈启明的助理李娜为决策人。""",
        ),
    )
    write(
        mail / "2026-04-11-hotline.eml",
        eml(
            "hotline",
            "Sat, 11 Apr 2026 09:15:00 +0800",
            "星河-7 值班热线分机",
            "周敏 <zhou.min@lumengrid.example>",
            "陈启明 <chen.qiming@huawei.example>",
            """值班热线分机 EXT-XH7-3608，演示分机 EXT-0000 不要外呼。""",
        ),
    )
    write(
        mail / "2026-04-08-accept.eml",
        eml(
            "accept",
            "Wed, 08 Apr 2026 11:20:00 +0800",
            "星河-7 现场验收窗口编号",
            "周敏 <zhou.min@lumengrid.example>",
            "陈启明 <chen.qiming@huawei.example>",
            """客户现场验收窗口编号 ACC-LG-202604-19，地点 LumenGrid 亦庄机房。
不要使用演示窗口 ACC-DEMO-000。""",
        ),
    )
    write(
        mail / "2026-04-14-pass.eml",
        eml(
            "pass",
            "Tue, 14 Apr 2026 10:05:00 +0800",
            "亦庄机房临时通行证",
            "周敏 <zhou.min@lumengrid.example>",
            "陈启明 <chen.qiming@huawei.example>",
            """亦庄机房临时通行证编号 PASS-XH7-62，前台纸质条作废，不要再用 PASS-000。""",
        ),
    )
    write(
        mail / "2026-04-02-netwo.eml",
        eml(
            "netwo",
            "Thu, 02 Apr 2026 14:20:00 +0800",
            "鲲鹏上架网络作业报备",
            "赵宇 <zhao.yu@huawei.example>",
            "陈启明 <chen.qiming@huawei.example>",
            """鲲鹏服务器上架窗口我已报备网络作业单 NET-WO-4401。
演示单 NET-WO-000 不要用。""",
        ),
    )
    write(
        mail / "2026-01-09-noise.eml",
        eml(
            "noise",
            "Fri, 09 Jan 2026 09:00:00 +0800",
            "节后问候与 Kunpeng 白皮书",
            "marketing@huawei.example",
            "all@lumengrid.example",
            """新年快乐。附件是公开 Kunpeng 介绍，与星河-7 采购清单无关。
请忽略其中的示例订单号 DEMO-0001。
另：财务内部结算编码 SETTLE-XH7-77，不要写进对客合同。""",
        ),
    )

    meeting = ROOT / "corpus" / "meeting"
    write(
        meeting / "2026-03-11-dr.md",
        """---
title: "星河-7 容灾演练纪要"
date: "2026-03-11T15:00:00+08:00"
---
参加人：陈启明、刘芳、王磊、赵宇、客户张衡。
决议：生产 GaussDB 的 RTO 目标定为 15分钟，RPO 目标 2分钟。
本次容灾演练工单号 WO-DR-20260311-07，已录入变更台账。
否决了“RTO 1小时”的保守草案。eSight 仅作硬件告警，不承担该 RTO 承诺。
""",
    )
    write(
        meeting / "2026-02-18-nce-old.md",
        """---
title: "iMaster NCE 版本预选"
date: "2026-02-18T10:00:00+08:00"
---
预选 iMaster NCE-IP V100R024C00。该决议已被 4 月评审会更新，不得再作为实施基线。
""",
    )
    write(
        meeting / "2026-04-09-nce-new.json",
        """{
  "title": "iMaster NCE 版本终审",
  "date": "2026-04-09T16:30:00+08:00",
  "text": "终审：星河-7 承载网控制器升级为 iMaster NCE-IP V100R024C10。V100R024C00 仅允许实验室保留。赵宇负责升级窗口。"
}
""",
    )
    write(
        meeting / "2026-03-25-compute.md",
        """---
title: "算力分工会"
date: "2026-03-25T09:30:00+08:00"
---
Kunpeng 服务器配额由赵宇（网络与基础设施）负责申请；Ascend 推理节点配额由王磊按 GaussDB 侧 AI 质检需求提出，批准人仍是陈启明。
不要把 Ascend 配额记到刘芳名下。
""",
    )
    write(
        meeting / "2026-03-08-ideahub.md",
        """---
title: "作战室设备"
date: "2026-03-08T13:00:00+08:00"
---
LumenGrid 总部会议室 A 的 IdeaHub Board 3 资产编号 IH-LG-A-0881，用于星河-7 日站会。
日站会配套投影终端编号 PJ-LG-A-17。
会议室 B 的 IH-LG-B-0012 不在本项目范围。
""",
    )
    write(
        meeting / "2026-03-19-monitor.md",
        """---
title: "监控边界"
date: "2026-03-19T11:00:00+08:00"
---
eSight 负责服务器、OceanStor 硬件告警；iMaster NCE 负责 IP 网络与隧道。业务 SQL 慢查询仍走 GaussDB 自带监控，不进 eSight。
总部会议室 A 门禁码 DH-A-5521，会议室 B 的 DH-B-0004 仅供参观。
""",
    )

    im = ROOT / "corpus" / "im"
    write(
        im / "welink-xh7.ndjson",
        """
{"id":"im-001","ts":"2026-03-12T09:01:00+08:00","user":"刘芳","alias":"小刘","text":"OceanStor 缓存池先按 40TB 规划，我下午对一下。"}
{"id":"im-002","ts":"2026-03-12T18:22:00+08:00","user":"刘芳","alias":"小刘","text":"更正：生产缓存池最终是 64TB，40TB 是测试池。变更单 CHG-8821 已提单。"}
{"id":"im-003","ts":"2026-03-13T10:10:00+08:00","user":"王磊","alias":"磊哥","text":"GaussDB 账户密码轮换窗口定在每周二 23:30，由我执行，不要用默认周六窗口。"}
{"id":"im-004","ts":"2026-03-13T10:12:00+08:00","user":"陈启明","alias":"老陈","text":"收到。小刘你把 CHG-8821 抄送给客户张衡。"}
{"id":"im-005","ts":"2026-03-14T08:03:00+08:00","user":"赵宇","alias":"宇","text":"开玩笑：要不明天把生产交换机重启一下？"}
{"id":"im-006","ts":"2026-03-14T08:04:00+08:00","user":"赵宇","alias":"宇","text":"刚才是玩笑。正式承诺：核心交换机维护窗口是 2026-05-09 01:00，已报备。"}
{"id":"im-008","ts":"2026-03-16T19:40:00+08:00","user":"王磊","alias":"磊哥","text":"应急语音桥接号定为 BRIDGE-XH7-19，与演示号 BRIDGE-000 无关。"}
{"id":"im-009","ts":"2026-03-16T21:05:00+08:00","user":"刘芳","alias":"小刘","text":"今晚值班交接单 HANDOFF-XH7-33 已建，演示单 HANDOFF-000 作废。"}
{"id":"im-010","ts":"2026-03-25T16:40:00+08:00","user":"赵宇","alias":"宇","text":"算力会后补一句：跳纤窗口批文号是 JF-XH7-08，刚才会上没写进纪要。"}
{"id":"im-011","ts":"2026-03-26T11:18:00+08:00","user":"王磊","alias":"磊哥","text":"GaussDB 备份窗口编号 BK-XH7-14，不要去备份控制台找单号。"}
""".strip(),
    )

    web = ROOT / "corpus" / "web"
    write(
        web / "sitemap.xml",
        """<?xml version="1.0"?>
<urlset>
  <url><loc>https://hcs.lumengrid.example/portal/tenant.html</loc></url>
  <url><loc>https://hcs.lumengrid.example/portal/gaussdb.html</loc></url>
  <url><loc>https://hcs.lumengrid.example/portal/cmdb.html</loc></url>
  <url><loc>https://hcs.lumengrid.example/portal/project.html</loc></url>
  <url><loc>https://hcs.lumengrid.example/portal/acl.html</loc></url>
  <url><loc>https://hcs.lumengrid.example/portal/old-wiki.html</loc></url>
  <url><loc>https://hcs.lumengrid.example/portal/vpn.html</loc></url>
  <url><loc>https://hcs.lumengrid.example/portal/vpn-old.html</loc></url>
  <url><loc>https://hcs.lumengrid.example/portal/customer.html</loc></url>
</urlset>
""",
    )
    write(
        web / "tenant.html",
        """<html data-updated="2026-04-01T08:00:00+08:00"><head><title>HCS 租户</title></head>
<body><h1>Huawei Cloud Stack 租户</h1>
<p>项目星河-7 管理面 URL：/console/regions/cn-xh7-1</p>
<p>租户ID：tn-lg-xh7-20481</p>
<p>干扰项：演示租户 tn-demo-000 不可用。</p>
</body></html>""",
    )
    write(
        web / "gaussdb.html",
        """<html data-updated="2026-04-15T08:00:00+08:00"><head><title>GaussDB 版本</title></head>
<body><p>当前生产 GaussDB 内核版本 505.2.0.B023。旧 wiki 上的 505.1.0.B010 已下线。</p></body></html>""",
    )
    write(
        web / "old-wiki.html",
        """<html data-updated="2026-01-05T08:00:00+08:00"><head><title>过期 wiki</title></head>
<body><p>GaussDB 505.1.0.B010 安装记录，仅供历史查阅。</p></body></html>""",
    )
    write(
        web / "vpn-old.html",
        """<html data-updated="2026-01-08T08:00:00+08:00"><head><title>过期 VPN</title></head>
<body><p>历史 VPN 接入码 VPN-OLD-11，2026-01 已停用。</p></body></html>""",
    )
    write(
        web / "vpn.html",
        """<html data-updated="2026-04-18T08:00:00+08:00"><head><title>生产 VPN</title></head>
<body><p>当前生产 VPN 远程拨入口令 VPN-NOW-88。历史码 VPN-OLD-11 停用。</p></body></html>""",
    )
    write(
        web / "customer.html",
        """<html data-updated="2026-03-21T08:00:00+08:00"><head><title>客户现场代表</title></head>
<body><p>LumenGrid 现场代表张衡，工牌 BADGE-LG-204。演示工牌 BADGE-000 无效。</p></body></html>""",
    )
    write(
        web / "cmdb.html",
        """<html data-updated="2026-03-30T08:00:00+08:00"><head><title>CMDB</title></head>
<body><p>OceanStor Dorado 8000 序列号 2102350BHB10XH7001 对应 CI 编号 CI-STOR-77821。</p>
<p>另一台实验室阵列 SN 2102000LAB 对应 CI-STOR-00011，非生产。</p></body></html>""",
    )
    write(
        web / "project.html",
        """<html data-updated="2026-02-01T08:00:00+08:00"><head><title>项目编码</title></head>
<body><p>内部项目编码 XH-7，对外名称星河-7，客户 LumenGrid。</p></body></html>""",
    )
    write(
        web / "acl.html",
        """<html data-updated="2026-04-02T08:00:00+08:00"><head><title>备份页权限</title></head>
<body><p>GaussDB 备份控制台仅授权组 grp-xh7-dba 可见。grp-xh7-guest 只能看容量看板。</p>
<p>审计日志桶 obs-xh7-audit-07，演示桶 obs-demo-000 不可用。</p>
<p>生产监控空间编号 mon-xh7-prod-4。</p></body></html>""",
    )

    (ROOT / "NOTICE.txt").write_text(
        "本目录全部为合成 ToB 场景，产品名来自公开资料，项目/客户/工单均为虚构。\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    build()
    print("corpus written", ROOT / "corpus")
