"""
测试分层模块
"""

import unittest
from hlc.layers import (
    Layer, LayerType, L1, L2, L3a, L3b, L4,
    get_layer, get_layer_by_name,
    rgb_to_lab, lab_to_rgb,
    generate_grayscale_palette, generate_cmyk_palette, generate_srgb_palette
)


class TestLayerDefinitions(unittest.TestCase):
    """测试层定义"""
    
    def test_l1_layer(self):
        """测试 L1 层"""
        self.assertEqual(L1.layer_type, LayerType.L1)
        self.assertEqual(L1.symbol_count, 2)
        self.assertEqual(L1.bits_per_module, 1)
        self.assertEqual(L1.color_space, "Binary")
        self.assertFalse(L1.needs_calibration)
        self.assertAlmostEqual(L1.ecc_redundancy, 0.20, places=2)
    
    def test_l2_layer(self):
        """测试 L2 层"""
        self.assertEqual(L2.layer_type, LayerType.L2)
        self.assertEqual(L2.symbol_count, 16)
        self.assertEqual(L2.bits_per_module, 4)
        self.assertEqual(L2.color_space, "Grayscale")
        self.assertTrue(L2.needs_calibration)
        self.assertAlmostEqual(L2.ecc_redundancy, 0.35, places=2)
    
    def test_l3a_layer(self):
        """测试 L3a 层"""
        self.assertEqual(L3a.layer_type, LayerType.L3a)
        self.assertEqual(L3a.symbol_count, 64)
        self.assertEqual(L3a.bits_per_module, 6)
        self.assertEqual(L3a.color_space, "CMYK")
        self.assertTrue(L3a.needs_calibration)
        self.assertAlmostEqual(L3a.ecc_redundancy, 0.40, places=2)
    
    def test_l3b_layer(self):
        """测试 L3b 层"""
        self.assertEqual(L3b.layer_type, LayerType.L3b)
        self.assertEqual(L3b.symbol_count, 256)
        self.assertEqual(L3b.bits_per_module, 8)
        self.assertEqual(L3b.color_space, "sRGB")
        self.assertTrue(L3b.needs_calibration)
        self.assertAlmostEqual(L3b.ecc_redundancy, 0.40, places=2)
    
    def test_l4_layer(self):
        """测试 L4 层"""
        self.assertEqual(L4.layer_type, LayerType.L4)
        self.assertEqual(L4.symbol_count, 16777216)  # 2^24
        self.assertEqual(L4.bits_per_module, 24)
        self.assertEqual(L4.color_space, "TrueColor")
        self.assertFalse(L4.needs_calibration)
        self.assertAlmostEqual(L4.ecc_redundancy, 0.05, places=2)


