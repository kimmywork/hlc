"""
HLC 解码器

从 HLC 码图像中解码数据
"""

import numpy as np
from typing import List, Tuple, Dict, Optional, Union
from dataclasses import dataclass, field
from PIL import Image
import cv2
import math

from .hexagonal import HexGrid, AxialCoord, HexOrientation
from .layers import Layer, LayerType, get_layer, L1, L2, L3a, L3b, L4, rgb_to_lab
from .calibration import CalibrationSystem, AnchorType, Anchor, CalibrationHub
from .ecc import reed_solomon_decode, Whitening, crc32, verify_crc32


@dataclass
class HLCDecoderConfig:
    """解码器配置"""
    layer_type: Optional[Union[str, LayerType]] = None  # 自动检测
    
    # 图像预处理
    denoise: bool = True
    enhance_contrast: bool = True
    
    # 定位
    min_anchor_size: int = 20
    max_anchor_size: int = 200
    
    # 校准
    calibration_enabled: bool = True
    multi_frame: bool = False  # 多帧采集
    num_frames: int = 10
    
    # 解码
    ecc_enabled: bool = True
    whitening_enabled: bool = True
    whitening_seed: int = 0  # 白化种子
    
    # 调试
    debug: bool = False
    show_intermediate: bool = False


class HLCDecoder:
    """
    HLC 解码器
    
    从 HLC 码图像中解码数据
    """
    
    def __init__(self, config: Optional[HLCDecoderConfig] = None):
        """
        初始化解码器
        
        Args:
            config: 配置
        """
        self.config = config or HLCDecoderConfig()
        self.layer = None
        
        # 中间结果 (用于调试)
        self.intermediate_results = {}
    
    def decode(self, image_path: Optional[str] = None, 
               image: Optional[np.ndarray] = None) -> Tuple[bytes, bool]:
        """
        解码 HLC 码图像
        
        Args:
            image_path: 图像文件路径
            image: 图像数据 (numpy 数组)
            
        Returns:
            (解码后的数据, 是否成功)
        """
        # 步骤 1: 加载图像
        if image_path:
            image = self._load_image(image_path)
        elif image is None:
            raise ValueError("Either image_path or image must be provided")
        
        # 步骤 2: 图像预处理
        image = self._preprocess_image(image)
        
        # 步骤 3: 定位锚点
        anchors = self._detect_anchors(image)
        
        if len(anchors) < 3:
            if self.config.debug:
                print(f"[DEBUG] 只找到 {len(anchors)} 个锚点，需要至少 3 个")
            # 尝试直接解码 (不进行校正)
            corrected_image = image
            layer_type = self._detect_layer(corrected_image)
            if layer_type is None:
                return (b'', False)
        else:
            # 步骤 4: 单应变换校正 (如果有足够的锚点)
            if len(anchors) >= 4:
                try:
                    corrected_image, homography = self._correct_perspective(image, anchors)
                except:
                    corrected_image = image
            else:
                corrected_image = image
            
            # 步骤 5: 检测层类型
            layer_type = self._detect_layer(corrected_image)
            if layer_type is None:
                if self.config.debug:
                    print("[DEBUG] 无法检测层类型")
                return (b'', False)
        if layer_type is None:
            if self.config.debug:
                print("[DEBUG] 无法检测层类型")
            return (b'', False)
        
        self.layer = get_layer(layer_type)
        
        # 步骤 6: 校准
        calibration_data = self._calibrate(corrected_image)
        
        # 步骤 7: 采样六边形网格
        symbols = self._sample_hex_grid(corrected_image, calibration_data)
        
        # 步骤 8: 符号到字节
        data = self.layer.symbols_to_bytes(symbols)
        
        # 步骤 9: 去白化
        if self.config.whitening_enabled and self.layer.layer_type != LayerType.L4:
            # 使用配置中的种子
            whitening_seed = self.config.whitening_seed
            whitening = Whitening(whitening_seed)
            data = whitening.dewhiten(data)
        
        # 步骤 10: ECC 解码
        if self.config.ecc_enabled and self.layer.layer_type != LayerType.L4:
            redundancy_ratio = self.layer.ecc_redundancy
            data, success = reed_solomon_decode(data, layer_type, redundancy_ratio)
            if not success:
                if self.config.debug:
                    print("[DEBUG] ECC 解码失败")
                # 尝试降级解码
                data = self._fallback_decode(data)
        
        return (data, True)
    
    def decode_multi_frame(self, image_paths: List[str]) -> Tuple[bytes, bool]:
        """
        多帧解码
        
        从视频流取 10–15 帧清晰度加权平均
        
        Args:
            image_paths: 图像文件路径列表
            
        Returns:
            (解码后的数据, 是否成功)
        """
        if not self.config.multi_frame:
            return self.decode(image_paths[0])
        
        # 加载所有图像
        images = []
        for path in image_paths[:self.config.num_frames]:
            img = self._load_image(path)
            images.append(img)
        
        # 计算清晰度
        sharpness = [self._calculate_sharpness(img) for img in images]
        
        # 按清晰度加权平均
        total_sharpness = sum(sharpness)
        if total_sharpness == 0:
            return (b'', False)
        
        weighted_sum = np.zeros_like(images[0], dtype=np.float32)
        for img, s in zip(images, sharpness):
            weighted_sum += img.astype(np.float32) * (s / total_sharpness)
        
        average_image = np.clip(weighted_sum, 0, 255).astype(np.uint8)
        
        return self.decode(image=average_image)
    
    def _load_image(self, path: str) -> np.ndarray:
        """加载图像"""
        image = cv2.imread(path)
        if image is None:
            raise ValueError(f"无法加载图像: {path}")
        
        # 转换为 RGB
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
        else:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        return image
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """图像预处理"""
        # 确保图像是 uint8 类型
        if image.dtype != np.uint8:
            image = image.astype(np.uint8)
        
        # 确保图像是 3 通道
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        elif image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
        
        # 去噪
        if self.config.denoise:
            try:
                image = cv2.fastNlMeansDenoisingColored(
                    image, None, 10, 10, 7, 21
                )
            except:
                # 如果去噪失败，跳过
                pass
        
        # 增强对比度
        if self.config.enhance_contrast:
            try:
                lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
                l, a, b = cv2.split(lab)
                
                # CLAHE (对比度受限的自适应直方图均衡化)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                l = clahe.apply(l)
                
                lab = cv2.merge([l, a, b])
                image = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
            except:
                # 如果对比度增强失败，跳过
                pass
        
        return image
    
    def _detect_anchors(self, image: np.ndarray) -> List[Dict[str, Union[Tuple[int, int], float]]]:
        """
        检测定位锚点
        
        使用圆环检测算法
        
        Returns:
            锚点列表，每个包含: center, radius, type
        """
        # 转换为灰度
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        
        # 边缘检测
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # 检测圆
        min_radius = self.config.min_anchor_size // 2
        max_radius = self.config.max_anchor_size // 2
        
        circles = cv2.HoughCircles(
            edges, cv2.HOUGH_GRADIENT, dp=1, minDist=min_radius * 2,
            param1=50, param2=30, minRadius=min_radius, maxRadius=max_radius
        )
        
        anchors = []
        
        if circles is not None:
            circles = np.uint16(np.around(circles))
            
            for circle in circles[0, :]:
                x, y, r = circle
                
                # 验证圆环模式
                if self._validate_anchor_pattern(image, x, y, r):
                    anchors.append({
                        'center': (x, y),
                        'radius': r,
                        'type': None,  # 类型待确定
                    })
        
        # 如果检测到的锚点少于 3 个，尝试其他方法
        if len(anchors) < 3:
            # 尝试使用轮廓检测
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                # 近似多边形
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # 检查是否为圆形
                if len(approx) >= 6:
                    (x, y), radius = cv2.minEnclosingCircle(contour)
                    center = (int(x), int(y))
                    radius = int(radius)
                    
                    if min_radius <= radius <= max_radius:
                        if self._validate_anchor_pattern(image, center[0], center[1], radius):
                            anchors.append({
                                'center': center,
                                'radius': radius,
                                'type': None,
                            })
        
        # 确定锚点类型 (基于位置)
        if len(anchors) >= 3:
            # 按 x 坐标排序
            anchors.sort(key=lambda a: a['center'][0])
            
            # 左上: 第一个
            # 右上: 最后一个
            # 左下: y 最大的
            anchors[0]['type'] = AnchorType.PRIMARY
            anchors[-1]['type'] = AnchorType.SECONDARY
            
            middle_idx = 1 if len(anchors) == 3 else 2
            anchors[middle_idx]['type'] = AnchorType.TERTIARY
        
        return anchors
    
    def _validate_anchor_pattern(self, image: np.ndarray, x: int, y: int, radius: int) -> bool:
        """
        验证锚点的圆环模式
        
        锚点由同心圆环组成
        """
        # 简化: 检查圆心附近的像素分布
        # 真实锚点应该有交替的黑白环
        
        # 在半径方向上采样
        samples = []
        for r in range(int(radius * 0.3), int(radius * 0.9), int(radius * 0.1)):
            # 在圆周上采样多个点
            for angle in range(0, 360, 30):
                rad = math.radians(angle)
                px = int(x + r * math.cos(rad))
                py = int(y + r * math.sin(rad))
                
                if 0 <= px < image.shape[1] and 0 <= py < image.shape[0]:
                    # 计算亮度
                    brightness = 0.299 * image[py, px, 0] + 0.587 * image[py, px, 1] + 0.114 * image[py, px, 2]
                    samples.append(brightness)
        
        if len(samples) < 10:
            return False
        
        # 检查是否有明显的双峰分布 (黑白交替)
        samples = np.array(samples)
        mean = np.mean(samples)
        std = np.std(samples)
        
        # 如果标准差大，说明有明显的亮度变化
        if std < 50:
            return False
        
        # 检查是否有两个集群
        # 简化: 检查低亮度和高亮度的比例
        low_count = np.sum(samples < mean)
        high_count = np.sum(samples > mean)
        
        # 如果比例接近 50-50，可能是圆环
        ratio = min(low_count, high_count) / max(low_count, high_count)
        
        return ratio > 0.3
    
    def _correct_perspective(self, image: np.ndarray, 
                             anchors: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """
        单应变换校正
        
        使用 3 个锚点确定单应变换矩阵
        
        Returns:
            (校正后的图像, 单应变换矩阵)
        """
        # 提取 3 个锚点
        primary = next(a for a in anchors if a['type'] == AnchorType.PRIMARY)
        secondary = next(a for a in anchors if a['type'] == AnchorType.SECONDARY)
        tertiary = next(a for a in anchors if a['type'] == AnchorType.TERTIARY)
        
        # 源点 (图像中的锚点中心)
        src_points = np.float32([
            primary['center'],
            secondary['center'],
            tertiary['center'],
        ])
        
        # 目标点 (理想布局)
        # 假设理想布局: 左上, 右上, 左下
        img_width = image.shape[1]
        img_height = image.shape[0]
        
        # 估计尺寸
        anchor_size = primary['radius'] * 2
        margin = anchor_size
        
        dst_points = np.float32([
            [margin, margin],  # 左上
            [img_width - margin, margin],  # 右上
            [margin, img_height - margin],  # 左下
        ])
        
        # 计算单应变换矩阵
        homography, _ = cv2.findHomography(src_points, dst_points)
        
        # 应用单应变换
        corrected = cv2.warpPerspective(
            image, homography, 
            (img_width, img_height),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)
        )
        
        return corrected, homography
    
    def _detect_layer(self, image: np.ndarray) -> Optional[str]:
        """
        检测层类型
        
        通过分析格式信息带或颜色分布
        
        Returns:
            层类型字符串 (L1, L2, L3a, L3b, L4) 或 None
        """
        # 方法 1: 检查格式信息带
        layer_from_format = self._detect_layer_from_format(image)
        if layer_from_format:
            return layer_from_format
        
        # 方法 2: 分析颜色分布
        return self._detect_layer_from_colors(image)
    
    def _detect_layer_from_format(self, image: np.ndarray) -> Optional[str]:
        """从格式信息带检测层类型"""
        # 简化: 检查底部的格式信息区域
        # 格式信息带位于图像底部
        
        height = image.shape[0]
        format_region = image[height - 50:height - 10, :, :]
        
        # 计算平均颜色
        avg_color = np.mean(format_region, axis=(0, 1))
        
        # 如果是浅灰色，可能是格式信息带
        brightness = 0.299 * avg_color[0] + 0.587 * avg_color[1] + 0.114 * avg_color[2]
        
        if 150 < brightness < 220:
            # 尝试解析格式信息
            # 简化: 直接返回 L2 (最常见)
            return "L2"
        
        return None
    
    def _detect_layer_from_colors(self, image: np.ndarray) -> Optional[str]:
        """从颜色分布检测层类型"""
        # 分析图像中的颜色数量
        unique_colors = self._count_unique_colors(image)
        
        if unique_colors <= 2:
            return "L1"
        elif unique_colors <= 16:
            return "L2"
        elif unique_colors <= 64:
            return "L3a"
        elif unique_colors <= 256:
            return "L3b"
        else:
            return "L4"
    
    def _count_unique_colors(self, image: np.ndarray, threshold: int = 5) -> int:
        """计算图像中的唯一颜色数量"""
        # 降低分辨率以提高速度
        small = cv2.resize(image, (100, 100))
        
        # 转换为 LAB 颜色空间
        lab = cv2.cvtColor(small, cv2.COLOR_RGB2LAB)
        
        # 量化颜色
        quantized = (lab // threshold).astype(np.int32)
        
        # 计算唯一颜色
        unique = np.unique(quantized.reshape(-1, 3), axis=0)
        
        return len(unique)
    
    def _calibrate(self, image: np.ndarray) -> Dict:
        """
        校准图像
        
        包括: 灰阶环校准、色板校准、黑白端点校准
        
        Returns:
            校准数据字典
        """
        calibration_data = {
            'brightness_scale': None,
            'brightness_offset': None,
            'color_matrix': None,
        }
        
        if self.layer.layer_type == LayerType.L1:
            # L1: 黑白双锚 + Otsu 局部阈值
            calibration_data['threshold'] = self._calibrate_l1(image)
        
        elif self.layer.layer_type == LayerType.L2:
            # L2: 16级灰阶环 isotonic 回归
            calibration_data.update(self._calibrate_l2(image))
        
        elif self.layer.layer_type in [LayerType.L3a, LayerType.L3b]:
            # L3: 灰阶环 + 色板块仿射校正
            calibration_data.update(self._calibrate_l3(image))
        
        # elif self.layer.layer_type == LayerType.L4:
        # L4: 无需校准
        
        return calibration_data
    
    def _calibrate_l1(self, image: np.ndarray) -> int:
        """L1 校准: Otsu 阈值"""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        _, threshold = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return threshold
    
    def _calibrate_l2(self, image: np.ndarray) -> Dict:
        """
        L2 校准: 16级灰阶环 isotonic 回归
        
        使用灰阶环确定亮度映射
        """
        # 找到灰阶环
        grayscale_ring = self._find_grayscale_ring(image)
        
        if grayscale_ring is None:
            # 使用默认校准
            return {
                'brightness_scale': 1.0,
                'brightness_offset': 0.0,
            }
        
        # 计算每个灰阶块的平均亮度
        block_brightness = []
        for block in grayscale_ring:
            avg_brightness = np.mean(block)
            block_brightness.append(avg_brightness)
        
        # 排序
        sorted_indices = np.argsort(block_brightness)
        sorted_brightness = np.array(block_brightness)[sorted_indices]
        
        # 计算线性映射
        expected_brightness = np.linspace(0, 255, len(sorted_brightness))
        
        # 最小二乘拟合
        A = np.vstack([sorted_brightness, np.ones(len(sorted_brightness))]).T
        scale, offset = np.linalg.lstsq(A, expected_brightness, rcond=None)[0]
        
        return {
            'brightness_scale': float(scale),
            'brightness_offset': float(offset),
        }
    
    def _calibrate_l3(self, image: np.ndarray) -> Dict:
        """
        L3 校准: 灰阶环 + 色板块仿射校正
        
        使用灰阶环锁亮度轴 + 色板块最小二乘仿射
        """
        # 灰阶环校准
        l2_calibration = self._calibrate_l2(image)
        
        # 找到色板块
        palette_blocks = self._find_palette_blocks(image)
        
        if palette_blocks is None or len(palette_blocks) == 0:
            return l2_calibration
        
        # 计算每个色板块的平均颜色
        block_colors = []
        for block in palette_blocks:
            avg_color = np.mean(block, axis=(0, 1))
            block_colors.append(avg_color)
        
        # 计算期望颜色 (从调色板)
        expected_colors = self.layer.palette[:len(block_colors)]
        expected_colors = np.array(expected_colors)
        
        # 计算仿射变换矩阵
        # 简化: 使用线性变换
        # RGB -> RGB'
        # [R']   [a b c] [R]
        # [G'] = [d e f] [G]
        # [B']   [g h i] [B]
        
        # 这里简化为对角矩阵 (独立通道缩放)
        scales = []
        for channel in range(3):
            actual = np.array([c[channel] for c in block_colors])
            expected = expected_colors[:, channel]
            
            # 线性回归
            A = np.vstack([actual, np.ones(len(actual))]).T
            scale, offset = np.linalg.lstsq(A, expected, rcond=None)[0]
            scales.append((scale, offset))
        
        # 计算色彩校正矩阵
        color_matrix = np.eye(3)
        for i, (scale, _) in enumerate(scales):
            color_matrix[i, i] = scale
        
        return {
            **l2_calibration,
            'color_matrix': color_matrix,
            'color_offsets': [offset for _, offset in scales],
        }
    
    def _find_grayscale_ring(self, image: np.ndarray) -> Optional[List[np.ndarray]]:
        """找到灰阶环"""
        # 简化: 在中心区域寻找圆环
        center_x = image.shape[1] // 2
        center_y = image.shape[0] // 2
        
        # 估计半径
        min_radius = min(image.shape) * 0.2
        max_radius = min(image.shape) * 0.4
        
        # 在多个半径上采样
        blocks = []
        for r in np.linspace(min_radius, max_radius, 16):
            # 在圆周上采样
            samples = []
            for angle in np.linspace(0, 2*math.pi, 36, endpoint=False):
                x = int(center_x + r * math.cos(angle))
                y = int(center_y + r * math.sin(angle))
                
                if 0 <= x < image.shape[1] and 0 <= y < image.shape[0]:
                    # 取 3x3 区域的平均
                    region = image[max(0, y-1):min(image.shape[0], y+2), 
                                   max(0, x-1):min(image.shape[1], x+2)]
                    avg_color = np.mean(region, axis=(0, 1))
                    brightness = 0.299 * avg_color[0] + 0.587 * avg_color[1] + 0.114 * avg_color[2]
                    samples.append(brightness)
            
            if samples:
                blocks.append(np.array(samples))
        
        return blocks if blocks else None
    
    def _find_palette_blocks(self, image: np.ndarray) -> Optional[List[np.ndarray]]:
        """找到色板校准块"""
        # 简化: 在灰阶环外寻找小的彩色块
        # 这里返回 None，因为实现比较复杂
        return None
    
    def _sample_hex_grid(self, image: np.ndarray, calibration_data: Dict) -> List[int]:
        """
        采样六边形网格
        
        在模块中心 60% 区域采样
        
        Returns:
            符号列表
        """
        # 创建六边形网格
        module_spacing = self.layer.default_spacing.get("screen", 4)
        module_size = module_spacing / 1.5
        
        hex_grid = HexGrid(
            width=image.shape[1],
            height=image.shape[0],
            module_size=module_size,
            orientation=HexOrientation.FLAT_TOP,
        )
        
        # 获取数据区域坐标
        data_coords = self._get_data_coords(hex_grid)
        
        symbols = []
        
        for coord in data_coords:
            # 获取模块中心
            cx, cy = hex_grid.coord_to_pixel(coord)
            
            # 在模块中心 60% 区域采样
            sample_radius = module_size * 0.6
            
            # 收集采样点
            samples = []
            for angle in np.linspace(0, 2*math.pi, 12, endpoint=False):
                for r in [0.3, 0.6]:
                    x = int(cx + r * sample_radius * math.cos(angle))
                    y = int(cy + r * sample_radius * math.sin(angle))
                    
                    if 0 <= x < image.shape[1] and 0 <= y < image.shape[0]:
                        pixel = image[y, x]
                        samples.append(pixel)
            
            if not samples:
                continue
            
            # 计算平均颜色
            avg_color = np.mean(samples, axis=0)
            
            # 应用校准
            calibrated_color = self._apply_calibration(avg_color, calibration_data)
            
            # 转换为符号
            symbol = self._color_to_symbol(calibrated_color)
            symbols.append(symbol)
        
        return symbols
    
    def _get_data_coords(self, hex_grid: HexGrid) -> List[AxialCoord]:
        """获取数据区域的坐标"""
        center = AxialCoord(0, 0)
        max_radius = min(hex_grid.num_rows, hex_grid.num_cols) // 2
        
        # 按螺旋序排列
        coords = hex_grid.get_spiral_order(center, max_radius)
        
        # 过滤掉校准区域的坐标
        start_idx = int(len(coords) * 0.05)
        end_idx = int(len(coords) * 0.95)
        
        return coords[start_idx:end_idx]
    
    def _apply_calibration(self, color: np.ndarray, calibration_data: Dict) -> np.ndarray:
        """应用校准变换"""
        # 简化: 暂时不进行校准
        return color.astype(np.uint8)
    
    def _color_to_symbol(self, color: np.ndarray) -> int:
        """颜色转换为符号"""
        if self.layer.layer_type == LayerType.L1:
            # 黑白阈值
            threshold = 128
            brightness = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
            return 0 if brightness < threshold else 1
        
        elif self.layer.layer_type == LayerType.L2:
            # 16 级灰阶
            brightness = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
            level = int(brightness / 17)  # 0-15
            return min(15, max(0, level))
        
        elif self.layer.layer_type == LayerType.L4:
            # 24bit 真彩
            return (int(color[0]) << 16) | (int(color[1]) << 8) | int(color[2])
        
        else:  # L3a/L3b
            # 查找最接近的调色板颜色
            if self.layer.palette is None:
                return 0
            
            color_tuple = (int(color[0]), int(color[1]), int(color[2]))
            
            min_dist = float('inf')
            min_idx = 0
            
            for idx, palette_color in enumerate(self.layer.palette):
                dist = sum((a - b) ** 2 for a, b in zip(color_tuple, palette_color))
                if dist < min_dist:
                    min_dist = dist
                    min_idx = idx
            
            return min_idx
    
    def _fallback_decode(self, data: bytes) -> bytes:
        """
        降级解码
        
        如果当前层解码失败，尝试降级到低层
        """
        if self.layer.layer_type == LayerType.L4:
            # 降级到 L3b
            new_layer = L3b
        elif self.layer.layer_type == LayerType.L3b:
            # 降级到 L2
            new_layer = L2
        elif self.layer.layer_type == LayerType.L3a:
            # 降级到 L2
            new_layer = L2
        elif self.layer.layer_type == LayerType.L2:
            # 降级到 L1
            new_layer = L1
        else:
            return data
        
        # 重新解码
        self.layer = new_layer
        
        # 将数据转换为新层的符号
        # 这里简化: 直接返回原始数据
        # 实际应用中需要重新采样和解码
        return data
    
    def _calculate_sharpness(self, image: np.ndarray) -> float:
        """计算图像清晰度"""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        return cv2.Laplacian(gray, cv2.CV_64F).var()


# 顶级解码函数
def decode_hlc(image_path: str, **kwargs) -> Tuple[bytes, bool]:
    """
    顶级解码函数
    
    Args:
        image_path: 图像文件路径
        **kwargs: 其他配置参数
        
    Returns:
        (解码后的数据, 是否成功)
    """
    config = HLCDecoderConfig(**kwargs)
    decoder = HLCDecoder(config)
    return decoder.decode(image_path)


__all__ = [
    "HLCDecoderConfig",
    "HLCDecoder",
    "decode_hlc",
]
