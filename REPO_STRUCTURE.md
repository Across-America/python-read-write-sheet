# 📁 仓库结构说明

## 🎯 核心目录

### `/` 根目录
- `main.py` - 主入口文件
- `requirements.txt` - Python 依赖
- `README.md` - 主文档
- `.github/workflows/` - GitHub Actions 工作流

### `/config/` - 配置文件
- `settings.py` - 所有配置（API keys, Assistant IDs, Sheet IDs）

### `/services/` - 服务层
- `vapi_service.py` - VAPI API 服务
- `smartsheet_service.py` - Smartsheet API 服务

### `/workflows/` - 工作流代码
- `cancellations.py` - CL1 Project - Cancellation Workflow
- `renewals.py` - N1 Project - Renewal Workflow
- `non_renewals.py` - N1 Project - Non-Renewal Workflow
- `direct_bill.py` - Direct Bill Workflow
- `mortgage_bill.py` - Mortgage Bill Workflow
- `cross_sells.py` - Cross-Sells Workflow
- `stm1.py` - STM1 Project Workflow (Statement Call - All American Claims)

### `/tests/` - 正式测试
- 单元测试和集成测试

### `/scripts/` - 临时脚本 ⭐ 新增
- 开发/测试过程中创建的临时脚本
- 测试脚本、检查脚本、工具脚本
- 详见 `scripts/README.md`

### `/docs/` - 文档 ⭐ 新增
- 部署指南、设置指南、报告等
- 详见 `docs/README.md`

### `/utils/` - 工具函数
- `phone_formatter.py` - 电话号码格式化

## 📝 使用说明

- **核心代码**: `/workflows/`, `/services/`, `/config/`
- **临时脚本**: `/scripts/` (开发测试用)
- **文档**: `/docs/` (详细文档)
- **主文档**: `/README.md` (快速开始)

