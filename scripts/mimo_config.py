import logging
#!/usr/bin/env python3
"""
MiMo Token Plan 配置写入器

logger = logging.getLogger(__name__)

由 start.bat 调用，根据用户选择写入各模块的偏好文件。
不修改 config.yaml，仅写入 app/cache/ 下的偏好文件。
启动时 Config._load() 会自动读取这些偏好文件并覆盖 config.yaml 的值。

用法:
    python scripts/mimo_config.py <choice>

    choice:
        0 - 跳过 (清除所有 MiMo 偏好，恢复 config.yaml 默认值)
        1 - 全部使用 MiMo (LLM+TTS+ASR+Vision)
        2 - 仅 LLM
        3 - 仅 TTS
        4 - 仅 ASR
        5 - LLM + TTS
        6 - LLM + ASR + Vision
"""

import json
import os
import sys

# 项目根目录
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(PROJECT_DIR, "app", "cache")

# MiMo Token Plan 专用 Base URL
MIMO_TOKEN_PLAN_URL = "https://token-plan-cn.xiaomimimo.com/v1"

# 模块启用映射: choice -> (llm, tts, asr, vision)
CHOICE_MAP = {
    "0": (False, False, False, False),
    "1": (True,  True,  True,  True),
    "2": (True,  False, False, False),
    "3": (False, True,  False, False),
    "4": (False, False, True,  False),
    "5": (True,  True,  False, False),
    "6": (True,  False, True,  True),
}


def _load_json(path):
    """安全加载 JSON 文件"""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_json(path, data):
    """安全保存 JSON 文件"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _clear_mimo_prefs(prefs, provider_key="mimo"):
    """从偏好文件中移除 MiMo 的 provider 和 base_url 覆盖"""
    # 不删除 provider_configs 中 mimo 的记录（保留给下次切换用）
    pass


def configure_llm(llm_mimo):
    """写入 LLM 偏好文件"""
    path = os.path.join(CACHE_DIR, "llm_preferences.json")
    d = _load_json(path)
    d.setdefault("provider_configs", {})
    pc = d["provider_configs"]
    pc.setdefault("mimo", {})

    if llm_mimo:
        d["provider"] = "mimo"
        d["model"] = "mimo-v2.5"
        pc["mimo"]["base_url"] = MIMO_TOKEN_PLAN_URL
        pc["mimo"]["model"] = "mimo-v2.5"
        logger.info(f"  [MiMo] LLM → MiMo (token plan)")
    else:
        # 恢复默认: 让 config.yaml 的 provider 生效
        # 但保留 mimo base_url 以便 UI 中切换时也能用 token plan URL
        if "provider" in d and d["provider"] == "mimo":
            del d["provider"]
        if "model" in d and d["model"] == "mimo-v2.5":
            del d["model"]
        pc["mimo"]["base_url"] = MIMO_TOKEN_PLAN_URL
        logger.info(f"  [MiMo] LLM → 默认 (保留 token plan URL)")

    _save_json(path, d)


def configure_tts(tts_mimo):
    """写入 TTS 偏好文件"""
    path = os.path.join(CACHE_DIR, "tts_preferences.json")
    d = _load_json(path)

    if tts_mimo:
        d["provider"] = "mimo"
        d["voice"] = "mimo_default"
        d["engine"] = "MiMo TTS"
        d.setdefault("provider_configs", {})
        d["provider_configs"].setdefault("mimo", {})
        d["provider_configs"]["mimo"]["base_url"] = MIMO_TOKEN_PLAN_URL
        logger.info(f"  [MiMo] TTS → MiMo (token plan)")
    else:
        # 恢复默认: 不覆盖 provider，如果之前是 mimo 则删除
        if d.get("provider") == "mimo":
            del d["provider"]
        if d.get("voice") == "mimo_default":
            del d["voice"]
        if d.get("engine") == "MiMo TTS":
            del d["engine"]
        d.setdefault("provider_configs", {})
        d["provider_configs"].setdefault("mimo", {})
        d["provider_configs"]["mimo"]["base_url"] = MIMO_TOKEN_PLAN_URL
        logger.info(f"  [MiMo] TTS → 默认 (保留 token plan URL)")

    _save_json(path, d)


def configure_asr(asr_mimo):
    """写入 ASR 偏好文件"""
    path = os.path.join(CACHE_DIR, "asr_preferences.json")
    d = _load_json(path)

    if asr_mimo:
        d["provider"] = "mimo"
        d.setdefault("provider_configs", {})
        d["provider_configs"].setdefault("mimo", {})
        d["provider_configs"]["mimo"]["base_url"] = MIMO_TOKEN_PLAN_URL
        d["provider_configs"]["mimo"]["model"] = "mimo-v2.5"
        logger.info(f"  [MiMo] ASR → MiMo (token plan)")
    else:
        # 恢复默认
        if d.get("provider") == "mimo":
            del d["provider"]
        d.setdefault("provider_configs", {})
        d["provider_configs"].setdefault("mimo", {})
        d["provider_configs"]["mimo"]["base_url"] = MIMO_TOKEN_PLAN_URL
        logger.info(f"  [MiMo] ASR → 默认 (保留 token plan URL)")

    _save_json(path, d)


def configure_vision(vision_mimo):
    """写入 Vision 偏好文件"""
    path = os.path.join(CACHE_DIR, "vision_preferences.json")
    d = _load_json(path)

    if vision_mimo:
        d["default_provider"] = "mimo_vision"
        d.setdefault("provider_configs", {})
        d["provider_configs"].setdefault("mimo_vision", {})
        d["provider_configs"]["mimo_vision"]["base_url"] = MIMO_TOKEN_PLAN_URL
        logger.info(f"  [MiMo] Vision → MiMo (token plan)")
    else:
        # 恢复默认
        if d.get("default_provider") == "mimo_vision":
            del d["default_provider"]
        d.setdefault("provider_configs", {})
        d["provider_configs"].setdefault("mimo_vision", {})
        d["provider_configs"]["mimo_vision"]["base_url"] = MIMO_TOKEN_PLAN_URL
        logger.info(f"  [MiMo] Vision → 默认 (保留 token plan URL)")

    _save_json(path, d)


def check_api_key():
    """检查 MiMo API Key 是否已配置"""
    path = os.path.join(CACHE_DIR, "api_keys.json")
    d = _load_json(path)
    mimo_key = d.get("mimo", "")
    if mimo_key and mimo_key.startswith("tp-"):
        logger.info(f"  [MiMo] API Key: 已配置 (token plan)")
        return True
    else:
        logger.info(f"  [MiMo] API Key: 未配置 — 请在 UI 中填入 MiMo Token Plan API Key")
        return False


def main():
    choice = sys.argv[1] if len(sys.argv) > 1 else "1"

    if choice not in CHOICE_MAP:
        logger.info(f"[错误] 无效选择: {choice}，请输入 0-6")
        sys.exit(1)

    llm_mimo, tts_mimo, asr_mimo, vision_mimo = CHOICE_MAP[choice]

    logger.info()
    if choice == "0":
        logger.info("[MiMo] 清除偏好，恢复 config.yaml 默认配置")
    else:
        logger.info(f"[MiMo] 配置方案 {choice}:")
    logger.info()

    configure_llm(llm_mimo)
    configure_tts(tts_mimo)
    configure_asr(asr_mimo)
    configure_vision(vision_mimo)
    check_api_key()

    logger.info()
    logger.info("[MiMo] 配置完成 ✓")


if __name__ == "__main__":
    main()
