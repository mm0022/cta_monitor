# cta_monitor 设计文档 — CTA 每轮信号执行情况监控

日期：2026-07-17
状态：待评审

## 1. 目标（一句话）

每小时跑一次，对被监控账户下每个 ticker 的**最新一轮**信号，核对「本轮想调的仓位」是否已被 TWAP 执行到位，产出一张 14 列表（见 §5），拼成等宽文本表发到 Slack（不发图片）。

数据要拼三个源：**datahub 信号** + **biyi financials** + **PG `order_event_his` 成交**。

## 2. 名词 & 链路

一轮「信号」= CTA signal publisher 每个 grid tick 给某 (account, coin) 发布的一条目标仓位。它落两处：

- **datahub**：`CTA_SIGNAL_PUBLISHER-LAST_PUBLISHED_V1-<account>-<coin>` 的 sequenced 记录（每轮一个新 seq）。承载**决策意图**。
- **biyi**：同一轮的 TWAP 执行状态（`strategies/{s}/financials` 的 tableData）。承载**执行侧现场**（单笔粒度、当前库存、事务状态、追踪ID）。

实际成交明细进 PG `order_event_his`，按 `(strategy_name, sym, 时间)` 过滤汇总。

## 3. 触发与闸门（每小时 cron）

1. 拉 biyi 监控范围内策略 + 每个 ticker 的 datahub 最新信号。
2. **无新信号闸门**：本账户最新一轮 signal 时间不在过去 1 小时内（还是上一轮那批）→ 不出表，Slack 提示「上一小时没有新信号在运行」后退出。
3. **运行中**：某 ticker biyi `事务状态 == running` → 该行标「正在运行中」，**不做成交统计**（DB 列留空）。`stop` 才统计。
4. **信号时间校验（时间 + delta 一起看）**：当 biyi `信号时间` ≠ datahub `signal_bar_ts_ms` 时，分两种：
   - **小额正常**：datahub 最新信号 `abs(delta_qty) × mark_price < 10 USDT`（`MIN_NOTIONAL_U`，可配）→ 名义额低于最小下单金额，biyi 不下单也不更新信号时间，属**正常**，不告警；该行标「小额未下单」，DB 列留空。
   - **真告警**：名义额 ≥ 10u 但时间仍不匹配 → 打「信号时间不匹配」告警标注（仍尽量出数，供人工核对）。

## 4. 数据源与取数

### 4.1 biyi（token 鉴权，base `https://biyi.tky.laozi.pro/biyi`）

- `login_biyi(login_url, user, passwd)` → token（`data.token`）。
- `strategy_list_all(token)`：`GET /biyi/strategy/list?curPage=0&pageSize=100`，过滤 `key ∈ ('CTA','CTA_EMS')` 且 `state=='RUNNING'`，返回 `{ strategySpec : accountNames[0] }`。
  - **默认监控全部入选策略**（不写死账户）；`strategySpec` 即 `order_event.strategy_name`，`accountNames[0]` 即 datahub key 的 account 段。
  - 可选：config 里配账户 allowlist 收窄监控范围（留空 = 全部）。
- 对每个入选 `s`：`GET /biyi/api/strategies/{s}/financials`（Bearer token）→ `data.tableData`。
  - `tableData[0]` 是表头（`列名|...` 逗号分隔），按列名找下标解析（同 `cta_strategies_info` 套路）。
  - 每行一个 symbol，取：`TICKER` / `VENUE` / `单笔粒度` / `信号时间` / `事务状态` / `追踪ID` / `当前库存` / `目标库存`。
  - 该行 `strategy_name = s`。

### 4.2 datahub（sequenced 读，**由 biyi 驱动**）

biyi 侧已给出「账户(`accountNames[0]`) + 币种(financials 每行的 TICKER)」，**直接用它拼 datahub key，不在 datahub 侧另配清单**：

- `account` = biyi `accountNames[0]`；`coin` = TICKER 的 base 段小写（`DOGE/USDT` → `doge`）。
- key = `["CYBERX_PROD", "CTA_SIGNAL_PUBLISHER", "LAST_PUBLISHED_V1", account, coin]`（严格同名，已确认，无需映射）。
  - 例：`CYBERX_PROD-CTA_SIGNAL_PUBLISHER-LAST_PUBLISHED_V1-binance_tokyo_cta_momentum_test1_new-btc`。
- `request_latest_sequenced_data(key, limit=1)` → 最新一条 `LastPublishedRecord`。
- 取字段：`mark_price` / `current_qty_at_decision` / `target_qty` / `delta_qty` / `signal_bar_ts_ms`。

### 4.3 PG `order_event_his`（复用 `analyse_excution` 的 `shiji` 库凭证）

对每个「已 stop 且有 delta」的 ticker：

