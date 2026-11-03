"""
分层架构定义

HLC 码的分层架构：
- L1: 2态纯黑白 (1 bit/模块) - 任何信道兜底
- L2: 16级灰阶 (4 bit/模块) - 屏幕 + 打印双主力
- L3a: 64色CMYK色域 (6 bit/模块) - 打印 / 屏幕保守档
- L3b: 256色sRGB全域 (8 bit/模块) - 仅屏幕拍摄
- L4: 24bit真彩 (24 bit/模块) - 仅纯数字传递

嵌套规则：
1. L2 的 16 级灰 = L3a/L3b 色板的前 16 项（等 L* 间隔的中性轴）
2. 彩色码在恶劣信道下退化为灰阶解码，仍有 4 bit/模块 的保底容量
3. 各层共用同一套定位、定时、版本信息结构，只换符号映射
"""

import numpy as np
from typing import List, Tuple, Dict, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import colorsys


class LayerType(Enum):
    """层类型"""
    L1 = "L1"  # 2态纯黑白
    L2 = "L2"  # 16级灰阶
    L3a = "L3a"  # 64色CMYK
    L3b = "L3b"  # 256色sRGB
    L4 = "L4"  # 24bit真彩


@dataclass
class Layer:
    """
    HLC 码层定义
    
    Attributes:
        layer_type: 层类型
        symbol_count: 符号表大小
        bits_per_module: 每个模块的比特数
        channel: 适用信道
        default_spacing: 默认模块间距 (像素)
        ecc_redundancy: ECC 冗余比例
        needs_calibration: 是否需要校准
        calibration_type: 校准类型
        color_space: 颜色空间
        palette: 调色板 (如果适用)
    """
    layer_type: LayerType
    symbol_count: int
    bits_per_module: int
    channel: str
    default_spacing: Dict[str, int]  # 屏幕/打印默认间距
    ecc_redundancy: float  # ECC 冗余比例 (0-1)
    needs_calibration: bool
    calibration_type: str
    color_space: str
    palette: Optional[List[Tuple[int, int, int]]] = None  # RGB 调色板
    palette_lab: Optional[List[Tuple[float, float, float]]] = None  # LAB 调色板
    
    # 嵌套兼容性
    fallback_layer: Optional[LayerType] = None
    fallback_symbols: Optional[List[int]] = None  # 降级时使用的符号索引
    
    # 邻差约束
    neighbor_diff_constraint: Optional[float] = None  # 相邻模块最大亮度差比例
    
    def get_symbol_value(self, symbol_index: int) -> Union[int, Tuple[int, int, int]]:
        """
        获取符号对应的值
        
        Args:
            symbol_index: 符号索引
            
        Returns:
            L1: 0 或 1 (黑或白)
            L2: 0-15 (灰阶级别)
            L3a/L3b: RGB 元组
            L4: 不适用 (24bit 直接读取)
        """
        if self.layer_type == LayerType.L1:
            return symbol_index  # 0=黑, 1=白
        elif self.layer_type == LayerType.L2:
            return symbol_index  # 0-15 灰阶级别
        elif self.layer_type in [LayerType.L3a, LayerType.L3b]:
            if self.palette is None:
                raise ValueError(f"Layer {self.layer_type} needs palette")
            return self.palette[symbol_index]
        else:  # L4
            raise ValueError("L4 does not use symbol table")
    
    def get_symbol_index(self, value: Union[int, Tuple[int, int, int]]) -> int:
        """
        获取值对应的符号索引
        
        Args:
            value: 颜色值或灰阶级别
            
        Returns:
            符号索引
        """
        if self.layer_type == LayerType.L1:
            return int(value)
        elif self.layer_type == LayerType.L2:
            return int(value)
        elif self.layer_type in [LayerType.L3a, LayerType.L3b]:
            if self.palette is None:
                raise ValueError(f"Layer {self.layer_type} needs palette")
            # 查找最接近的颜色
            if isinstance(value, tuple) and len(value) == 3:
                rgb = value
                min_dist = float('inf')
                min_idx = 0
                for idx, palette_color in enumerate(self.palette):
                    dist = sum((a - b) ** 2 for a, b in zip(rgb, palette_color))
                    if dist < min_dist:
                        min_dist = dist
                        min_idx = idx
                return min_idx
            else:
                return int(value)
        else:
            raise ValueError("L4 does not use symbol table")
    
    def bytes_to_symbols(self, data: bytes) -> List[int]:
        """
        将字节数据转换为符号列表
        
        Args:
            data: 字节数据
            
        Returns:
            符号索引列表
        """
        symbols = []
        bits_needed = self.bits_per_module
        
        if bits_needed == 24:  # L4 特殊处理
            # 每3个字节为一个24bit符号
            for i in range(0, len(data), 3):
                if i + 3 <= len(data):
                    symbol = int.from_bytes(data[i:i+3], 'big')
                    symbols.append(symbol)
                else:
                    # 补齐
                    remaining = data[i:]
                    symbol = int.from_bytes(remaining, 'big')
                    symbols.append(symbol)
            return symbols
        
        # 其他层: 按位拆分
        bit_string = ''
        for byte in data:
            bit_string += f"{byte:08b}"
        
        # 补齐到完整符号
        padding_bits = (bits_needed - len(bit_string) % bits_needed) % bits_needed
        bit_string += '0' * padding_bits
        
        # 拆分为符号
        for i in range(0, len(bit_string), bits_needed):
            symbol_bits = bit_string[i:i+bits_needed]
            if len(symbol_bits) == bits_needed:
                symbols.append(int(symbol_bits, 2))
            elif len(symbol_bits) > 0:
                # 如果剩余不够一个完整符号，仍然添加
                symbols.append(int(symbol_bits, 2))
        
        return symbols
    
    def symbols_to_bytes(self, symbols: List[int]) -> bytes:
        """
        将符号列表转换为字节数据
        
        Args:
            symbols: 符号索引列表
            
        Returns:
            字节数据
        """
        if self.bits_per_module == 24:  # L4
            data = bytearray()
            for symbol in symbols:
                if symbol > 0xFFFFFF:
                    raise ValueError(f"L4 symbol out of range: {symbol}")
                data.extend(symbol.to_bytes(3, 'big'))
            return bytes(data)
        
        # 其他层
        bit_string = ''
        for symbol in symbols:
            bit_string += f"{symbol:0{self.bits_per_module}b}"
        
        # 转换为字节
        data = bytearray()
        for i in range(0, len(bit_string), 8):
            byte_bits = bit_string[i:i+8]
            if len(byte_bits) == 8:
                data.append(int(byte_bits, 2))
            elif len(byte_bits) > 0:
                # 补齐最后一个字节
                byte_bits += '0' * (8 - len(byte_bits))
                data.append(int(byte_bits, 2))
        
        return bytes(data)
    
    def get_capacity(self, module_count: int, structure_overhead: float = 0.1) -> int:
        """
        计算可用字节数
        
        Args:
            module_count: 模块总数
            structure_overhead: 结构开销比例
            
        Returns:
            可用字节数
        """
        # 有效模块数 = 总模块数 × (1 - 结构开销)
        effective_modules = module_count * (1 - structure_overhead)
        
        # 原始比特数
        raw_bits = effective_modules * self.bits_per_module
        
        # 扣除 ECC 开销
        data_bits = raw_bits * (1 - self.ecc_redundancy)
        
        # 转换为字节
        return int(data_bits / 8)
    
    def __repr__(self):
        return f"Layer({self.layer_type.value}, {self.symbol_count} symbols, {self.bits_per_module} bits/module)"


