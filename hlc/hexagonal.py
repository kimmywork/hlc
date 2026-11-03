"""
六边形网格几何模块

采用 flat-top 正六边形模块，边长 a：
- 横向中心距: 1.5a
- 奇偶列错位: √3a/2
- 纵向行距: √3a
- 名义间距 p ≈ 1.5a
- 模块数 N ≈ 1.155 × W×H / p²
"""

import math
import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum


class HexOrientation(Enum):
    """六边形方向"""
    FLAT_TOP = "flat_top"  # 平顶 (水平对边)
    POINTY_TOP = "pointy_top"  # 尖顶 (垂直对边)


@dataclass
class AxialCoord:
    """
    轴向坐标系 (q, r)
    
    六边形网格的轴向坐标，满足 q + r + s = 0
    第三个坐标 s = -q - r
    """
    q: int
    r: int
    
    @property
    def s(self) -> int:
        return -self.q - self.r
    
    def to_tuple(self) -> Tuple[int, int]:
        return (self.q, self.r)
    
    def __hash__(self):
        return hash(self.to_tuple())
    
    def __eq__(self, other):
        return self.q == other.q and self.r == other.r
    
    def __add__(self, other):
        return AxialCoord(self.q + other.q, self.r + other.r)
    
    def __sub__(self, other):
        return AxialCoord(self.q - other.q, self.r - other.r)
    
    def __mul__(self, scalar: int) -> 'AxialCoord':
        return AxialCoord(self.q * scalar, self.r * scalar)
    
    def distance_to(self, other: 'AxialCoord') -> int:
        """六边形距离 (步数)"""
        return (abs(self.q - other.q) + abs(self.r - other.r) + abs(self.s - other.s)) // 2
    
    def to_offset(self, row: int) -> Tuple[int, int]:
        """转换为偏移坐标 (用于数组索引)"""
        # 奇偶偏移坐标
        col = self.q + (row - (row & 1)) // 2
        return (row, col)
    
    @classmethod
    def from_offset(cls, row: int, col: int) -> 'AxialCoord':
        """从偏移坐标转换"""
        q = col - (row - (row & 1)) // 2
        r = row
        return cls(q, r)
    
    def to_pixel(self, center: Tuple[float, float], size: float, 
                  orientation: HexOrientation = HexOrientation.FLAT_TOP) -> Tuple[float, float]:
        """
        转换为像素坐标
        
        Args:
            center: 六边形中心坐标
            size: 六边形边长 a
            orientation: 方向
            
        Returns:
            (x, y) 像素坐标
        """
        if orientation == HexOrientation.FLAT_TOP:
            x = center[0] + size * (3/2) * self.q
            y = center[1] + size * math.sqrt(3) * (self.r + self.q / 2)
        else:  # POINTY_TOP
            x = center[0] + size * math.sqrt(3) * (self.q + self.r / 2)
            y = center[1] + size * (3/2) * self.r
        return (x, y)
    
    @classmethod
    def from_pixel(cls, x: float, y: float, center: Tuple[float, float], 
                   size: float, orientation: HexOrientation = HexOrientation.FLAT_TOP) -> 'AxialCoord':
        """
        从像素坐标转换为轴向坐标
        
        Args:
            x, y: 像素坐标
            center: 网格原点
            size: 六边形边长
            orientation: 方向
            
        Returns:
            轴向坐标
        """
        if orientation == HexOrientation.FLAT_TOP:
            q = (x - center[0]) / (size * 1.5)
            r = (y - center[1] - size * math.sqrt(3)/2 * q) / (size * math.sqrt(3))
        else:  # POINTY_TOP
            q = (x - center[0] - size * math.sqrt(3)/2 * (y - center[1])) / (size * math.sqrt(3))
            r = (y - center[1]) / (size * 1.5)
        
        # 四舍五入到整数
        q_round = round(q)
        r_round = round(r)
        s_round = round(-q - r)
        
        # 修正误差
        q_diff = abs(q - q_round)
        r_diff = abs(r - r_round)
        s_diff = abs(-q - r - s_round)
        
        if q_diff > r_diff and q_diff > s_diff:
            q_round = -r_round - s_round
        elif r_diff > s_diff:
            r_round = -q_round - s_round
        else:
            s_round = -q_round - r_round
        
        return cls(q_round, r_round)
    
    def __repr__(self):
        return f"AxialCoord(q={self.q}, r={self.r})"


