// ============================================
// GuguGaga AI VTuber Mobile - 组件统一导出
// ============================================

// 基础组件
export { ChatBubble } from './ChatBubble';
export { CharacterCard } from './CharacterCard';
export { EmptyState } from './EmptyState';
export { Header } from './Header';
export { LoadingOverlay } from './LoadingOverlay';
export { SearchBar } from './SearchBar';

// 动画组件
export { AnimatedBubble } from './AnimatedBubble';
export { AnimatedButton } from './AnimatedButton';
export { TypingIndicator } from './TypingIndicator';
export { EmotionBadge } from './EmotionBadge';
export { FadeInView, FadeInListItem } from './FadeInView';

// Live2D 模型
export { default as Live2DView } from './live2d/Live2DView';

// VRM 3D 模型
export { default as VRMView } from './vrm/VRMView';

// 音频分析
export { audioAnalyzer, simpleLipSync } from '../services/audioAnalyzer';
