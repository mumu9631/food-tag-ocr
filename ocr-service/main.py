"""
食品标签OCR识别服务
基于PaddleOCR实现食品标签智能识别和13项强制标示内容提取
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, List, Any
import paddleocr
import requests
from PIL import Image
import io
import re
import os
import sys
import logging
from datetime import datetime

# 禁用PaddlePaddle模型源检查（必须在使用paddleocr之前设置）
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'
os.environ['PADDLE_SKIP_CHECK_DYNAMIC_LIBRARY'] = 'True'

# 配置日志（输出到stdout，以便Railway显示）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="食品标签OCR识别服务",
    description="基于PaddleOCR的食品标签智能识别与解析",
    version="1.0.0"
)

# 配置CORS（允许小程序调用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局PaddleOCR实例（避免重复加载）
ocr = None

def get_ocr_engine():
    """获取或初始化OCR引擎"""
    global ocr
    if ocr is None:
        logger.info("初始化PaddleOCR引擎...")
        print("[DEBUG] 正在初始化PaddleOCR...")
        # 使用最基础的参数，避免版本兼容问题
        ocr = paddleocr.PaddleOCR(
            use_angle_cls=True,  # 使用方向分类器
            lang='ch'            # 中文
        )
        logger.info("PaddleOCR引擎初始化完成")
        print("[DEBUG] PaddleOCR初始化完成")
    return ocr


# 请求模型
class OCRRequest(BaseModel):
    imageUrl: str  # 云存储图片URL


# 响应模型
class NutritionInfo(BaseModel):
    energy: Optional[str] = None
    protein: Optional[str] = None
    fat: Optional[str] = None
    carbohydrate: Optional[str] = None
    sugar: Optional[str] = None
    sodium: Optional[str] = None
    energyNRV: Optional[str] = None
    proteinNRV: Optional[str] = None
    fatNRV: Optional[str] = None
    carbohydrateNRV: Optional[str] = None
    sugarNRV: Optional[str] = None
    sodiumNRV: Optional[str] = None


class FoodLabelResponse(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    processingTime: Optional[float] = None


@app.get("/")
async def root():
    """健康检查接口"""
    return {
        "service": "食品标签OCR识别服务",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """简单健康检查（仅检查服务是否运行）"""
    return {
        "service": "食品标签OCR识别服务",
        "status": "running"
    }


@app.get("/health/detailed")
async def detailed_health_check():
    """详细健康检查（包含OCR引擎状态）"""
    try:
        # 尝试初始化OCR引擎
        engine = get_ocr_engine()
        return {
            "status": "healthy",
            "ocr_engine": "initialized",
            "memory_usage": f"{os.environ.get('MEMORY_USAGE', 'N/A')}"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"服务未就绪: {str(e)}")


@app.post("/ocr", response_model=FoodLabelResponse)
async def recognize_food_label(request: OCRRequest):
    """
    识别食品标签并返回结构化数据

    接收图片URL，使用PaddleOCR识别文字，智能解析13项强制标示内容
    """
    start_time = datetime.now()

    try:
        print(f"[DEBUG] 开始识别图片: {request.imageUrl}")
        logger.info(f"开始识别图片: {request.imageUrl}")

        # 1. 下载图片
        img_data = download_image(request.imageUrl)
        print(f"[DEBUG] 图片下载完成，数据长度: {len(img_data)} bytes")
        logger.info(f"图片下载完成，数据长度: {len(img_data)} bytes")

        # 2. PaddleOCR识别
        # 验证图片数据
        print(f"[DEBUG] 传递给PaddleOCR的数据长度: {len(img_data)} bytes")
        print(f"[DEBUG] 数据前16字节(hex): {img_data[:16].hex() if len(img_data) >= 16 else img_data.hex()}")
        logger.info(f"传递给PaddleOCR的数据长度: {len(img_data)} bytes")

        # 检查是否为有效的JPEG/PNG数据
        if len(img_data) >= 4:
            if img_data[:2] == b'\xff\xd8':
                print("[DEBUG] 图片格式验证: JPEG (魔数: FF D8)")
                logger.info("图片格式验证: JPEG")
            elif img_data[:8] == b'\x89PNG\r\n\x1a\n':
                print("[DEBUG] 图片格式验证: PNG (魔数: 89 50 4E 47)")
                logger.info("图片格式验证: PNG")
            else:
                print(f"[DEBUG] 警告: 未知的图片格式，前4字节: {img_data[:4].hex()}")
                logger.warning(f"未知的图片格式，前4字节: {img_data[:4].hex()}")

        engine = get_ocr_engine()
        print(f"[DEBUG] 开始调用PaddleOCR...")
        logger.info("开始调用PaddleOCR...")
        ocr_result = engine.ocr(img_data)
        print(f"[DEBUG] PaddleOCR调用完成")
        logger.info("PaddleOCR调用完成")

        # 3. 提取识别的文本
        # 调试：打印OCR原始结果结构
        print(f"[DEBUG] OCR原始结果类型: {type(ocr_result)}")
        logger.info(f"OCR原始结果类型: {type(ocr_result)}")
        if ocr_result:
            print(f"[DEBUG] OCR结果长度: {len(ocr_result)}")
            logger.info(f"OCR结果长度: {len(ocr_result)}")
            if len(ocr_result) > 0:
                print(f"[DEBUG] OCR结果[0]类型: {type(ocr_result[0])}")
                logger.info(f"OCR结果[0]类型: {type(ocr_result[0])}")
                if ocr_result[0]:
                    print(f"[DEBUG] OCR结果[0]长度: {len(ocr_result[0])}")
                    logger.info(f"OCR结果[0]长度: {len(ocr_result[0])}")
                    print(f"[DEBUG] OCR结果[0]前3项: {ocr_result[0][:3]}")
                    logger.info(f"OCR结果[0]前3项: {ocr_result[0][:3]}")

        text_lines = extract_text_lines(ocr_result)
        print(f"[DEBUG] 识别到 {len(text_lines)} 行文本")
        logger.info(f"识别到 {len(text_lines)} 行文本")

        # 调试：打印前10行识别的文本
        if text_lines:
            logger.info(f"前10行文本: {text_lines[:10]}")
        else:
            logger.warning("未识别到任何文本！")

        # 4. 智能解析13项食品标签内容
        food_label = parse_food_label(text_lines)

        # 5. 计算处理时间
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
    """
    下载图片并返回字节数据

    Args:
        image_url: 图片URL

    Returns:
        图片字节数据
    """
    try:
        # 设置请求头（模拟浏览器）
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        print(f"[DEBUG] 开始下载图片: {image_url}")
        logger.info(f"开始下载图片: {image_url}")

        # 下载图片（超时10秒）
        response = requests.get(image_url, headers=headers, timeout=10)
        response.raise_for_status()

        # 检查文件大小（限制10MB）
        content_length = len(response.content)
        print(f"[DEBUG] 原始图片大小: {content_length} bytes ({content_length / 1024:.2f}KB)")
        logger.info(f"原始图片大小: {content_length} bytes ({content_length / 1024:.2f}KB)")

        if content_length > 10 * 1024 * 1024:
            raise ValueError(f"图片过大: {content_length / 1024 / 1024:.2f}MB")

        # 检查Content-Type
        content_type = response.headers.get('Content-Type', '')
        print(f"[DEBUG] Content-Type: {content_type}")
        logger.info(f"Content-Type: {content_type}")

        # 图片预处理（压缩、调整大小）
        img = preprocess_image(response.content)

        return img

    except requests.RequestException as e:
        print(f"[DEBUG] 图片下载失败: {str(e)}")
        raise Exception(f"图片下载失败: {str(e)}")
    except Exception as e:
        print(f"[DEBUG] 图片处理失败: {str(e)}")
        raise Exception(f"图片处理失败: {str(e)}")


def preprocess_image(img_bytes: bytes) -> bytes:
    """
    图片预处理：压缩和格式转换

    Args:
        img_bytes: 原始图片字节数据

    Returns:
        处理后的图片字节数据
    """
    try:
        print(f"[DEBUG] 开始图片预处理...")
        logger.info("开始图片预处理...")

        img = Image.open(io.BytesIO(img_bytes))

        # 详细图片信息
        print(f"[DEBUG] 图片格式: {img.format}")
        print(f"[DEBUG] 图片模式: {img.mode}")
        print(f"[DEBUG] 图片尺寸: {img.size} (宽x高)")
        print(f"[DEBUG] 图片模式详情: {img.mode if hasattr(img, 'mode') else 'N/A'}")
        logger.info(f"图片格式: {img.format}, 模式: {img.mode}, 尺寸: {img.size}")

        # 转为RGB（去除透明通道）
        if img.mode != 'RGB':
            print(f"[DEBUG] 转换图片模式: {img.mode} -> RGB")
            img = img.convert('RGB')

        # 压缩图片（最大边长2048px）
        original_size = img.size
        max_size = 2048
        if max(img.size) > max_size:
            print(f"[DEBUG] 压缩图片: {img.size} -> 最大边长{max_size}px")
            img.thumbnail((max_size, max_size))
            print(f"[DEBUG] 压缩后尺寸: {img.size}")

        # 保存到内存
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=85)
        output.seek(0)

        processed_bytes = output.read()
        print(f"[DEBUG] 图片预处理完成: {len(img_bytes)} -> {len(processed_bytes)} bytes (压缩率: {(1-len(processed_bytes)/len(img_bytes))*100:.1f}%)")
        logger.info(f"图片压缩完成: {len(img_bytes)} -> {len(processed_bytes)} bytes")

        return processed_bytes

    except Exception as e:
        print(f"[DEBUG] 图片预处理失败，使用原图: {str(e)}")
        logger.warning(f"图片预处理失败，使用原图: {str(e)}")
        return img_bytes


def extract_text_lines(ocr_result) -> List[str]:
    """
    从OCR结果中提取文本行

    Args:
        ocr_result: PaddleOCR返回的结果

    Returns:
        文本行列表
    """
    text_lines = []

    if not ocr_result or len(ocr_result) == 0:
        logger.warning("OCR结果为空")
        return text_lines

    try:
        print(f"[DEBUG] 开始提取文本，ocr_result[0]长度: {len(ocr_result[0]) if ocr_result[0] else 0}")
        logger.info(f"开始提取文本，ocr_result[0]长度: {len(ocr_result[0]) if ocr_result[0] else 0}")

        for idx, line in enumerate(ocr_result[0]):
            # line格式: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]], (text, confidence)
            if len(line) >= 2:
                text = line[1][0] if line[1] else ""
                confidence = line[1][1] if len(line[1]) > 1 else 0

                # 调试：打印前10个识别结果（增加到10个）
                if idx < 10:
                    print(f"[DEBUG] 识别结果[{idx}]: text='{text}', confidence={confidence:.3f}")
                    logger.info(f"识别结果[{idx}]: text='{text}', confidence={confidence:.3f}")

                # 降低置信度阈值到0.1（几乎不过滤，先看是否有识别结果）
                if confidence > 0.1 and text.strip():
                    text_lines.append(text.strip())

        print(f"[DEBUG] 经过置信度过滤(>0.1)后，剩余{len(text_lines)}行文本")
        logger.info(f"经过置信度过滤(>0.1)后，剩余{len(text_lines)}行文本")

    except Exception as e:
        logger.error(f"提取文本失败: {str(e)}", exc_info=True)

    return text_lines


def parse_food_label(text_lines: List[str]) -> Dict[str, Any]:
    """
    从OCR文本中智能解析食品标签13项强制标示内容

    Args:
        text_lines: OCR识别的文本行列表

    Returns:
        结构化的食品标签数据
    """
    # 合并所有文本
    full_text = '\n'.join(text_lines)

    food_label = {
        # 1. 食品名称
        'name': extract_food_name(text_lines, full_text),

        # 2. 配料表
        'ingredients': extract_ingredients(text_lines, full_text),

        # 3. 净含量和规格
        'netContent': extract_net_content(full_text),
        'specification': extract_specification(full_text),

        # 4. 生产者和经营者信息
        'producer': extract_producer(text_lines, full_text),
        'address': extract_address(text_lines, full_text),
        'contactInfo': extract_contact_info(full_text),

        # 5. 日期标示
        'productionDate': extract_production_date(full_text),
        'shelfLife': extract_shelf_life(full_text),

        # 6. 贮存条件
        'storageConditions': extract_storage_conditions(text_lines, full_text),

        # 7. 食品生产许可证编号
        'foodProductionLicenseNumber': extract_license_number(full_text),

        # 8. 产品标准代号
        'productStandardCode': extract_standard_code(full_text),

        # 9. 质量（品质）等级
        'qualityGrade': extract_quality_grade(full_text),

        # 10. 致敏物质
        'allergens': extract_allergens(full_text),

        # 11. 营养标签
        'nutrition': extract_nutrition(text_lines, full_text),

        # 12. 警示语
        'warning': extract_warning(text_lines, full_text),

        # 13. 辐照食品标示
        'irradiated': extract_irradiated(full_text),

        # 额外字段
        'commodityBarcode': extract_barcode(full_text),
    }

    # 清理空值（保留字段，但将None转为空字符串）
    food_label = {k: (v if v is not None else '') for k, v in food_label.items()}

    return food_label


# ==================== 提取函数 ====================

def extract_food_name(text_lines: List[str], full_text: str) -> Optional[str]:
    """提取食品名称"""
    # 查找包含"食品名称"的行
    for line in text_lines:
        if '食品名称' in line or '产品名称' in line:
            # 提取冒号后的内容
            match = re.search(r'[名称][:：]\s*(.+)', line)
            if match:
                return match.group(1).strip()

    # 如果没有明确标注，取第一行非空文本（通常是名称）
    for line in text_lines:
        if len(line) > 2 and len(line) < 50:
            return line.strip()

    return None


def extract_ingredients(text_lines: List[str], full_text: str) -> Optional[str]:
    """提取配料表"""
    for line in text_lines:
        if any(keyword in line for keyword in ['配料', '成分', '原料']):
            # 提取冒号后的内容
            match = re.search(r'[配料表|成分|原料][:：]\s*(.+)', line)
            if match:
                ingredients = match.group(1).strip()
                # 如果内容过短，可能在下一行
                if len(ingredients) < 10:
                    # 查找后续行
                    idx = text_lines.index(line)
                    for i in range(idx + 1, min(idx + 5, len(text_lines))):
                        if text_lines[i].strip():
                            ingredients += ' ' + text_lines[i].strip()
                            if len(ingredients) > 50:  # 配料表通常较长
                                break
                return ingredients.strip()

    return None


def extract_net_content(full_text: str) -> Optional[str]:
    """提取净含量"""
    patterns = [
        r'净含量[:：]\s*(\d+\.?\d*)\s*([克gG千克kgK毫升mlML升L])',
        r'净含量[:：]\s*(\d+\.?\d*)\s*([克千克克毫升升]+)',
        r'(\d+\.?\d*)\s*[克gG][克gG]?\s*(?:/\s*[袋瓶盒包箱])',
    ]

    for pattern in patterns:
        match = re.search(pattern, full_text)
        if match:
            value = match.group(1)
            unit = match.group(2) if len(match.groups()) > 1 else '克'
            return f"{value}{unit}"

    return None


def extract_specification(full_text: str) -> Optional[str]:
    """提取规格"""
    patterns = [
        r'规格[:：]\s*(.+?)(?:\n|$)',
        r'(\d+[\u4e00-\u9fa5]/[\u4e00-\u9fa5]+)',
        r'(\d+)[克gGg]/[盒瓶包袋]',
    ]

    for pattern in patterns:
        match = re.search(pattern, full_text)
        if match:
            return match.group(1).strip()

    return None


def extract_producer(text_lines: List[str], full_text: str) -> Optional[str]:
    """提取生产者名称"""
    keywords = ['生产商', '生产厂家', '制造商', '委托生产企业', '生产者']

    for keyword in keywords:
        if keyword in full_text:
            # 查找关键词后的内容
            idx = full_text.find(keyword)
            match = re.search(r'{0}[:：]\s*(.+?)(?:\n|地址|电话)'.format(keyword), full_text[idx:])
            if match:
                return match.group(1).strip()

    # 尝试从文本行中提取（通常包含"有限公司"）
    for line in text_lines:
        if '有限公司' in line and '地址' not in line and len(line) < 50:
            return line.strip()

    return None


def extract_address(text_lines: List[str], full_text: str) -> Optional[str]:
    """提取地址"""
    for line in text_lines:
        if '地址' in line:
            match = re.search(r'地址[:：]\s*(.+)', line)
            if match:
                address = match.group(1).strip()
                # 地址可能跨行
                if len(address) < 10:
                    idx = text_lines.index(line)
                    if idx + 1 < len(text_lines):
                        address += ' ' + text_lines[idx + 1].strip()
                return address

    return None


def extract_contact_info(full_text: str) -> Optional[str]:
    """提取联系方式"""
    # 提取电话号码
    phone_patterns = [
        r'电话[:：]\s*(\d{3,4}[-\s]?\d{7,8})',
        r'联系方式[:：]\s*(.+?)(?:\n|$)',
        r'(\d{3,4}[-\s]?\d{7,8})',
    ]

    for pattern in phone_patterns:
        match = re.search(pattern, full_text)
        if match:
            return match.group(1).strip()

    return None


def extract_production_date(full_text: str) -> Optional[str]:
    """提取生产日期"""
    patterns = [
        r'生产日期[:：]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',
        r'生产日期[:：]\s*(\d{4}\.\d{1,2}\.\d{1,2})',
        r'见封口|见瓶身|见包装',  # 如果标注见某处
    ]

    for pattern in patterns:
        match = re.search(pattern, full_text)
        if match:
            return match.group(1).strip()

    return None


def extract_shelf_life(full_text: str) -> Optional[str]:
    """提取保质期"""
    patterns = [
        r'保质期[:：]\s*(\d+)\s*([个月天年周])',
        r'保质期[:：]\s*(.+?)(?:\n|$)',
    ]

    for pattern in patterns:
        match = re.search(pattern, full_text)
        if match:
            if len(match.groups()) > 1:
                return f"{match.group(1)}{match.group(2)}"
            return match.group(1).strip()

    return None


def extract_storage_conditions(text_lines: List[str], full_text: str) -> Optional[str]:
    """提取贮存条件"""
    for line in text_lines:
        if any(keyword in line for keyword in ['贮存', '保存', '储藏', '存放']):
            # 可能跨多行
            storage = line.strip()
            idx = text_lines.index(line)
            for i in range(idx + 1, min(idx + 3, len(text_lines))):
                if text_lines[i].strip() and not any(keyword in text_lines[i] for keyword in ['生产', '厂址', '电话']):
                    storage += ' ' + text_lines[i].strip()
                else:
                    break
            return storage

    return None


def extract_license_number(full_text: str) -> Optional[str]:
    """提取食品生产许可证编号"""
    patterns = [
        r'SC[1|2]\d{13}',  # 新版SC开头
        r'QS\d{12}',        # 旧版QS开头
        r'生产许可证编号[:：]\s*(SC\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, full_text)
        if match:
            return match.group(0) if pattern.startswith('SC') or pattern.startswith('QS') else match.group(1)

    return None


def extract_standard_code(full_text: str) -> Optional[str]:
    """提取产品标准代号"""
    patterns = [
        r'产品标准代号[:：]\s*([A-Z]{1,2}/[T]\s*\d+(?:\.\d+)?)',
        r'GB\s*/?\s*T\s*\d+(?:\.\d+)?',
        r'QB\s*/?\s*\d+(?:\.\d+)?',  # 轻工标准
        r'[A-Z]{1,2}/[T]\s*\d+(?:\.\d+)?',
    ]

    for pattern in patterns:
        match = re.search(pattern, full_text)
        if match:
            return match.group(1) if len(match.groups()) > 0 else match.group(0)

    return None


def extract_quality_grade(full_text: str) -> Optional[str]:
    """提取质量等级"""
    patterns = [
        r'质量等级[:：]\s*(.+?)(?:\n|$)',
        r'等级[:：]\s*([一二三四特优]+等)',
        r'([一二三四特优]+等品)',
    ]

    for pattern in patterns:
        match = re.search(pattern, full_text)
        if match:
            return match.group(1).strip()

    return None


def extract_allergens(full_text: str) -> Optional[str]:
    """提取致敏物质"""
    allergen_keywords = [
        '含有', '过敏', '致敏物质', '过敏原',
        '花生', '坚果', '牛奶', '乳制品', '鸡蛋',
        '大豆', '小麦', '鱼类', '甲壳类', '芝麻'
    ]

    for keyword in allergen_keywords:
        if keyword in full_text:
            # 查找完整的致敏提示
            match = re.search(r'(?:致敏物质|过敏原|含有)[:：]?\s*(.+?)(?:\n|$)', full_text)
            if match:
                return match.group(1).strip()
            return f"含有{keyword}"

    return None


def extract_nutrition(text_lines: List[str], full_text: str) -> Dict[str, Optional[str]]:
    """提取营养标签"""
    nutrition = {}

    # 营养成分正则模式
    patterns = {
        'energy': [
            r'能量[:：\s]*(\d+\.?\d*)\s*(kJ|千焦|kcal|千卡)',
            r'能量\s*(\d+\.?\d*)\s*(千焦|kJ)',
        ],
        'protein': [
            r'蛋白质[:：\s]*(\d+\.?\d*)\s*g',
        ],
        'fat': [
            r'脂肪[:：\s]*(\d+\.?\d*)\s*g',
        ],
        'carbohydrate': [
            r'碳水化合物[:：\s]*(\d+\.?\d*)\s*g',
        ],
        'sugar': [
            r'糖[:：\s]*(\d+\.?\d*)\s*g',
        ],
        'sodium': [
            r'钠[:：\s]*(\d+\.?\d*)\s*mg',
        ]
    }

    # 提取各项营养成分
    for key, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, full_text)
            if match:
                value = match.group(1)
                unit = match.group(2) if len(match.groups()) > 1 else ''
                nutrition[key] = f"{value}{unit}"
                break

    # 如果没有找到任何营养成分，尝试查找营养表区域
    if not nutrition:
        nutrition = extract_nutrition_from_table(text_lines)

    # 计算NRV百分比
    if nutrition:
        nutrition = calculate_nrv(nutrition)

    return nutrition


def extract_nutrition_from_table(text_lines: List[str]) -> Dict[str, Optional[str]]:
    """从表格形式的营养标签中提取"""
    nutrition = {}
    nutrition_keywords = ['能量', '蛋白质', '脂肪', '碳水化合物', '糖', '钠']

    for i, line in enumerate(text_lines):
        for keyword in nutrition_keywords:
            if keyword in line:
                # 尝试提取数值
                match = re.search(r'{0}[:：\s]*(\d+\.?\d*)\s*([a-zA-Z\u4e00-\u9fa5]+)'.format(keyword), line)
                if match:
                    key_map = {
                        '能量': 'energy',
                        '蛋白质': 'protein',
                        '脂肪': 'fat',
                        '碳水化合物': 'carbohydrate',
                        '糖': 'sugar',
                        '钠': 'sodium'
                    }
                    en_key = key_map.get(keyword)
                    if en_key:
                        nutrition[en_key] = f"{match.group(1)}{match.group(2)}"

    return nutrition


def calculate_nrv(nutrition: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    """计算营养素参考值百分比"""
    # NRV标准值（GB28050-2011）
    nrv_values = {
        'energy': 8400,     # kJ
        'protein': 60,      # g
        'fat': 60,          # g
        'carbohydrate': 300,# g
        'sugar': 50,        # g（参考值）
        'sodium': 2000      # mg
    }

    for key, nrv_ref in nrv_values.items():
        if key in nutrition and nutrition[key]:
            # 提取数值
            value_match = re.search(r'(\d+\.?\d*)', nutrition[key])
            if value_match:
                value = float(value_match.group(1))

                # 单位转换
                unit_match = re.search(r'(kcal|千卡|kJ|千焦)', nutrition[key])
                if unit_match:
                    unit = unit_match.group(1)
                    if unit in ['kcal', '千卡']:
                        value = value * 4.184  # 转换为kJ

                # 计算NRV%
                if key == 'energy':
                    nrv_percent = int((value / nrv_ref) * 100)
                else:
                    nrv_percent = int((value / nrv_ref) * 100)

                nutrition[f'{key}NRV'] = f"{nrv_percent}%"

    return nutrition


def extract_warning(text_lines: List[str], full_text: str) -> Optional[str]:
    """提取警示语"""
    for line in text_lines:
        if any(keyword in line for keyword in ['警示', '注意', '警告']):
            return line.strip()

    return None


def extract_irradiated(full_text: str) -> Optional[str]:
    """提取辐照食品标示"""
    if '辐照' in full_text or '本产品经辐照' in full_text:
        return "本品已辐照"

    return None


def extract_barcode(full_text: str) -> Optional[str]:
    """提取商品条码"""
    patterns = [
        r'条码[:：]\s*(\d{13})',
        r'69\d{11}',  # 中国商品条码以69开头
    ]

    for pattern in patterns:
        match = re.search(pattern, full_text)
        if match:
            return match.group(1) if len(match.groups()) > 0 else match.group(0)

    return None


# ==================== 启动配置 ====================

if __name__ == "__main__":
    import uvicorn

    # 从环境变量读取端口，默认8000
    port = int(os.environ.get("PORT", 8000))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
