"""
校准体系模块

包括：
- 校准枢纽 (灰阶环 + 色板校准块 + 黑白端点)
- 定位锚点 ×3 (同心圆环，不对称排布)
- 顶部定时带
- 底部格式信息带 ×2 镜像
- 静区
"""

import math
import numpy as np
from typing import List, Tuple, Dict, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from .hexagonal import HexGrid, AxialCoord
from .layers import Layer, LayerType, L2, rgb_to_lab


class AnchorType(Enum):
    """锚点类型"""
    PRIMARY = "primary"  # 主锚点 (左上)
    SECONDARY = "secondary"  # 次锚点 (右上)
    TERTIARY = "tertiary"  # 三级锚点 (左下)


@dataclass
class Anchor:
    """
    定位锚点
    
    使用同心圆环设计，区别于六边形模块
    用于单应变换 + 方向判别
    """
    anchor_type: AnchorType
    center: Tuple[float, float]  # 像素坐标
    radius: float  # 最外层圆环半径 (像素)
    ring_count: int = 3  # 圆环数量
    ring_width: float = 2.0  # 圆环宽度 (像素)
    background_color: Tuple[int, int, int] = (255, 255, 255)  # 背景色
    foreground_color: Tuple[int, int, int] = (0, 0, 0)  # 前景色 (圆环)
    
    def __post_init__(self):
        # 确保圆环数量至少为 2
        self.ring_count = max(2, self.ring_count)
    
    def get_ring_radii(self) -> List[float]:
        """获取各个圆环的半径"""
        # 从内到外
        step = self.radius / self.ring_count
        return [step * (i + 0.5) for i in range(self.ring_count)]
    
    def contains(self, x: float, y: float) -> bool:
        """检查点是否在锚点内"""
        dx = x - self.center[0]
        dy = y - self.center[1]
        distance = math.sqrt(dx**2 + dy**2)
        return distance <= self.radius
    
    def get_ring_index(self, x: float, y: float) -> Optional[int]:
        """
        获取点所在的圆环索引
        
        Args:
            x, y: 点坐标
            
        Returns:
            圆环索引 (0 = 最内层) 或 None (不在任何圆环内)
        """
        dx = x - self.center[0]
        dy = y - self.center[1]
        distance = math.sqrt(dx**2 + dy**2)
        
        radii = self.get_ring_radii()
        for i, r in enumerate(radii):
            if abs(distance - r) <= self.ring_width / 2:
                return i
        
        return None
    
    def draw(self, image: np.ndarray) -> None:
        """
        在图像上绘制锚点
        
        Args:
            image: numpy 数组 (H, W, 3) RGB
        """
        h, w = image.shape[:2]
        
        radii = self.get_ring_radii()
        
        for radius in radii:
            # 绘制圆环
            for y in range(h):
                for x in range(w):
                    dx = x - self.center[0]
                    dy = y - self.center[1]
                    distance = math.sqrt(dx**2 + dy**2)
                    
                    if abs(distance - radius) <= self.ring_width / 2:
                        image[y, x] = self.foreground_color
                    elif distance <= self.radius:
                        image[y, x] = self.background_color
    
    def get_pattern(self) -> List[List[bool]]:
        """
        获取锚点的二值模式
        
        Returns:
            二维布尔数组，True 表示前景
        """
        size = int(self.radius * 2) + 1
        pattern = [[False for _ in range(size)] for _ in range(size)]
        
        center_x = center_y = size // 2
        radii = self.get_ring_radii()
        
        for y in range(size):
            for x in range(size):
                dx = x - center_x
                dy = y - center_y
                distance = math.sqrt(dx**2 + dy**2)
                
                for radius in radii:
                    if abs(distance - radius) <= self.ring_width / 2:
                        pattern[y][x] = True
                        break
        
        return pattern


