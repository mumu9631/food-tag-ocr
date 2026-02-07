# 食品标签OCR识别服务

基于PaddleOCR的食品标签智能识别与解析服务，符合GB 7718-2025标准，支持13项强制标示内容自动提取。

## 功能特性

✅ **高精度识别**: 基于PaddleOCR，中文识别准确率高
✅ **智能解析**: 自动提取13项强制标示内容
✅ **营养计算**: 自动计算NRV营养素参考值
✅ **快速部署**: 支持Docker一键部署
✅ **免费额度**: 兼容Railway/Render免费云平台

## 13项强制标示内容

1. 食品名称
2. 配料表
3. 净含量和规格
4. 生产者和经营者信息（名称、地址、联系方式）
5. 日期标示（生产日期、保质期）
6. 贮存条件
7. 食品生产许可证编号
8. 产品标准代号
9. 质量（品质）等级
10. 致敏物质
11. 营养标签
12. 警示语
13. 辐照食品标示

## 快速开始

### 本地运行

```bash
# 1. 克隆项目
cd ocr-service

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python main.py

# 服务将在 http://localhost:8000 启动
```

### Railway.app 部署（推荐）

1. **准备账号**
   - 访问 [Railway.app](https://railway.app/)
   - 使用GitHub账号登录
   - 新用户可获得$5免费额度/月

2. **部署步骤**
   ```bash
   # 安装Railway CLI
   npm install -g @railway/cli

   # 登录
   railway login

   # 初始化项目
   railway init

   # 部署
   railway up
   ```

3. **获取服务URL**
   - 访问 Railway 控制台
   - 查看项目部署后的URL
   - 示例: `https://your-project.railway.app`

### Render 部署

1. **准备账号**
   - 访问 [Render.com](https://render.com/)
   - 使用GitHub账号登录

2. **部署步骤**
   - 将代码推送到GitHub
   - 在Render中创建"New Web Service"
   - 连接GitHub仓库
   - 选择"Docker"运行时
   - 点击"Deploy"

## API 文档

### 健康检查

```
GET /health
```

**响应示例**:
```json
{
  "status": "healthy",
  "ocr_engine": "initialized"
}
```

### OCR识别

```
POST /ocr
```

**请求参数**:
```json
{
  "imageUrl": "https://your-cloud-storage.com/food-label.jpg"
}
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "name": "全麦吐司面包",
    "ingredients": "全麦粉、小麦粉、水、白砂糖、食用植物油、酵母、食盐、乳粉",
    "netContent": "400g",
    "producer": "XX烘焙食品有限公司",
    "nutrition": {
      "energy": "1450kJ",
      "protein": "10.2g",
      "fat": "5.6g",
      "carbohydrate": "52.0g",
      "sugar": "6.8g",
      "sodium": "350mg",
      "energyNRV": "17%",
      "proteinNRV": "17%",
      "fatNRV": "9%",
      "carbohydrateNRV": "17%",
      "sodiumNRV": "18%"
    }
  },
  "processingTime": 2.35
}
```

## 与小程序集成

### 1. 部署服务后获取URL

假设部署后的URL为: `https://your-ocr-service.railway.app`

### 2. 修改云函数

在 `cloudfunctions/analyzeFoodLabel/index.js` 中添加:

```javascript
const OCR_SERVICE_URL = 'https://your-ocr-service.railway.app';

exports.main = async (event, context) => {
  const { imageUrl } = event;

  if (imageUrl) {
    // 调用OCR服务
    const ocrResult = await callOCRService(imageUrl);
    return ocrResult;
  }
};

async function callOCRService(imageUrl) {
  const axios = require('axios');

  try {
    const response = await axios.post(
      `${OCR_SERVICE_URL}/ocr`,
      { imageUrl },
      { timeout: 30000 }
    );

    return response.data;
  } catch (error) {
    console.error('OCR调用失败', error);
    throw error;
  }
}
```

### 3. 小程序前端调用

```javascript
// 上传图片到云存储
const uploadRes = await wx.cloud.uploadFile({
  cloudPath: `ocr/${Date.now()}.jpg`,
  filePath: imagePath
});

// 获取临时URL
const fileList = await wx.cloud.getTempFileURL({
  fileList: [uploadRes.fileID]
});
const imageUrl = fileList.fileList[0].tempFileURL;

// 调用云函数
const result = await wx.cloud.callFunction({
  name: 'analyzeFoodLabel',
  data: { imageUrl }
});
```

## 性能优化

### 图片处理

- **压缩**: 自动将图片压缩至2048px以内
- **格式转换**: 自动转为RGB格式
- **大小限制**: 最大10MB

### 识别速度

- **平均耗时**: 2-5秒
- **首次调用**: 5-10秒（加载模型）
- **后续调用**: 1-3秒（模型已缓存）

### 费用估算

基于Railway免费版:
- **免费额度**: $5/月 ≈ 500小时运行时间
- **单次识别**: 约0.001小时
- **月调用次数**: 约500,000次（理论值）

## 故障排查

### OCR识别失败

1. **图片质量问题**
   - 确保图片清晰，光线充足
   - 避免反光和模糊
   - 建议分辨率≥720p

2. **文字遮挡**
   - 确保标签完整无遮挡
   - 避免折叠和污损

3. **服务超时**
   - 默认超时30秒
   - 可在云函数中调整`timeout`参数

### 部署失败

1. **内存不足**
   - Railway免费版: 512MB
   - 如果内存溢出，考虑升级到付费版

2. **模型下载慢**
   - 首次启动需下载PaddleOCR模型（~10MB）
   - 耐心等待1-2分钟

## 技术栈

- **Web框架**: FastAPI
- **OCR引擎**: PaddleOCR
- **深度学习**: PaddlePaddle
- **图像处理**: Pillow
- **部署**: Docker + Railway/Render

## 许可证

本项目仅用于学习和研究目的。

## 联系方式

如有问题，请提交Issue。