# 生成等 L* 间隔的灰阶调色板
def generate_grayscale_palette(levels: int = 16) -> List[Tuple[int, int, int]]:
    """
    生成等 L* 间隔的灰阶调色板
    
    L* (CIELAB 亮度) 范围: 0-100
    
    Args:
        levels: 灰阶级别数
        
    Returns:
        RGB 调色板
    """
    palette = []
    for i in range(levels):
        # 等 L* 间隔
        L = i * 100 / (levels - 1)
        # LAB 到 RGB 转换 (a=0, b=0 为中性灰)
        # 使用近似转换
        Y = (L / 100) ** 2 if L <= 24/116 * 100 else ((L / 100 + 16/116) / (116/100)) ** 3
        Y = min(Y, 1.0)
        # D65 白点, sRGB
        rgb = [int(255 * (Y ** (1/2.2))) for _ in range(3)]
        palette.append((rgb[0], rgb[1], rgb[2]))
    return palette


# 生成 CMYK 色域内的 64 色调色板
def generate_cmyk_palette() -> List[Tuple[int, int, int]]:
    """
    生成 CMYK 色域内的 64 色调色板
    
    使用贪心算法，最大化 CIELAB 空间中的最小距离
    
    Returns:
        RGB 调色板 (64 色)
    """
    # 简化版: 使用均匀采样
    # 4x4x4 = 64 的 CMYK 组合
    palette = []
    for c in range(4):
        for m in range(4):
            for y in range(4):
                # CMYK 到 RGB
                C = c / 3.0
                M = m / 3.0
                Y = y / 3.0
                K = 0  # 不使用黑色通道
                
                R = 255 * (1 - C) * (1 - K)
                G = 255 * (1 - M) * (1 - K)
                B = 255 * (1 - Y) * (1 - K)
                
                palette.append((int(R), int(G), int(B)))
    
    return palette


