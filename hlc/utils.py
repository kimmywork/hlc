"""
工具函数模块

包含各种辅助函数
"""

import math
import numpy as np
from typing import List, Tuple, Dict, Optional, Union
import colorsys


def generate_palette(num_colors: int, color_space: str = "sRGB", 
                     harmony: bool = False, hue_range: float = 60.0) -> List[Tuple[int, int, int]]:
    """
    生成调色板
    
    Args:
        num_colors: 颜色数量
        color_space: 颜色空间 (sRGB, CMYK, Grayscale)
        harmony: 是否使用和谐色板 (限制色相范围)
        hue_range: 色相范围 (度) 0-360
        
    Returns:
        RGB 调色板
    """
    if color_space == "Grayscale":
        # 等 L* 间隔的灰阶
        return _generate_grayscale_palette(num_colors)
    
    elif color_space == "CMYK":
        # CMYK 色域内的调色板
        return _generate_cmyk_palette(num_colors)
    
    else:  # sRGB
        if harmony:
            return _generate_harmony_palette(num_colors, hue_range)
        else:
            return _generate_srgb_palette(num_colors)


def _generate_grayscale_palette(num_colors: int) -> List[Tuple[int, int, int]]:
    """生成等 L* 间隔的灰阶调色板"""
    palette = []
    for i in range(num_colors):
        # 等 L* 间隔
        L = i * 100 / (num_colors - 1)
        # LAB 到 RGB 转换 (a=0, b=0 为中性灰)
        Y = (L / 100) ** 2 if L <= 24/116 * 100 else ((L / 100 + 16/116) / (116/100)) ** 3
        Y = min(Y, 1.0)
        # D65 白点, sRGB
        rgb = [int(255 * (Y ** (1/2.2))) for _ in range(3)]
        palette.append((rgb[0], rgb[1], rgb[2]))
    return palette


def _generate_cmyk_palette(num_colors: int) -> List[Tuple[int, int, int]]:
    """生成 CMYK 色域内的调色板"""
    # 使用均匀采样
    # 计算每个通道的分割数
    side = int(round(num_colors ** (1/3)))
    side = max(2, min(side, 8))
    
    # 如果不是立方数，调整
    actual_colors = side ** 3
    
    palette = []
    count = 0
    
    for c in range(side):
        for m in range(side):
            for y in range(side):
                if count >= num_colors:
                    break
                
                # CMYK 到 RGB
                C = c / (side - 1)
                M = m / (side - 1)
                Y = y / (side - 1)
                K = 0  # 不使用黑色通道
                
                R = 255 * (1 - C) * (1 - K)
                G = 255 * (1 - M) * (1 - K)
                B = 255 * (1 - Y) * (1 - K)
                
                palette.append((int(R), int(G), int(B)))
                count += 1
        
        if count >= num_colors:
            break
    
    # 如果不够，添加灰阶
    while len(palette) < num_colors:
        v = int(len(palette) * 255 / num_colors)
        palette.append((v, v, v))
    
    return palette[:num_colors]


def _generate_srgb_palette(num_colors: int) -> List[Tuple[int, int, int]]:
    """生成 sRGB 全域的调色板"""
    # 使用 6x6x6 = 216 色 + 补齐
    palette = []
    
    side = 6
    for r in range(side):
        for g in range(side):
            for b in range(side):
                R = int(r * 255 / (side - 1))
                G = int(g * 255 / (side - 1))
                B = int(b * 255 / (side - 1))
                palette.append((R, G, B))
    
    # 如果不够，添加灰阶和高饱和度颜色
    while len(palette) < num_colors:
        i = len(palette) - 216
        if i < 16:
            # 灰阶
            v = int(i * 255 / 15)
            palette.append((v, v, v))
        else:
            # 高饱和度颜色
            h = (i - 16) / (num_colors - 216 - 16) * 360
            s = 1.0
            v = 1.0
            r, g, b = colorsys.hsv_to_rgb(h / 360, s, v)
            palette.append((int(r * 255), int(g * 255), int(b * 255)))
    
    return palette[:num_colors]


