# 工业芯片缺陷检测系统

基于 HSV 色彩空间分割的芯片表面暗点/污渍缺陷视觉检测系统。

## 快速开始

```bash
# 1. 安装依赖
pip install -r chip_inspector/requirements.txt

# 2. 启动应用
python chip_inspector/main.py
```

支持: Python 3.8+ / Windows 10+

## 检测原理

1. **芯片定位** — HSV 色彩过滤识别芯片区域
2. **安全区定义** — 边缘内缩避免边界误判
3. **缺陷检测** — 安全区内检测低亮度暗点
4. **判定输出** — 面积阈值过滤噪点，输出 OK/NG

## 目录结构

```
├── chip_inspector/          # 重构后的主工程
│   ├── main.py              # 应用入口
│   ├── algorithms/          # 检测算法（插件化）
│   ├── config/              # 配置 & 配方管理
│   ├── core/                # 领域模型 & 枚举
│   ├── data/                # SQLite 持久化层
│   ├── services/            # 业务服务层
│   ├── ui/                  # PySide6 界面
│   └── utils/               # 工具函数
├── configs/                 # 旧版配方文件
└── test3.py                 # 原始单文件版本
```

## 更多文档

- [chip_inspector/README.md](chip_inspector/README.md) — 完整使用说明、参数解释
- [chip_inspector/REFACTORING_SUMMARY.md](chip_inspector/REFACTORING_SUMMARY.md) — 架构重构总结
