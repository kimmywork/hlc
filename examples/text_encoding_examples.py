"""
HLC Text Encoding Examples

This script demonstrates encoding various classic texts using different HLC layers.
All text content is sourced from the internet, not self-generated.

Sources:
- Hello World: Standard programming example
- README prefix: From this repository's README.md
- The quick brown fox: English pangram
- Lorem ipsum: From https://en.wikipedia.org/wiki/Lorem_ipsum
- Chu Shi Biao (出师表): From https://zh.wikipedia.org/wiki/出师表
- Declaration of Independence: From https://en.wikipedia.org/wiki/United_States_Declaration_of_Independence
- Heart Sutra (心经): From https://zh.wikipedia.org/wiki/心经
"""

from hlc import HLCEncoder, HLCEncoderConfig, LayerType
import os

# Create output directory
os.makedirs("example_outputs", exist_ok=True)

# 1. Hello World - Standard programming greeting
HELLO_WORLD = b"Hello, World!"

# 2. README prefix - First part of this repository's README
README_PREFIX = b"""# HLC Code (Hexagonal Layered Code)

A set of same geometric framework, changing symbol tables according to channel capacity progressive 2D graphic codes.

HLC Code is an innovative 2D graphic code system that uses a hexagonal grid design and supports a layered architecture."""

# 3. The quick brown fox jumps over the lazy dog - English pangram
QUICK_BROWN_FOX = b"The quick brown fox jumps over the lazy dog"

# 4. Lorem ipsum - Classic placeholder text from Wikipedia
LOREM_IPSUM = b"""Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."""

# 5. Chu Shi Biao (前出师表) - Classic Chinese text by Zhuge Liang
CHU_SHI_BIAO = """先帝创业未半而中道崩殂，今天下三分，益州疲弊，此诚危急存亡之秋也。然侍卫之臣不懈于内，忠志之士忘身于外者，盖追先帝之殊遇，欲报之于陛下也。"""

# 6. Declaration of Independence - Opening paragraph
DECLARATION_OF_INDEPENDENCE = b"""In Congress, July 4, 1776. The unanimous Declaration of the thirteen united States of America. When in the Course of human events, it becomes necessary for one people to dissolve the political bands which have connected them with another."""

# 7. Heart Sutra (心经) - Mahayana Buddhist text
HEART_SUTRA = """观自在菩萨，行深般若波罗蜜多时，照见五蕴皆空，度一切苦厄。舍利子，色不异空，空不异色，色即是空，空即是色，受想行识，亦复如是。"""


def encode_with_layer(data: bytes, layer: LayerType, output_path: str, 
                     width: int = 512, height: int = 512, 
                     module_spacing: int = 4, description: str = "") -> None:
    """Encode data using the specified layer"""
    print(f"\nEncoding: {description}")
    print(f"Layer: {layer.value}")
    print(f"Data size: {len(data)} bytes")
    
    config = HLCEncoderConfig(
        layer_type=layer,
        width=width,
        height=height,
        module_spacing=module_spacing,
        ecc_enabled=True,
        whitening_enabled=True,
        interleaving_enabled=True,
    )
    
    encoder = HLCEncoder(config)
    info = encoder.get_info()
    
    print(f"Estimated modules: {info['estimated_modules']}")
    print(f"Theoretical capacity: {info['capacity']} bytes")
    
    try:
        image = encoder.encode(data, output_path=output_path)
        print(f"Success! Image saved to {output_path}")
        return True
    except ValueError as e:
        print(f"Failed: {e}")
        return False


def main():
    print("HLC Text Encoding Examples")
    print("="*60)
    
    # 1. Hello World - L1
    encode_with_layer(
        HELLO_WORLD,
        LayerType.L1,
        "example_outputs/hello_world_L1.png",
        width=512, height=512, module_spacing=8,
        description="Hello World (L1)"
    )
    
    # 2. README prefix - L2
    encode_with_layer(
        README_PREFIX,
        LayerType.L2,
        "example_outputs/readme_prefix_L2.png",
        width=512, height=512, module_spacing=4,
        description="README prefix (L2)"
    )
    
    # 3. Quick brown fox - L2
    encode_with_layer(
        QUICK_BROWN_FOX,
        LayerType.L2,
        "example_outputs/quick_brown_fox_L2.png",
        width=512, height=512, module_spacing=4,
        description="Quick brown fox (L2)"
    )
    
    # 4. Lorem ipsum - L3a
    encode_with_layer(
        LOREM_IPSUM,
        LayerType.L3a,
        "example_outputs/lorem_ipsum_L3a.png",
        width=512, height=512, module_spacing=4,
        description="Lorem ipsum (L3a)"
    )
    
    # 5. Chu Shi Biao - L3b
    encode_with_layer(
        CHU_SHI_BIAO.encode('utf-8'),
        LayerType.L3b,
        "example_outputs/chu_shi_biao_L3b.png",
        width=512, height=512, module_spacing=4,
        description="Chu Shi Biao (L3b)"
    )
    
    # 6. Declaration - L3b
    encode_with_layer(
        DECLARATION_OF_INDEPENDENCE,
        LayerType.L3b,
        "example_outputs/declaration_L3b.png",
        width=512, height=512, module_spacing=4,
        description="Declaration (L3b)"
    )
    
    # 7. Heart Sutra - L3b (using L3b instead of L4 as L4 has issues)
    encode_with_layer(
        HEART_SUTRA.encode('utf-8'),
        LayerType.L3b,
        "example_outputs/heart_sutra_L3b.png",
        width=512, height=512, module_spacing=4,
        description="Heart Sutra (L3b)"
    )
    
    print("\n" + "="*60)
    print("All examples completed!")
    print("Images saved in the 'example_outputs' directory.")


if __name__ == "__main__":
    main()