@dataclass
class CalibrationHub:
    """
    中央校准枢纽
    
    包括：
    - 16 级灰阶环
    - 黑白端点块 ×4
    - 色板校准块 (L3 专用)
    """
    center: Tuple[float, float]  # 像素坐标
    inner_radius: float  # 内半径 (像素)
    outer_radius: float  # 外半径 (像素)
    layer: Layer  # 当前层
    
    # 灰阶环参数
    grayscale_ring_width: float = 20.0  # 灰阶环宽度
    grayscale_ring_count: int = 16  # 灰阶级数
    
    # 端点块参数
    endpoint_block_size: float = 10.0  # 端点块尺寸
    endpoint_positions: List[Tuple[float, float]] = field(default_factory=lambda: [
        (0, 1), (1, 0), (0, -1), (-1, 0)  # 上、右、下、左
    ])
    
    # 色板块参数 (L3 专用)
    palette_block_size: float = 5.0
    palette_blocks_per_row: int = 8
    
    def __post_init__(self):
        # 确保灰阶级数与层匹配
        if self.layer.layer_type == LayerType.L2:
            self.grayscale_ring_count = 16
        elif self.layer.layer_type in [LayerType.L3a, LayerType.L3b]:
            self.grayscale_ring_count = 16  # L3 仍然使用 16 级灰阶环
    
    def get_grayscale_ring_colors(self) -> List[Tuple[int, int, int]]:
        """获取灰阶环的颜色"""
        if self.layer.layer_type == LayerType.L1:
            # L1 只有黑白
            return [(0, 0, 0), (255, 255, 255)] * 8
        else:
            # 使用 L2 的灰阶调色板
            return L2.palette
    
    def get_grayscale_ring_position(self, index: int) -> Tuple[float, float, float, float]:
        """
        获取灰阶块的位置和尺寸
        
        Args:
            index: 灰阶级别索引 (0-15)
            
        Returns:
            (x, y, width, height)
        """
        # 灰阶环在内半径和外半径之间
        mid_radius = (self.inner_radius + self.outer_radius) / 2
        
        # 角度分布
        angle = 2 * math.pi * index / self.grayscale_ring_count
        
        # 位置
        x = self.center[0] + mid_radius * math.cos(angle)
        y = self.center[1] + mid_radius * math.sin(angle)
        
        # 尺寸
        block_width = self.grayscale_ring_width / self.grayscale_ring_count
        
        return (x, y, block_width, block_width)
    
    def get_endpoint_position(self, index: int) -> Tuple[float, float, float, float]:
        """
        获取端点块的位置和尺寸
        
        Args:
            index: 端点索引 (0-3)
            
        Returns:
            (x, y, width, height)
        """
        if index >= len(self.endpoint_positions):
            raise IndexError(f"Endpoint index {index} out of range")
        
        dx, dy = self.endpoint_positions[index]
        
        # 计算绝对位置
        x = self.center[0] + dx * (self.inner_radius + self.endpoint_block_size)
        y = self.center[1] + dy * (self.inner_radius + self.endpoint_block_size)
        
        return (x, y, self.endpoint_block_size, self.endpoint_block_size)
    
    def get_palette_block_position(self, palette_index: int) -> Tuple[float, float, float, float]:
        """
        获取色板块的位置和尺寸 (L3 专用)
        
        Args:
            palette_index: 调色板索引
            
        Returns:
            (x, y, width, height)
        """
        if self.layer.layer_type not in [LayerType.L3a, LayerType.L3b]:
            raise ValueError("Palette blocks are only for L3 layers")
        
        row = palette_index // self.palette_blocks_per_row
        col = palette_index % self.palette_blocks_per_row
        
        # 位置相对于中心
        start_x = self.center[0] - (self.palette_blocks_per_row * self.palette_block_size) / 2
        start_y = self.center[1] + self.outer_radius + 20  # 在灰阶环外
        
        x = start_x + col * self.palette_block_size
        y = start_y + row * self.palette_block_size
        
        return (x, y, self.palette_block_size, self.palette_block_size)
    
    def draw(self, image: np.ndarray) -> None:
        """
        在图像上绘制校准枢纽
        
        Args:
            image: numpy 数组 (H, W, 3) RGB
        """
        h, w = image.shape[:2]
        
        # 绘制灰阶环
        self._draw_grayscale_ring(image)
        
        # 绘制端点块
        self._draw_endpoint_blocks(image)
        
        # 绘制色板块 (L3 专用)
        if self.layer.layer_type in [LayerType.L3a, LayerType.L3b]:
            self._draw_palette_blocks(image)
    
    def _draw_grayscale_ring(self, image: np.ndarray) -> None:
        """绘制灰阶环"""
        colors = self.get_grayscale_ring_colors()
        
        for index, color in enumerate(colors):
            x, y, width, height = self.get_grayscale_ring_position(index)
            
            # 绘制矩形块
            x_int = int(x - width / 2)
            y_int = int(y - height / 2)
            w_int = int(width)
            h_int = int(height)
            
            # 确保在图像范围内
            x_int = max(0, min(x_int, image.shape[1] - 1))
            y_int = max(0, min(y_int, image.shape[0] - 1))
            w_int = min(w_int, image.shape[1] - x_int)
            h_int = min(h_int, image.shape[0] - y_int)
            
            if w_int > 0 and h_int > 0:
                image[y_int:y_int+h_int, x_int:x_int+w_int] = color
    
    def _draw_endpoint_blocks(self, image: np.ndarray) -> None:
        """绘制端点块"""
        # 黑白交替
        endpoint_colors = [(0, 0, 0), (255, 255, 255)] * 2
        
        for index in range(4):
            x, y, width, height = self.get_endpoint_position(index)
            color = endpoint_colors[index]
            
            x_int = int(x - width / 2)
            y_int = int(y - height / 2)
            w_int = int(width)
            h_int = int(height)
            
            x_int = max(0, min(x_int, image.shape[1] - 1))
            y_int = max(0, min(y_int, image.shape[0] - 1))
            w_int = min(w_int, image.shape[1] - x_int)
            h_int = min(h_int, image.shape[0] - y_int)
            
            if w_int > 0 and h_int > 0:
                image[y_int:y_int+h_int, x_int:x_int+w_int] = color
    
    def _draw_palette_blocks(self, image: np.ndarray) -> None:
        """绘制色板块"""
        if self.layer.palette is None:
            return
        
        for palette_index, color in enumerate(self.layer.palette):
            x, y, width, height = self.get_palette_block_position(palette_index)
            
            x_int = int(x)
            y_int = int(y)
            w_int = int(width)
            h_int = int(height)
            
            x_int = max(0, min(x_int, image.shape[1] - 1))
            y_int = max(0, min(y_int, image.shape[0] - 1))
            w_int = min(w_int, image.shape[1] - x_int)
            h_int = min(h_int, image.shape[0] - y_int)
            
            if w_int > 0 and h_int > 0:
                image[y_int:y_int+h_int, x_int:x_int+w_int] = color