```sql
SELECT s.is_maker, s.exchange_quantity, s.exchange_price, s.event_time
FROM order_event_his s
WHERE s.strategy_name = %(strategy_name)s
  AND s.sym          = %(sym)s
  AND s.app_receive  > %(signal_time)s
  AND s.event_type   = 'FULL_EXEC';
```

- `sym` = `<VENUE>_PERP_<BASE>_<QUOTE>`，由 biyi `TICKER`(如 `DOGE/USDT`) + `VENUE`(如 `BINANCE`) 拼出。
- `signal_time` = 本轮 signal 时间（北京时间字符串，与 `app_receive` 同时区）。

汇总：
- `maker比例` = `Σ(exchange_quantity×exchange_price | is_maker=1) / Σ(exchange_quantity×exchange_price)`
- `开始时间` = `min(event_time)`，`结束时间` = `max(event_time)`，`执行时间ms` = `max − min`

## 5. 输出表：14 列定义

一行 = 一个 ticker 的最新一轮。

| 列 | 含义 | 来源 | 公式 |
|---|---|---|---|
| A | TICKER | biyi | 如 `DOGE/USDT` |
| B | mark_price | datahub | `mark_price` |
| C | 单笔粒度 | biyi | `单笔粒度` |
| D | 单笔报单金额u | 计算 | `trunc(C × B, 0)`（整数、截断，复现截图；如 179.67→179） |
| E | 币量变化 | datahub | `current_qty_at_decision → target_qty` |
| F | delta币量 | datahub | `delta_qty` |
| G | ~报单笔数 | 计算 | `trunc(abs(delta_qty)/单笔粒度, 1)`（截断，非 roundup；12.3756→12.3）；`abs(delta)/单笔粒度 < 1` → 「小于单笔报单量，没交易」，DB 列（H/I/J/K）留空 |
| H | maker比例 | PG | 成交金额口径，见 §4.3；显示整数百分比 `44%` |
| I | 结束时间 | PG | `max(event_time)`（ms） |
| J | 开始时间 | PG | `min(event_time)`（ms） |
| K | 执行时间ms | 计算 | `I − J` |
| L | twap未完成的量 | 计算 | `当前库存(biyi) − target_qty(datahub)` |
| M | 未完成的金额u | 计算 | `L × mark_price` |
| N | 完成比例 | 计算 | `round((1 − abs(L)/abs(delta_qty)) × 100, 2)`（分母取 abs，兼容 delta 为负）；显示两位小数百分比 `95.55%` |

校验：DOGE 行 `1 − 1376/30939.1 = 95.55%` ✓。

## 6. 输出与告警（Slack）

- **不发图片**：14 列表拼成**等宽文本表**，包 ``` 代码块，用 incoming webhook 发到频道（超长按 ~3800 字符分片多条发）。
- 异常行行首打状态标记：运行中 / 小额 / 未下单 / ⚠时间不符 / ⚠无成交 / ⚠无信号。
- 头部一行汇总：本轮 signal 时间、覆盖 ticker 数、正常/运行中/告警计数。
- 特殊情形：
  - 无新信号 → 纯文本「上一小时没有新信号在运行」。

## 7. 工程形态

独立 uv 项目（不依赖 alpha_copy），结构：

```
cta_monitor/
  config.toml            # PG / biyi / datahub gateway / slack 凭证（.gitignore）
  config.example.toml
  src/cta_monitor/
    config.py            # 读 config + 目标账户 / 时区
    biyi.py              # login + strategy_list_all + financials 解析
    datahub.py           # sequenced 最新信号读取
    db.py                # order_event_his 汇总
    metrics.py           # 组 14 列表 + 闸门/状态判定
    render.py            # 表 → 等宽文本表
    slack.py             # 发送
  scripts/run.py         # cron 入口
  tests/                 # metrics / 解析 / 公式 单测
```

## 8. 待实现阶段确认的凭证 / 开放项

1. **凭证**：biyi `user/passwd`、datahub gateway 地址 + key、Slack webhook/channel。PG 复用 `analyse_excution/config.toml`。
2. **datahub sequenced 读的落地方式**（风险项）：`request_latest_sequenced_data` 在 alpha_copy 里走的是内部 client/SDK。独立项目需确认：是能走 HTTP gateway 直接读 sequenced，还是必须依赖 alpha_copy 的 `clients.data_hub`。若无法薄实现，退路 = 允许 import alpha_copy 那一个 client。
3. ~~账户名对齐~~：已确认 datahub key 严格 = `CYBERX_PROD-CTA_SIGNAL_PUBLISHER-LAST_PUBLISHED_V1-<biyi账户>-<币小写>`，无需映射。
4. **coin ↔ TICKER 对齐**：datahub 按 coin（如 `btc`）建 key，biyi 按 `TICKER`（`BTC/USDT`）；按 base 币大写 join，注意 `1000PEPE` 等特例。
5. **Slack 呈现**：文本表（代码块，webhook 发送），不发图片。
