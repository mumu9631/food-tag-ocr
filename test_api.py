"""
OCR服务测试脚本
用于本地测试API接口
"""

import requests
import json

# 服务地址（本地测试）
BASE_URL = "http://localhost:8000"

# 测试图片URL（可以使用云存储中的真实图片URL）
TEST_IMAGE_URL = "https://example.com/food-label.jpg"


def test_health():
    """测试健康检查接口"""
    print("\n=== 测试健康检查 ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_ocr(image_url: str):
    """测试OCR识别接口"""
    print("\n=== 测试OCR识别 ===")
    print(f"图片URL: {image_url}")

    payload = {"imageUrl": image_url}

    try:
        response = requests.post(
            f"{BASE_URL}/ocr",
            json=payload,
            timeout=60  # 60秒超时
        )

        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\n识别成功！耗时: {result.get('processingTime', 0):.2f}秒")

            if result.get('success'):
                data = result.get('data', {})
                print("\n--- 识别结果 ---")

                # 打印13项内容
                items = [
                    ('食品名称', data.get('name')),
                    ('配料表', data.get('ingredients')),
                    ('净含量', data.get('netContent')),
                    ('生产商', data.get('producer')),
                    ('地址', data.get('address')),
                    ('生产日期', data.get('productionDate')),
                    ('保质期', data.get('shelfLife')),
                    ('贮存条件', data.get('storageConditions')),
                    ('许可证编号', data.get('foodProductionLicenseNumber')),
                    ('标准代号', data.get('productStandardCode')),
                    ('致敏物质', data.get('allergens')),
                ]

                for label, value in items:
                    if value:
                        print(f"{label}: {value}")

                # 打印营养成分
                nutrition = data.get('nutrition', {})
                if nutrition:
                    print("\n--- 营养成分 ---")
                    for key, value in nutrition.items():
                        print(f"{key}: {value}")

                # 完整JSON
                print("\n--- 完整JSON ---")
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print(f"\n识别失败: {result.get('error')}")
        else:
            print(f"请求失败: {response.text}")

    except requests.Timeout:
        print("请求超时（60秒）")
    except Exception as e:
        print(f"发生错误: {str(e)}")


if __name__ == "__main__":
    print("OCR服务测试工具")
    print("=" * 50)

    # 测试健康检查
    test_health()

    # 测试OCR识别（需要提供真实图片URL）
    # test_ocr(TEST_IMAGE_URL)

    print("\n提示: 修改TEST_IMAGE_URL为真实图片URL后，取消注释test_ocr()进行测试")
