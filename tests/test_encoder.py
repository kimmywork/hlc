#!/usr/bin/env python3
"""
测试编码器模块
"""

import unittest
import os
import tempfile
from hlc.encoder import HLCEncoder, HLCEncoderConfig
from hlc.layers import LayerType


class TestHLCEncoder(unittest.TestCase):
    """测试 HLC 编码器"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        # 删除临时文件
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)
    
    def test_encoder_creation(self):
        """测试编码器创建"""
        config = HLCEncoderConfig(
            layer_type=LayerType.L2,
            width=512,
            height=512,
            module_spacing=4,
        )
        
        encoder = HLCEncoder(config)
        
        self.assertEqual(encoder.config.width, 512)
        self.assertEqual(encoder.config.height, 512)
        self.assertEqual(encoder.layer.layer_type, LayerType.L2)
    
    def test_encode_small_data(self):
        """测试编码小数据"""
        config = HLCEncoderConfig(
            layer_type=LayerType.L2,
            width=512,
            height=512,
            module_spacing=8,
        )
        
        encoder = HLCEncoder(config)
        data = b"Hello, World!"
        
        image = encoder.encode(data)
        
        self.assertIsNotNone(image)
        self.assertEqual(image.shape[0], 512)
        self.assertEqual(image.shape[1], 512)
        self.assertEqual(image.shape[2], 3)  # RGB
    
    def test_encode_to_file(self):
        """测试编码到文件"""
        config = HLCEncoderConfig(
            layer_type=LayerType.L2,
            width=512,
            height=512,
            module_spacing=8,
        )
        
        encoder = HLCEncoder(config)
        data = b"Test message"
        
        output_path = os.path.join(self.temp_dir, "test_hlc.png")
        image = encoder.encode(data, output_path=output_path)
        
        self.assertTrue(os.path.exists(output_path))
    
    def test_get_info(self):
        """测试获取编码器信息"""
        config = HLCEncoderConfig(
            layer_type=LayerType.L2,
            width=1024,
            height=1024,
            module_spacing=4,
        )
        
        encoder = HLCEncoder(config)
        info = encoder.get_info()
        
        self.assertIn('layer', info)
        self.assertIn('width', info)
        self.assertIn('height', info)
        self.assertIn('module_spacing', info)
        self.assertIn('capacity', info)
    
    def test_capacity_calculation(self):
        """测试容量计算"""
        config = HLCEncoderConfig(
            layer_type=LayerType.L2,
            width=1024,
            height=1024,
            module_spacing=4,
        )
        
        encoder = HLCEncoder(config)
        info = encoder.get_info()
        
        # L2: 4 bit/模块, 35% ECC, 10% 结构开销
        # 模块数 ≈ 1.1547 * 1024 * 1024 / 4^2 ≈ 75688
        # 有效模块 = 75688 * 0.9 ≈ 68119
        # 原始比特 = 68119 * 4 ≈ 272476
        # 数据比特 = 272476 * 0.65 ≈ 177110
        # 字节 = 177110 / 8 ≈ 22138
        
        self.assertGreater(info['capacity'], 20000)
        self.assertLess(info['capacity'], 25000)
    
    def test_different_layers(self):
        """测试不同层的编码"""
        data = b"Test"
        
        for layer_type in [LayerType.L1, LayerType.L2, LayerType.L3a, LayerType.L3b]:
            config = HLCEncoderConfig(
                layer_type=layer_type,
                width=512,
                height=512,
                module_spacing=8,
            )
            
            encoder = HLCEncoder(config)
            image = encoder.encode(data)
            
            self.assertIsNotNone(image)
    
    def test_data_too_large(self):
        """测试数据过大"""
        config = HLCEncoderConfig(
            layer_type=LayerType.L2,
            width=100,
            height=100,
            module_spacing=10,  # 很大的间距，容量很小
        )
        
        encoder = HLCEncoder(config)
        data = b"x" * 10000  # 很大的数据
        
        with self.assertRaises(ValueError):
            encoder.encode(data)
    
    def test_empty_data(self):
        """测试空数据"""
        config = HLCEncoderConfig(
            layer_type=LayerType.L2,
            width=512,
            height=512,
            module_spacing=8,
        )
        
        encoder = HLCEncoder(config)
        
        with self.assertRaises(ValueError):
            encoder.encode(b"")
    
    def test_aesthetic_mode(self):
        """测试美学模式"""
        config = HLCEncoderConfig(
            layer_type=LayerType.L3b,
            width=1024,
            height=1024,
            aesthetic_mode=True,
            max_module_spacing=32,
        )
        
        encoder = HLCEncoder(config)
        data = b"Short message"
        
        image = encoder.encode(data)
        
        self.assertIsNotNone(image)
        
        # 检查是否使用了较大的间距
        info = encoder.get_info()
        self.assertGreaterEqual(info['module_spacing'], 8)
    
    def test_ecc_enabled(self):
        """测试 ECC 启用"""
        config = HLCEncoderConfig(
            layer_type=LayerType.L2,
            width=512,
            height=512,
            module_spacing=4,
            ecc_enabled=True,
        )
        
        encoder = HLCEncoder(config)
        data = b"Test message"
        
        image = encoder.encode(data)
        
        self.assertIsNotNone(image)
    
    def test_whitening_enabled(self):
        """测试白化启用"""
        config = HLCEncoderConfig(
            layer_type=LayerType.L2,
            width=512,
            height=512,
            module_spacing=4,
            whitening_enabled=True,
            whitening_seed=42,
        )
        
        encoder = HLCEncoder(config)
        data = b"Test message"
        
        image = encoder.encode(data)
        
        self.assertIsNotNone(image)


class TestHLCEncoderConfig(unittest.TestCase):
    """测试编码器配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = HLCEncoderConfig()
        
        self.assertEqual(config.layer_type, LayerType.L2)
        self.assertEqual(config.width, 1024)
        self.assertEqual(config.height, 1024)
        self.assertEqual(config.module_spacing, 4)
        self.assertTrue(config.ecc_enabled)
        self.assertTrue(config.whitening_enabled)
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = HLCEncoderConfig(
            layer_type=LayerType.L3b,
            width=2048,
            height=2048,
            module_spacing=2,
            ecc_enabled=False,
        )
        
        self.assertEqual(config.layer_type, LayerType.L3b)
        self.assertEqual(config.width, 2048)
        self.assertEqual(config.height, 2048)
        self.assertEqual(config.module_spacing, 2)
        self.assertFalse(config.ecc_enabled)


if __name__ == '__main__':
    unittest.main()
