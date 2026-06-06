# 📺 直播平台使用指南

> **版本**: v1.16.0  
> **更新日期**: 2026-06-03

---

## 🚀 快速开始

### 第一步：打开直播设置页面

1. 启动咕咕嘎嘎 AI VTuber 原生桌面版
2. 在左侧导航栏中点击 **"直播设置"** 按钮
3. 进入直播平台配置页面

### 第二步：配置直播平台

以 **Bilibili** 为例：

1. 在左侧平台列表中点击 **"📺 Bilibili"**
2. 在右侧配置面板中填写：
   - **直播间ID**: 你的Bilibili直播间ID（URL中的数字）
   - **用户UID**: 你的Bilibili用户UID
   - **认证Token**: 从浏览器开发者工具获取
3. 点击 **"启用Bilibili直播"** 开关
4. 点击 **"连接直播间"** 按钮

### 第三步：开始互动

连接成功后：
- AI会自动读取直播间弹幕
- AI会自动生成回复
- AI会自动发送弹幕回复
- 收到礼物时会自动感谢

---

## 📋 支持的平台列表

| 平台 | 配置入口 | 配置项 | 状态 |
|------|----------|--------|------|
| **Bilibili** | 直播设置 → Bilibili | room_id, uid, token | ✅ 完整 |
| **抖音** | 直播设置 → 抖音 | room_id, cookie | ✅ 可用 |
| **快手** | 直播设置 → 快手 | room_id, cookie | ✅ 可用 |
| **斗鱼** | 直播设置 → 斗鱼 | room_id | ✅ 可用 |
| **虎牙** | 直播设置 → 虎牙 | room_id | ✅ 可用 |
| **YouTube** | 直播设置 → YouTube | channel_id, api_key | ✅ 可用 |
| **Twitch** | 直播设置 → Twitch | channel, oauth_token | ✅ 可用 |
| **TikTok** | 直播设置 → TikTok | room_id, cookie | ✅ 可用 |
| **微信视频号** | 直播设置 → 微信视频号 | room_id | ✅ 可用 |

---

## 🎯 各平台详细配置

### 1. Bilibili 直播

#### 获取直播间ID
1. 登录Bilibili，进入你的直播间
2. 查看URL：`https://live.bilibili.com/123456`
3. `123456` 就是你的直播间ID

#### 获取用户UID
1. 登录Bilibili，点击头像进入个人主页
2. 查看URL：`https://space.bilibili.com/789012`
3. `789012` 就是你的用户UID

#### 获取认证Token
1. 登录Bilibili直播间
2. 打开浏览器开发者工具（F12）
3. 切换到 **Network** 标签页
4. 刷新页面，查找 **WebSocket** 连接
5. 从连接信息中获取Token

#### 配置示例
```yaml
live:
  bilibili:
    enabled: true
    room_id: '123456'
    uid: 789012
    token: 'your_token_here'
```

---

### 2. 抖音直播

#### 获取直播间ID
1. 登录抖音，进入你的直播间
2. 查看URL中的数字

#### 获取Cookie
1. 登录抖音直播网页版
2. 打开浏览器开发者工具（F12）
3. 切换到 **Application** 标签页
4. 在 **Cookies** 中复制所有Cookie

#### 配置示例
```yaml
live:
  douyin:
    enabled: true
    room_id: 'your_room_id'
    cookie: 'your_cookie_here'
```

---

### 3. 快手直播

#### 获取直播间ID
1. 登录快手，进入你的直播间
2. 查看URL中的数字

#### 获取Cookie
1. 登录快手直播网页版
2. 打开浏览器开发者工具（F12）
3. 切换到 **Application** 标签页
4. 在 **Cookies** 中复制所有Cookie

#### 配置示例
```yaml
live:
  kuaishou:
    enabled: true
    room_id: 'your_room_id'
    cookie: 'your_cookie_here'
```

---

### 4. YouTube 直播