def _generate_harmony_palette(num_colors: int, hue_range: float = 60.0) -> List[Tuple[int, int, int]]:
    """
    生成和谐色板
    
    限制色相范围，降低饱和度档位
    """
    palette = []
    
    # 中心色相
    center_hue = 0.0  # 可以随机选择
    
    for i in range(num_colors):
        # 计算色相 (在 hue_range 范围内)
        hue = center_hue + (i / num_colors - 0.5) * (hue_range / 360)
        hue = hue % 1.0
        
        # 计算饱和度 (降低饱和度)
        saturation = 0.5 + 0.5 * (i % 2)  # 交替使用 0.5 和 1.0
        
        # 计算明度
        value = 0.5 + 0.5 * ((i // 2) % 2)  # 交替使用 0.5 和 1.0
        
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        palette.append((int(r * 255), int(g * 255), int(b * 255)))
    
    return palette


def get_module_count(width: int, height: int, module_spacing: float) -> int:
    """
    计算给定尺寸和间距下的模块数
    
    Args:
        width: 图像宽度
        height: 图像高度
        module_spacing: 模块间距 p
        
    Returns:
        模块数
    """
    DENSITY_FACTOR = 1.154700538  # 2/sqrt(3)
    area = width * height
    return int(DENSITY_FACTOR * area / (module_spacing ** 2))


def calculate_capacity(width: int, height: int, module_spacing: float, 
                      layer_type: str = "L2", structure_overhead: float = 0.1) -> int:
    """
    计算容量
    
    Args:
        width: 图像宽度
        height: 图像高度
        module_spacing: 模块间距
        layer_type: 层类型 (L1, L2, L3a, L3b, L4)
        structure_overhead: 结构开销比例
        
    Returns:
        可用字节数
    """
    from .layers import get_layer
    
    layer = get_layer(layer_type)
    module_count = get_module_count(width, height, module_spacing)
    
    # 有效模块数 = 总模块数 × (1 - 结构开销)
    effective_modules = module_count * (1 - structure_overhead)
    
    # 原始比特数
    raw_bits = effective_modules * layer.bits_per_module
    
    # 扣除 ECC 开销
    data_bits = raw_bits * (1 - layer.ecc_redundancy)
    
    # 转换为字节
    return int(data_bits / 8)


def select_aesthetic_spacing(data_size: int, width: int = 1024, height: int = 1024,
                            min_occupancy: float = 0.6) -> int:
    """
    美学模式: 自动选择最大的模块间距
    
    从 {32, 24, 16, 12, 8, 6, 4, 2}px 中选最大间距，
    使该档容量 ≥ 有效载荷，且数据区占用 ≥ 60%
    
    Args:
        data_size: 数据大小 (字节)
        width: 图像宽度
        height: 图像高度
        min_occupancy: 最小占用率
        
    Returns:
        模块间距 (像素)
    """
    possible_spacings = [32, 24, 16, 12, 8, 6, 4, 2]
    
    for spacing in sorted(possible_spacings, reverse=True):
        capacity = calculate_capacity(width, height, spacing, "L2")
        
        # 计算数据区占用率
        module_count = get_module_count(width, height, spacing)
        data_modules = data_size * 8 / 2  # L2: 2 bits per module (简化)
        data_ratio = data_modules / module_count if module_count > 0 else 0
        
        if capacity >= data_size and data_ratio >= min_occupancy:
            return spacing
    
    # 如果没有找到合适的间距，使用最小的
    return possible_spacings[-1]


def create_hexagon_path(center_x: float, center_y: float, size: float, 
                        orientation: str = "flat_top") -> List[Tuple[float, float]]:
    """
    创建六边形路径
    
    Args:
        center_x, center_y: 中心坐标
        size: 边长
        orientation: 方向 (flat_top 或 pointy_top)
        
    Returns:
        6 个顶点的坐标列表 (顺时针)
    """
    if orientation == "flat_top":
        # 平顶六边形
        vertices = [
            (center_x + size, center_y),  # 右
            (center_x + size/2, center_y + size * math.sqrt(3)/2),  # 右上
            (center_x - size/2, center_y + size * math.sqrt(3)/2),  # 左上
            (center_x - size, center_y),  # 左
            (center_x - size/2, center_y - size * math.sqrt(3)/2),  # 左下
            (center_x + size/2, center_y - size * math.sqrt(3)/2),  # 右下
        ]
    else:  # pointy_top
        # 尖顶六边形
        vertices = [
            (center_x + size * math.sqrt(3)/2, center_y + size/2),  # 右上
            (center_x + size * math.sqrt(3)/2, center_y - size/2),  # 右下
            (center_x, center_y - size),  # 下
            (center_x - size * math.sqrt(3)/2, center_y - size/2),  # 左下
            (center_x - size * math.sqrt(3)/2, center_y + size/2),  # 左上
            (center_x, center_y + size),  # 上
        ]
    
    return vertices


def distance_p2p(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """计算两点之间的距离"""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def hexagon_area(size: float) -> float:
    """计算六边形面积"""
    return (3 * math.sqrt(3) / 2) * size ** 2


def hexagon_perimeter(size: float) -> float:
    """计算六边形周长"""
    return 6 * size


__all__ = [
    "generate_palette",
    "get_module_count",
    "calculate_capacity",
    "select_aesthetic_spacing",
    "create_hexagon_path",
    "distance_p2p",
    "hexagon_area",
    "hexagon_perimeter",
]
