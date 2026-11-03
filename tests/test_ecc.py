"""
测试纠错编码模块
"""

import unittest
from hlc.ecc import (
    GF256, SimpleRS, Whitening, Interleaver, crc32, verify_crc32,
    reed_solomon_encode, reed_solomon_decode
)


class TestGF256(unittest.TestCase):
    """测试 GF(256) 算术"""
    
    def test_addition(self):
        """测试加法"""
        self.assertEqual(GF256.add(0x12, 0x34), 0x12 ^ 0x34)
        self.assertEqual(GF256.add(0xFF, 0xFF), 0)
        self.assertEqual(GF256.add(0x00, 0xAB), 0xAB)
    
    def test_subtraction(self):
        """测试减法"""
        self.assertEqual(GF256.subtract(0x12, 0x34), 0x12 ^ 0x34)
        self.assertEqual(GF256.subtract(0xFF, 0xFF), 0)
    
    def test_multiplication(self):
        """测试乘法"""
        # 1 * x = x
        self.assertEqual(GF256.multiply(1, 0xAB), 0xAB)
        
        # 0 * x = 0
        self.assertEqual(GF256.multiply(0, 0xAB), 0)
        
        # x * 1 = x
        self.assertEqual(GF256.multiply(0xAB, 1), 0xAB)
    
    def test_division(self):
        """测试除法"""
        # x / 1 = x
        self.assertEqual(GF256.divide(0xAB, 1), 0xAB)
        
        # x / x = 1
        self.assertEqual(GF256.divide(0xAB, 0xAB), 1)
    
    def test_inverse(self):
        """测试逆元"""
        # x * x^(-1) = 1
        for x in range(1, 256):
            inv = GF256.inverse(x)
            self.assertEqual(GF256.multiply(x, inv), 1)
    
    def test_power(self):
        """测试幂运算"""
        # x^0 = 1
        self.assertEqual(GF256.power(0xAB, 0), 1)
        
        # x^1 = x
        self.assertEqual(GF256.power(0xAB, 1), 0xAB)
        
        # 0^x = 0 (x > 0)
        self.assertEqual(GF256.power(0, 5), 0)


class TestSimpleRS(unittest.TestCase):
    """测试简化 RS 编码器"""
    
    def test_encode_decode(self):
        """测试编码和解码"""
        rs = SimpleRS(n=10, k=5)
        
        data = b'\x01\x02\x03\x04\x05'
        encoded = rs.encode(data)
        
        self.assertEqual(len(encoded), 10)
        
        decoded, success = rs.decode(encoded)
        self.assertTrue(success)
        self.assertEqual(decoded, data)
    
    def test_encode_decode_larger(self):
        """测试较大数据的编码和解码"""
        rs = SimpleRS(n=255, k=250)
        
        data = bytes(range(250))
        encoded = rs.encode(data)
        
        self.assertEqual(len(encoded), 255)
        
        decoded, success = rs.decode(encoded)
        self.assertTrue(success)
        self.assertEqual(decoded, data)
    
    def test_invalid_length(self):
        """测试无效长度"""
        rs = SimpleRS(n=10, k=5)
        
        data = b'\x01\x02\x03\x04'  # 4 字节，需要 5 字节
        
        with self.assertRaises(ValueError):
            rs.encode(data)


class TestWhitening(unittest.TestCase):
    """测试白化"""
    
    def test_whiten_dewhiten(self):
        """测试白化和去白化"""
        seed = 42
        whitening = Whitening(seed)
        
        data = b'\x01\x02\x03\x04\x05'
        
        whitened = whitening.whiten(data)
        dewhitened = whitening.dewhiten(whitened)
        
        self.assertEqual(dewhitened, data)
    
    def test_different_seeds(self):
        """测试不同种子产生不同结果"""
        data = b'\x01\x02\x03\x04\x05'
        
        whitening1 = Whitening(42)
        whitening2 = Whitening(123)
        
        whitened1 = whitening1.whiten(data)
        whitened2 = whitening2.whiten(data)
        
        self.assertNotEqual(whitened1, whitened2)
    
    def test_same_seed_same_result(self):
        """测试相同种子产生相同结果"""
        seed = 42
        data = b'\x01\x02\x03\x04\x05'
        
        whitening1 = Whitening(seed)
        whitening2 = Whitening(seed)
        
        whitened1 = whitening1.whiten(data)
        whitened2 = whitening2.whiten(data)
        
        self.assertEqual(whitened1, whitened2)


class TestInterleaver(unittest.TestCase):
    """测试交织器"""
    
    def test_interleave_deinterleave(self):
        """测试交织和去交织"""
        num_blocks = 4
        block_size = 10
        
        interleaver = Interleaver(num_blocks, block_size)
        
        # 创建测试数据
        blocks = [
            bytes([i * 4 + j for j in range(block_size)]) 
            for i in range(num_blocks)
        ]
        
        interleaved = interleaver.interleave(blocks)
        deinterleaved = interleaver.deinterleave(interleaved)
        
        for i in range(num_blocks):
            self.assertEqual(deinterleaved[i], blocks[i])
    
    def test_wrong_num_blocks(self):
        """测试错误的块数"""
        interleaver = Interleaver(4, 10)
        
        blocks = [b'\x00' * 10 for _ in range(3)]  # 3 个块，需要 4 个
        
        with self.assertRaises(ValueError):
            interleaver.interleave(blocks)


class TestCRC32(unittest.TestCase):
    """测试 CRC32"""
    
    def test_crc32(self):
        """测试 CRC32 计算"""
        data = b'\x01\x02\x03\x04\x05'
        checksum = crc32(data)
        
        self.assertIsInstance(checksum, int)
        self.assertGreaterEqual(checksum, 0)
        self.assertLess(checksum, 2**32)
    
    def test_verify_crc32(self):
        """测试 CRC32 验证"""
        data = b'\x01\x02\x03\x04\x05'
        checksum = crc32(data)
        
        self.assertTrue(verify_crc32(data, checksum))
        self.assertFalse(verify_crc32(data, checksum + 1))


class TestTopLevelFunctions(unittest.TestCase):
    """测试顶级函数"""
    
    def test_reed_solomon_encode_decode(self):
        """测试顶级 RS 编码和解码"""
        data = b'\x01\x02\x03\x04\x05' * 10  # 50 字节
        
        encoded = reed_solomon_encode(data, "L2", redundancy_ratio=0.35)
        decoded, success = reed_solomon_decode(encoded, "L2", redundancy_ratio=0.35)
        
        self.assertTrue(success)
        self.assertEqual(decoded[:len(data)], data)


if __name__ == '__main__':
    unittest.main()