class TestLayerFunctions(unittest.TestCase):
    """测试层函数"""
    
    def test_get_layer(self):
        """测试获取层"""
        layer = get_layer(LayerType.L2)
        self.assertEqual(layer, L2)
        
        layer = get_layer("L2")
        self.assertEqual(layer, L2)
    
    def test_get_layer_by_name(self):
        """测试通过名称获取层"""
        layer = get_layer_by_name("L1")
        self.assertEqual(layer, L1)
        
        layer = get_layer_by_name("L3a")
        self.assertEqual(layer, L3a)
    
    def test_bytes_to_symbols_l1(self):
        """测试字节到符号转换 (L1)"""
        data = b'\x01\x00\x01\x00'  # 4 字节 = 4 bit
        symbols = L1.bytes_to_symbols(data)
        
        # L1: 1 bit/模块，所以 4 字节 = 32 bit = 32 个符号
        self.assertEqual(len(symbols), 32)
        self.assertEqual(symbols[0], 1)
        self.assertEqual(symbols[1], 0)
    
    def test_bytes_to_symbols_l2(self):
        """测试字节到符号转换 (L2)"""
        data = b'\x0F\x00'  # 2 字节 = 16 bit = 4 个符号 (4 bit/符号)
        symbols = L2.bytes_to_symbols(data)
        
        self.assertEqual(len(symbols), 4)
        self.assertEqual(symbols[0], 15)  # 0x0F
        self.assertEqual(symbols[1], 0)   # 0x00
    
    def test_symbols_to_bytes_l2(self):
        """测试符号到字节转换 (L2)"""
        symbols = [15, 0, 15, 0]
        data = L2.symbols_to_bytes(symbols)
        
        self.assertEqual(data, b'\x0F\x00\x0F\x00')
    
    def test_bytes_to_symbols_l4(self):
        """测试字节到符号转换 (L4)"""
        data = b'\x12\x34\x56\x78\x9A\xBC'  # 6 字节 = 2 个 24bit 符号
        symbols = L4.bytes_to_symbols(data)
        
        self.assertEqual(len(symbols), 2)
        self.assertEqual(symbols[0], 0x123456)
        self.assertEqual(symbols[1], 0x789ABC)
    
    def test_symbols_to_bytes_l4(self):
        """测试符号到字节转换 (L4)"""
        symbols = [0x123456, 0x789ABC]
        data = L4.symbols_to_bytes(symbols)
        
        self.assertEqual(data, b'\x12\x34\x56\x78\x9A\xBC')
    
    def test_capacity_calculation(self):
        """测试容量计算"""
        module_count = 1000
        
        # L1: 1 bit/模块, 20% ECC
        capacity_l1 = L1.get_capacity(module_count)
        expected_l1 = int(module_count * 0.9 * 0.8 / 8)  # 90% 结构, 80% 数据
        self.assertEqual(capacity_l1, expected_l1)
        
        # L2: 4 bit/模块, 35% ECC
        capacity_l2 = L2.get_capacity(module_count)
        expected_l2 = int(module_count * 0.9 * 0.65 * 4 / 8)
        self.assertEqual(capacity_l2, expected_l2)


class TestPaletteGeneration(unittest.TestCase):
    """测试调色板生成"""
    
    def test_grayscale_palette(self):
        """测试灰阶调色板"""
        palette = generate_grayscale_palette(16)
        
        self.assertEqual(len(palette), 16)
        
        # 第一个应该是黑色
        self.assertEqual(palette[0], (0, 0, 0))
        
        # 最后一个应该是白色
        self.assertEqual(palette[15], (255, 255, 255))
    
    def test_cmyk_palette(self):
        """测试 CMYK 调色板"""
        palette = generate_cmyk_palette()
        
        self.assertEqual(len(palette), 64)
        
        # 第一个应该是白色 (C=0, M=0, Y=0)
        self.assertEqual(palette[0], (255, 255, 255))
    
    def test_srgb_palette(self):
        """测试 sRGB 调色板"""
        palette = generate_srgb_palette()
        
        self.assertEqual(len(palette), 256)
        
        # 第一个应该是黑色
        self.assertEqual(palette[0], (0, 0, 0))


class TestColorSpaceConversion(unittest.TestCase):
    """测试颜色空间转换"""
    
    def test_rgb_to_lab_black(self):
        """测试 RGB 到 LAB 转换 (黑色)"""
        L, a, b = rgb_to_lab((0, 0, 0))
        
        self.assertAlmostEqual(L, 0, places=1)
        self.assertAlmostEqual(a, 0, places=1)
        self.assertAlmostEqual(b, 0, places=1)
    
    def test_rgb_to_lab_white(self):
        """测试 RGB 到 LAB 转换 (白色)"""
        L, a, b = rgb_to_lab((255, 255, 255))
        
        self.assertAlmostEqual(L, 100, places=1)
        self.assertAlmostEqual(a, 0, places=1)
        self.assertAlmostEqual(b, 0, places=1)
    
    def test_lab_to_rgb_roundtrip(self):
        """测试 LAB 到 RGB 往返转换"""
        rgb = (128, 128, 128)
        lab = rgb_to_lab(rgb)
        rgb_back = lab_to_rgb(lab)
        
        # 允许小的误差
        for i in range(3):
            self.assertAlmostEqual(rgb[i], rgb_back[i], delta=5)


if __name__ == '__main__':
    unittest.main()
