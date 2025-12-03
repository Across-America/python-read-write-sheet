# 📁 Scripts 目录

这个目录包含一些有用的工具脚本和部署脚本。

## 📋 脚本列表

### 部署和运行脚本
- `deploy_renewal.py` - Renewal Workflow 部署脚本（检查配置并部署）
- `run_renewal_production.py` - 手动运行 Renewal Workflow 生产环境

## ⚠️ 注意

- 大部分临时测试脚本已被清理
- 正式的测试文件位于 `tests/` 目录
- 生产环境主要通过 GitHub Actions 自动运行（见 `.github/workflows/`）
- 这些脚本主要用于手动部署和调试

