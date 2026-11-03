#!/usr/bin/env python3
"""
HLC 码基本编码示例

演示如何使用 HLC 编码器将数据编码为二维图形码
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hlc import HLCEncoder, HLCEncoderConfig, LayerType
from hlc.layers import get_layer
from hlc.utils import calculate_capacity


def demo_basic_encoding():
    """基本编码演示"""
    print("=" * 60)
    print("HLC 码基本编码演示")
    print("=" * 60)
    
    # 要编码的数据
    data = b"Hello, HLC Code! This is a test message."
    print(f"\n原始数据: {data}")
    print(f"数据大小: {len(data)} 字节")
    
    # 创建编码器配置
    config = HLCEncoderConfig(
        layer_type=LayerType.L2,  # 使用 L2 层 (16 级灰阶)
        width=1024,
        height=1024,
        module_spacing=8,  # 模块间距 8px
        aesthetic_mode=False,
        debug=True,
    )
    
    # 创建编码器
    encoder = HLCEncoder(config)
    
    # 获取编码器信息
    info = encoder.get_info()
    print("\n编码器信息:")
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # 计算容量
    capacity = calculate_capacity(
        width=1024,
        height=1024,
        module_spacing=8,
        layer_type="L2",
    )
    print(f"\n计算容量: {capacity} 字节")
    
    # 编码数据
    print("\n正在编码...")
    image = encoder.encode(data, output_path="hlc_code_L2.png")
    print("编码完成!")
    print(f"图像保存为: hlc_code_L2.png")
    
    return image


def demo_layer_comparison():
    """不同层的比较演示"""
    print("\n" + "=" * 60)
    print("不同层比较演示")
    print("=" * 60)
    
    data = b"HLC Layer Comparison Test"
    
    layers = [LayerType.L1, LayerType.L2, LayerType.L3b]
    
    for layer_type in layers:
        print(f"\n--- {layer_type.value} 层 ---")
        
        layer = get_layer(layer_type)
        print(f"符号表大小: {layer.symbol_count}")
        print(f"比特/模块: {layer.bits_per_module}")
        print(f"ECC 冗余: {layer.ecc_redundancy * 100}%")
        
        # 计算容量
        capacity = calculate_capacity(
            width=1024,
            height=1024,
            module_spacing=4,
            layer_type=layer_type.value,
        )
        print(f"容量 (1024x1024, 4px 间距): {capacity} 字节")
        
        # 编码
        config = HLCEncoderConfig(
            layer_type=layer_type,
            width=512,
            height=512,
            module_spacing=4,
            aesthetic_mode=False,
        )
        
        encoder = HLCEncoder(config)
        output_path = f"hlc_code_{layer_type.value}.png"
        
        try:
            image = encoder.encode(data, output_path=output_path)
            print(f"编码成功! 图像保存为: {output_path}")
        except ValueError as e:
            print(f"编码失败: {e}")


def demo_aesthetic_mode():
    """美学模式演示"""
    print("\n" + "=" * 60)
    print("美学模式演示")
    print("=" * 60)
    
    # 小数据量
    small_data = b"https://example.com"
    print(f"\n小数据量: {small_data} ({len(small_data)} 字节)")
    
    config = HLCEncoderConfig(
        layer_type=LayerType.L3b,
        width=1024,
        height=1024,
        aesthetic_mode=True,
        max_module_spacing=32,
        harmony_palette=True,
    )
    
    encoder = HLCEncoder(config)
    image = encoder.encode(small_data, output_path="hlc_code_aesthetic.png")
    print("美学模式编码完成!")
    print(f"图像保存为: hlc_code_aesthetic.png")
    
    info = encoder.get_info()
    print(f"最终模块间距: {info['module_spacing']}px")


def demo_capacity_table():
    """容量表演示"""
    print("\n" + "=" * 60)
    print("容量表 (屏幕信道)")
    print("=" * 60)
    
    sizes = [256, 512, 1024]
    spacings = [2, 4, 8]
    layers = ["L1", "L2", "L3b"]
    
    print("\n{:<10} {:<10} {:<10} {:<15} {:<15} {:<15}".format(
        "图像", "间距", "模块数", "L1 (黑白)", "L2 (灰阶)", "L3b (256色)"
    ))
    print("-" * 70)
    
    for size in sizes:
        for spacing in spacings:
            module_count = (size * size * 1.1547) / (spacing ** 2)
            module_count = int(module_count)
            
            capacities = {}
            for layer in layers:
                cap = calculate_capacity(size, size, spacing, layer)
                capacities[layer] = cap
            
            print("{:>6}px × {:>6}px {:>8} {:>12} {:>12} {:>12}".format(
                size, spacing, module_count,
                f"{capacities['L1']:.1f} KiB" if capacities['L1'] >= 1024 else f"{capacities['L1']} B",
                f"{capacities['L2']:.1f} KiB" if capacities['L2'] >= 1024 else f"{capacities['L2']} B",
                f"{capacities['L3b']:.1f} KiB" if capacities['L3b'] >= 1024 else f"{capacities['L3b']} B",
            ))


if __name__ == "__main__":
    print("HLC 码编码示例\n")
    
    # 基本编码演示
    demo_basic_encoding()
    
    # 不同层比较
    demo_layer_comparison()
    
    # 美学模式
    demo_aesthetic_mode()
    
    # 容量表
    demo_capacity_table()
    
    print("\n" + "=" * 60)
    print("所有演示完成!")
    print("生成的图像文件:")
    print("  - hlc_code_L2.png")
    print("  - hlc_code_L1.png")
    print("  - hlc_code_L2.png")
    print("  - hlc_code_L3b.png")
    print("  - hlc_code_aesthetic.png")
    print("=" * 60)
