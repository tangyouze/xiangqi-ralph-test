# Jieqi 项目文档索引

## P0 - 核心规范
- [p0-fen-spec.md](./p0-fen-spec.md) - FEN 格式规范

## P1 - 开发必读
- [p1-architecture.md](./p1-architecture.md) - 系统架构和分层设计
- [p1-rust-ai-api.md](./p1-rust-ai-api.md) - Rust AI 接口文档
- [p1-testing.md](./p1-testing.md) - 测试策略

## P2 - 参考文档
- [p2-streamlit.md](./p2-streamlit.md) - Streamlit UI 需求
- [p2-search-visualization.md](./p2-search-visualization.md) - 搜索树可视化设计
- [p2-verbose-output-format.md](./p2-verbose-output-format.md) - Verbose 输出格式

## 快速开始

### 运行测试
```bash
just test        # 所有测试
just test-rust   # 只测Rust
just test-py     # 只测Python
```

### 使用 Rust AI
```bash
# 获取走法
just rustai-moves "FEN字符串"

# 获取最佳走法（默认 it2 策略，0.5秒）
just rustai-best "FEN字符串"

# 自定义参数
just rustai-best "FEN字符串" it2 1.0 5
```

### 启动 UI
```bash
just streamlit   # Streamlit UI
```

## 规则文档
- [RULES.md](../RULES.md) - 揭棋规则详解
