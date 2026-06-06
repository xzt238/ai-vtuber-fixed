/**
 * 任务路由策略
 *
 * 根据任务类型和配置决定使用本地模型还是云端模型
 */

import { AITask, AITaskType } from '../../types/ai';
import { cloudModel } from './cloudModel';
import { useAppStore } from '../../store/appStore';

export type ModelSource = 'cloud' | 'local' | 'server';

class TaskRouter {
  // 决定使用哪个模型源
  resolve(task: AITask): ModelSource {
    // 1. 优先检查是否有云端 LLM 配置
    if (cloudModel.isConfigured()) {
      return 'cloud';
    }

    // 2. 检查是否连接到服务器
    const isConnected = useAppStore.getState().isConnected;
    if (isConnected) {
      return 'server';
    }

    // 3. 回退到本地模型
    return 'local';
  }

  // 获取当前可用的模型源描述
  getActiveSource(): string {
    if (cloudModel.isConfigured()) {
      return '云端 LLM';
    }

    const isConnected = useAppStore.getState().isConnected;
    if (isConnected) {
      return '桌面端服务器';
    }

    return '本地模型';
  }

  // 检查是否有可用的模型
  // 本地模型始终可用，所以始终返回 true
  hasAvailableModel(): boolean {
    return true;
  }
}

// 导出单例
export const taskRouter = new TaskRouter();