#### 获取频道ID
1. 登录YouTube，进入你的频道
2. 查看URL：`https://www.youtube.com/channel/UCxxxxxx`
3. `UCxxxxxx` 就是你的频道ID

#### 获取API Key
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建项目并启用YouTube Data API v3
3. 创建API Key

#### 配置示例
```yaml
live:
  youtube:
    enabled: true
    channel_id: 'UCxxxxxx'
    api_key: 'your_api_key_here'
```

---

### 5. Twitch 直播

#### 获取频道名
1. 登录Twitch，进入你的频道
2. 查看URL：`https://www.twitch.tv/your_channel`
3. `your_channel` 就是你的频道名

#### 获取OAuth Token
1. 访问 [Twitch Token Generator](https://twitchtokengenerator.com/)
2. 生成OAuth Token

#### 配置示例
```yaml
live:
  twitch:
    enabled: true
    channel: 'your_channel'
    oauth_token: 'your_oauth_token_here'
```

---

## 🔧 配置方式

### 方式1：通过软件界面配置（推荐）

1. 打开咕咕嘎嘎 AI VTuber
2. 点击左侧导航栏的 **"直播设置"**
3. 选择要配置的平台
4. 填写配置参数
5. 点击 **"连接直播间"**

### 方式2：通过配置文件配置

编辑 `app/config.yaml` 文件：

```yaml
live:
  enabled: true
  default_platform: bilibili
  
  bilibili:
    enabled: true
    room_id: '123456'
    uid: 789012
    token: 'your_token'
  
  douyin:
    enabled: false
    room_id: ''
    cookie: ''
```

---

## 🎮 使用流程

### 1. 启动软件
```bash
# Windows
scripts/start.bat

# 或者直接运行
python -m native.main
```

### 2. 配置直播平台
1. 点击 **"直播设置"**
2. 选择平台
3. 填写配置
4. 启用平台
5. 连接直播间

### 3. 开始直播
1. 在直播平台开启直播
2. AI会自动监听弹幕
3. AI会自动回复弹幕
4. 收到礼物会自动感谢

### 4. 查看状态
- **日志标签页**: 查看实时日志
- **状态标签页**: 查看连接状态

---

## 📊 功能说明

### 自动回复
- AI会自动读取直播间弹幕
- AI会根据弹幕内容生成回复
- AI会自动发送弹幕回复

### 礼物感谢
- 收到礼物时自动发送感谢消息
- 感谢消息会包含用户名和礼物名称

### 多平台支持
- 可以同时连接多个平台
- 每个平台独立配置
- 每个平台独立管理

---

## ⚠️ 注意事项

### 1. 网络要求
- 需要稳定的网络连接
- 部分平台可能需要VPN

### 2. 账号要求
- 需要登录对应的直播平台
- 部分平台需要特殊权限

### 3. 配置安全
- Token和Cookie是敏感信息
- 不要分享给他人
- 定期更换Token

### 4. 平台限制
- 部分平台有弹幕发送频率限制
- 部分平台有弹幕长度限制
- 遵守平台规则

---

## 🔍 常见问题

### Q: 为什么连接失败？
A: 可能的原因：
1. 直播间ID错误
2. Token/Cookie过期
3. 网络连接问题
4. 平台限制

### Q: 为什么没有自动回复？
A: 可能的原因：
1. 未启用自动回复
2. LLM未配置
3. 弹幕内容不适合回复

### Q: 可以同时连接多个平台吗？
A: 可以，每个平台独立配置和连接。

### Q: 如何获取Token/Cookie？
A: 参考各平台的详细配置说明。

---

## 📞 技术支持

如有问题，请：
1. 查看日志标签页的错误信息
2. 检查配置是否正确
3. 参考本文档的常见问题
4. 在GitHub提交Issue

---

**文档版本**: v1.16.0  
**更新日期**: 2026-06-03  
**编写人**: 齐活林（Qi）· 交付总监