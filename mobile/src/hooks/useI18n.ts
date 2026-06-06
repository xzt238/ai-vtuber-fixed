// ============================================
// 国际化 Hook
// ============================================
import { useState, useEffect, useCallback, useMemo } from 'react';
import { i18n, Language, LanguageInfo } from '../services/i18n';

// useI18n Hook
export function useI18n() {
  const [currentLanguage, setCurrentLanguage] = useState<Language>(i18n.getCurrentLanguage());
  
  // 监听语言变化
  useEffect(() => {
    const unsubscribe = i18n.onLanguageChange((language: Language) => {
      setCurrentLanguage(language);
    });
    
    return unsubscribe;
  }, []);
  
  // 翻译函数
  const t = useCallback((key: string, params?: Record<string, string | number>) => {
    return i18n.t(key, params);
  }, [currentLanguage]); // 依赖当前语言，语言变化时重新计算
  
  // 设置语言
  const setLanguage = useCallback((language: Language) => {
    i18n.setLanguage(language);
  }, []);
  
  // 获取当前语言信息
  const languageInfo = useMemo(() => {
    return i18n.getCurrentLanguageInfo();
  }, [currentLanguage]);
  
  // 获取支持的语言列表
  const supportedLanguages = useMemo(() => {
    return i18n.getSupportedLanguages();
  }, []);
  
  // 检查是否是RTL
  const isRTL = useMemo(() => {
    return i18n.isRTL();
  }, [currentLanguage]);
  
  return {
    t,
    currentLanguage,
    languageInfo,
    supportedLanguages,
    isRTL,
    setLanguage,
  };
}

// useTranslation Hook (别名)
export const useTranslation = useI18n;

// 导出类型
export type { Language, LanguageInfo };