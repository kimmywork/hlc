"""
HLC (Hexagonal Layered Code) - 渐进式二维图形码

一套"同几何框架、按信道能力换符号表"的渐进式二维图形码：
- 几何层完全统一
- 符号层从 1 bit 黑白一路扩展到 24 bit 真彩纯数字模式
- 层与层之间单调嵌套、可平滑降级

分层架构:
- L1: 2态纯黑白 (1 bit/模块)
- L2: 16级灰阶 (4 bit/模块)
- L3a: 64色CMYK色域 (6 bit/模块)
- L3b: 256色sRGB全域 (8 bit/模块)
- L4: 24bit真彩 (24 bit/模块)
"""

from .hexagonal import HexGrid, AxialCoord
from .layers import Layer, L1, L2, L3a, L3b, L4, get_layer, LayerType
from .calibration import CalibrationHub, Anchor
from .encoder import HLCEncoder, HLCEncoderConfig
from .decoder import HLCDecoder, HLCDecoderConfig
from .ecc import reed_solomon_encode, reed_solomon_decode
from .utils import generate_palette, get_module_count
from . import cli

__version__ = "0.1.0"
__all__ = [
    "HexGrid", "AxialCoord",
    "Layer", "L1", "L2", "L3a", "L3b", "L4", "get_layer",
    "CalibrationHub", "Anchor",
    "HLCEncoder", "HLCEncoderConfig",
    "HLCDecoder", "HLCDecoderConfig",
    "reed_solomon_encode", "reed_solomon_decode",
    "generate_palette", "get_module_count",
    "LayerType",
]
