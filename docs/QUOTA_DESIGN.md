# Open WebUI (Deploy) - 用户配额系统设计

> 目标：为 50 名初中生提供 LLM token 和生图次数的用量限制。

---

## 一、现有基础设施

### Token 追踪（已存在，零成本）

`chat_message` 表 `usage` JSON 列已记录每条 AI 回复的 token 消耗：

```json
{
  "input_tokens": 1234,
  "output_tokens": 567,
  "total_tokens": 1801,
  "prompt_tokens_details": {
    "cached_tokens": 200
  }
}
```

- `utils/response.py:normalize_usage()` — 多后端标准化（OpenAI/Ollama/llama.cpp）
- `models/chat_messages.py:get_token_usage_by_user()` — 按用户聚合 token 统计
- `/api/usage` 端点 — 已有管理端用量查看

### DeepSeek 定价

| 类型 | 价格（¥/百万 token） | 单 token 价 |
|---|---|---|
| 输入（缓存命中）| ¥1 | ¥0.000001 |
| 输入（缓存未命中）| ¥4 | ¥0.000004 |
| 输出 | ¥16 | ¥0.000016 |

---

## 二、实现方案

### 架构（三层）

```
quota_middleware.py  ──→  每次请求前检查余额
utils/quota.py       ──→  计费公式 + 配额查询
config 表             ──→  存储配额上限（按用户/用户组）
```

### 文件清单

| 文件 | 操作 | 作用 | 估算行数 |
|---|---|---|---|
| `utils/quota.py` | **新建** | 计费公式、配额检查、超限异常 | ~60 |
| `main.py` | 修改 | `chat_completion()` 前插入 quota check | +25 |
| `routers/images.py` | 修改 | `image_generations()` 前插入 quota check | +10 |
| `config.py` | 修改 | 默认配额常量 | +5 |
| `routers/auths.py` | 修改 | 登录时返回剩余额度 | +5 |

### 计费公式（`utils/quota.py`）

```python
# 硬编码 DeepSeek 定价，后续可通过 Config 配置
def deepseek_cost(input_tokens, output_tokens, cache_hit_tokens=0):
    cache_miss = input_tokens - cache_hit_tokens
    return (
        cache_hit_tokens * 0.000001 +  # 命中
        cache_miss * 0.000004 +         # 未命中
        output_tokens * 0.000016        # 输出
    )
```

### 配额检查流程

```
用户发消息
  │
  ▼
quota_check(user_id)
  ├── 查 DB: 该用户今日累计费用 (利用 get_token_usage_by_user + 计费)
  ├── 查 Config: 该用户组/个人的配额上限
  ├── 已超限? → HTTP 429 "今日额度已用完，请明天再试"
  └── 未超   → 放行，LLM 正常执行
                └── 流结束 → usage 写入 DB (已有逻辑)
```

### 生图配额

```
quota_check_image(user_id)
  ├── 查 DB: 该用户今日生图次数 (COUNT chat_message WHERE user_id=X AND created_at>today)
  ├── 超限? → HTTP 429
  └── 未超  → 放行
```

### 流式场景处理

DeepSeek 流式返回时 `usage` 在最后一个 chunk 才出现，无法预扣。采用后扣策略：

- 请求前只检查**当前累计**是否超限
- 如果累计已超 → 直接拒绝
- 如果未超 → 放行（此次可能略微超限，可接受）
- 流结束后 usage 自动写入 DB（现有逻辑）

---

## 三、复杂度评估

| 维度 | 评估 |
|---|---|
| Token 追踪基础设施 | **已有**，不需要写 |
| 计费公式 | **3 行核心代码**，简单数学 |
| 配额存储 | 复用 `config` 表，Key-Value 存储 |
| 检查逻辑 | 每次请求 1 次 SQL 聚合查询 |
| 改动范围 | 3-4 个文件，~100 行新代码 |
| 与现有代码耦合 | **极低**，纯拦截器模式，不改业务逻辑 |
| 重置周期 | 用 UTC+8 自然日，SQL DATE 函数即可 |

### 整体判定：**中低复杂度，完全可以做。**

---

## 四、配额配置设计

```json
{
  "quota.default.daily_token_budget_rmb": 1.0,
  "quota.default.daily_image_limit": 5,
  "quota.per_user": {
    "user-uuid-1": {
      "daily_token_budget_rmb": 2.0,
      "daily_image_limit": 10
    }
  }
}
```

存储在 `config` 表中，管理员通过 API 修改。默认值在 `config.py` 硬编码。

---

## 五、待确认项

1. DeepSeek 流式响应中 `prompt_tokens_details.cached_tokens` 的具体字段路径 — 需验证
2. 配额是否需要在管理后台有 GUI 界面，还是直接 API/DB 操作
3. 超限后是否给友好的提示信息（"您今天已用 ¥1.05，今日限额 ¥1.00"）
