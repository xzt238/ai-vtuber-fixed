# 🐱 咕咕嘎嘎 AI虚拟形象 - 快速开始

## 一键打包（推荐）

双击 `build.bat` 即可自动完成：
1. 安装所有依赖
2. 打包成 .exe

## 手动打包

```cmd
cd app
pip install -r requirements.txt
python build.py --auto
```

## 运行

```
dist\gugugaga_single.exe
```

或目录版本：
```
dist\gugugaga\gugugaga.exe
```

## 配置

编辑 `app/config.yaml`：
```yaml
llm:
  minimax:
    api_key: "你的API密钥"
```

## 可选：添加Live2D模型

将模型文件放入：
```
app/web/assets/model/
```

---

🐱 咕咕嘎嘎 - AI虚拟形象