"""
HLC 编码器

将数据编码为 HLC 码图像
"""

import numpy as np
from typing import List, Tuple, Dict, Optional, Union
from dataclasses import dataclass, field
from PIL import Image, ImageDraw
from .hexagonal import HexGrid, AxialCoord, HexOrientation
from .layers import Layer, LayerType, get_layer, L1, L2, L3a, L3b, L4
from .calibration import CalibrationSystem, AnchorType
from .ecc import reed_solomon_encode, Whitening, Interleaver, crc32
from .utils import generate_palette


@dataclass
class HLCEncoderConfig:
    """编码器配置"""
    layer_type: Union[str, LayerType] = LayerType.L2
    width: int = 1024
    height: int = 1024
    module_spacing: int = 4  # 模块间距 (像素)
    module_size: Optional[float] = None  # 模块边长 (自动计算)
    
    # 纠错
    ecc_enabled: bool = True
    redundancy_ratio: Optional[float] = None  # 覆盖默认冗余比例
    
    # 白化
    whitening_enabled: bool = True
    whitening_seed: int = 0
    
    # 交织
    interleaving_enabled: bool = True
    num_blocks: int = 4
    
    # 邻差约束
    neighbor_constraint_enabled: bool = True
    
    # 美学选项
    aesthetic_mode: bool = False
    max_module_spacing: Optional[int] = None  # 美学模式下的最大间距
    harmony_palette: bool = False  # 和谐色板
    logo_island: Optional[str] = None  # Logo 岛图像路径
    
    # 调试
    debug: bool = False


