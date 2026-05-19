# 大语言模型与翻译服务 API 配置完整教程

> **最后更新日期：2026年5月18日**
>
> 本教程涵盖当前主流大语言模型（LLM）及翻译服务的API配置步骤，包含详细的注册流程、密钥获取、代码示例、计费标准和常见问题解决方案。适合不同技术水平的开发者阅读和操作。

---

## 目录

1. [基础概念](#1-基础概念)
2. [DeepSeek API](#2-deepseek-api)
3. [通义千问 Qwen API](#3-通义千问-qwen-api)
4. [KIMI (Moonshot) API](#4-kimi-moonshot-api)
5. [智谱GLM API](#5-智谱glm-api)
6. [OpenAI API](#6-openai-api)
7. [Anthropic Claude API](#7-anthropic-claude-api)
8. [Google Gemini API](#8-google-gemini-api)
9. [百度文心一言 API](#9-百度文心一言-api)
10. [DeepL 翻译 API](#10-deepl-翻译-api)
11. [有道翻译 API](#11-有道翻译-api)
12. [安全最佳实践](#12-安全最佳实践)
13. [性能优化建议](#13-性能优化建议)
14. [多语言支持对比与选择建议](#14-多语言支持对比与选择建议)
15. [API服务状态监控](#15-api服务状态监控)
16. [常见错误代码速查表](#16-常见错误代码速查表)

---

## 1. 基础概念

在开始使用各个API之前，需要理解以下核心概念：

### 1.1 Token（词元）

Token是大模型处理文本的基本单位，不是按"字"或"词"来计算的：

| 语言 | Token换算 | 示例 |
|------|-----------|------|
| 英文 | 1 Token ≈ 0.75个单词（约4个字符） | "Hello, world!" ≈ 3-4 Token |
| 中文 | 1 Token ≈ 1-1.5个汉字 | "今天天气很好" ≈ 6 Token |

### 1.2 Context Window（上下文窗口）

模型一次能"记住"的最大文本量，包含输入和输出。主流模型的上下文窗口：

| 模型 | 上下文窗口 | 约等于中文字数 |
|------|------------|---------------|
| DeepSeek V4 | 1,000,000 tokens | ~75万字 |
| GPT-5.4 | 128,000 tokens | ~9.6万字 |
| Claude Opus 4.7 | 1,000,000 tokens | ~75万字 |
| Gemini 2.5 Pro | 1,000,000+ tokens | ~75万字 |
| Qwen3 Max | 256,000 tokens | ~19万字 |
| GLM-4-Plus | 128,000 tokens | ~9.6万字 |

### 1.3 Temperature（温度）

控制生成内容的随机性和创造性：

- **0 ~ 0.3**：确定性高，适合数据提取、分类、代码生成
- **0.3 ~ 0.7**：平衡创造性和准确性，适合一般对话、文案撰写
- **0.7 ~ 1.0**：创造性最高，适合创意写作、头脑风暴

### 1.4 认证方式

| 认证方式 | 说明 | 常见使用场景 |
|----------|------|-------------|
| API Key (Bearer Token) | 在HTTP Header中添加 `Authorization: Bearer <key>` | OpenAI、DeepSeek、KIMI等 |
| API Key + Secret Key | 先用Key换取Access Token，再用Token调用 | 百度文心一言、有道翻译 |
| OAuth 2.0 | 第三方授权 | 企业级应用 |

---

## 2. DeepSeek API

> **官网：** [https://platform.deepseek.com/](https://platform.deepseek.com/)
>
> **API文档：** [https://api-docs.deepseek.com/](https://api-docs.deepseek.com/)
>
> **最后更新：2026年5月**

### 2.1 简介

DeepSeek是深度求索公司推出的大语言模型，以高性能、低成本著称。API完全兼容OpenAI格式，迁移成本极低。当前主推V4系列模型。

### 2.2 注册与获取API密钥

**步骤1：访问官网并注册**

1. 打开浏览器，访问 [https://platform.deepseek.com/](https://platform.deepseek.com/)
2. 点击页面右上角的「注册/登录」按钮
3. 选择注册方式：支持手机号注册或微信扫码登录
4. 按提示完成注册流程，绑定手机号

**步骤2：创建API Key**

1. 登录后，在左侧菜单栏找到「API Keys」选项，点击进入
2. 点击「创建API Key」按钮
3. 在弹出的对话框中输入自定义名称（如"我的项目"、"测试用"等）
4. 点击确认创建
5. **重要：** API Key创建成功后只会显示一次，请立即复制并妥善保存到安全位置（如密码管理器）
6. 如果密钥丢失，只能重新创建新的API Key

> **截图获取提示：** 可在DeepSeek开放平台登录后，在API Keys页面截取密钥管理界面。建议模糊处理已显示的密钥内容。

### 2.3 可用模型

| 模型ID | 说明 | 上下文 | 最大输出 | 输入价格(/1M tokens) | 输出价格(/1M tokens) |
|--------|------|--------|----------|---------------------|---------------------|
| `deepseek-v4-flash` | 高速性价比模型 | 1M | 384K | $0.14 | $0.28 |
| `deepseek-v4-pro` | 旗舰推理模型 | 1M | 384K | $0.435 (75%折扣中) | $0.87 (75%折扣中) |
| `deepseek-chat` | ⚠️ 已弃用别名，映射到V4-Flash非思考模式，2026年7月24日后失效 | | | | |
| `deepseek-reasoner` | ⚠️ 已弃用别名，映射到V4-Flash思考模式，2026年7月24日后失效 | | | | |

**注意：** V4-Pro模型当前享有75%折扣，折扣有效期至2026年5月31日15:59 UTC。缓存命中（Cache Hit）价格仅为原价的1/10。

### 2.4 API调用示例

**Base URL：** `https://api.deepseek.com`

#### Python示例

```python
# 安装依赖：pip install openai

import os
from openai import OpenAI

# 从环境变量读取API Key（推荐方式，不要硬编码）
client = OpenAI(
    api_key=os.environ.get("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# 非流式调用
response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "你是一个有帮助的助手。"},
        {"role": "user", "content": "请用中文介绍一下深度学习的基本概念。"},
    ],
    temperature=0.7,
    max_tokens=2048,
    stream=False,
)

print(response.choices[0].message.content)

# 预期输出示例：
# 深度学习是机器学习的一个分支，它通过构建多层神经网络来学习数据的层次化表示...
```

**流式输出示例：**

```python
# 流式调用（适合需要打字机效果的场景）
stream = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "user", "content": "写一首关于人工智能的短诗。"},
    ],
    temperature=0.8,
    stream=True,
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

#### JavaScript (Node.js) 示例

```javascript
// 安装依赖：npm install openai

import OpenAI from 'openai';

const client = new OpenAI({
    apiKey: process.env.DEEPSEEK_API_KEY,
    baseURL: 'https://api.deepseek.com',
});

// 非流式调用
async function chatWithDeepSeek() {
    const response = await client.chat.completions.create({
        model: 'deepseek-v4-flash',
        messages: [
            { role: 'system', content: '你是一个有帮助的助手。' },
            { role: 'user', content: '请用中文介绍一下深度学习的基本概念。' },
        ],
        temperature: 0.7,
        max_tokens: 2048,
        stream: false,
    });

    console.log(response.choices[0].message.content);
}

chatWithDeepSeek();

// 流式调用
async function streamChat() {
    const stream = await client.chat.completions.create({
        model: 'deepseek-v4-flash',
        messages: [
            { role: 'user', content: '写一首关于人工智能的短诗。' },
        ],
        stream: true,
    });

    for await (const chunk of stream) {
        if (chunk.choices[0]?.delta?.content) {
            process.stdout.write(chunk.choices[0].delta.content);
        }
    }
}

streamChat();
```

#### cURL 示例

```bash
curl https://api.deepseek.com/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -d '{
    "model": "deepseek-v4-flash",
    "messages": [
      {"role": "system", "content": "你是一个有帮助的助手。"},
      {"role": "user", "content": "你好！"}
    ],
    "stream": false
  }'
```

### 2.5 计费标准

| 计费项 | deepseek-v4-flash | deepseek-v4-pro (折扣价) |
|--------|-------------------|--------------------------|
| 输入 (缓存未命中) | $0.14 / 1M tokens | $0.435 / 1M tokens |
| 输入 (缓存命中) | $0.0028 / 1M tokens | $0.003625 / 1M tokens |
| 输出 | $0.28 / 1M tokens | $0.87 / 1M tokens |

**费用计算示例：** 假如一次对话，输入1000 tokens，输出500 tokens（使用v4-flash）：
- 费用 = (1000/1000000 × $0.14) + (500/1000000 × $0.28) = $0.00014 + $0.00014 = $0.00028（约0.002元人民币）

### 2.6 调用限制

- 新注册账号赠送500万 tokens免费额度
- 具体RPM（每分钟请求数）和TPM（每分钟Token数）限制可在平台控制台查看
- 超过限制将返回429错误

### 2.7 常见错误及解决方案

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| 401 | API Key无效或未提供 | 检查API Key是否正确设置，确认Key未过期 |
| 429 | 请求频率超限 | 降低请求频率，实现指数退避重试 |
| 400 | 请求参数错误 | 检查请求体JSON格式，确认model参数正确 |
| 500 | 服务器内部错误 | 等待几分钟后重试，如持续出现联系官方支持 |
| 503 | 服务暂时不可用 | 实现重试机制，采用指数退避策略 |

---

## 3. 通义千问 Qwen API

> **官网：** [https://tongyi.aliyun.com/](https://tongyi.aliyun.com/)
>
> **API文档：** [https://help.aliyun.com/document_detail/610978.html](https://help.aliyun.com/document_detail/610978.html)
>
> **最后更新：2026年4月（Qwen3.6系列）**

### 3.1 简介

通义千问（Qwen）是阿里云推出的自研大语言模型系列，具备强大的中文理解和生成能力。通过DashScope（灵积）平台提供API服务，兼容OpenAI接口格式。

### 3.2 注册与获取API密钥

**步骤1：注册阿里云账号**

1. 访问 [https://www.aliyun.com/](https://www.aliyun.com/)
2. 点击右上角「免费注册」
3. 按指引完成账号注册和实名认证（需要手机号和身份证信息）
4. 实名认证通常在5分钟内完成审核

**步骤2：开通DashScope服务**

1. 访问 [https://dashscope.console.aliyun.com/overview](https://dashscope.console.aliyun.com/overview)
2. 点击「去开通」按钮
3. 阅读服务协议后勾选确认，点击开通
4. 开通成功后，系统会赠送100万tokens免费额度（有效期30天）

**步骤3：创建API Key**

1. 访问 [https://dashscope.console.aliyun.com/apiKey](https://dashscope.console.aliyun.com/apiKey)
2. 点击「创建新的API-KEY」按钮
3. 在弹出的对话框中填写自定义名称（如"我的应用"）
4. 点击确定创建
5. **重要：** API Key创建后立即复制保存，关闭页面后将无法再次查看完整密钥

> **截图获取提示：** 登录阿里云DashScope控制台，在API-KEY管理页面可截取密钥列表。建议对密钥内容打码处理。

### 3.3 可用模型与计费

| 模型ID | 说明 | 上下文 | 输入价格(元/千tokens) | 输出价格(元/千tokens) |
|--------|------|--------|----------------------|----------------------|
| `qwen3.6-flash` | 最新高速模型，支持深度思考和视觉识别 | 256K | 视具体阶梯 | 视具体阶梯 |
| `qwen3.6-plus` | 增强版，支持深度思考和视觉理解 | 256K | 阶梯计费 | 阶梯计费 |
| `qwen3-max` | 旗舰模型，最强推理能力 | 256K | ≤32K: 0.00335，32K-128K: 0.00675，>128K: 0.01 | ≤32K: 0.0135，32K-128K: 0.0268，>128K: 0.04 |
| `qwen-plus` | 性能均衡 | 128K | 0.004 | 0.012 |
| `qwen-turbo` | 速度快、成本低 | 128K | 0.002 | 0.006 |
| `qwen-long` | 长文本优化，极高性价比 | 10M | 0.0005 | 0.002 |

### 3.4 API调用示例

**Base URL：** `https://dashscope.aliyuncs.com/compatible-mode/v1`（兼容OpenAI格式）

#### Python示例（使用OpenAI SDK）

```python
# 安装依赖：pip install openai

import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("DASHSCOPE_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 非流式调用
response = client.chat.completions.create(
    model="qwen-plus",
    messages=[
        {"role": "system", "content": "你是一个专业的学术助手。"},
        {"role": "user", "content": "请解释什么是注意力机制（Attention Mechanism）。"},
    ],
    temperature=0.5,
    max_tokens=2048,
)

print(response.choices[0].message.content)

# 预期输出示例：
# 注意力机制是深度学习中的一种技术，灵感来源于人类的视觉注意力...
```

**流式输出示例：**

```python
# 流式调用
stream = client.chat.completions.create(
    model="qwen-turbo",
    messages=[
        {"role": "user", "content": "介绍一下杭州西湖。"},
    ],
    temperature=0.7,
    stream=True,
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

#### JavaScript (Node.js) 示例

```javascript
// 安装依赖：npm install openai

import OpenAI from 'openai';

const client = new OpenAI({
    apiKey: process.env.DASHSCOPE_API_KEY,
    baseURL: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
});

async function chatWithQwen() {
    const response = await client.chat.completions.create({
        model: 'qwen-plus',
        messages: [
            { role: 'system', content: '你是一个专业的学术助手。' },
            { role: 'user', content: '请解释什么是注意力机制。' },
        ],
        temperature: 0.5,
        max_tokens: 2048,
    });

    console.log(response.choices[0].message.content);
}

chatWithQwen();
```

### 3.5 使用注意事项

1. **阶梯计费：** Qwen3 Max等模型采用阶梯计费，输入越长单价越高，建议控制输入长度
2. **免费额度：** 开通DashScope一次性赠送100万tokens，有效期30天
3. **AccessKey鉴权：** 除了API-Key，还可以使用阿里云的AccessKey ID + AccessKey Secret方式鉴权，适用于企业级应用
4. **区域选择：** 国内用户使用默认Endpoint即可，延迟极低

### 3.6 常见错误及解决方案

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| 401 | API Key无效 | 检查Key是否正确复制，确认未过期 |
| 400 | InvalidParameter | 检查model参数是否正确，确认模型可用 |
| 429 | Throttling | 降低请求频率，实现重试逻辑 |
| 500 | InternalError | 稍后重试 |

---

## 4. KIMI (Moonshot) API

> **官网：** [https://platform.moonshot.ai/](https://platform.moonshot.ai/)
>
> **API文档：** [https://platform.moonshot.ai/docs](https://platform.moonshot.ai/docs)
>
> **最后更新：2025年11月（KIMI K2系列）**

### 4.1 简介

KIMI是月之暗面（Moonshot AI）公司开发的大语言模型，以超长上下文处理能力著称（最高256K tokens）。K2系列是最新主力模型，在编程和Agent任务上表现出色。API兼容OpenAI格式。

### 4.2 注册与获取API密钥

**步骤1：注册Moonshot账号**

1. 访问 [https://platform.moonshot.ai/](https://platform.moonshot.ai/)
2. 点击「注册」按钮
3. 选择注册方式：
   - Google账号一键登录（推荐国际用户）
   - 手机号注册（国内用户，支持+86手机号）
   - 邮箱注册
4. 按提示完成注册流程

**步骤2：创建API Key**

1. 登录后进入控制台（Console）
2. 在左侧导航栏或顶部菜单找到「API Keys」或「密钥管理」
3. 点击「创建API Key」按钮
4. 输入API Key名称（如"开发测试"）
5. 点击确认创建
6. 立即复制并保存API Key，关闭后无法再次查看

**步骤3：绑定手机号（推荐）**

- 建议在账户设置中绑定手机号，便于后续管理账户和查看使用情况

> **截图获取提示：** 在Moonshot开放平台控制台的API Keys页面可截图。注意对密钥内容进行模糊处理。

### 4.3 可用模型与计费

| 模型 | 说明 | 上下文 | 输入价格(/1M tokens) | 输出价格(/1M tokens) |
|------|------|--------|---------------------|---------------------|
| `kimi-k2-thinking` | K2思考模型，复杂推理、Agent任务 | 256K | $0.15(缓存命中) ~ $2.40(缓存未命中) | $10.00 |
| `kimi-k2-thinking-turbo` | K2思考极速版，速度更快 | 256K | $0.15(缓存命中) / $1.15(缓存未命中) | $8.00 |
| `kimi-k2-turbo` | K2极速版 | 256K | $0.15(缓存命中) / $1.15(缓存未命中) | $8.00 |
| `moonshot-v1-128k` | 旧版128K上下文模型 | 128K | ¥0.012/千tokens(~$0.15/1M) | ¥0.018/千tokens(~$0.25/1M) |
| `moonshot-v1-32k` | 旧版32K上下文模型 | 32K | ¥0.004/千tokens | ¥0.006/千tokens |
| `moonshot-v1-8k` | 旧版8K上下文模型 | 8K | ¥0.004/千tokens | ¥0.006/千tokens |

**注意：** 旧版moonshot-v1系列模型需要将base_url设置为 `https://api.moonshot.cn/v1`，K2系列模型使用新版API地址。

### 4.4 API调用示例

**Base URL（K2系列）：** `https://api.moonshot.ai/v1`

#### Python示例（使用OpenAI SDK）

```python
# 安装依赖：pip install openai

import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("MOONSHOT_API_KEY"),
    base_url="https://api.moonshot.ai/v1",
)

# 非流式调用
response = client.chat.completions.create(
    model="kimi-k2-thinking-turbo",
    messages=[
        {"role": "system", "content": "你是一个编程助手，擅长代码生成和调试。"},
        {"role": "user", "content": "用Python写一个快速排序算法，并加上中文注释。"},
    ],
    temperature=0.3,
    max_tokens=2048,
)

print(response.choices[0].message.content)

# 预期输出示例：
# ```python
# def quick_sort(arr):
#     """快速排序算法"""
#     if len(arr) <= 1:
#         return arr
#     pivot = arr[len(arr) // 2]  # 选择中间元素作为基准
#     left = [x for x in arr if x < pivot]   # 小于基准的放左边
#     middle = [x for x in arr if x == pivot] # 等于基准的放中间
#     right = [x for x in arr if x > pivot]   # 大于基准的放右边
#     return quick_sort(left) + middle + quick_sort(right)
# ```
```

#### JavaScript (Node.js) 示例

```javascript
import OpenAI from 'openai';

const client = new OpenAI({
    apiKey: process.env.MOONSHOT_API_KEY,
    baseURL: 'https://api.moonshot.ai/v1',
});

async function codeGeneration() {
    const response = await client.chat.completions.create({
        model: 'kimi-k2-thinking-turbo',
        messages: [
            { role: 'system', content: '你是一个编程助手。' },
            { role: 'user', content: '用Python写一个快速排序算法，加上中文注释。' },
        ],
        temperature: 0.3,
        max_tokens: 2048,
    });

    console.log(response.choices[0].message.content);
}

codeGeneration();
```

### 4.5 超长上下文处理技巧

KIMI模型支持256K tokens的超长上下文，适合处理大型代码库、长文档分析等场景。使用建议：

```python
# 处理长文档时，将内容分段按角色组织
response = client.chat.completions.create(
    model="kimi-k2-thinking-turbo",
    messages=[
        {"role": "system", "content": "你是一个代码审查专家，请分析以下代码库。"},
        {"role": "user", "content": f"请分析这个项目的架构：\n\n{codebase_content}"},
    ],
    temperature=0.3,
    max_tokens=4096,
)
```

### 4.6 常见错误及解决方案

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| 401 Unauthorized | API Key无效 | 检查Key是否正确、是否已过期 |
| 429 Rate Limit | 超RPM/TPM限制 | 降低频率，实现指数退避重试 |
| 400 Bad Request | 参数错误或模型不存在 | 检查model名称是否正确 |
| 413 Payload Too Large | 请求体过大 | 缩减输入内容长度 |

---

## 5. 智谱GLM API

> **官网：** [https://open.bigmodel.cn/](https://open.bigmodel.cn/)
>
> **API文档：** [https://docs.bigmodel.cn/](https://docs.bigmodel.cn/)
>
> **最后更新：2025年11月（GLM-4.6系列）**

### 5.1 简介

智谱AI由清华大学技术团队孵化，推出的GLM系列大模型在中文语义理解、逻辑推理和多轮对话方面具有显著优势。平台提供免费模型GLM-4-Flash，是入门学习的绝佳选择。

### 5.2 注册与获取API密钥

**步骤1：注册智谱开放平台账号**

1. 访问 [https://open.bigmodel.cn/](https://open.bigmodel.cn/)
2. 点击右上角的「注册/登录」按钮
3. 支持手机号注册
4. 按提示完成注册流程

**步骤2：获取API Key**

1. 登录后，在个人中心页面或直接访问 [https://bigmodel.cn/usercenter/proj-mgmt/apikeys](https://bigmodel.cn/usercenter/proj-mgmt/apikeys)
2. 点击「API Keys」选项
3. 点击「创建新的API Key」
4. 输入名称后点击确认
5. **立即复制保存API Key**，妥善保管

> **截图获取提示：** 登录智谱开放平台后，在个人中心的API Keys页面可截取。注意打码处理密钥内容。

### 5.3 可用模型与计费

| 模型ID | 说明 | 上下文 | 价格(元/百万tokens) |
|--------|------|--------|---------------------|
| `GLM-4.6` | 最新旗舰，355B参数，200K上下文 | 200K | 输入2.12，缓存命中0.424，输出6.36 |
| `GLM-5.1` | 通用旗舰大语言模型 | 128K | 视具体套餐 |
| `glm-4-plus` | 高性能模型 | 128K | 5元/百万tokens |
| `glm-4-air-250414` | 高性价比模型 | 128K | 0.5元/百万tokens |
| `glm-4-airx` | 极速推理版 | 8K | 10元/百万tokens |
| `glm-4-flashx-250414` | 高速低价模型 | 128K | 0.1元/百万tokens |
| `glm-4-flash` | **免费模型** | 128K | **免费** |

### 5.4 API调用示例

**Base URL：** `https://open.bigmodel.cn/api/paas/v4`

#### Python示例

```python
# 安装依赖：pip install openai

import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("ZHIPU_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4",
)

# 使用付费模型 glm-4-plus
response = client.chat.completions.create(
    model="glm-4-plus",
    messages=[
        {"role": "system", "content": "你是一个乐于解答各种问题的助手，你的任务是为用户提供专业、准确、有见地的建议。"},
        {"role": "user", "content": "你好，请介绍一下自己。"},
    ],
    max_tokens=4096,
    temperature=0.7,
)

print(response.choices[0].message.content)

# 预期输出示例：
# 你好！我是智谱AI开发的智能助手，基于GLM-4大语言模型...

# 使用免费模型 glm-4-flash（零成本入门）
free_response = client.chat.completions.create(
    model="glm-4-flash",
    messages=[
        {"role": "user", "content": "用一句话解释什么是机器学习。"},
    ],
    max_tokens=500,
    temperature=0.5,
)

print(free_response.choices[0].message.content)
# 预期输出：机器学习是一种让计算机从数据中自动学习规律和模式的技术...
```

#### JavaScript (Node.js) 示例

```javascript
import OpenAI from 'openai';

const client = new OpenAI({
    apiKey: process.env.ZHIPU_API_KEY,
    baseURL: 'https://open.bigmodel.cn/api/paas/v4',
});

async function chatWithGLM() {
    // 使用免费模型
    const response = await client.chat.completions.create({
        model: 'glm-4-flash',
        messages: [
            { role: 'user', content: '用一句话解释什么是机器学习。' },
        ],
        max_tokens: 500,
        temperature: 0.5,
    });

    console.log(response.choices[0].message.content);
}

chatWithGLM();
```

### 5.5 特色功能

- **GLM-4-Flash免费模型：** 零成本使用，128K上下文，适合学习和原型验证
- **深度思考（Thinking Mode）：** 支持链式推理，适合复杂逻辑问题
- **工具调用（Function Calling）：** 强大的工具调用能力，支持外部工具集成
- **流式输出：** 支持实时流式响应，提升用户交互体验
- **联网搜索：** 支持实时网页检索

### 5.6 常见错误及解决方案

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| 401 | API Key无效 | 检查Key配置 |
| 429 | 请求频率超限 | 降低频率，使用免费模型需注意限制 |
| 400 | 参数错误 | 检查model名称和参数格式 |

---

## 6. OpenAI API

> **官网：** [https://platform.openai.com/](https://platform.openai.com/)
>
> **API文档：** [https://platform.openai.com/docs](https://platform.openai.com/docs)
>
> **最后更新：2026年5月（GPT-5.4系列）**

### 6.1 简介

OpenAI是全球领先的AI研究公司，GPT系列模型是业界标杆。当前最新主打模型为GPT-5.4系列（旗舰、Mini、Nano），以及多模态的GPT-Realtime、GPT-Image等。API生态最为成熟，文档最完善。

### 6.2 注册与获取API密钥

**步骤1：注册OpenAI账号**

1. 访问 [https://platform.openai.com/](https://platform.openai.com/)
2. 点击「Sign up」注册账号
3. 使用邮箱注册，或通过Google/Microsoft/Apple账号登录
4. 完成邮箱验证

**步骤2：创建API Key**

1. 登录后，访问 [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. 点击「Create new secret key」按钮
3. 在弹出的对话框中输入自定义名称（可选）
4. 点击「Create secret key」
5. **立即复制API Key并安全保存**，此密钥仅显示一次
6. 格式为 `sk-...` 开头

**步骤3：设置付款方式（必需）**

1. 访问 [https://platform.openai.com/settings/organization/billing](https://platform.openai.com/settings/organization/billing)
2. 添加付款方式（支持国际信用卡）
3. 设置使用限额（Usage Limits）以防止意外超额消费

> **注意：** 国内用户访问OpenAI需要使用合规的网络工具，注册可能需要海外手机号验证。建议通过合规渠道注册使用。

> **截图获取提示：** 在OpenAI Platform的API Keys页面可截图。务必对密钥内容完全打码。

### 6.3 可用模型与计费

**标准层级（Standard Tier）价格，单位：$/1M tokens**

| 模型 | 输入价格 | 缓存输入 | 输出价格 | 上下文 |
|------|----------|----------|----------|--------|
| GPT-5.4 (短上下文) | $2.50 | $0.25 | $15.00 | 128K |
| GPT-5.4 (长上下文) | $5.00 | $0.50 | $22.50 | 128K+ |
| GPT-5.4 Mini | $0.75 | $0.075 | $4.50 | 128K |
| GPT-5.4 Nano | $0.20 | $0.02 | $1.25 | 128K |
| GPT-5.4 Pro | $30.00 | - | $180.00 | 128K |
| GPT-Image-1.5 (图像) | $8.00 | $2.00 | $32.00 | - |
| GPT-Image-1.5 (文本) | $5.00 | $1.25 | $10.00 | - |

**Batch API（50%折扣）：**

使用Batch API异步处理24小时内的任务，输入和输出费用可节省50%。

### 6.4 API调用示例

**Base URL：** `https://api.openai.com/v1`

#### Python示例

```python
# 安装依赖：pip install openai

import os
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 使用GPT-5.4 Mini（高性价比）
response = client.chat.completions.create(
    model="gpt-5.4-mini",
    messages=[
        {"role": "system", "content": "你是一个有帮助的助手。"},
        {"role": "user", "content": "请用通俗的语言解释什么是气候变化。"},
    ],
    temperature=0.7,
    max_tokens=1000,
)

print(response.choices[0].message.content)

# 预期输出示例：
# 气候变化是指地球长期天气模式发生的变化...
```

**流式输出示例：**

```python
stream = client.chat.completions.create(
    model="gpt-5.4-mini",
    messages=[
        {"role": "user", "content": "写一篇200字的关于环境保护的短文。"},
    ],
    stream=True,
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

#### JavaScript (Node.js) 示例

```javascript
import OpenAI from 'openai';

const client = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
});

async function chatWithGPT() {
    const stream = await client.chat.completions.create({
        model: 'gpt-5.4-mini',
        messages: [
            { role: 'user', content: '写一篇200字的关于环境保护的短文。' },
        ],
        stream: true,
    });

    for await (const chunk of stream) {
        if (chunk.choices[0]?.delta?.content) {
            process.stdout.write(chunk.choices[0].delta.content);
        }
    }
}

chatWithGPT();
```

### 6.5 服务层级说明

| 层级 | 特点 | 适用场景 |
|------|------|----------|
| **Batch** (最便宜) | 异步24小时内返回，50%折扣 | 大批量离线处理 |
| **Flex** | 价格折半但速度较慢/不稳定 | 非生产环境、内部工具 |
| **Standard** (默认) | 标准速度和成本 | 面向用户的应用 |
| **Priority** (最快) | 更快更稳定，价格2倍 | 关键任务应用 |

### 6.6 常见错误及解决方案

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| 401 Incorrect API key | API Key无效 | 重新生成Key |
| 429 Rate limit reached | 频率超限 | 降低频率，升级Tier |
| 402 Insufficient quota | 额度不足 | 检查账单，充值 |
| 500 Server Error | 服务端错误 | 实现重试逻辑 |

---

## 7. Anthropic Claude API

> **官网：** [https://console.anthropic.com/](https://console.anthropic.com/)
>
> **API文档：** [https://docs.anthropic.com/](https://docs.anthropic.com/)
>
> **最后更新：2026年（Claude Opus 4.7）**

### 7.1 简介

Claude是Anthropic公司开发的大语言模型系列，以安全性、诚实性和代码理解能力著称。最新旗舰模型为Claude Opus 4.7，支持1M tokens上下文窗口。

### 7.2 注册与获取API密钥

**步骤1：注册Anthropic账号**

1. 访问 [https://console.anthropic.com/](https://console.anthropic.com/)
2. 点击「Sign Up」注册账号
3. 使用邮箱注册
4. 完成邮箱验证

**步骤2：获取API Key**

1. 登录Console后，在左侧导航栏找到「API Keys」
2. 点击「Create Key」按钮
3. 输入名称后确认
4. **立即复制API Key**并安全保存

> **注意：** Claude API目前不在中国大陆直接提供服务，需要通过合规渠道访问。新注册账号通常赠送免费试用额度。

> **截图获取提示：** 在Anthropic Console的API Keys管理页面可截图。

### 7.3 可用模型与计费

| 模型 | 说明 | 上下文 | 最大输出 | 输入(/1M tokens) | 输出(/1M tokens) |
|------|------|--------|----------|------------------|------------------|
| `claude-opus-4-7` | 最强通用模型，代理编码 | 1M | 128K | $5 | $25 |
| `claude-sonnet-4-6` | 速度与智能平衡 | 1M | 64K | $3 | $15 |
| `claude-haiku-4-5` | 最快模型，接近前沿智能 | 200K | 64K | $1 | $5 |

### 7.4 API调用示例

**Base URL：** `https://api.anthropic.com`

#### Python示例

```python
# 安装依赖：pip install anthropic

import os
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    system="你是一个有帮助的助手。",
    messages=[
        {"role": "user", "content": "请用中文解释量子计算的基本原理。"},
    ],
)

print(response.content[0].text)

# 预期输出示例：
# 量子计算是一种利用量子力学原理进行信息处理的新型计算方式...
```

**流式输出示例：**

```python
with client.messages.stream(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "写一首关于星空的短诗。"},
    ],
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

#### JavaScript (Node.js) 示例

```javascript
// 安装依赖：npm install @anthropic-ai/sdk

import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic({
    apiKey: process.env.ANTHROPIC_API_KEY,
});

async function chatWithClaude() {
    const response = await client.messages.create({
        model: 'claude-sonnet-4-6',
        max_tokens: 1024,
        system: '你是一个有帮助的助手。',
        messages: [
            { role: 'user', content: '请用中文解释量子计算的基本原理。' },
        ],
    });

    console.log(response.content[0].text);
}

chatWithClaude();
```

### 7.5 特色功能

- **扩展思考（Extended Thinking）：** Sonnet和Haiku支持，适合复杂推理
- **批量处理API（Message Batches）：** 50%折扣
- **提示词缓存：** 可降低高达90%成本
- **视觉能力：** 所有模型支持图像输入

### 7.6 常见错误

| 错误 | 解决方案 |
|------|----------|
| 401 Unauthorized | 检查API Key |
| 429 Rate Limit | 降低频率 |
| 400 Bad Request | 检查参数格式 |

---

## 8. Google Gemini API

> **官网：** [https://aistudio.google.com/](https://aistudio.google.com/)
>
> **API文档：** [https://ai.google.dev/gemini-api/docs](https://ai.google.dev/gemini-api/docs)
>
> **最后更新：2025年11月（Gemini 3 Pro Preview）**

### 8.1 简介

Google Gemini是多模态大语言模型，支持文本、图像、音频和视频输入。免费层级慷慨，上下文窗口高达100万tokens，是开发测试和原型验证的理想选择。

### 8.2 注册与获取API密钥

**步骤1：访问Google AI Studio**

1. 打开浏览器，访问 [https://aistudio.google.com/](https://aistudio.google.com/)
2. 使用Google账号登录（没有的话先创建Google账号）
3. 首次访问需要同意服务条款

**步骤2：获取API Key**

1. 登录后，在左侧点击「Get API key」按钮
2. 系统会提示选择或创建Google Cloud项目
3. 选择「Create API key in new project」（最简单）
4. API Key立即生成并显示
5. **立即复制并安全保存**，格式为 `AIza...` 开头（39个字符）

> **截图获取提示：** 在Google AI Studio的API Keys页面可截取。注意打码处理。

### 8.3 免费层级限制

| 项目 | Gemini 2.5 Flash | Gemini 2.5 Pro |
|------|-----------------|----------------|
| 每分钟请求数(RPM) | 15 | 5 |
| 每天请求数(RPD) | 1,500 | 25 |
| 每分钟Token数(TPM) | 1,000,000 | 32,000 |
| 免费试用期 | 永久 | 90天 |

### 8.4 API调用示例

#### Python示例

```python
# 安装依赖：pip install google-generativeai

import os
import google.generativeai as genai

# 配置API Key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# 创建模型实例
model = genai.GenerativeModel('gemini-2.5-flash')

# 生成文本
response = model.generate_content("请用中文介绍Google Gemini模型的特点。")
print(response.text)

# 预期输出示例：
# Google Gemini是谷歌开发的多模态大语言模型，主要特点包括...
```

**多轮对话示例：**

```python
# 开启对话模式
chat = model.start_chat(history=[
    {"role": "user", "parts": ["你好"]},
    {"role": "model", "parts": ["你好！有什么我可以帮助你的吗？"]},
])

response = chat.send_message("介绍一下Transformer架构。")
print(response.text)

# 继续对话
response = chat.send_message("它在NLP中的应用有哪些？")
print(response.text)
```

**流式输出：**

```python
response = model.generate_content(
    "写一篇100字的关于人工智能的短文。",
    stream=True,
)

for chunk in response:
    if chunk.text:
        print(chunk.text, end="", flush=True)
```

#### JavaScript (Node.js) 示例

```javascript
// 安装依赖：npm install @google/generative-ai

import { GoogleGenerativeAI } from '@google/generative-ai';

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const model = genAI.getGenerativeModel({ model: 'gemini-2.5-flash' });

async function chatWithGemini() {
    const result = await model.generateContent(
        '请用中文介绍Google Gemini模型的特点。'
    );
    console.log(result.response.text());
}

chatWithGemini();
```

### 8.5 常见错误

| 错误 | 解决方案 |
|------|----------|
| 403 Forbidden | 检查API Key权限，确认项目已启用API |
| 429 Resource Exhausted | 达到免费层级限制，等待配额重置（太平洋时间0点） |
| 400 Invalid Argument | 检查请求参数 |

---

## 9. 百度文心一言 API

> **官网：** [https://cloud.baidu.com/](https://cloud.baidu.com/)
>
> **千帆平台：** [https://console.bce.baidu.com/qianfan](https://console.bce.baidu.com/qianfan)
>
> **最后更新：2026年4月**

### 9.1 简介

文心一言（ERNIE Bot）是百度推出的大语言模型产品，在中文理解、知识问答等方面表现优异。通过百度智能云千帆大模型平台提供服务，需要两步认证（API Key + Secret Key → Access Token）。

### 9.2 注册与获取API密钥

**步骤1：注册百度智能云账号**

1. 访问 [https://cloud.baidu.com/](https://cloud.baidu.com/)
2. 点击「注册」，使用手机号注册百度账号
3. 完成实名认证（上传身份证正反面照片）
4. 认证通常在5分钟内完成

**步骤2：开通千帆大模型服务**

1. 登录百度智能云控制台
2. 在搜索栏输入「千帆」，进入「千帆大模型平台」
3. 点击「立即开通」
4. 阅读服务协议后勾选确认，完成开通

**步骤3：创建应用获取密钥**

1. 进入千帆控制台，左侧导航栏选择「应用接入」
2. 点击「创建应用」按钮
3. 填写应用名称（如"我的AI助手"）和描述
4. 选择需要调用的模型服务
5. 点击确认创建
6. 创建成功后页面显示 **API Key** 和 **Secret Key**
7. **重要：** Secret Key仅首次可见，务必立即复制备份！

> **截图获取提示：** 在千帆平台的应用详情页可截取密钥信息。必须对Secret Key完全打码。

### 9.3 可用模型

| 模型 | 说明 |
|------|------|
| ERNIE-4.0-8K | 旗舰模型，8K上下文 |
| ERNIE-4.0-Turbo-8K | 极速版 |
| ERNIE-3.5-8K | 性价比之选 |
| ERNIE-Speed-8K | 最快速的轻量模型 |

### 9.4 鉴权流程

文心一言API使用两步鉴权：
1. 使用API Key + Secret Key换取Access Token（有效期30天）
2. 使用Access Token调用API

### 9.5 API调用示例

#### Python示例

```python
# 安装依赖：pip install requests

import requests
import json

API_KEY = "your_api_key"
SECRET_KEY = "your_secret_key"

# 步骤1：获取Access Token
def get_access_token(api_key, secret_key):
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": api_key,
        "client_secret": secret_key,
    }
    response = requests.post(url, params=params)
    return response.json().get("access_token")

# 步骤2：调用文心一言API
def chat_with_ernie(access_token, message):
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-4.0-8k"
    url += f"?access_token={access_token}"

    payload = json.dumps({
        "messages": [
            {"role": "user", "content": message}
        ],
        "temperature": 0.5,
    })

    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.post(url, headers=headers, data=payload)
    return response.json()

# 使用示例
access_token = get_access_token(API_KEY, SECRET_KEY)
result = chat_with_ernie(access_token, "你好，请介绍一下你自己。")
print(result.get("result"))

# 预期输出示例：
# 你好！我是文心一言，百度开发的大语言模型...
```

**使用千帆SDK（推荐方式）：**

```python
# 安装依赖：pip install qianfan

import os
import qianfan

# 方式一：【推荐】使用安全认证AK/SK鉴权
os.environ["QIANFAN_ACCESS_KEY"] = "your_iam_ak"
os.environ["QIANFAN_SECRET_KEY"] = "your_iam_sk"

# 方式二：使用应用AK/SK鉴权
# os.environ["QIANFAN_AK"] = "应用API_Key"
# os.environ["QIANFAN_SK"] = "应用Secret_Key"

chat_comp = qianfan.ChatCompletion()

response = chat_comp.do(
    model="ERNIE-4.0-8K",
    messages=[
        {"role": "user", "content": "你好，请介绍一下你自己。"}
    ],
    temperature=0.5,
)

print(response["result"])
```

#### JavaScript (Node.js) 示例

```javascript
// 安装依赖：npm install axios

import axios from 'axios';

const API_KEY = 'your_api_key';
const SECRET_KEY = 'your_secret_key';

// 获取Access Token
async function getAccessToken() {
    const response = await axios.post(
        'https://aip.baidubce.com/oauth/2.0/token',
        null,
        {
            params: {
                grant_type: 'client_credentials',
                client_id: API_KEY,
                client_secret: SECRET_KEY,
            },
        }
    );
    return response.data.access_token;
}

// 调用文心一言
async function chatWithERNIE(message) {
    const accessToken = await getAccessToken();
    const url = `https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/ernie-4.0-8k?access_token=${accessToken}`;

    const response = await axios.post(url, {
        messages: [{ role: 'user', content: message }],
        temperature: 0.5,
    });

    console.log(response.data.result);
}

chatWithERNIE('你好，请介绍一下你自己。');
```

### 9.6 常见错误

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| 110 | Access Token无效 | 重新获取Token |
| 111 | Access Token过期 | Token有效期30天，重新获取 |
| 100 | 参数错误 | 检查请求参数 |
| 17 | 日调用量超限 | 检查配额，等待次日重置 |

---

## 10. DeepL 翻译 API

> **官网：** [https://www.deepl.com/pro-api](https://www.deepl.com/pro-api)
>
> **API文档：** [https://developers.deepl.com/](https://developers.deepl.com/)
>
> **最后更新：2026年5月**

### 10.1 简介

DeepL是全球领先的机器翻译服务，以翻译质量高、语义理解准确著称。支持超过30种语言的互译，提供文本翻译和文档翻译（DOCX、PPTX等格式）。提供免费和付费两种API方案。

### 10.2 注册与获取API密钥

**步骤1：注册DeepL API账号**

1. 访问 [https://www.deepl.com/pro-api](https://www.deepl.com/pro-api)
2. 浏览API方案，选择合适的计划
3. **注意：** 如果你已有DeepL Translator（网页翻译）账号，需要**退出后重新创建独立的API账号**
4. 点击对应方案的「注册」按钮
5. 填写邮箱、密码等基本信息
6. 完成邮箱验证

**步骤2：选择方案（Free vs Pro）**

| 版本 | 特点 | 限制 | 价格 |
|------|------|------|------|
| DeepL API Free | 免费使用 | 每月500,000字符 | 免费 |
| DeepL API Pro | 无限制、支持商业用途 | 无字符上限 | 按使用量计费 |

**Free版Key特征：** 以 `:fx` 结尾，如 `279a2e9d-83b3-c416-7e2d-f721593e42a0:fx`

**步骤3：获取API Key**

1. 登录后，访问账户设置页面或直接访问 [https://www.deepl.com/your-account/keys](https://www.deepl.com/your-account/keys)
2. 在「API Keys」标签页中查看已有Key或点击创建新Key
3. 可创建多个API Key
4. 免费用户最多2个活跃Key
5. 点击复制Key并安全保存

> **截图获取提示：** 在DeepL账户的API Keys页面截图。注意打码处理。

### 10.3 API Endpoint

| 版本 | Endpoint |
|------|----------|
| API Free | `https://api-free.deepl.com` |
| API Pro | `https://api.deepl.com` |

### 10.4 API调用示例

#### Python示例

```python
# 方式一：使用官方Python SDK（推荐）
# 安装依赖：pip install deepl

import deepl

# 认证密钥从环境变量读取
auth_key = "your-auth-key"  # 生产环境请使用环境变量
deepl_client = deepl.DeepLClient(auth_key)

# 翻译文本
result = deepl_client.translate_text(
    "Hello, world!",
    target_lang="ZH"  # 目标语言：中文
)
print(result.text)  # 输出：你好，世界！
print(f"检测到的源语言：{result.detected_source_lang}")
print(f"计费字符数：{result.billed_characters}")

# 批量翻译
texts = ["Good morning!", "How are you?", "Thank you very much!"]
results = deepl_client.translate_text(texts, target_lang="ZH")
for i, r in enumerate(results):
    print(f"{texts[i]} → {r.text}")

# 预期输出：
# Good morning! → 早上好！
# How are you? → 你好吗？
# Thank you very much! → 非常感谢！
```

```python
# 方式二：使用HTTP请求
import requests

def translate_with_deepl(text, target_lang, auth_key):
    # Free版使用 api-free.deepl.com
    url = "https://api-free.deepl.com/v2/translate"

    params = {
        "auth_key": auth_key,
        "text": text,
        "target_lang": target_lang,
    }

    response = requests.post(url, data=params)

    if response.status_code == 200:
        data = response.json()
        return data["translations"][0]["text"]
    else:
        print(f"错误：{response.status_code} - {response.text}")
        return None

# 使用示例
translated = translate_with_deepl(
    "人工智能正在改变世界。",
    "EN",
    "your-auth-key"
)
print(translated)  # 预期输出：Artificial intelligence is changing the world.
```

#### JavaScript (Node.js) 示例

```javascript
// 方式一：使用官方JavaScript SDK
// 安装依赖：npm install deepl-node

import * as deepl from 'deepl-node';

const authKey = 'your-auth-key';
const deeplClient = new deepl.DeepLClient(authKey);

async function translateText() {
    const result = await deeplClient.translateText(
        'Hello, world!',
        null,  // source_lang: null表示自动检测
        'ZH'   // target_lang: 中文
    );

    console.log(result.text);  // 输出：你好，世界！
    console.log(`检测到的源语言：${result.detectedSourceLang}`);
}

translateText();
```

```javascript
// 方式二：使用fetch
async function translateWithDeepL(text, targetLang, authKey) {
    const url = 'https://api-free.deepl.com/v2/translate';

    const params = new URLSearchParams({
        auth_key: authKey,
        text: text,
        target_lang: targetLang,
    });

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: params,
    });

    const data = await response.json();
    console.log(data.translations[0].text);
}

translateWithDeepL('人工智能正在改变世界。', 'EN', 'your-auth-key');
```

### 10.5 支持的语言代码

| 语言 | 代码 | 语言 | 代码 |
|------|------|------|------|
| 中文（简体） | ZH | 日语 | JA |
| 英语 | EN | 韩语 | KO |
| 英语（美式） | EN-US | 法语 | FR |
| 英语（英式） | EN-GB | 德语 | DE |
| 西班牙语 | ES | 意大利语 | IT |
| 葡萄牙语 | PT | 葡萄牙语（巴西） | PT-BR |
| 俄语 | RU | 荷兰语 | NL |
| 阿拉伯语 | AR | 波兰语 | PL |

### 10.6 计费标准

- **Free版：** 每月500,000字符免费
- **Pro版：** 按字符使用量计费，具体价格参考官网定价页面

### 10.7 常见错误

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| 403 Forbidden | API Key无效或账户冻结 | 检查Key是否正确，检查账户状态 |
| 456 Quota Exceeded | 字符配额超限 | Free用户升级到Pro，或等待下月重置 |
| 400 Bad Request | 参数缺失或语法错误 | 检查请求参数完整性 |
| 429 Too Many Requests | 请求频率过高 | 降低请求频率 |

---

## 11. 有道翻译 API

> **官网：** [https://ai.youdao.com/](https://ai.youdao.com/)
>
> **API文档：** [https://ai.youdao.com/doc.s#docs](https://ai.youdao.com/doc.s#docs)
>
> **最后更新：2026年1月**

### 11.1 简介

有道翻译API由网易有道提供，是国内最成熟的翻译API之一。支持文本翻译、网页翻译等多种服务，中文翻译质量优秀。采用签名鉴权方式（SHA256），安全性较高。

### 11.2 注册与获取API密钥

**步骤1：注册有道智云开发者账号**

1. 访问 [https://ai.youdao.com/](https://ai.youdao.com/)
2. 点击右上角的「注册/登录」按钮
3. 填写注册信息，完成注册
4. **添加官方微信可免费获得50元体验金**

**步骤2：完成实名认证**

1. 首次登录后需要进行实名认证
2. 按提示填写个人信息并提交
3. 等待审核通过

**步骤3：创建应用获取密钥**

1. 认证成功后，进入控制台
2. 在「应用总览」页面点击「创建应用」按钮
3. 填写信息：
   - **应用名称：** 如"我的翻译工具"
   - **服务类型：** 选择「自然语言翻译」→「文本翻译」或「网页翻译」
   - **接入方式：** 选择「API」
4. 点击确认创建应用
5. 创建成功后，在应用详情页查看：
   - **应用ID（App Key）**
   - **应用密钥（Secret Key）**
6. 这两个密钥是后续API调用的核心凭证，务必安全保存

> **截图获取提示：** 在有道智云控制台的应用详情页截取密钥信息。务必对Secret Key打码。

### 11.3 计费标准

| 套餐 | 字符数 | 价格 | 备注 |
|------|--------|------|------|
| 免费试用 | 240万字符/年 | 免费 | 注册即送 |
| 基础套餐 | 1000万字符 | 1200元/年 | |
| 进阶套餐 | 3000万字符 | 2800元/年 | |
| 企业套餐 | 1亿字符 | 6800元/年 | |

### 11.4 鉴权说明

有道翻译API使用**签名鉴权（v3）**，需要以下参数：

- **appKey：** 应用ID
- **salt：** UUID随机字符串（防重放攻击）
- **curtime：** 当前UTC时间戳（秒）
- **sign：** `sha256(应用ID + input + salt + curtime + 应用密钥)`

其中 `input` 的计算方式：
- 当文本长度 ≤ 20时：`input = 原文本`
- 当文本长度 > 20时：`input = 文本前10个字符 + 文本长度 + 文本后10个字符`

### 11.5 API调用示例

#### Python示例

```python
import requests
import hashlib
import time
import uuid

# 配置信息
APP_KEY = "your_app_key"
APP_SECRET = "your_app_secret"

def translate_youdao(text, from_lang="auto", to_lang="auto"):
    """
    调用有道翻译API
    from_lang: 源语言代码，如 'zh-CHS'(中文), 'en'(英文), 'auto'(自动检测)
    to_lang: 目标语言代码
    """
    url = "https://openapi.youdao.com/api"

    # 生成必要参数
    salt = str(uuid.uuid4())
    curtime = str(int(time.time()))

    # 计算input（用于签名）
    def truncate(q):
        if len(q) <= 20:
            return q
        return q[:10] + str(len(q)) + q[-10:]

    input_text = truncate(text)

    # 生成签名 sign = sha256(appKey + input + salt + curtime + appSecret)
    sign_str = APP_KEY + input_text + salt + curtime + APP_SECRET
    sign = hashlib.sha256(sign_str.encode('utf-8')).hexdigest()

    # 构建请求参数
    params = {
        'q': text,
        'appKey': APP_KEY,
        'salt': salt,
        'from': from_lang,
        'to': to_lang,
        'sign': sign,
        'signType': 'v3',
        'curtime': curtime,
    }

    # 发送请求
    response = requests.post(url, data=params)
    result = response.json()

    if result.get('errorCode') == '0':
        return result['translation'][0]
    else:
        error_msg = f"翻译失败，错误码：{result.get('errorCode')}"
        print(error_msg)
        return None

# 使用示例
# 中译英
text_zh = "你好，很高兴认识你！"
translated = translate_youdao(text_zh, from_lang="zh-CHS", to_lang="en")
print(f"原文：{text_zh}")
print(f"译文：{translated}")
# 预期输出：
# 原文：你好，很高兴认识你！
# 译文：Hello, nice to meet you!

# 英译中
text_en = "Artificial intelligence is changing the world."
translated = translate_youdao(text_en, from_lang="en", to_lang="zh-CHS")
print(f"原文：{text_en}")
print(f"译文：{translated}")
# 预期输出：
# 原文：Artificial intelligence is changing the world.
# 译文：人工智能正在改变世界。
```

#### JavaScript (Node.js) 示例

```javascript
// 安装依赖：npm install crypto axios uuid

import crypto from 'crypto';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';

const APP_KEY = 'your_app_key';
const APP_SECRET = 'your_app_secret';

function truncate(q) {
    if (q.length <= 20) return q;
    return q.substring(0, 10) + q.length + q.substring(q.length - 10);
}

async function translateYoudao(text, fromLang = 'auto', toLang = 'auto') {
    const salt = uuidv4();
    const curtime = Math.round(Date.now() / 1000).toString();
    const input = truncate(text);

    // 生成签名
    const signStr = APP_KEY + input + salt + curtime + APP_SECRET;
    const sign = crypto.createHash('sha256').update(signStr).digest('hex');

    const params = new URLSearchParams({
        q: text,
        appKey: APP_KEY,
        salt: salt,
        from: fromLang,
        to: toLang,
        sign: sign,
        signType: 'v3',
        curtime: curtime,
    });

    try {
        const response = await axios.post(
            'https://openapi.youdao.com/api',
            params
        );

        if (response.data.errorCode === '0') {
            console.log(response.data.translation[0]);
            return response.data.translation[0];
        } else {
            console.error(`翻译失败，错误码：${response.data.errorCode}`);
        }
    } catch (error) {
        console.error('请求错误：', error.message);
    }
}

// 使用示例
translateYoudao('你好，很高兴认识你！', 'zh-CHS', 'en');
```

### 11.6 支持语言代码

| 语言 | 代码 | 语言 | 代码 |
|------|------|------|------|
| 中文（简体） | zh-CHS | 日语 | ja |
| 中文（繁体） | zh-CHT | 韩语 | ko |
| 英语 | en | 法语 | fr |
| 德语 | de | 西班牙语 | es |
| 俄语 | ru | 葡萄牙语 | pt |
| 意大利语 | it | 阿拉伯语 | ar |
| 越南语 | vi | 印尼语 | id |
| 泰语 | th | 荷兰语 | nl |

### 11.7 常见错误代码

| 错误码 | 含义 | 解决方案 |
|--------|------|----------|
| 0 | 成功 | - |
| 101 | 缺少必填参数 | 检查参数完整性 |
| 102 | 不支持的语言类型 | 检查from/to参数 |
| 103 | 翻译文本过长 | 单次不超过5000字符 |
| 108 | 应用ID无效 | 检查appKey |
| 109 | 应用服务未开通 | 在控制台开通服务 |
| 110 | 账户余额不足 | 充值 |
| 202 | 签名检验失败 | 检查签名生成逻辑 |

---

## 12. 安全最佳实践

### 12.1 API密钥存储原则

**绝对禁止的操作：**
- ❌ 将API Key硬编码在源代码中
- ❌ 将API Key提交到Git等版本控制系统
- ❌ 将API Key暴露在前端/客户端代码中
- ❌ 在日志中打印API Key
- ❌ 通过截图、聊天工具分享API Key

**推荐做法：**

```python
# ✅ 方式1：使用环境变量（推荐）
import os
api_key = os.environ.get("OPENAI_API_KEY")

# ✅ 方式2：使用.env文件（仅开发环境，不要提交到Git）
# 安装：pip install python-dotenv
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
```

```javascript
// ✅ Node.js中使用环境变量
// .env文件内容（不提交Git）：
// OPENAI_API_KEY=sk-your-key-here
import dotenv from 'dotenv';
dotenv.config();
const apiKey = process.env.OPENAI_API_KEY;
```

```bash
# ✅ 系统级环境变量设置
# Linux/Mac (.bashrc 或 .zshrc)
export OPENAI_API_KEY="sk-your-key-here"
export DASHSCOPE_API_KEY="sk-your-key-here"
export DEEPSEEK_API_KEY="sk-your-key-here"

# Windows PowerShell
$env:OPENAI_API_KEY="sk-your-key-here"
```

### 12.2 .gitignore配置

在项目根目录的 `.gitignore` 中添加：

```
# API密钥和环境配置
.env
.env.local
.env.*.local
*.pem
secrets.yaml
credentials.json

# IDE配置
.idea/
.vscode/*
!.vscode/settings.json
```

### 12.3 生产环境密钥管理

| 方案 | 说明 | 适用场景 |
|------|------|----------|
| AWS Secrets Manager | AWS云密钥管理 | AWS用户 |
| Google Secret Manager | GCP密钥管理服务 | GCP用户 |
| Azure Key Vault | Azure密钥保管库 | Azure用户 |
| HashiCorp Vault | 跨平台密钥管理 | 企业级应用 |
| Docker Secrets | Docker环境密钥 | 容器化部署 |

### 12.4 API密钥轮换策略

1. **定期轮换：** 建议每90天更换一次API Key
2. **泄露处理：** 一旦怀疑密钥泄露，立即在平台控制台撤销旧Key并创建新Key
3. **监控告警：** 设置使用量告警，异常使用可能是密钥泄露的信号
4. **最小权限：** 为不同应用创建不同Key，便于追踪和隔离

### 12.5 后端代理模式

**永远不要在前端代码中直接使用API Key！** 正确的架构是：

```
用户浏览器 → 你的后端服务器 → AI API服务
           (持有API Key)    (不需要Key)
```

**后端代理代码示例（FastAPI）：**

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import os

app = FastAPI()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """后端代理，前端不暴露API Key"""
    try:
        response = client.chat.completions.create(
            model="gpt-5.4-mini",
            messages=[{"role": "user", "content": request.message}],
            max_tokens=1000,
        )
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 13. 性能优化建议

### 13.1 网络层面优化

| 优化项 | 方法 | 效果 |
|--------|------|------|
| **连接池** | 使用HTTP连接池（如Python的httpx、requests Session） | 减少TCP握手开销30-50% |
| **Keep-Alive** | 保持HTTP长连接 | 复用连接减少延迟 |
| **就近部署** | 国内API使用国内Endpoint，国际API使用代理 | 降低网络延迟50-80% |
| **异步请求** | 使用asyncio/aiohttp并发请求 | 吞吐量提升3-10倍 |

```python
# ✅ 使用连接池和异步请求（推荐）
import httpx
import asyncio

async def batch_chat(messages, api_key):
    async with httpx.AsyncClient(  # 连接池复用
        timeout=60.0,
        limits=httpx.Limits(max_keepalive_connections=20),
    ) as client:
        tasks = [
            client.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "deepseek-v4-flash",
                    "messages": [{"role": "user", "content": msg}],
                    "max_tokens": 500,
                }
            )
            for msg in messages
        ]
        responses = await asyncio.gather(*tasks)
    return [r.json() for r in responses]
```

### 13.2 提示词优化

```python
# ❌ 不推荐：冗余提示词，浪费Token
prompt_bad = """请你作为一个专业的、经验丰富的、拥有多年从业经历的
学术研究人员，非常详细地、全面地、面面俱到地介绍一下深度学习这个
重要的人工智能领域的核心概念和关键技术..."""

# ✅ 推荐：精简提示词，同样效果
prompt_good = """你是一位学术专家。请用清晰的结构介绍深度学习：
1. 定义 2. 核心技术（神经网络、反向传播、优化器）
3. 主要应用领域。每点控制在100字内。"""

# Token节省率：可节省50-70%
```

### 13.3 缓存策略

```python
# 实现简单的语义缓存
import hashlib
from functools import lru_cache
import json

cache = {}

def get_cache_key(messages, model):
    """生成缓存键"""
    content = json.dumps(messages, ensure_ascii=False) + model
    return hashlib.md5(content.encode()).hexdigest()

# 适合翻译、摘要等确定性场景
# 不适合创意写作、头脑风暴等场景
```

### 13.4 Token用量控制

```python
# 实现Token消耗监控
import tiktoken

def count_tokens(text, model="gpt-4"):
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

# 在发送请求前预估Token消耗
message = "用户输入的文本..."
token_count = count_tokens(message)
max_budget = 10000  # 设定Token预算

if token_count > max_budget:
    # 自动截断或提示用户
    message = message[:max_budget * 2]  # 粗略截断
```

### 13.5 批量处理策略

| 策略 | 适用场景 | 成本节省 |
|------|----------|----------|
| OpenAI Batch API | 大批量离线任务 | 50% |
| DeepSeek Disk Cache | 高频重复任务 | 98% (缓存命中) |
| Anthropic Message Batches | 批量异步 | 50% |
| 本地缓存复用 | 翻译/摘要 | 100% (相同请求) |

### 13.6 错误重试最佳实践

```python
import time
import random

def call_with_retry(func, max_retries=3):
    """带指数退避的重试机制"""
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            wait = (2 ** attempt) + random.uniform(0, 1)
            print(f"速率限制，{wait:.1f}秒后重试...")
            time.sleep(wait)
```

---

## 14. 多语言支持对比与选择建议

### 14.1 各模型/服务语言能力对比

| 服务 | 中文 | 英文 | 日/韩 | 小语种 | 综合评分 |
|------|------|------|-------|--------|----------|
| DeepSeek V4 Pro | ★★★★★ | ★★★★☆ | ★★★☆☆ | ★★☆☆☆ | 4.3 |
| Qwen3 Max | ★★★★★ | ★★★★☆ | ★★★★☆ | ★★★☆☆ | 4.5 |
| GPT-5.4 | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★★ | 4.8 |
| Claude Opus 4.7 | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★★ | 4.8 |
| Gemini 2.5 Pro | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★★ | 4.7 |
| GLM-4.6 | ★★★★★ | ★★★★☆ | ★★★☆☆ | ★★☆☆☆ | 4.2 |
| DeepL | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★★★ | 4.7 |
| 有道翻译 | ★★★★★ | ★★★★☆ | ★★★☆☆ | ★★☆☆☆ | 3.8 |

### 14.2 场景化推荐

| 使用场景 | 首选方案 | 备选方案 | 理由 |
|----------|----------|----------|------|
| **纯中文应用（最低成本）** | DeepSeek V4 Flash | Qwen Turbo | 中文质量好，成本极低(~$0.14/1M) |
| **中英双语应用** | Qwen3 Plus / GPT-5.4 Mini | DeepSeek V4 Pro | 中英能力均衡 |
| **代码生成与审查** | Claude Opus 4.7 | KIMI K2 Thinking | 代码理解业界最佳 |
| **学术文献翻译** | DeepL | 有道翻译 | 学术翻译质量最佳 |
| **多语言客服** | GPT-5.4 Mini | Gemini 2.5 Flash | 支持语言种类最多 |
| **长文档分析** | Gemini 2.5 Pro | Claude Opus 4.7 | 1M上下文，可处理整本书 |
| **免费学习/原型** | GLM-4-Flash | Gemini免费层 | 完全免费，128K上下文 |
| **实时语音/多模态** | GPT-Realtime | Gemini 2.5 Flash | OpenAI多模态最完善 |

### 14.3 成本综合对比

以处理100万中文tokens为例（输入）的中英文场景：

| 服务 | 模型 | 约花费 | 中文质量 | 性价比排名 |
|------|------|--------|----------|-----------|
| DeepSeek | V4 Flash | ~$0.14 | ★★★★★ | 🥇 |
| 智谱 | GLM-4-Flash | ¥0 (免费) | ★★★★☆ | 🥈 |
| 阿里Qwen | Qwen Turbo | ~¥0.002 | ★★★★☆ | 🥉 |
| Google | Gemini 2.5 Flash | 免费层内免费 | ★★★★☆ | 4 |
| KIMI | K2 | ~$0.85 | ★★★★★ | 5 |
| OpenAI | GPT-5.4 Mini | ~$0.75 | ★★★★★ | 6 |
| Anthropic | Claude Haiku 4.5 | ~$1.00 | ★★★★★ | 7 |

### 14.4 多服务架构设计

建议采用**多Provider统一路由**架构，根据不同任务动态选择最优模型：

```python
# 统一路由示例
PROVIDERS = {
    "low_cost_chinese": {"provider": "deepseek", "model": "deepseek-v4-flash"},
    "code_generation": {"provider": "claude", "model": "claude-sonnet-4-6"},
    "translation_en_zh": {"provider": "deepl", "model": None},
    "translation_zh_en": {"provider": "youdao", "model": None},
    "multilingual": {"provider": "openai", "model": "gpt-5.4-mini"},
    "long_document": {"provider": "gemini", "model": "gemini-2.5-flash"},
}

def get_provider(task_type: str) -> dict:
    """根据任务类型选择最优Provider"""
    return PROVIDERS.get(task_type, PROVIDERS["low_cost_chinese"])
```

---

## 15. API服务状态监控

### 15.1 各服务官方状态页

| 服务 | 状态页URL | 监控内容 |
|------|-----------|----------|
| OpenAI | [https://status.openai.com/](https://status.openai.com/) | API可用性、延迟、故障历史 |
| Anthropic | [https://status.anthropic.com/](https://status.anthropic.com/) | Claude API整体状态 |
| DeepSeek | 平台公告页 | 服务升级、维护通知 |
| 阿里云DashScope | [https://status.aliyun.com/](https://status.aliyun.com/) | 阿里云全产品状态 |
| Google Cloud | [https://status.cloud.google.com/](https://status.cloud.google.com/) | GCP服务状态 |
| 智谱AI | 平台公告 | GLM API状态 |

### 15.2 自建监控方案

```python
# 简单的API健康检查脚本
import time
import httpx

SERVICES = [
    {"name": "DeepSeek", "url": "https://api.deepseek.com/v1/models", "key": "DEEPSEEK_API_KEY"},
    {"name": "OpenAI", "url": "https://api.openai.com/v1/models", "key": "OPENAI_API_KEY"},
]

async def health_check(service):
    headers = {"Authorization": f"Bearer {service['key']}"}
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(service["url"], headers=headers)
        elapsed_ms = (time.time() - start) * 1000
        status = "OK" if resp.status_code == 200 else f"ERR ({resp.status_code})"
    except Exception as e:
        status = f"DOWN: {e}"
        elapsed_ms = -1
    return service["name"], status, elapsed_ms
```

### 15.3 告警策略

| 告警级别 | 触发条件 | 通知方式 | 响应时间 |
|----------|----------|----------|----------|
| P0 - 紧急 | API完全不可用 > 5分钟 | 电话+短信+企业微信 | 5分钟内响应 |
| P1 - 严重 | 错误率 > 10% 或 P99延迟 > 10s | 企业微信+邮件 | 15分钟内响应 |
| P2 - 警告 | 错误率 > 5% 或 P99延迟 > 3s | 企业微信 | 30分钟内关注 |
| P3 - 信息 | 用量接近配额/费用异常 | 邮件 | 次日处理 |

### 15.4 使用量监控

```python
# 简单的日级使用量追踪
import json
import datetime

class UsageTracker:
    def __init__(self):
        self.daily_usage = {}  # {"2026-05-18": {"deepseek": 15234, "openai": 8765}}

    def record_usage(self, provider, tokens_used):
        today = datetime.date.today().isoformat()
        if today not in self.daily_usage:
            self.daily_usage[today] = {}
        self.daily_usage[today][provider] = self.daily_usage[today].get(provider, 0) + tokens_used

    def check_alert(self, daily_limit=1000000):
        """检查日使用量是否超过限制"""
        today = datetime.date.today().isoformat()
        total = sum(self.daily_usage.get(today, {}).values())
        if total > daily_limit * 0.9:
            print(f"⚠️ 警告：今日已使用 {total:,} tokens，接近限额 {daily_limit:,}")
        return total
```

---

## 16. 常见错误代码速查表

### 16.1 HTTP状态码通用含义

| 状态码 | 含义 | 典型场景 |
|--------|------|----------|
| 200 | 成功 | 请求正常返回 |
| 400 | 请求参数错误 | Model名称错误、参数格式不对 |
| 401 | 未授权 | API Key无效或过期 |
| 402 | 付款要求 | 账户余额不足 |
| 403 | 禁止访问 | 无权限、服务未开通、地区限制 |
| 404 | 资源不存在 | Model不存在或已下线 |
| 413 | 请求体过大 | 输入超过模型限制 |
| 429 | 请求过多 | 超过RPM/TPM限制 |
| 500 | 服务器内部错误 | 服务端故障，需要重试 |
| 502 | 网关错误 | 上游服务暂时不可用 |
| 503 | 服务不可用 | 服务正在维护 |
| 529 | 服务过载 | Anthropic特有，服务器负载过高 |

### 16.2 服务特有错误速查

| 服务 | 错误码 | 说明 | 处理方式 |
|------|--------|------|----------|
| OpenAI | `insufficient_quota` | 余额不足 | 充值或等待计费周期重置 |
| OpenAI | `context_length_exceeded` | 上下文过长 | 缩减输入内容 |
| DeepSeek | `invalid_api_key` | Key无效 | 检查或重新生成Key |
| Anthropic | `overloaded_error` (529) | 服务器过载 | 等待并指数退避重试 |
| Gemini | `429 RESOURCE_EXHAUSTED` | 免费配额用完 | 等待太平洋时间0点重置 |
| 百度千帆 | `17` | 日调用量超限 | 等待次日重置或升级套餐 |
| DeepL | `456` | 字符配额超限 | 等待下月重置或升级Pro |
| 有道翻译 | `202` | 签名错误 | 检查签名生成算法 |
| Qwen/阿里 | `InvalidParameter` | 参数错误 | 检查model参数 |

### 16.3 通用调试流程

```
1. 检查API Key是否正确设置（格式、前缀）
2. 确认Account余额是否充足
3. 验证Base URL是否正确
4. 检查网络连接（防火墙/VPN）
5. 确认Model名称没有拼写错误
6. 检查请求参数JSON格式
7. 查看RPM/TPM限制是否被触发
8. 对照API官方文档确认参数兼容性
```

---

## 附录A：环境变量配置模板

创建 `.env.example` 文件（可提交到Git），团队成员复制为 `.env` 后填入实际值：

```bash
# ====== 大语言模型 API Keys ======

# OpenAI
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.openai.com/v1

# DeepSeek
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com

# 通义千问 (DashScope)
DASHSCOPE_API_KEY=sk-your-key-here

# KIMI (Moonshot)
MOONSHOT_API_KEY=sk-your-key-here

# 智谱GLM
ZHIPU_API_KEY=your-key-here

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Google Gemini
GEMINI_API_KEY=AIza-your-key-here

# 百度文心一言
BAIDU_API_KEY=your-api-key-here
BAIDU_SECRET_KEY=your-secret-key-here

# ====== 翻译服务 API Keys ======

# DeepL
DEEPL_AUTH_KEY=your-auth-key

# 有道翻译
YOUDAO_APP_KEY=your-app-key
YOUDAO_APP_SECRET=your-app-secret
```

---

## 附录B：快速测试脚本

以下是一个Python通用测试脚本，用于验证API Key是否配置正确：

```python
# test_all_apis.py - 一键测试所有API配置
import os
from openai import OpenAI

def test_api(provider_name, base_url, model, api_key_env):
    """通用API测试函数"""
    api_key = os.environ.get(api_key_env)
    if not api_key:
        print(f"⏭️  {provider_name}: 未配置 {api_key_env}，跳过")
        return

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "你好，请回复'API配置成功'"}],
            max_tokens=50,
            timeout=15,
        )
        content = response.choices[0].message.content
        print(f"✅ {provider_name} ({model}): {content[:60]}")
    except Exception as e:
        print(f"❌ {provider_name}: {type(e).__name__}: {e}")

if __name__ == "__main__":
    print("=== API配置测试 ===\n")

    test_api("DeepSeek", "https://api.deepseek.com", "deepseek-v4-flash", "DEEPSEEK_API_KEY")
    test_api("通义千问", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus", "DASHSCOPE_API_KEY")
    test_api("KIMI", "https://api.moonshot.ai/v1", "kimi-k2-thinking-turbo", "MOONSHOT_API_KEY")
    test_api("智谱GLM", "https://open.bigmodel.cn/api/paas/v4", "glm-4-flash", "ZHIPU_API_KEY")
    test_api("OpenAI", "https://api.openai.com/v1", "gpt-5.4-mini", "OPENAI_API_KEY")

    print("\n=== 测试完成 ===")

# 预期输出（各API正常时）：
# === API配置测试 ===
# ✅ DeepSeek (deepseek-v4-flash): API配置成功
# ✅ 通义千问 (qwen-plus): API配置成功
# ✅ KIMI (kimi-k2-thinking-turbo): API配置成功
# ✅ 智谱GLM (glm-4-flash): API配置成功
# ✅ OpenAI (gpt-5.4-mini): API配置成功
# === 测试完成 ===
```

---

## 附录C：版本变更说明

### 主要API版本变更记录（2025年11月至今）

| 日期 | 服务 | 变更内容 |
|------|------|----------|
| 2025-11 | DeepSeek | V4系列发布（Flash/Pro），弃用V3系列。V3→V4需将model参数从 `deepseek-chat` 改为 `deepseek-v4-flash` |
| 2025-11 | OpenAI | GPT-5.4系列发布（旗舰/Mini/Nano/Pro），新增Flex处理层级 |
| 2025-11 | Gemini | Gemini 3 Pro Preview发布，免费层级持续可用 |
| 2025-11 | GLM | GLM-4.6发布，355B参数，支持200K上下文 |
| 2025-11 | KIMI | K2系列全面上线 |
| 2026-01 | 有道翻译 | API文档更新至2026年版本 |
| 2026-04 | Qwen | Qwen3.6系列发布（Flash/Plus/Max） |
| 2026-05 | OpenAI | GPT-5.4降价，Batch API 50%折扣永久化 |
| 2026-05 | DeepL | API文档更新 |

### DeepSeek V3 → V4 迁移指南

```python
# ❌ 旧版（V3，即将弃用）
old_response = client.chat.completions.create(
    model="deepseek-chat",  # 2026年7月24日后失效
    messages=[{"role": "user", "content": "你好"}],
)

# ✅ 新版（V4 Flash，推荐）
new_response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[{"role": "user", "content": "你好"}],
)

# ✅ 需要推理能力（V4 Pro）
reasoning_response = client.chat.completions.create(
    model="deepseek-v4-pro",
    messages=[{"role": "user", "content": "复杂的逻辑推理问题..."}],
)
```

### OpenAI 旧 → GPT-5.4 Mini 迁移指南

```python
# ❌ 旧版
response = client.chat.completions.create(
    model="gpt-4o",  # 定价更高
    messages=[...],
)

# ✅ 新版（更高性价比）
response = client.chat.completions.create(
    model="gpt-5.4-mini",  # 同样质量，价格更低
    messages=[...],
)
```

---

> **编写说明：** 本教程所有信息截至2026年5月18日。各服务API文档会持续更新，请以各平台官方文档为准。如有变更，建议定期（每季度）检查API版本更新和计费调整。
>
> **反馈渠道：** 如发现教程内容有误或过时，请通过GitHub Issues反馈，我们将及时更新。