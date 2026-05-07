# PySide6 兼容性修复

## 修复的问题

### 1. QSizePolicy.Expanding 修复

**问题**: `QSizePolicy.Expanding` 在 PySide6 中改为 `QSizePolicy.Policy.Expanding`

**文件**: `ui/widgets/canvas_widget.py`

**修复前**:
```python
from PySide6.QtWidgets import QWidget, QLabel
...
self.setSizePolicy(
    self.sizePolicy().Expanding,
    self.sizePolicy().Expanding
)
```

**修复后**:
```python
from PySide6.QtWidgets import QWidget, QLabel, QSizePolicy
...
self.setSizePolicy(
    QSizePolicy.Policy.Expanding,
    QSizePolicy.Policy.Expanding
)
```

### 2. QPainter.font() 修复

**问题**: `QPainter.font()` 是静态方法，应使用实例方法

**文件**: `ui/widgets/canvas_widget.py`

**修复前**:
```python
painter.setFont(QPainter.font())
```

**修复后**:
```python
font = painter.font()
painter.setFont(font)
```

### 3. RecipeEditDialog 缺少 config_service 参数

**问题**: `RecipeEditDialog` 类需要访问 `config_service` 来获取算法参数定义

**文件**: `ui/views/recipe_view.py`

**修复**: 添加 `config_service` 参数到构造函数，并在调用时传入

```python
def __init__(
    self,
    algorithms: List[dict],
    config_service,  # 新增参数
    parent: Optional[QWidget] = None
):
    ...
    self._config_service = config_service
```

## 运行测试

安装依赖后运行：

```bash
cd chip_inspector
pip install -r requirements.txt
python test_imports.py
```

如果导入测试通过，可以运行应用：

```bash
python main.py
```

## 其他 PySide6 注意事项

1. **枚举值访问**: 使用 `Enum.Member.value` 而不是 `.name`
2. **信号连接**: 使用 `Signal` 类型而不是旧式的信号定义
3. **字符串处理**: `QString` 已移除，直接使用 Python `str`
4. **容器类型**: 使用 Python 原生类型而不是 Qt 容器类型

以上问题已在重构中正确处理。
