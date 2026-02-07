# 快速开始指南

5分钟完成OCR服务部署

## 方式A：Railway.app（最简单）

### 1. 准备代码（2分钟）

```bash
# 进入OCR服务目录
cd E:\claudePractice\scan\ocr-service

# 初始化Git
git init
git add .
git commit -m "Initial commit"

# 推送到GitHub
# （先在GitHub创建新仓库）
git remote add origin https://github.com/YOUR_USERNAME/ocr-service.git
git push -u origin main
```

### 2. Railway部署（3分钟）

1. 访问 **https://railway.app/**
2. 点击"Login" → 用GitHub登录
3. 点击"New Project" → "Deploy from GitHub repo"
4. 选择你的仓库
5. 等待自动部署完成（首次5分钟）

### 3. 获取URL（30秒）

部署成功后，复制Railway显示的URL，例如：
```
https://ocr-service.up.railway.app
```

### 4. 配置云函数（1分钟）

在微信云开发控制台设置环境变量：
```
OCR_SERVICE_URL=https://ocr-service.up.railway.app
```

### 5. 测试（30秒）

在小程序中使用OCR扫描功能！

---

## 方式B：本地运行（仅测试）

```bash
# 安装依赖
cd ocr-service
pip install -r requirements.txt

# 启动服务
python main.py

# 服务运行在 http://localhost:8000
```

云函数环境变量设置为：
```
OCR_SERVICE_URL=http://localhost:8000
```

---

## 验证服务

访问以下URL测试：

```bash
# 健康检查
curl https://your-url/health

# 预期响应：
# {"status":"healthy","ocr_engine":"initialized"}
```

---

## 完成！

现在您的小程序已具备真实的OCR识别能力！🎉

识别内容：
- ✅ 食品名称
- ✅ 配料表
- ✅ 营养成分
- ✅ 生产信息
- ✅ 13项强制标示内容
