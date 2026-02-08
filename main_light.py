"""
食品标签OCR识别服务（轻量级测试版）
使用Tesseract OCR（无需PaddlePaddle，支持Python 3.14）
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, List, Any
import pytesseract
from PIL import Image
import requests
import io
import re
import os
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="食品标签OCR识别服务（测试版）",
    description="基于Tesseract OCR的食品标签智能识别",
    version="1.0.0-test"
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


@app.get("/")
async def root():
    """健康检查"""
    return {
        "service": "食品标签OCR识别服务（测试版）",
        "version": "1.0.0",
        "ocr_engine": "Tesseract",
        "status": "running",
        "note": "这是测试版本，使用Tesseract OCR。生产环境请使用PaddleOCR版本"
    }


@app.get("/health")
async def health_check():
    """详细健康检查"""
    try:
        # 检查Tesseract是否可用
        pytesseract.get_tesseract_version()
        return {
            "status": "healthy",
            "ocr_engine": "Tesseract",
            "tesseract_version": str(pytesseract.get_tesseract_version())
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"OCR引擎未就绪: {str(e)}")


@app.post("/ocr", response_model=FoodLabelResponse)
async def recognize_food_label(request: OCRRequest):
    """识别食品标签"""
    start_time = datetime.now()

    try:
        logger.info(f"开始识别图片: {request.imageUrl}")

        # 1. 下载图片
        img_data = download_image(request.imageUrl)
        img = Image.open(io.BytesIO(img_data))

        # 2. OCR识别（使用中英文）
        text = pytesseract.image_to_string(img, lang='chi_sim+eng')

        logger.info(f"OCR识别完成，文本长度: {len(text)}")

        # 3. 解析文本
        food_label = parse_text_to_food_label(text)

        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"识别完成，耗时: {processing_time:.2f}秒")

        return FoodLabelResponse(
            success=True,
            data=food_label,
            processingTime=processing_time
        )

    except Exception as e:
        logger.error(f"识别失败: {str(e)}", exc_info=True)
        processing_time = (datetime.now() - start_time).total_seconds()
        return FoodLabelResponse(
            success=False,
            error=str(e),
            processingTime=processing_time
        )


def download_image(image_url: str) -> bytes:
    """下载图片"""
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(image_url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.content


def parse_text_to_food_label(text: str) -> Dict[str, Any]:
    """从OCR文本中解析食品标签（简化版）"""

    food_label = {}

    # 简化的提取逻辑（用于测试）
    lines = text.split('\n')

    # 食品名称（取第一个有意义的行）
    for line in lines:
        if len(line) > 2 and len(line) < 50:
            food_label['name'] = line.strip()
            break

    # 配料表
    for line in lines:
        if '配料' in line:
            food_label['ingredients'] = line.replace('配料', '').replace('：', '').strip()
            break

    # 净含量
    match = re.search(r'净含量.*?(\d+\.?\d*)\s*([克gG千克kg])', text)
    if match:
        food_label['netContent'] = f"{match.group(1)}{match.group(2)}"

    # 生产日期
    match = re.search(r'生产日期.*?(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', text)
    if match:
        food_label['productionDate'] = match.group(1)

    # 保质期
    match = re.search(r'保质期.*?(\d+)\s*([个月天年周])', text)
    if match:
        food_label['shelfLife'] = f"{match.group(1)}{match.group(2)}"

    # 生产商
    for line in lines:
        if '有限公司' in line and '地址' not in line:
            food_label['producer'] = line.strip()
            break

    # 营养成分（简化版）
    nutrition = {}
    energy_match = re.search(r'能量.*?(\d+\.?\d*)\s*(kJ|千焦)', text)
    if energy_match:
        nutrition['energy'] = f"{energy_match.group(1)}{energy_match.group(2)}"

    protein_match = re.search(r'蛋白质.*?(\d+\.?\d*)\s*g', text)
    if protein_match:
        nutrition['protein'] = f"{protein_match.group(1)}g"

    fat_match = re.search(r'脂肪.*?(\d+\.?\d*)\s*g', text)
    if fat_match:
        nutrition['fat'] = f"{fat_match.group(1)}g"

    if nutrition:
        food_label['nutrition'] = nutrition

    return food_label


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main_light:app", host="0.0.0.0", port=port, reload=True)
