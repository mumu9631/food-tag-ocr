"""
食品标签OCR识别服务（模拟测试版）
无需任何OCR引擎，用于测试完整流程
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
import logging
from datetime import datetime
import random

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="食品标签OCR识别服务（模拟版）",
    description="模拟OCR识别，用于测试完整流程",
    version="1.0.0-mock"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class OCRRequest(BaseModel):
    imageUrl: str

# 响应模型
class FoodLabelResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processingTime: Optional[float] = None


# 模拟的食品标签数据
MOCK_DATA = [
    {
        "name": "全麦吐司面包",
        "category": "焙烤食品",
        "ingredients": "全麦粉、小麦粉、水、白砂糖、食用植物油、酵母、食盐、乳粉、面包改良剂",
        "netContent": "400g",
        "specification": "400g/袋",
        "producer": "XX烘焙食品有限公司",
        "address": "XX市XX区XX街道XX路烘焙产业园3号楼",
        "contactInfo": "0XX-34567890",
        "productionDate": "2025-04-20",
        "shelfLife": "7天",
        "storageConditions": "置于阴凉干燥处保存",
        "foodProductionLicenseNumber": "SC10435792468013",
        "productStandardCode": "GB/T 20981",
        "allergens": "含有小麦制品、乳制品",
        "commodityBarcode": "6913579246801",
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
    {
        "name": "特级生抽酱油",
        "category": "调味品",
        "ingredients": "水、非转基因大豆、小麦粉、食用盐、白砂糖、谷氨酸钠",
        "netContent": "500mL",
        "producer": "XX调味品有限公司",
        "productionDate": "2025-04-01",
        "shelfLife": "18个月",
        "nutrition": {
            "energy": "180kJ",
            "protein": "8.6g",
            "fat": "0g",
            "carbohydrate": "12.0g",
            "sugar": "9.5g",
            "sodium": "5800mg"
        }
    }
]


@app.get("/")
async def root():
    """健康检查"""
    return {
        "service": "食品标签OCR识别服务（模拟版）",
        "version": "1.0.0-mock",
        "status": "running",
        "note": "这是模拟测试版本，返回随机示例数据。生产环境请部署完整版到Railway"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "ocr_engine": "Mock (for testing only)"
    }


@app.post("/ocr", response_model=FoodLabelResponse)
async def recognize_food_label(request: OCRRequest):
    """
    模拟OCR识别（返回随机示例数据）
    用于测试完整的前后端流程
    """
    start_time = datetime.now()

    try:
        logger.info(f"模拟OCR识别: {request.imageUrl}")

        # 模拟处理时间（2-3秒）
        import time
        time.sleep(random.uniform(2, 3))

        # 随机返回一个示例数据
        food_label = random.choice(MOCK_DATA)

        # 添加随机变化，模拟不同识别结果
        food_label['commodityBarcode'] = f"69{random.randint(100000000, 999999999)}"

        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"模拟识别完成，耗时: {processing_time:.2f}秒")

        return FoodLabelResponse(
            success=True,
            data=food_label,
            processingTime=processing_time
        )

    except Exception as e:
        logger.error(f"处理失败: {str(e)}", exc_info=True)
        processing_time = (datetime.now() - start_time).total_seconds()
        return FoodLabelResponse(
            success=False,
            error=str(e),
            processingTime=processing_time
        )


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    logger.info("启动模拟OCR服务...")
    logger.info("注意：这是测试版本，不会进行真实OCR识别")
    logger.info("生产环境请使用完整PaddleOCR版本并部署到Railway")
    uvicorn.run("main_mock:app", host="0.0.0.0", port=port, reload=True)
