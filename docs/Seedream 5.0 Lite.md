# Seedream 5.0 Lite API 技术文档

## 1. 概述
Seedream 5.0 Lite 是火山引擎推出的高性能文生图/图生图模型。支持同步与流式两种调用模式，无需轮询，直接返回结果。

- **接口地址**: `POST https://ark.cn-beijing.volces.com/api/v3/images/generations`
- **认证方式**: Header `Authorization: Bearer <API_KEY>`
- **内容类型**: `Content-Type: application/json`

---

## 2. 核心参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `model` | string | ✅ | 模型 ID (如 `doubao-seedream-5-0-lite-xxx`) |
| `prompt` | string | ✅ | 提示词 (建议 <300汉字 / <600英文单词) |
| `size` | string | ❌ | 分辨率: `1K`, `2K`, `4K` (默认 `1K`) |
| `n` | integer | ❌ | 生成数量 (默认 1) |
| `stream` | boolean | ❌ | **流式输出**: `true`(流式), `false`(同步, 默认) |
| `image` | array/string | ❌ | 参考图 URL 或 Base64 (支持多图融合) |
| `output_format` | string | ❌ | 格式: `png`, `jpeg` (默认 `png`) |
| `response_format` | string | ❌ | 返回格式: `url`, `b64_json` (默认 `url`) |
| `watermark` | boolean | ❌ | 是否添加水印 (默认 `true`) |

> **注意**: `stream`, `tools`, `sequential_image_generation` 仅 Lite 版本支持。

---

## 3. 调用模式

### 模式 A：同步调用 (推荐简单场景)
等待所有图片生成完毕后，一次性返回完整 JSON。

**请求示例:**
```bash
curl -X POST https://ark.cn-beijing.volces.com/api/v3/images/generations \
  -H "Authorization: Bearer $ARK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "doubao-seedream-5-0-lite-251128",
    "prompt": "一只在太空漫步的猫，赛博朋克风格",
    "size": "2K",
    "stream": false
  }'
```

**响应示例:**
```json
{
  "id": "img-xxxx",
  "data": [
    {
      "url": "https://.../image.png", 
      "revised_prompt": "..."
    }
  ]
}
```

### 模式 B：流式调用 (推荐多图/高延迟场景)
建立 SSE 连接，每生成一张图即时推送数据。

**请求示例:**
```json
{
  "model": "doubao-seedream-5-0-lite-251128",
  "prompt": "一组四季风景画",
  "n": 4,
  "stream": true
}
```

**响应特征:**
服务端会分块返回 `data:` 开头的 JSON 片段，客户端需逐行解析提取 `url`。

---

## 4. 高级功能

1. **图生图/多图融合**: 
   - 传入 `image` 字段（URL 数组或 Base64）。
   - 支持最多 14 张参考图。
2. **组图生成**: 
   - 设置 `sequential_image_generation: "auto"` 可自动生成关联系列图。
3. **联网搜索增强**: 
   - 设置 `tools: [{"type": "web_search"}]` 可让模型基于实时信息生成更准确的图像。

---

## 5. 注意事项

1. **链接有效期**: 返回的图片 URL 仅在 **24小时** 内有效，请及时下载保存。
2. **超时设置**: 建议客户端 HTTP 超时时间设置为 **60秒** 以上，以防高分辨率图片生成超时。
3. **错误处理**: 若返回 `4xx` 或 `5xx` 状态码，请检查 `error.message` 获取具体原因（如余额不足、提示词违规等）。
4. **异步误区**: 本接口**不需要**通过 `task_id` 进行轮询查询。

---