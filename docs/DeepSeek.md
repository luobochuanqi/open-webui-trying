# DeepSeek API

## 认证
`Authorization: Bearer ${DEEPSEEK_API_KEY}`

## 端点
OpenAI 格式 `https://api.deepseek.com`

## 模型

| 名称 | 说明 | 上下文 | 最大输出 |
|------|------|--------|---------|
| `deepseek-v4-flash` | 快速推理 | 1M | 384K |
| `deepseek-v4-pro` | 高性能推理 | 1M | 384K |

旧模型 `deepseek-chat` / `deepseek-reasoner` 即将弃用，对应 v4-flash。

## 价格 (每 1M tokens)

| 项目 | flash | pro |
|------|-------|-----|
| 输入(缓存命中) | 0.02元 | 0.025元 |
| 输入(缓存未命中) | 1元 | 3元 |
| 输出 | 2元 | 6元 |

## 并发限制
flash: 2500, pro: 500（账户级别，超限返回 429）

## 核心参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `model` | ✓ | `deepseek-v4-flash` 或 `deepseek-v4-pro` |
| `messages` | ✓ | 对话历史 |
| `max_tokens` | ✗ | 最大生成 token 数 |
| `temperature` | ✗ | 0-2，默认 1 |
| `top_p` | ✗ | 0-1，默认 1 |
| `stream` | ✗ | 默认 false |
| `stop` | ✗ | 最多 16 个 |
| `user_id` | ✗ | 用户隔离（格式 `[a-zA-Z0-9\-_]+`，最大 512 字符）(用不着) |

已弃用: `frequency_penalty`, `presence_penalty`

## 思考模式
```json
{"thinking": {"type": "enabled"}, "reasoning_effort": "high"}
```
- `type: "enabled"`（默认）或 `"disabled"`
- `reasoning_effort`: `"high"` 或 `"max"`

## JSON 输出
必须设置 `response_format: {"type": "json_object"}`，prompt 中需含 "json" 字样。

## 工具调用
标准 OpenAI 函数调用格式。Strict Mode (Beta): `base_url="https://api.deepseek.com/beta"` + `"strict": true`。

## 流式
SSE 格式，最后以 `data: [DONE]` 结束。可设置 `stream_options.include_usage: true` 获取 token 统计。

## Log Probs
```python
logprobs=True, top_logprobs=5  # 最多 20
```

## 响应字段
- `finish_reason`: `stop`, `length`, `content_filter`, `tool_calls`, `insufficient_system_resource`
- `reasoning_content`: 思考模式下的推理内容
- `usage`: `prompt_tokens`, `completion_tokens`, `prompt_cache_hit_tokens`, `prompt_cache_miss_tokens`, `completion_tokens_details.reasoning_tokens`

## 保活
非流式：持续返回空行；流式：SSE keep-alive 注释。10 分钟无推理则关闭连接。

## 错误码
400 请求体格式无效 → 修改请求体 | 401 API Key 错误 → 检查 Key | 402 余额不足 → 充值 | 422 参数无效 → 修改参数 | 429 请求过快 → 降频或换服务商 | 500 服务器错误 → 重试 | 503 过载 → 重试

## 最佳实践
- 简单任务用 flash，复杂推理用 pro
- 上下文缓存可大幅降低成本
- 大多数任务输出不超过 10K tokens
- 不要在 `user_id` 中包含隐私信息
- 环境变量管理 API Key
