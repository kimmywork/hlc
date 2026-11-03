#!/usr/bin/env python3
"""
HLC 码命令行工具
"""

import argparse
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hlc import HLCEncoder, HLCEncoderConfig, HLCDecoder, HLCDecoderConfig, LayerType
from hlc.layers import get_layer


def encode_command(args):
    """编码命令"""
    # 解析层类型
    layer_type = getattr(LayerType, args.layer.upper()) if args.layer else LayerType.L2
    
    # 创建配置
    config = HLCEncoderConfig(
        layer_type=layer_type,
        width=args.width,
        height=args.height,
        module_spacing=args.spacing,
        aesthetic_mode=args.aesthetic,
        max_module_spacing=args.max_spacing if args.aesthetic else None,
        harmony_palette=args.harmony,
        ecc_enabled=not args.no_ecc,
        whitening_enabled=not args.no_whitening,
        debug=args.debug,
    )
    
    # 创建编码器
    encoder = HLCEncoder(config)
    
    # 读取输入数据
    if args.input_file:
        with open(args.input_file, 'rb') as f:
            data = f.read()
    else:
        data = args.input.encode('utf-8') if args.input else b""
    
    if not data:
        print("错误: 输入数据为空", file=sys.stderr)
        return 1
    
    # 编码
    try:
        image = encoder.encode(data, output_path=args.output)
        print(f"编码成功! 图像保存为: {args.output}")
        
        # 显示信息
        info = encoder.get_info()
        print(f"\n编码信息:")
        print(f"  层: {info['layer']}")
        print(f"  图像尺寸: {info['width']}x{info['height']}")
        print(f"  模块间距: {info['module_spacing']}px")
        print(f"  模块数: {info['estimated_modules']}")
        print(f"  容量: {info['capacity']} 字节")
        print(f"  数据大小: {len(data)} 字节")
        
        return 0
    except ValueError as e:
        print(f"编码失败: {e}", file=sys.stderr)
        return 1


def decode_command(args):
    """解码命令"""
    # 解析层类型
    layer_type = getattr(LayerType, args.layer.upper()) if args.layer else None
    
    # 创建配置
    config = HLCDecoderConfig(
        layer_type=layer_type,
        denoise=not args.no_denoise,
        enhance_contrast=not args.no_enhance,
        multi_frame=args.multi_frame,
        num_frames=args.num_frames,
        debug=args.debug,
    )
    
    # 创建解码器
    decoder = HLCDecoder(config)
    
    # 解码
    try:
        if args.multi_frame:
            # 多帧解码
            image_paths = args.input if isinstance(args.input, list) else [args.input]
            decoded_data, success = decoder.decode_multi_frame(image_paths)
        else:
            # 单帧解码
            decoded_data, success = decoder.decode(args.input)
        
        if success:
            # 输出数据
            if args.output:
                with open(args.output, 'wb') as f:
                    f.write(decoded_data)
                print(f"解码成功! 数据保存为: {args.output}")
            else:
                # 显示为文本或十六进制
                try:
                    text = decoded_data.decode('utf-8')
                    print(f"解码成功:\n{text}")
                except UnicodeDecodeError:
                    print(f"解码成功 (二进制数据): {len(decoded_data)} 字节")
                    if args.hex:
                        print(decoded_data.hex())
            
            return 0
        else:
            print("解码失败", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"解码错误: {e}", file=sys.stderr)
        return 1


def info_command(args):
    """信息命令"""
    # 显示层信息
    for layer_name in ["L1", "L2", "L3a", "L3b", "L4"]:
        layer = get_layer(layer_name)
        print(f"\n{layer_name} 层:")
        print(f"  符号表大小: {layer.symbol_count}")
        print(f"  比特/模块: {layer.bits_per_module}")
        print(f"  颜色空间: {layer.color_space}")
        print(f"  ECC 冗余: {layer.ecc_redundancy * 100}%")
        print(f"  需要校准: {layer.needs_calibration}")
        print(f"  校准类型: {layer.calibration_type}")
        
        # 计算不同尺寸的容量
        if args.size:
            sizes = [int(s) for s in args.size.split(',')]
        else:
            sizes = [512, 1024, 2048]
        
        print(f"\n  容量表:")
        for size in sizes:
            from hlc.utils import calculate_capacity
            capacity = calculate_capacity(size, size, 4, layer_name)
            print(f"    {size}x{size} (4px): {capacity:.1f} 字节 ({capacity/1024:.2f} KiB)")
    
    return 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="HLC 码 (Hexagonal Layered Code) 命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 编码
  hlc-encode --input "Hello, World!" --output code.png --layer L2
  
  # 解码
  hlc-decode --input code.png --output message.txt
  
  # 显示信息
  hlc-info
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # 编码命令
    encode_parser = subparsers.add_parser('encode', help='编码数据为 HLC 码')
    encode_parser.add_argument('-i', '--input', type=str, default='', help='输入文本')
    encode_parser.add_argument('-f', '--input-file', type=str, help='输入文件路径')
    encode_parser.add_argument('-o', '--output', type=str, required=True, help='输出图像路径')
    encode_parser.add_argument('-l', '--layer', type=str, default='L2', 
                               choices=['L1', 'L2', 'L3a', 'L3b', 'L4'],
                               help='层类型 (默认: L2)')
    encode_parser.add_argument('-w', '--width', type=int, default=1024, help='图像宽度 (默认: 1024)')
    encode_parser.add_argument('-H', '--height', type=int, default=1024, help='图像高度 (默认: 1024)')
    encode_parser.add_argument('-s', '--spacing', type=int, default=4, help='模块间距 (默认: 4)')
    encode_parser.add_argument('-a', '--aesthetic', action='store_true', help='启用美学模式')
    encode_parser.add_argument('--max-spacing', type=int, default=32, help='美学模式最大间距 (默认: 32)')
    encode_parser.add_argument('--harmony', action='store_true', help='使用和谐色板')
    encode_parser.add_argument('--no-ecc', action='store_true', help='禁用 ECC')
    encode_parser.add_argument('--no-whitening', action='store_true', help='禁用白化')
    encode_parser.add_argument('-d', '--debug', action='store_true', help='调试模式')
    
    # 解码命令
    decode_parser = subparsers.add_parser('decode', help='解码 HLC 码')
    decode_parser.add_argument('-i', '--input', type=str, required=True, 
                               help='输入图像路径 (多帧时支持多个路径)')
    decode_parser.add_argument('-o', '--output', type=str, help='输出文件路径')
    decode_parser.add_argument('-l', '--layer', type=str, 
                               choices=['L1', 'L2', 'L3a', 'L3b', 'L4'],
                               help='层类型 (可选，自动检测)')
    decode_parser.add_argument('--no-denoise', action='store_true', help='禁用去噪')
    decode_parser.add_argument('--no-enhance', action='store_true', help='禁用对比度增强')
    decode_parser.add_argument('-m', '--multi-frame', action='store_true', help='多帧解码')
    decode_parser.add_argument('-n', '--num-frames', type=int, default=10, help='帧数 (默认: 10)')
    decode_parser.add_argument('--hex', action='store_true', help='以十六进制显示二进制数据')
    decode_parser.add_argument('-d', '--debug', action='store_true', help='调试模式')
    
    # 信息命令
    info_parser = subparsers.add_parser('info', help='显示层信息')
    info_parser.add_argument('--size', type=str, help='要计算的图像尺寸 (逗号分隔)')
    
    args = parser.parse_args()
    
    if args.command == 'encode':
        return encode_command(args)
    elif args.command == 'decode':
        return decode_command(args)
    elif args.command == 'info':
        return info_command(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