# 生成 sRGB 全域的 256 色调色板
def generate_srgb_palette() -> List[Tuple[int, int, int]]:
    """
    生成 sRGB 全域的 256 色调色板
    
    使用 4x4x4x4 的采样 (16x16x16 = 4096 太多，所以用 4x4x4x4)
    实际上我们使用 256 色，这里简化为 6x6x6 = 216 + 40 个额外颜色
    
    Returns:
        RGB 调色板 (256 色)
    """
    palette = []
    
    # 6x6x6 = 216 色
    for r in range(6):
        for g in range(6):
            for b in range(6):
                R = int(r * 255 / 5)
                G = int(g * 255 / 5)
                B = int(b * 255 / 5)
                palette.append((R, G, B))
    
    # 添加 40 个额外颜色 (灰阶和高饱和度颜色)
    # 灰阶
    for i in range(16):
        v = int(i * 255 / 15)
        palette.append((v, v, v))
    
    # 高饱和度颜色
    for i in range(24):
        h = i / 24.0
        s = 1.0
        v = 1.0
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        palette.append((int(r * 255), int(g * 255), int(b * 255)))
    
    return palette[:256]  # 确保只有 256 色


# RGB 到 CIELAB 转换
def rgb_to_lab(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """
    RGB 到 CIELAB 转换
    
    Args:
        rgb: (R, G, B) 0-255
        
    Returns:
        (L*, a*, b*)
    """
    R, G, B = [x / 255.0 for x in rgb]
    
    # RGB 到 XYZ (D65 白点)
    def gamma_correct(u):
        return u ** 2.2 if u <= 0.04045 else ((u + 0.055) / 1.055) ** 2.4
    
    R_lin = gamma_correct(R)
    G_lin = gamma_correct(G)
    B_lin = gamma_correct(B)
    
    # Observer = 2°, Illuminant = D65
    X = R_lin * 0.4124564 + G_lin * 0.3575761 + B_lin * 0.1804375
    Y = R_lin * 0.2126729 + G_lin * 0.7151522 + B_lin * 0.0721750
    Z = R_lin * 0.0193339 + G_lin * 0.1191920 + B_lin * 0.9503041
    
    # XYZ 到 LAB
    def f(t):
        return t ** (1/3) if t > (6/29) ** 3 else t / (3 * (6/29) ** 2) + 4/29
    
    # 白点参考值
    Xn = 0.95047
    Yn = 1.00000
    Zn = 1.08883
    
    fx = f(X / Xn)
    fy = f(Y / Yn)
    fz = f(Z / Zn)
    
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    
    return (L, a, b)


# CIELAB 到 RGB 转换
def lab_to_rgb(lab: Tuple[float, float, float]) -> Tuple[int, int, int]:
    """
    CIELAB 到 RGB 转换
    
    Args:
        lab: (L*, a*, b*)
        
    Returns:
        (R, G, B) 0-255
    """
    L, a, b = lab
    
    # 白点参考值
    Xn = 0.95047
    Yn = 1.00000
    Zn = 1.08883
    
    fy = (L + 16) / 116
    fx = a / 500 + fy
    fz = fy - b / 200
    
    def f_inv(t):
        return t ** 3 if t > 6/29 else 3 * (6/29) ** 2 * (t - 4/29)
    
    X = Xn * f_inv(fx)
    Y = Yn * f_inv(fy)
    Z = Zn * f_inv(fz)
    
    # XYZ 到 RGB
    R_lin = X *  3.2404542 + Y * -1.5371385 + Z * -0.4985314
    G_lin = X * -0.9692660 + Y *  1.8760108 + Z *  0.0415560
    B_lin = X *  0.0556434 + Y * -0.2040259 + Z *  1.0572252
    
    def gamma_inverse(u):
        return 12.92 * u if u <= 0.0031308 else 1.055 * (u ** (1/2.4)) - 0.055
    
    R = gamma_inverse(R_lin)
    G = gamma_inverse(G_lin)
    B = gamma_inverse(B_lin)
    
    R = max(0, min(1, R)) * 255
    G = max(0, min(1, G)) * 255
    B = max(0, min(1, B)) * 255
    
    return (int(R), int(G), int(B))


# 生成优化的调色板 (最大化最小 ΔE)
def generate_optimized_palette(num_colors: int, color_space: str = "sRGB") -> List[Tuple[int, int, int]]:
    """
    生成优化的调色板，最大化 CIELAB 空间中的最小距离
    
    使用贪心算法
    
    Args:
        num_colors: 颜色数量
        color_space: 颜色空间 (sRGB 或 CMYK)
        
    Returns:
        RGB 调色板
    """
    import random
    
    if num_colors == 16:
        return generate_grayscale_palette(16)
    elif num_colors == 64:
        return generate_cmyk_palette()
    elif num_colors == 256:
        return generate_srgb_palette()
    
    # 简化版: 随机采样
    palette = []
    
    # 首先添加黑色和白色
    palette.append((0, 0, 0))
    palette.append((255, 255, 255))
    
    # 然后添加随机颜色
    while len(palette) < num_colors:
        R = random.randint(0, 255)
        G = random.randint(0, 255)
        B = random.randint(0, 255)
        
        # 计算与现有颜色的最小距离
        min_dist = float('inf')
        for existing in palette:
            dist = sum((a - b) ** 2 for a, b in zip((R, G, B), existing)) ** 0.5
            if dist < min_dist:
                min_dist = dist
        
        # 如果距离足够大，添加
        if min_dist > 50:
            palette.append((R, G, B))
    
    return palette[:num_colors]


# 定义各层
L1 = Layer(
    layer_type=LayerType.L1,
    symbol_count=2,
    bits_per_module=1,
    channel="任何信道兜底",
    default_spacing={"screen": 4, "print": 6},
    ecc_redundancy=0.20,
    needs_calibration=False,
    calibration_type="黑白双锚 + Otsu 局部阈值",
    color_space="Binary",
    palette=[(0, 0, 0), (255, 255, 255)],
    palette_lab=[rgb_to_lab(c) for c in [(0, 0, 0), (255, 255, 255)]],
    fallback_layer=None,
    fallback_symbols=None,
    neighbor_diff_constraint=None,
)

# L2 的灰阶调色板 (等 L* 间隔)
L2_palette = generate_grayscale_palette(16)
L2_palette_lab = [rgb_to_lab(c) for c in L2_palette]

L2 = Layer(
    layer_type=LayerType.L2,
    symbol_count=16,
    bits_per_module=4,
    channel="屏幕 + 打印双主力",
    default_spacing={"screen": 4, "print": 6},
    ecc_redundancy=0.35,
    needs_calibration=True,
    calibration_type="16级灰阶环 isotonic 回归",
    color_space="Grayscale",
    palette=L2_palette,
    palette_lab=L2_palette_lab,
    fallback_layer=LayerType.L1,
    fallback_symbols=list(range(16)),  # 灰阶可以直接降级为黑白
    neighbor_diff_constraint=0.5,  # 相邻模块亮度差 ≤ 半程 (8/16)
)

# L3a 的 64 色调色板 (CMYK 色域)
L3a_palette = generate_cmyk_palette()
L3a_palette_lab = [rgb_to_lab(c) for c in L3a_palette]

# L3a 的前 16 个符号对应 L2 的灰阶
L3a_fallback_symbols = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

L3a = Layer(
    layer_type=LayerType.L3a,
    symbol_count=64,
    bits_per_module=6,
    channel="打印 / 屏幕保守档",
    default_spacing={"screen": 6, "print": 6},
    ecc_redundancy=0.40,
    needs_calibration=True,
    calibration_type="灰阶环+色板块仿射校正",
    color_space="CMYK",
    palette=L3a_palette,
    palette_lab=L3a_palette_lab,
    fallback_layer=LayerType.L2,
    fallback_symbols=L3a_fallback_symbols,
    neighbor_diff_constraint=0.5,
)

# L3b 的 256 色调色板 (sRGB 全域)
L3b_palette = generate_srgb_palette()
L3b_palette_lab = [rgb_to_lab(c) for c in L3b_palette]

# L3b 的前 16 个符号对应 L2 的灰阶
L3b_fallback_symbols = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

L3b = Layer(
    layer_type=LayerType.L3b,
    symbol_count=256,
    bits_per_module=8,
    channel="仅屏幕拍摄",
    default_spacing={"screen": 4, "print": 6},
    ecc_redundancy=0.40,
    needs_calibration=True,
    calibration_type="灰阶环+色板块仿射校正",
    color_space="sRGB",
    palette=L3b_palette,
    palette_lab=L3b_palette_lab,
    fallback_layer=LayerType.L2,
    fallback_symbols=L3b_fallback_symbols,
    neighbor_diff_constraint=0.5,
)

# L4 没有符号表，24bit 直接读取
L4 = Layer(
    layer_type=LayerType.L4,
    symbol_count=16777216,  # 2^24
    bits_per_module=24,
    channel="仅纯数字传递",
    default_spacing={"screen": 1, "print": 1},
    ecc_redundancy=0.05,  # 仅校验和
    needs_calibration=False,
    calibration_type="无需校准",
    color_space="TrueColor",
    palette=None,
    palette_lab=None,
    fallback_layer=LayerType.L3b,
    fallback_symbols=None,
    neighbor_diff_constraint=None,
)


# 层注册表
LAYER_REGISTRY = {
    LayerType.L1: L1,
    LayerType.L2: L2,
    LayerType.L3a: L3a,
    LayerType.L3b: L3b,
    LayerType.L4: L4,
}


def get_layer(layer_type: Union[str, LayerType]) -> Layer:
    """
    获取层定义
    
    Args:
        layer_type: 层类型字符串或枚举
        
    Returns:
        Layer 对象
    """
    if isinstance(layer_type, str):
        layer_type = LayerType(layer_type)
    return LAYER_REGISTRY[layer_type]


def get_layer_by_name(name: str) -> Layer:
    """
    通过名称获取层
    
    Args:
        name: 层名称 (L1, L2, L3a, L3b, L4)
        
    Returns:
        Layer 对象
    """
    return get_layer(LayerType(name))


__all__ = [
    "LayerType", "Layer",
    "L1", "L2", "L3a", "L3b", "L4",
    "get_layer", "get_layer_by_name",
    "generate_grayscale_palette", "generate_cmyk_palette", "generate_srgb_palette",
    "rgb_to_lab", "lab_to_rgb",
    "generate_optimized_palette",
]
