# 应该运行哪个脚本？STM1脚本说明

## 🎯 核心说明

**GitHub Actions运行的是**: `scripts/auto_stm1_calling.py`

**本地手动测试应该用**: `scripts/auto_stm1_calling.py` （与GitHub Actions相同）

## 📋 脚本对比

### 1. `scripts/auto_stm1_calling.py` ⭐ **这是GitHub Actions运行的脚本**

**用途**: 
- 连续自动化调用STM1客户
- 从9:00 AM到4:55 PM Pacific Time持续运行
- 专门处理 `called_times` 为空的行
- 每次调用间隔36秒

**运行方式**:
```bash
# 本地测试（与GitHub Actions完全相同）
python scripts/auto_stm1_calling.py
```

**GitHub Actions配置**:
- 文件: `.github/workflows/daily-stm1.yml`
- 运行命令: `python scripts/auto_stm1_calling.py`
- 自动运行时间: UTC 16:00 (PDT) 或 UTC 17:00 (PST)

**特点**:
- ✅ 这是**生产环境**使用的脚本
- ✅ 与GitHub Actions运行的是**同一个脚本**
- ✅ 本地测试成功 = GitHub Actions也会成功（如果token同步）

---

### 2. `workflows/stm1.py` - STM1工作流逻辑

**用途**:
- 包含STM1的核心业务逻辑
- 提供 `run_stm1_batch_calling()` 函数
- 被其他脚本调用，不直接运行

**运行方式**:
```bash
# 直接运行（批量模式）
python workflows/stm1.py
```

**特点**:
- ⚠️ 这是**批量调用模式**，不是连续调用
- ⚠️ 与GitHub Actions运行的模式**不同**
- ✅ 适合一次性测试所有符合条件的客户

---

### 3. `main.py` - 主入口脚本

**用途**:
- 支持多个workflow（cancellations, renewals, stm1等）
- 可以通过参数选择运行哪个workflow

**运行方式**:
```bash
# 运行STM1 workflow
python main.py stm1
```

**特点**:
- ⚠️ 运行的是 `workflows/stm1.py` 的批量模式
- ⚠️ 与GitHub Actions运行的模式**不同**
- ✅ 适合测试多个workflow

---

## 🔍 如何确认GitHub Actions运行的是哪个脚本？

### 方法1: 查看Workflow文件

文件: `.github/workflows/daily-stm1.yml`

```yaml
- name: Run Automated STM1 Calling
  env:
    SMARTSHEET_ACCESS_TOKEN: ${{ secrets.SMARTSHEET_ACCESS_TOKEN }}
    VAPI_API_KEY: ${{ secrets.VAPI_API_KEY }}
  run: python scripts/auto_stm1_calling.py  # ← 这里！
```

### 方法2: 查看GitHub Actions日志

1. 访问: https://github.com/Across-America/python-read-write-sheet/actions
2. 点击最新的STM1 workflow运行
3. 查看日志中的第一行，应该看到：
   ```
   🤖 AUTOMATED STM1 CALLING - EMPTY CALLED_TIMES
   ```

---

## ✅ 本地测试的正确方法

### 推荐：使用与GitHub Actions相同的脚本

```bash
# 1. 确保token已同步
python scripts/verify_token_sync.py

# 2. 运行与GitHub Actions相同的脚本
python scripts/auto_stm1_calling.py
```

**为什么这样做？**
- ✅ 确保本地和GitHub Actions运行的是**完全相同的代码**
- ✅ 本地测试成功 = GitHub Actions也会成功
- ✅ 避免"本地可以但GitHub Actions不行"的问题

---

## 📊 脚本功能对比表

| 脚本 | 运行模式 | 调用方式 | GitHub Actions使用 | 本地测试推荐 |
|------|---------|---------|-------------------|-------------|
| `scripts/auto_stm1_calling.py` | 连续调用 | 持续运行9 AM-4:55 PM | ✅ **是** | ✅ **推荐** |
| `workflows/stm1.py` | 批量调用 | 一次性处理所有 | ❌ 否 | ⚠️ 仅测试用 |
| `main.py stm1` | 批量调用 | 一次性处理所有 | ❌ 否 | ⚠️ 仅测试用 |

---

## 🚨 常见混淆

### ❌ 错误理解
"我运行了 `workflows/stm1.py` 成功了，所以GitHub Actions也会成功"

**问题**: 
- `workflows/stm1.py` 是批量模式
- GitHub Actions运行的是连续模式 (`scripts/auto_stm1_calling.py`)
- 两者逻辑不同！

### ✅ 正确理解
"我运行了 `scripts/auto_stm1_calling.py` 成功了，所以GitHub Actions也会成功"

**原因**:
- 这是GitHub Actions实际运行的脚本
- 本地和GitHub Actions运行的是**完全相同的代码**

---

## 🔧 如何确保本地和GitHub使用相同代码？

### 1. 检查当前运行的脚本

```bash
# 查看GitHub Actions配置
cat .github/workflows/daily-stm1.yml | grep "python"
```

### 2. 本地运行相同脚本

```bash
# 运行与GitHub Actions相同的脚本
python scripts/auto_stm1_calling.py
```

### 3. 验证代码已提交

```bash
# 检查是否有未提交的更改
git status

# 如果有更改，提交并推送
git add scripts/auto_stm1_calling.py
git commit -m "Update STM1 calling script"
git push origin master
```

---

## 📝 快速参考

### 本地测试STM1（推荐）
```bash
python scripts/auto_stm1_calling.py
```

### 查看GitHub Actions运行的脚本
```bash
cat .github/workflows/daily-stm1.yml
```

### 验证token同步
```bash
python scripts/verify_token_sync.py
```

### 同步token到GitHub
```bash
python scripts/sync_token_to_github_secrets.py
```

---

## 🎯 总结

1. **GitHub Actions运行**: `scripts/auto_stm1_calling.py`
2. **本地测试应该用**: `scripts/auto_stm1_calling.py` （相同脚本）
3. **确保代码已提交**: 本地更改后要push到GitHub
4. **确保token同步**: 使用 `sync_token_to_github_secrets.py`

**记住**: 本地测试成功 ≠ GitHub Actions成功，除非：
- ✅ 运行的是**同一个脚本**
- ✅ 代码已**提交到GitHub**
- ✅ Token已**同步到GitHub Secrets**
