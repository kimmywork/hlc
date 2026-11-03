#!/usr/bin/env python3
"""
HLC 码解码演示

演示如何使用 HLC 解码器从图像中解码数据
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hlc import HLCDecoder, HLCDecoderConfig
from hlc.encoder import HLCEncoder, HLCEncoderConfig, encode_hlc
from hlc.layers import LayerType


def demo_encode_decode():
    """编码和解码完整演示"""
    print("=" * 60)
    print("HLC 码编码-解码演示")
    print("=" * 60)
    
    # 要编码的数据
    original_data = b"Hello, HLC Code! This is a test message for encoding and decoding."
    print(f"\n原始数据: {original_data}")
    print(f"数据大小: {len(original_data)} 字节")
    
    # 编码
    print("\n--- 编码 ---")
    config = HLCEncoderConfig(
        layer_type=LayerType.L2,
        width=1024,
        height=1024,
        module_spacing=4,
        aesthetic_mode=False,
        ecc_enabled=True,
        whitening_enabled=True,
    )
    
    encoder = HLCEncoder(config)
    image_path = "test_hlc_code.png"
    image = encoder.encode(original_data, output_path=image_path)
    print(f"编码完成! 图像保存为: {image_path}")
    
    # 解码
    print("\n--- 解码 ---")
    decoder_config = HLCDecoderConfig(
        layer_type=LayerType.L2,
        denoise=True,
        enhance_contrast=True,
        debug=True,
    )
    
    decoder = HLCDecoder(decoder_config)
    decoded_data, success = decoder.decode(image_path)
    
    if success:
        print(f"解码成功!")
        print(f"解码数据: {decoded_data}")
        print(f"数据大小: {len(decoded_data)} 字节")
        
        # 比较原始数据和解码数据
        if decoded_data == original_data:
            print("\n✓ 数据验证通过! 原始数据和解码数据完全一致。")
        else:
            print("\n✗ 数据验证失败! 原始数据和解码数据不一致。")
            print(f"差异: {len(original_data) - len(decoded_data)} 字节")
    else:
        print("解码失败!")


def demo_layer_fallback():
    """层降级演示"""
    print("\n" + "=" * 60)
    print("层降级演示")
    print("=" * 60)
    
    # 使用 L3b 编码
    original_data = b"Layer fallback test message"
    print(f"\n原始数据: {original_data}")
    
    config = HLCEncoderConfig(
        layer_type=LayerType.L3b,
        width=512,
        height=512,
        module_spacing=4,
    )
    
    encoder = HLCEncoder(config)
    image_path = "test_hlc_l3b.png"
    image = encoder.encode(original_data, output_path=image_path)
    print(f"使用 L3b 编码完成! 图像保存为: {image_path}")
    
    # 尝试用 L2 解码 (降级)
    print("\n尝试用 L2 解码 (降级)...")
    decoder_config = HLCDecoderConfig(
        layer_type=LayerType.L2,
        debug=True,
    )
    
    decoder = HLCDecoder(decoder_config)
    decoded_data, success = decoder.decode(image_path)
    
    if success:
        print("降级解码成功!")
        print(f"解码数据: {decoded_data}")
    else:
        print("降级解码失败!")


def demo_multi_layer_encoding():
    """多层编码演示"""
    print("\n" + "=" * 60)
    print("多层编码演示")
    print("=" * 60)
    
    messages = {
        LayerType.L1: b"L1: Binary message",
        LayerType.L2: b"L2: Grayscale message with more capacity",
        LayerType.L3b: b"L3b: Color message with even more capacity!",
    }
    
    for layer_type, message in messages.items():
        print(f"\n--- {layer_type.value} 层 ---")
        print(f"消息: {message}")
        
        config = HLCEncoderConfig(
            layer_type=layer_type,
            width=512,
            height=512,
            module_spacing=4,
        )
        
        encoder = HLCEncoder(config)
        image_path = f"multi_layer_{layer_type.value}.png"
        
        try:
            image = encoder.encode(message, output_path=image_path)
            print(f"编码成功! 图像保存为: {image_path}")
        except ValueError as e:
            print(f"编码失败: {e}")


def demo_with_corruption():
    """带干扰的解码演示"""
    print("\n" + "=" * 60)
    print("带干扰的解码演示")
    print("=" * 60)
    
    import cv2
    import numpy as np
    
    # 原始数据
    original_data = b"Test message with ECC protection"
    print(f"\n原始数据: {original_data}")
    
    # 编码
    config = HLCEncoderConfig(
        layer_type=LayerType.L2,
        width=512,
        height=512,
        module_spacing=4,
        ecc_enabled=True,
        redundancy_ratio=0.35,
    )
    
    encoder = HLCEncoder(config)
    image_path = "test_with_ecc.png"
    image = encoder.encode(original_data, output_path=image_path)
    print(f"编码完成! 图像保存为: {image_path}")
    
    # 添加干扰 (模拟噪声)
    print("\n添加干扰...")
    corrupted_path = "test_corrupted.png"
    
    # 加载图像
    img = cv2.imread(image_path)
    
    # 添加高斯噪声
    noise = np.random.normal(0, 25, img.shape).astype(np.int16)
    corrupted = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # 添加一些随机像素错误
    for _ in range(100):
        x = np.random.randint(0, corrupted.shape[1])
        y = np.random.randint(0, corrupted.shape[0])
        corrupted[y, x] = [np.random.randint(0, 256) for _ in range(3)]
    
    cv2.imwrite(corrupted_path, corrupted)
    print(f"干扰图像保存为: {corrupted_path}")
    
    # 尝试解码干扰图像
    print("\n尝试解码干扰图像...")
    decoder_config = HLCDecoderConfig(
        layer_type=LayerType.L2,
        denoise=True,
        enhance_contrast=True,
        debug=True,
    )
    
    decoder = HLCDecoder(decoder_config)
    decoded_data, success = decoder.decode(corrupted_path)
    
    if success:
        print("解码成功!")
        print(f"解码数据: {decoded_data}")
        
        if decoded_data == original_data:
            print("\n✓ ECC 纠错成功! 数据完全恢复。")
        else:
            print("\n✗ 部分数据丢失，但 ECC 纠错了部分错误。")
    else:
        print("解码失败! 干扰太严重。")


if __name__ == "__main__":
    print("HLC 码解码演示\n")
    
    # 编码-解码演示
    demo_encode_decode()
    
    # 层降级演示
    demo_layer_fallback()
    
    # 多层编码
    demo_multi_layer_encoding()
    
    # 带干扰的解码
    demo_with_corruption()
    
    print("\n" + "=" * 60)
    print("所有演示完成!")
    print("=" * 60)