class HexGrid:
    """
    六边形网格
    
    管理六边形模块的布局、地址和数据放置
    """
    
    DENSITY_FACTOR = 1.154700538  # 2/sqrt(3) ≈ 1.1547
    
    def __init__(self, width: int, height: int, module_size: float = 1.0,
                 orientation: HexOrientation = HexOrientation.FLAT_TOP,
                 center: Optional[Tuple[float, float]] = None):
        """
        初始化六边形网格
        
        Args:
            width: 图像宽度 (像素)
            height: 图像高度 (像素)
            module_size: 模块边长 a (像素)
            orientation: 六边形方向
            center: 网格中心坐标 (默认为图像中心)
        """
        self.width = width
        self.height = height
        self.module_size = module_size
        self.orientation = orientation
        self.center = center or (width / 2, height / 2)
        
        # 计算网格参数
        self._compute_params()
    
    def _compute_params(self):
        """计算网格参数"""
        # 横向和纵向间距
        if self.orientation == HexOrientation.FLAT_TOP:
            self.col_spacing = 1.5 * self.module_size
            self.row_spacing = math.sqrt(3) * self.module_size
            self.offset_y = self.row_spacing / 2
        else:  # POINTY_TOP
            self.col_spacing = math.sqrt(3) * self.module_size
            self.row_spacing = 1.5 * self.module_size
            self.offset_y = self.col_spacing / 2
        
        # 计算行数和列数
        self.num_rows = int(self.height / self.row_spacing) + 2
        self.num_cols = int(self.width / self.col_spacing) + 2
        
        # 名义间距 p
        self.nominal_spacing = 1.5 * self.module_size
        
        # 估计模块数
        self.estimated_module_count = int(
            self.DENSITY_FACTOR * self.width * self.height / (self.nominal_spacing ** 2)
        )
    
    def get_coords_in_radius(self, center_coord: AxialCoord, radius: int) -> List[AxialCoord]:
        """
        获取以中心坐标为圆心，半径为radius的所有六边形坐标
        
        Args:
            center_coord: 中心坐标
            radius: 半径 (步数)
            
        Returns:
            坐标列表
        """
        results = []
        for q in range(-radius, radius + 1):
            for r in range(max(-radius, -q - radius), min(radius, -q + radius) + 1):
                results.append(AxialCoord(center_coord.q + q, center_coord.r + r))
        return results
    
    def get_spiral_order(self, center_coord: AxialCoord, max_radius: int) -> List[AxialCoord]:
        """
        按螺旋序获取坐标 (从外环向中心)
        
        Args:
            center_coord: 中心坐标
            max_radius: 最大半径
            
        Returns:
            按螺旋顺序排列的坐标列表
        """
        # 从外到内
        coords = []
        for radius in range(max_radius, -1, -1):
            coords.extend(self.get_coords_in_radius(center_coord, radius))
        
        # 根据极坐标角度排序 (每个环内)
        def sort_key(coord):
            # 计算相对于中心的角度
            dx = coord.q - center_coord.q
            dy = coord.r - center_coord.r
            angle = math.atan2(dy, dx)
            distance = coord.distance_to(center_coord)
            return (-distance, angle)  # 负距离实现从外到内
        
        coords.sort(key=sort_key)
        return coords
    
    def get_data_region_coords(self, margin: int = 2) -> List[AxialCoord]:
        """
        获取数据区域的坐标 (排除边缘margin行)
        
        Args:
            margin: 边缘保留的行数
            
        Returns:
            数据区域坐标列表
        """
        coords = []
        center_row = self.num_rows // 2
        center_col = self.num_cols // 2
        
        for row in range(margin, self.num_rows - margin):
            for col in range(margin, self.num_cols - margin):
                coord = AxialCoord.from_offset(row, col)
                coords.append(coord)
        
        return coords
    
    def coord_to_pixel(self, coord: AxialCoord) -> Tuple[float, float]:
        """坐标转像素"""
        return coord.to_pixel(self.center, self.module_size, self.orientation)
    
    def pixel_to_coord(self, x: float, y: float) -> AxialCoord:
        """像素转坐标"""
        return AxialCoord.from_pixel(x, y, self.center, self.module_size, self.orientation)
    
    def get_module_polygon(self, coord: AxialCoord) -> List[Tuple[float, float]]:
        """
        获取六边形模块的多边形顶点
        
        Args:
            coord: 模块坐标
            
        Returns:
            6个顶点的坐标列表 (顺时针)
        """
        cx, cy = self.coord_to_pixel(coord)
        size = self.module_size
        
        if self.orientation == HexOrientation.FLAT_TOP:
            # 平顶六边形
            vertices = [
                (cx + size, cy),  # 右
                (cx + size/2, cy + size * math.sqrt(3)/2),  # 右上
                (cx - size/2, cy + size * math.sqrt(3)/2),  # 左上
                (cx - size, cy),  # 左
                (cx - size/2, cy - size * math.sqrt(3)/2),  # 左下
                (cx + size/2, cy - size * math.sqrt(3)/2),  # 右下
            ]
        else:  # POINTY_TOP
            # 尖顶六边形
            vertices = [
                (cx + size * math.sqrt(3)/2, cy + size/2),  # 右上
                (cx + size * math.sqrt(3)/2, cy - size/2),  # 右下
                (cx, cy - size),  # 下
                (cx - size * math.sqrt(3)/2, cy - size/2),  # 左下
                (cx - size * math.sqrt(3)/2, cy + size/2),  # 左上
                (cx, cy + size),  # 上
            ]
        
        return vertices
    
    def get_module_center_pixel(self, coord: AxialCoord) -> Tuple[float, float]:
        """获取模块中心像素坐标"""
        return self.coord_to_pixel(coord)
    
    def get_bounding_box(self, coords: List[AxialCoord]) -> Tuple[float, float, float, float]:
        """
        获取坐标列表的边界框
        
        Args:
            coords: 坐标列表
            
        Returns:
            (x_min, y_min, x_max, y_max)
        """
        if not coords:
            return (0, 0, 0, 0)
        
        x_min = y_min = float('inf')
        x_max = y_max = float('-inf')
        
        for coord in coords:
            x, y = self.coord_to_pixel(coord)
            x_min = min(x_min, x)
            y_min = min(y_min, y)
            x_max = max(x_max, x)
            y_max = max(y_max, y)
        
        return (x_min, y_min, x_max, y_max)
    
    @staticmethod
    def get_module_count(width: int, height: int, module_spacing: float) -> int:
        """
        静态方法：计算给定尺寸和间距下的模块数
        
        Args:
            width: 图像宽度
            height: 图像高度
            module_spacing: 模块间距 p
            
        Returns:
            模块数
        """
        area = width * height
        return int(HexGrid.DENSITY_FACTOR * area / (module_spacing ** 2))
    
    def __repr__(self):
        return f"HexGrid({self.width}x{self.height}, size={self.module_size}, estimated_modules={self.estimated_module_count})"
