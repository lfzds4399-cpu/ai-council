# ai-council

> 多投票者共识框架——组合 Voter / 加权投票 / 一票否决 / 持久会议记录，为 LLM 和规则混合决策而做。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Status](https://img.shields.io/badge/status-beta-orange)

> 🌏 [English README](README.md)

## 这是什么

一个无依赖的小框架，让**几个"投票者"一起做决定**——单个模型或单条规则不够可靠时常用。你把若干 voter 装进 `Council`，对一个 proposal 提议进行 `deliberate`，得到一个 `Decision` 决议。

每个 `Voter` 就是一个带 `name`、`weight` 和 `vote(proposal, context, peers)` 方法的对象。内部你想跑 LLM、跑正则、查数据库都行——框架只看返回的 `Vote`。

## 为啥要单做一个框架

多 LLM 集成、人机评审委员会，每个项目都在重新发明一遍（量化交易、内容审核、代码评审……）。每次实现都把 4 件事搅成一团：

- **决定什么**（proposal 形状）
- **谁投票**（voters）
- **怎么聚合**（阈值、加权、否决）
- **审计日志放哪儿**

`ai-council` 把这 4 件事拆开。你提供 voters 和 proposal，框架管聚合和审计交接。

## 安装

```bash
pip install ai-council              # 上 PyPI 后
# 暂时:
pip install git+https://github.com/lfzds4399-cpu/ai-council.git
```

要求 Python 3.11+，零运行时依赖。

## 60 秒上手

```python
from ai_council import Council, Vote, function_voter

def cheap_voter(proposal, context, peers):
    cheap = proposal["price_usd"] < 100
    return Vote(voter="cheap", approve=cheap, score=80 if cheap else 20)

def reviewed_voter(proposal, context, peers):
    rated = proposal.get("rating", 0) >= 4.5
    return Vote(voter="reviewed", approve=rated, score=85 if rated else 30)

def stocked_voter(proposal, context, peers):
    in_stock = proposal.get("stock", 0) > 0
    return Vote(voter="stocked", approve=in_stock, score=90 if in_stock else 0,
                veto=not in_stock)  # 缺货 → 一票否决

council = Council(
    [
        function_voter("cheap", cheap_voter),
        function_voter("reviewed", reviewed_voter),
        function_voter("stocked", stocked_voter),
    ],
    threshold=2,                    # 2/3 通过
)

decision = council.deliberate({"price_usd": 79, "rating": 4.7, "stock": 12})
print(decision.approved, decision.final_score)
# True 85.0
```

## 核心概念

| 概念           | 含义                                                                          |
|----------------|-------------------------------------------------------------------------------|
| `Voter`        | 任何带 `name` / `weight` / `vote(proposal, context, peers)` 的对象            |
| `Vote`         | 单个投票者的判定：`approve`、`score`（0-100）、reasons、可选 `veto`            |
| `Council`      | 持有 voters 列表 + 阈值，执行 `deliberate(proposal)`                          |
| `Decision`     | 汇总结果：`approved` / `final_score` / 原始 votes / 时间戳                    |
| `MeetingStore` | 可选持久化（自带 `JsonMeetingStore`，DB 后端可自己实现）                       |

### 阈值

- `threshold=2` — 至少 2 个投票者赞成（绝对数）
- `threshold=0.6` — 至少 60%（向上取整）赞成（比例）

### 一票否决

任何 voter 可返回 `Vote(..., veto=True)`。否决**直接阻断通过**，即使其他人都赞成。用在硬红线场景（CSAM、未授权支付、破坏性 migration），任何共识都不该覆盖。

### 加权评分

`final_score` 是 vote score 的**加权平均**（阈值统计本身不加权——只看多少人 approve）。给资深 voter 设 `weight=2.0` 加大影响，又不至于直接给一票否决。

### 防御式 voter 处理

某 voter 抛异常时，默认会记录为 `score=0, approve=False` 的废票——单个 LLM 抽风不能让委员会崩溃。需要严格模式（dev / 调试）传 `strict=True`。

```python
council = Council(voters, threshold=2, strict=True)  # dev 阶段崩出来
```

## 示例

3 个可直接跑的示例放 [`examples/`](examples) 下，每个都用 3 个 voter 决一件事：

- [`domain_valuation.py`](examples/domain_valuation.py) — 这域名要不要买？（SEO + 品牌 + 转售对标价）
- [`code_review.py`](examples/code_review.py) — 这 PR 要不要合？（正确性 + 风格 + 可读性）
- [`content_moderation.py`](examples/content_moderation.py) — 这帖子要不要发？（政策 + 毒性 + 信誉）

```bash
python examples/domain_valuation.py
```

## 适用 / 不适用

适合：

- **多 LLM 集成**，每个模型的票都要被记录和审计
- **审核 / 审批流**，模型 + 规则混合 gate
- **决策日志**，需要解释 proposal 通过 / 否决的理由
- **敏感自动化**，单点故障不可接受

不适合：

- 单次 LLM 判断（直接调模型即可）
- 强化学习式回路（这里没有 reward 传播）
- 价格撮合 / 拍卖（用 price-clearing 不是投票）

## 状态

**Beta**——API 表面小且有测试覆盖，小版本可能还会调名字。基于此构建请 pin `ai-council==0.1.*`。

## 贡献

欢迎 issue 和 PR。pinned `help wanted` issue 给新人切入：vendor 一个 LLM-voter 助手 / 加 SQLite / Postgres backend / 加新领域 example。

## License

[MIT](LICENSE)