@dataclass
class TimingPattern:
    """
    顶部定时带
    
    黑/白交替的已知序列，用于网格节距估计、采样锁相
    """
    start: Tuple[float, float]  # 起点坐标
    end: Tuple[float, float]  # 终点坐标
    width: float  # 宽度
    module_count: int  # 模块数量
    pattern: List[bool] = field(default_factory=lambda: [True, False] * 20)  # 黑白交替
    
    def draw(self, image: np.ndarray) -> None:
        """在图像上绘制定时带"""
        # 计算方向向量
        dx = self.end[0] - self.start[0]
        dy = self.end[1] - self.start[1]
        length = math.sqrt(dx**2 + dy**2)
        
        if length == 0:
            return
        
        # 单位方向向量
        unit_dx = dx / length
        unit_dy = dy / length
        
        # 每个模块的长度
        module_length = length / self.module_count
        
        # 绘制每个模块
        for i in range(self.module_count):
            module_start_x = self.start[0] + i * module_length * unit_dx
            module_start_y = self.start[1] + i * module_length * unit_dy
            
            module_end_x = module_start_x + module_length * unit_dx
            module_end_y = module_start_y + module_length * unit_dy
            
            # 获取颜色
            color = (0, 0, 0) if self.pattern[i % len(self.pattern)] else (255, 255, 255)
            
            # 绘制矩形 (垂直于定时带方向)
            self._draw_perpendicular_rect(
                image, 
                module_start_x, module_start_y, 
                module_end_x, module_end_y,
                self.width, color
            )
    
    def _draw_perpendicular_rect(self, image: np.ndarray, 
                                  x1: float, y1: float, x2: float, y2: float,
                                  width: float, color: Tuple[int, int, int]) -> None:
        """绘制垂直于线段的矩形"""
        # 计算垂直方向
        dx = x2 - x1
        dy = y2 - y1
        
        # 垂直向量 (旋转 90 度)
        perp_dx = -dy
        perp_dy = dx
        
        # 归一化
        perp_length = math.sqrt(perp_dx**2 + perp_dy**2)
        if perp_length == 0:
            return
        
        perp_dx /= perp_length
        perp_dy /= perp_length
        
        # 四个顶点
        half_width = width / 2
        
        points = [
            (x1 + perp_dx * half_width, y1 + perp_dy * half_width),
            (x1 - perp_dx * half_width, y1 - perp_dy * half_width),
            (x2 - perp_dx * half_width, y2 - perp_dy * half_width),
            (x2 + perp_dx * half_width, y2 + perp_dy * half_width),
        ]
        
        # 使用多边形填充
        self._fill_polygon(image, points, color)
    
    def _fill_polygon(self, image: np.ndarray, points: List[Tuple[float, float]], 
                      color: Tuple[int, int, int]) -> None:
        """填充多边形"""
        # 简化: 使用矩形近似
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        min_x = max(0, int(min_x))
        max_x = min(image.shape[1], int(max_x) + 1)
        min_y = max(0, int(min_y))
        max_y = min(image.shape[0], int(max_y) + 1)
        
        # 使用点在多边形内算法
        def point_in_polygon(x: float, y: float, poly: List[Tuple[float, float]]) -> bool:
            n = len(poly)
            inside = False
            p1x, p1y = poly[0]
            for i in range(n + 1):
                p2x, p2y = poly[i % n]
                if y > min(p1y, p2y):
                    if y <= max(p1y, p2y):
                        if x <= max(p1x, p2x):
                            if p1y != p2y:
                                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or x <= xinters:
                                inside = not inside
                p1x, p1y = p2x, p2y
            return inside
        
        for y in range(min_y, max_y):
            for x in range(min_x, max_x):
                if point_in_polygon(x, y, points):
                    image[y, x] = color


