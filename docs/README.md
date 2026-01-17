# Jieqi 项目文档索引

## 架构设计
- [architecture.md](./architecture.md) - 系统架构和分层设计
- [testing.md](./testing.md) - 测试策略

## 历史文档
- [archived_strategies.md](./archived_strategies.md) - 已归档的Python AI策略

## 快速开始

### 运行测试
```bash
just test        # 所有测试
just test-rust   # 只测Rust
just test-py     # 只测Python
```

### 使用Rust AI
```bash
# 获取走法
just rustai-moves "FEN字符串"

# 获取最佳走法（默认it2策略，0.5秒）
just rustai-best "FEN字符串"

# 自定义参数
just rustai-best "FEN字符串" it2 1.0 5
```

### 启动UI
```bash
just start       # Streamlit UI
```

## 规则文档
- [RULES.md](../RULES.md) - 揭棋规则详解
