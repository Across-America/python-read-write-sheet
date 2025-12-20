# 测试脚本说明

## 核心测试脚本

### 1. `test_new_features.py` - 快速工作流测试
**用途**: 快速验证新功能的工作流集成
**运行**: `python scripts/test_new_features.py`

**测试内容**:
- Mortgage Bill 调用（14天和7天前）
- General Cancellation 调用（14、7、3天前）
- Non-Payment Cancellation 调用（14、7、1个工作日）

**特点**:
- 快速执行
- 测试模式（不实际拨打电话）
- 验证工作流集成

### 2. `test_comprehensive.py` - 全面详细测试
**用途**: 全面的功能测试，包括边界情况、数据验证等
**运行**: `python scripts/test_comprehensive.py`

**测试内容**:
- Mortgage Bill 边界情况（6个测试）
- 取消类型变化检测（15个测试）
- 日期解析（8个测试）
- 工作日计算详细测试（7个测试）
- 添加工作日（4个测试）
- 跟进日期计算
- 集成场景（3个测试）
- 全面数据验证（4个测试）
- 真实数据分析

**特点**:
- 全面覆盖
- 边界情况测试
- 数据格式变化测试
- 真实数据验证

## 使用建议

- **日常快速验证**: 使用 `test_new_features.py`
- **完整功能测试**: 使用 `test_comprehensive.py`
- **部署前验证**: 运行两个测试脚本确保所有功能正常

## 测试报告

测试结果保存在 `scripts/TEST_RESULTS.md`