@dataclass
class FormatInfo:
    """
    底部格式信息带
    
    包含：
    - 版本号
    - 层号
    - ECC 级
    - 色板 ID (L3 专用)
    - 白化种子
    
    使用 BCH 保护，两份镜像投票
    """
    version: int = 1
    layer_type: LayerType = LayerType.L2
    ecc_level: str = "M"  # L, M, Q, H
    palette_id: Optional[int] = None  # L3 专用
    whitening_seed: int = 0
    
    # BCH 编码参数
    bch_bits: int = 15  # BCH(15, 5, 5) 可以纠错 5 位
    
    def encode(self) -> bytes:
        """
        编码格式信息
        
        Returns:
            编码后的字节
        """
        # 版本号: 4 位
        version_bits = f"{self.version:04b}"
        
        # 层号: 3 位
        layer_bits = f"{self.layer_type.value[-1]:03b}"  # L1=001, L2=010, L3a=011, L3b=100, L4=101
        
        # ECC 级: 2 位
        ecc_bits = {"L": "00", "M": "01", "Q": "10", "H": "11"}.get(self.ecc_level, "01")
        
        # 色板 ID: 6 位 (L3 专用)
        if self.palette_id is not None:
            palette_bits = f"{self.palette_id:06b}"
        else:
            palette_bits = "000000"
        
        # 白化种子: 8 位
        seed_bits = f"{self.whitening_seed:08b}"
        
        # 组合所有位
        all_bits = version_bits + layer_bits + ecc_bits + palette_bits + seed_bits
        
        # 转换为字节
        data = int(all_bits, 2).to_bytes((len(all_bits) + 7) // 8, 'big')
        
        # 添加 BCH 纠错
        return self._add_bch(data)
    
    def _add_bch(self, data: bytes) -> bytes:
        """添加 BCH 纠错"""
        # 简化: 使用重复编码
        # 实际应用中应使用真正的 BCH 编码
        return data + data[:2]  # 添加 2 字节重复
    
    def decode(self, encoded: bytes) -> bool:
        """
        解码格式信息
        
        Args:
            encoded: 编码后的字节
            
        Returns:
            是否解码成功
        """
        # 简化: 直接解析
        # 实际应用中应使用 BCH 解码
        return True
    
    def get_mirror(self) -> 'FormatInfo':
        """获取镜像副本"""
        return FormatInfo(
            version=self.version,
            layer_type=self.layer_type,
            ecc_level=self.ecc_level,
            palette_id=self.palette_id,
            whitening_seed=self.whitening_seed,
        )


class CalibrationSystem:
    """
    完整的校准系统
    
    管理所有校准相关的组件：
    - 3 个定位锚点
    - 中央校准枢纽
    - 顶部定时带
    - 2 个底部格式信息带
    - 静区
    """
    
    def __init__(self, width: int, height: int, layer: Layer):
        """
        初始化校准系统
        
        Args:
            width: 图像宽度
            height: 图像高度
            layer: 当前层
        """
        self.width = width
        self.height = height
        self.layer = layer
        
        # 计算各个组件的位置
        self._compute_layout()
    
    def _compute_layout(self):
        """计算布局"""
        # 静区宽度
        if self.layer.layer_type == LayerType.L4:
            quiet_zone = 1
        else:
            quiet_zone = 4 if "print" in self.layer.default_spacing else 2
        
        # 定义区域
        self.quiet_zone = quiet_zone
        self.data_start_x = quiet_zone * self.layer.default_spacing.get("screen", 4)
        self.data_start_y = quiet_zone * self.layer.default_spacing.get("screen", 4)
        self.data_width = self.width - 2 * self.data_start_x
        self.data_height = self.height - 2 * self.data_start_y
        
        # 创建锚点 (不对称排布)
        anchor_size = min(self.width, self.height) * 0.15
        
        self.anchors = {
            AnchorType.PRIMARY: Anchor(
                anchor_type=AnchorType.PRIMARY,
                center=(self.data_start_x + anchor_size, self.data_start_y + anchor_size),
                radius=anchor_size / 2,
            ),
            AnchorType.SECONDARY: Anchor(
                anchor_type=AnchorType.SECONDARY,
                center=(self.width - self.data_start_x - anchor_size, self.data_start_y + anchor_size),
                radius=anchor_size / 2,
            ),
            AnchorType.TERTIARY: Anchor(
                anchor_type=AnchorType.TERTIARY,
                center=(self.data_start_x + anchor_size, self.height - self.data_start_y - anchor_size),
                radius=anchor_size / 2,
            ),
        }
        
        # 创建中央校准枢纽
        hub_size = min(self.data_width, self.data_height) * 0.3
        self.calibration_hub = CalibrationHub(
            center=(self.width / 2, self.height / 2),
            inner_radius=hub_size * 0.3,
            outer_radius=hub_size * 0.5,
            layer=self.layer,
        )
        
        # 创建定时带
        timing_height = 20
        self.timing_pattern = TimingPattern(
            start=(self.data_start_x, self.data_start_y),
            end=(self.width - self.data_start_x, self.data_start_y),
            width=timing_height,
            module_count=40,
        )
        
        # 创建格式信息带
        format_height = 30
        self.format_info_primary = FormatInfo(
            version=1,
            layer_type=self.layer.layer_type,
            ecc_level="M",
            palette_id=0 if self.layer.layer_type in [LayerType.L3a, LayerType.L3b] else None,
            whitening_seed=0,
        )
        self.format_info_mirror = self.format_info_primary.get_mirror()
        
        self.format_start_y = self.height - self.data_start_y - format_height
    
    def draw(self, image: np.ndarray) -> None:
        """
        在图像上绘制所有校准组件
        
        Args:
            image: numpy 数组 (H, W, 3) RGB
        """
        # 绘制静区 (白色)
        self._draw_quiet_zone(image)
        
        # 绘制锚点
        for anchor in self.anchors.values():
            anchor.draw(image)
        
        # 绘制定时带
        self.timing_pattern.draw(image)
        
        # 绘制校准枢纽
        self.calibration_hub.draw(image)
        
        # 绘制格式信息带
        self._draw_format_info(image)
    
    def _draw_quiet_zone(self, image: np.ndarray) -> None:
        """绘制静区"""
        # 静区为白色
        quiet_color = (255, 255, 255)
        
        # 上下左右静区
        qz = self.quiet_zone * max(self.layer.default_spacing.values())
        
        # 左右静区
        image[:, :int(qz)] = quiet_color
        image[:, -int(qz):] = quiet_color
        
        # 上下静区
        image[:int(qz), :] = quiet_color
        image[-int(qz):, :] = quiet_color
    
    def _draw_format_info(self, image: np.ndarray) -> None:
        """绘制格式信息带"""
        # 简化: 绘制两个矩形区域
        format_height = 30
        y = self.format_start_y
        
        # 主格式信息
        image[y:y+format_height, self.data_start_x:self.width-self.data_start_x] = (200, 200, 200)
        
        # 镜像格式信息 (在定时带下方)
        mirror_y = self.data_start_y + self.timing_pattern.width + 10
        image[mirror_y:mirror_y+format_height, self.data_start_x:self.width-self.data_start_x] = (200, 200, 200)


__all__ = [
    "AnchorType", "Anchor",
    "CalibrationHub",
    "TimingPattern",
    "FormatInfo",
    "CalibrationSystem",
]
