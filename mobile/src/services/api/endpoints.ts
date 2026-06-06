/**
 * API 端点定义
 */

export const ENDPOINTS = {
  // 设备管理
  DEVICE: {
    REGISTER: '/device/register',
    STATUS: '/device/status',
  },

  // 消息/对话
  MESSAGE: {
    SEND: '/message/send',
    HISTORY: '/message/history',
    STREAM: '/message/stream',
  },

  // 角色管理
  CHARACTER: {
    LIST: '/character/list',
    GET: '/character/:id',
    SELECT: '/character/select',
  },

  // 记忆系统
  MEMORY: {
    LIST: '/memory/list',
    ADD: '/memory/add',
    DELETE: '/memory/:id',
    CLEAR: '/memory/clear',
  },

  // AI 模型
  AI: {
    PROVIDERS: '/ai/providers',
    MODELS: '/ai/models',
    CHAT: '/ai/chat',
  },

  // 语音
  VOICE: {
    UPLOAD: '/voice/upload',
    SYNTHESIZE: '/voice/synthesize',
  },

  // 系统
  SYSTEM: {
    CONFIG: '/config',
    STATUS: '/status',
    HEALTH: '/health',
  },
} as const;
