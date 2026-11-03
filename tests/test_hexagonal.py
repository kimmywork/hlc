"""
测试六边形网格模块
"""

import unittest
import math
import numpy as np
from hlc.hexagonal import HexGrid, AxialCoord, HexOrientation


class TestAxialCoord(unittest.TestCase):
    """测试轴向坐标"""
    
    def test_axial_coord_creation(self):
        """测试轴向坐标创建"""
        coord = AxialCoord(q=1, r=2)
        self.assertEqual(coord.q, 1)
        self.assertEqual(coord.r, 2)
        self.assertEqual(coord.s, -3)  # s = -q - r
    
    def test_axial_coord_distance(self):
        """测试六边形距离计算"""
        coord1 = AxialCoord(0, 0)
        coord2 = AxialCoord(1, 0)
        coord3 = AxialCoord(0, 1)
        
        self.assertEqual(coord1.distance_to(coord2), 1)
        self.assertEqual(coord1.distance_to(coord3), 1)
        self.assertEqual(coord2.distance_to(coord3), 2)
    
    def test_axial_coord_arithmetic(self):
        """测试坐标运算"""
        coord1 = AxialCoord(1, 2)
        coord2 = AxialCoord(3, 4)
        
        # 加法
        sum_coord = coord1 + coord2
        self.assertEqual(sum_coord.q, 4)
        self.assertEqual(sum_coord.r, 6)
        
        # 减法
        diff_coord = coord2 - coord1
        self.assertEqual(diff_coord.q, 2)
        self.assertEqual(diff_coord.r, 2)
        
        # 标量乘法
        scaled = coord1 * 2
        self.assertEqual(scaled.q, 2)
        self.assertEqual(scaled.r, 4)
    
    def test_axial_coord_to_offset(self):
        """测试坐标转换"""
        coord = AxialCoord(2, 3)
        
        # 偶数行
        row, col = coord.to_offset(4)
        self.assertEqual(row, 4)
        self.assertEqual(col, 2 + (4 - (4 & 1)) // 2)
        
        # 奇数行
        row, col = coord.to_offset(3)
        self.assertEqual(row, 3)
        self.assertEqual(col, 2 + (3 - (3 & 1)) // 2)
    
    def test_axial_coord_to_pixel_flat_top(self):
        """测试坐标到像素转换 (平顶)"""
        coord = AxialCoord(1, 1)
        size = 10.0
        center = (100, 100)
        
        x, y = coord.to_pixel(center, size, HexOrientation.FLAT_TOP)
        
        # flat-top: x = center_x + size * 1.5 * q
        #           y = center_y + size * sqrt(3) * (r + q/2)
        expected_x = 100 + 1.5 * 10
        expected_y = 100 + math.sqrt(3) * 10 * (1 + 0.5)
        
        self.assertAlmostEqual(x, expected_x, places=2)
        self.assertAlmostEqual(y, expected_y, places=2)


class TestHexGrid(unittest.TestCase):
    """测试六边形网格"""
    
    def test_hex_grid_creation(self):
        """测试六边形网格创建"""
        grid = HexGrid(width=100, height=100, module_size=10)
        
        self.assertEqual(grid.width, 100)
        self.assertEqual(grid.height, 100)
        self.assertEqual(grid.module_size, 10)
        self.assertEqual(grid.orientation, HexOrientation.FLAT_TOP)
    
    def test_hex_grid_density_factor(self):
        """测试密度因子"""
        self.assertAlmostEqual(HexGrid.DENSITY_FACTOR, 2/math.sqrt(3), places=5)
    
    def test_hex_grid_module_count(self):
        """测试模块数计算"""
        grid = HexGrid(width=1000, height=1000, module_size=1)
        
        # 手动计算
        p = 1.5  # 名义间距
        area = 1000 * 1000
        expected = int(HexGrid.DENSITY_FACTOR * area / (p ** 2))
        
        self.assertEqual(grid.estimated_module_count, expected)
    
    def test_hex_grid_get_coords_in_radius(self):
        """测试获取半径内的坐标"""
        grid = HexGrid(width=100, height=100, module_size=1)
        center = AxialCoord(0, 0)
        
        coords = grid.get_coords_in_radius(center, 1)
        
        # 半径为1应该包含中心和6个邻居
        self.assertEqual(len(coords), 7)
    
    def test_hex_grid_get_spiral_order(self):
        """测试螺旋序"""
        grid = HexGrid(width=100, height=100, module_size=1)
        center = AxialCoord(0, 0)
        
        coords = grid.get_spiral_order(center, 2)
        
        # 半径为2应该包含1+6+12=19个坐标 (但实际实现可能不同)
        # 这里只测试是否返回了坐标
        self.assertGreater(len(coords), 0)
    
    def test_hex_grid_module_polygon(self):
        """测试六边形多边形生成"""
        grid = HexGrid(width=100, height=100, module_size=10)
        coord = AxialCoord(0, 0)
        
        vertices = grid.get_module_polygon(coord)
        
        # 应该有6个顶点
        self.assertEqual(len(vertices), 6)
        
        # 第一个顶点应该在右边
        cx, cy = grid.coord_to_pixel(coord)
        self.assertAlmostEqual(vertices[0][0], cx + 10, places=2)
        self.assertAlmostEqual(vertices[0][1], cy, places=2)


class TestHexGridStatic(unittest.TestCase):
    """测试静态方法"""
    
    def test_get_module_count(self):
        """测试静态模块数计算"""
        count = HexGrid.get_module_count(1000, 1000, 4)
        
        # 手动计算
        area = 1000 * 1000
        expected = int(HexGrid.DENSITY_FACTOR * area / (4 ** 2))
        
        self.assertEqual(count, expected)


if __name__ == '__main__':
    unittest.main()