class HLCEncoder:
    """
    HLC 编码器
    
    将数据编码为 HLC 码图像
    """
    
    def __init__(self, config: Optional[HLCEncoderConfig] = None):
        """
        初始化编码器
        
        Args:
            config: 配置 (默认使用 L2)
        """
        self.config = config or HLCEncoderConfig()
        self.layer = get_layer(self.config.layer_type)
        
        # 计算模块边长
        if self.config.module_size is None:
            # 对于 flat-top 六边形，间距 p = 1.5 * a
            self.module_size = self.config.module_spacing / 1.5
        else:
            self.module_size = self.config.module_size
        
        # 初始化六边形网格
        self.hex_grid = HexGrid(
            width=self.config.width,
            height=self.config.height,
            module_size=self.module_size,
            orientation=HexOrientation.FLAT_TOP,
        )
        
        # 初始化校准系统
        self.calibration_system = CalibrationSystem(
            width=self.config.width,
            height=self.config.height,
            layer=self.layer,
        )
        
        # 初始化白化器
        self.whitening = Whitening(self.config.whitening_seed) if self.config.whitening_enabled else None
        
        # 初始化交织器
        if self.config.interleaving_enabled:
            block_size = (self.config.width * self.config.height) // (self.config.num_blocks * 255)
            block_size = max(1, block_size)
            self.interleaver = Interleaver(
                num_blocks=self.config.num_blocks,
                block_size=block_size,
            )
        else:
            self.interleaver = None
    
    def encode(self, data: bytes, output_path: Optional[str] = None) -> np.ndarray:
        """
        编码数据为 HLC 码图像
        
        Args:
            data: 要编码的数据
            output_path: 输出图像路径 (可选)
            
        Returns:
            HLC 码图像 (numpy 数组)
        """
        # 步骤 1: 检查数据大小
        if len(data) == 0:
            raise ValueError("Data cannot be empty")
        
        # 步骤 2: 自动选择档位 (美学模式)
        if self.config.aesthetic_mode:
            self._auto_select_spacing(data)
        
        # 步骤 3: 计算容量
        capacity = self._calculate_capacity()
        if len(data) > capacity:
            raise ValueError(f"Data too large. Capacity: {capacity} bytes, Got: {len(data)} bytes")
        
        # 步骤 4: 应用白化
        if self.whitening:
            data = self.whitening.whiten(data)
        
        # 步骤 5: 应用 ECC
        if self.config.ecc_enabled:
            redundancy = self.config.redundancy_ratio or self.layer.ecc_redundancy
            data = reed_solomon_encode(data, self.layer.layer_type.value, redundancy)
        
        # 步骤 6: 转换为符号
        symbols = self.layer.bytes_to_symbols(data)
        
        # 步骤 7: 应用邻差约束 (L2/L3)
        if self.config.neighbor_constraint_enabled and self.layer.layer_type in [LayerType.L2, LayerType.L3a, LayerType.L3b]:
            symbols = self._apply_neighbor_constraint(symbols)
        
        # 步骤 8: 应用交织
        if self.interleaver and len(symbols) > 0:
            # 将符号转换为字节进行交织
            symbol_bytes = bytes(symbols)
            interleaved_bytes = self.interleaver.interleave(
                [symbol_bytes[i::self.config.num_blocks] for i in range(self.config.num_blocks)]
            )
            symbols = list(interleaved_bytes)
        
        # 步骤 9: 生成图像
        image = self._generate_image(symbols)
        
        # 步骤 10: 保存图像 (如果需要)
        if output_path:
            self._save_image(image, output_path)
        
        return image
    
    def _auto_select_spacing(self, data: bytes) -> None:
        """
        美学模式: 自动选择最大的模块间距
        
        从 {32, 24, 16, 12, 8, 6, 4, 2}px 中选最大间距，
        使该档容量 ≥ 有效载荷，且数据区占用 ≥ 60%
        """
        if not self.config.aesthetic_mode:
            return
        
        possible_spacings = [32, 24, 16, 12, 8, 6, 4, 2]
        
        # 如果指定了最大间距，只考虑小于等于它的值
        if self.config.max_module_spacing:
            possible_spacings = [s for s in possible_spacings if s <= self.config.max_module_spacing]
        
        for spacing in sorted(possible_spacings, reverse=True):
            # 更新间距
            old_spacing = self.config.module_spacing
            self.config.module_spacing = spacing
            self.module_size = spacing / 1.5
            
            # 重新初始化网格
            self.hex_grid = HexGrid(
                width=self.config.width,
                height=self.config.height,
                module_size=self.module_size,
                orientation=HexOrientation.FLAT_TOP,
            )
            
            # 计算容量
            capacity = self._calculate_capacity()
            
            # 检查数据区占用率
            module_count = self.hex_grid.estimated_module_count
            data_modules = len(data) * 8 / self.layer.bits_per_module
            data_ratio = data_modules / module_count if module_count > 0 else 0
            
            if capacity >= len(data) and data_ratio >= 0.6:
                # 选择这个间距
                return
            
            # 恢复原间距
            self.config.module_spacing = old_spacing
            self.module_size = old_spacing / 1.5
            self.hex_grid = HexGrid(
                width=self.config.width,
                height=self.config.height,
                module_size=self.module_size,
                orientation=HexOrientation.FLAT_TOP,
            )
        
        # 如果没有找到合适的间距，使用最小的
        self.config.module_spacing = possible_spacings[-1]
        self.module_size = self.config.module_spacing / 1.5
        self.hex_grid = HexGrid(
            width=self.config.width,
            height=self.config.height,
            module_size=self.module_size,
            orientation=HexOrientation.FLAT_TOP,
        )
    
    def _calculate_capacity(self) -> int:
        """计算当前配置的容量"""
        module_count = self.hex_grid.estimated_module_count
        
        # 扣除结构开销 (10%)
        effective_modules = int(module_count * 0.9)
        
        # 计算原始比特数
        raw_bits = effective_modules * self.layer.bits_per_module
        
        # 扣除 ECC 开销
        ecc_ratio = self.config.redundancy_ratio or self.layer.ecc_redundancy
        data_bits = raw_bits * (1 - ecc_ratio)
        
        # 转换为字节
        return int(data_bits / 8)
    
    def _apply_neighbor_constraint(self, symbols: List[int]) -> List[int]:
        """
        应用邻差约束
        
        相邻模块亮度差 ≤ 半程
        """
        if self.layer.palette is None:
            return symbols
        
        # 预计算亮度
        brightness = [0.299 * r + 0.587 * g + 0.114 * b for r, g, b in self.layer.palette]
        max_diff = 0.5 * 255  # 半程
        
        # 使用螺旋序放置数据
        # 首先获取数据区域的坐标
        data_coords = self._get_data_coords()
        
        if len(symbols) > len(data_coords):
            # 如果符号数量超过坐标数量，截断
            symbols = symbols[:len(data_coords)]
        
        # 为每个坐标分配符号
        placed_symbols = [0] * len(data_coords)
        
        # 使用螺旋序
        for idx, coord in enumerate(data_coords):
            if idx >= len(symbols):
                break
            
            # 获取邻居
            neighbors = self._get_neighbors(coord)
            neighbor_symbols = []
            for n_coord in neighbors:
                if n_coord in data_coords:
                    n_idx = data_coords.index(n_coord)
                    if n_idx < idx:  # 已经放置的邻居
                        neighbor_symbols.append(placed_symbols[n_idx])
            
            # 检查约束
            current_symbol = symbols[idx]
            valid = True
            
            for n_symbol in neighbor_symbols:
                diff = abs(brightness[current_symbol] - brightness[n_symbol])
                if diff > max_diff:
                    valid = False
                    break
            
            if valid:
                placed_symbols[idx] = current_symbol
            else:
                # 寻找满足约束的符号
                # 这里简化: 选择亮度最接近的符号
                best_symbol = current_symbol
                best_diff = float('inf')
                
                for test_symbol in range(self.layer.symbol_count):
                    max_neighbor_diff = 0
                    for n_symbol in neighbor_symbols:
                        diff = abs(brightness[test_symbol] - brightness[n_symbol])
                        max_neighbor_diff = max(max_neighbor_diff, diff)
                    
                    if max_neighbor_diff <= max_diff:
                        # 计算与原始符号的差异
                        diff = abs(brightness[test_symbol] - brightness[current_symbol])
                        if diff < best_diff:
                            best_diff = diff
                            best_symbol = test_symbol
                
                placed_symbols[idx] = best_symbol
        
        return placed_symbols
    
    def _get_data_coords(self) -> List[AxialCoord]:
        """获取数据区域的坐标 (螺旋序)"""
        # 获取所有坐标
        center = AxialCoord(0, 0)
        max_radius = min(self.hex_grid.num_rows, self.hex_grid.num_cols) // 2
        
        # 按螺旋序排列
        coords = self.hex_grid.get_spiral_order(center, max_radius)
        
        # 过滤掉校准区域的坐标
        # 简化: 只使用中心区域的 90%
        start_idx = int(len(coords) * 0.05)
        end_idx = int(len(coords) * 0.95)
        
        return coords[start_idx:end_idx]
    
    def _get_neighbors(self, coord: AxialCoord) -> List[AxialCoord]:
        """获取六边形的 6 个邻居"""
        # 六边形的 6 个方向
        directions = [
            AxialCoord(1, 0), AxialCoord(0, 1), AxialCoord(-1, 1),
            AxialCoord(-1, 0), AxialCoord(0, -1), AxialCoord(1, -1),
        ]
        
        neighbors = []
        for direction in directions:
            neighbor = coord + direction
            neighbors.append(neighbor)
        
        return neighbors
    
    def _generate_image(self, symbols: List[int]) -> np.ndarray:
        """生成 HLC 码图像"""
        # 创建空白图像 (白色背景)
        image = np.ones((self.config.height, self.config.width, 3), dtype=np.uint8) * 255
        
        # 绘制校准组件
        self.calibration_system.draw(image)
        
        # 绘制数据模块
        data_coords = self._get_data_coords()
        
        for idx, coord in enumerate(data_coords):
            if idx >= len(symbols):
                break
            
            symbol = symbols[idx]
            
            # 获取模块颜色
            if self.layer.layer_type == LayerType.L1:
                color = (0, 0, 0) if symbol == 0 else (255, 255, 255)
            elif self.layer.layer_type == LayerType.L2:
                # 灰阶
                level = symbol * 255 // 15
                color = (level, level, level)
            elif self.layer.layer_type == LayerType.L4:
                # 24bit 真彩
                color = (
                    (symbol >> 16) & 0xFF,
                    (symbol >> 8) & 0xFF,
                    symbol & 0xFF,
                )
            else:
                # L3a/L3b: 使用调色板
                if self.layer.palette and symbol < len(self.layer.palette):
                    color = self.layer.palette[symbol]
                else:
                    color = (0, 0, 0)
            
            # 绘制六边形模块
            self._draw_hexagon(image, coord, color)
        
        # 绘制 Logo 岛 (如果有)
        if self.config.logo_island:
            self._draw_logo_island(image)
        
        return image
    
    def _draw_hexagon(self, image: np.ndarray, coord: AxialCoord, color: Tuple[int, int, int]) -> None:
        """绘制六边形模块"""
        # 获取六边形多边形顶点
        vertices = self.hex_grid.get_module_polygon(coord)
        
        # 使用 PIL 绘制多边形
        pil_image = Image.fromarray(image)
        draw = ImageDraw.Draw(pil_image)
        
        # 转换为 PIL 坐标
        pil_vertices = [(int(v[0]), int(v[1])) for v in vertices]
        
        # 绘制填充
        draw.polygon(pil_vertices, fill=color, outline=color)
        
        # 转换回 numpy 数组
        np.copyto(image, np.array(pil_image))
    
    def _draw_logo_island(self, image: np.ndarray) -> None:
        """绘制 Logo 岛"""
        # 简化: 在中心绘制一个圆形区域
        center_x = self.config.width // 2
        center_y = self.config.height // 2
        radius = min(self.config.width, self.config.height) // 10
        
        # 绘制圆形
        for y in range(max(0, center_y - radius), min(self.config.height, center_y + radius)):
            for x in range(max(0, center_x - radius), min(self.config.width, center_x + radius)):
                dx = x - center_x
                dy = y - center_y
                if dx*dx + dy*dy <= radius*radius:
                    image[y, x] = (255, 255, 255)  # 白色背景
    
    def _save_image(self, image: np.ndarray, path: str) -> None:
        """保存图像"""
        Image.fromarray(image).save(path)
    
    def get_info(self) -> Dict[str, Union[str, int, float]]:
        """获取编码器信息"""
        return {
            "layer": self.layer.layer_type.value,
            "width": self.config.width,
            "height": self.config.height,
            "module_spacing": self.config.module_spacing,
            "module_size": self.module_size,
            "estimated_modules": self.hex_grid.estimated_module_count,
            "capacity": self._calculate_capacity(),
            "bits_per_module": self.layer.bits_per_module,
            "ecc_redundancy": self.layer.ecc_redundancy,
        }


# 顶级编码函数
def encode_hlc(data: bytes, output_path: Optional[str] = None, 
               layer: str = "L2", **kwargs) -> np.ndarray:
    """
    顶级编码函数
    
    Args:
        data: 要编码的数据
        output_path: 输出图像路径 (可选)
        layer: 层类型 (L1, L2, L3a, L3b, L4)
        **kwargs: 其他配置参数
        
    Returns:
        HLC 码图像 (numpy 数组)
    """
    config = HLCEncoderConfig(
        layer_type=layer,
        **kwargs,
    )
    
    encoder = HLCEncoder(config)
    return encoder.encode(data, output_path)


__all__ = [
    "HLCEncoderConfig",
    "HLCEncoder",
    "encode_hlc",
]
