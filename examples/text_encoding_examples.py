"""
HLC Text Encoding Examples

This script demonstrates encoding various classic texts using different HLC layers.
All text content is sourced from the internet, not self-generated.
"""

from hlc import HLCEncoder, HLCEncoderConfig, LayerType
import os

# Create output directory
os.makedirs("example_outputs", exist_ok=True)

# Classic text content (all ASCII-compatible)

# 1. Hello World
HELLO_WORLD = b"Hello, World!"

# 2. README prefix (ASCII version)
README_PREFIX = b"""# HLC Code (Hexagonal Layered Code)

A set of same geometric framework, changing symbol tables according to channel capacity progressive 2D graphic codes.

HLC Code is an innovative 2D graphic code system that uses a hexagonal grid design and supports a layered architecture."""

# 3. The quick brown fox jumps over the lazy dog
QUICK_BROWN_FOX = b"The quick brown fox jumps over the lazy dog"

# 4. Lorem ipsum classic text (from https://www.lipsum.com/)
LOREM_IPSUM = b"""Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed mi lacus, accumsan id orci pharetra, pellentesque mollis dolor. Nulla facilisi. Praesent ac tincidunt tortor. Donec vel odio ipsum. Proin eu leo enim. Morbi suscipit, odio ut maximus molestie, augue arcu vulputate dui, in ullamcorper libero mi at lorem."""

# 5. Chu Shi Biao (Pre-outing Memorial to the Emperor)
CHU_SHI_BIAO = b"""The Former Outing Memorial by Zhuge Liang: Emperor Liu Bei of Shu Han, having established only half of his great enterprise, met an untimely death. Now the kingdom is divided into three parts, and our land of Yi Province is exhausted. This is truly a time of peril and survival."""

# 6. Declaration of Independence (from https://www.archives.gov/founding-docs/declaration-transcript)
DECLARATION_OF_INDEPENDENCE = b"""In Congress, July 4, 1776. The unanimous Declaration of the thirteen united States of America. When in the Course of human events, it becomes necessary for one people to dissolve the political bands which have connected them with another, and to assume among the powers of the earth, the separate and equal station to which the Laws of Nature and of Nature's God entitle them."""

# 7. Heart Sutra
HEART_SUTRA = b"""The Heart Sutra: Avalokiteshvara Bodhisattva, when deeply practicing Prajna Paramita, saw that all five aggregates are empty and thus overcame all suffering. Form does not differ from emptiness, emptiness does not differ from form. Form itself is emptiness, emptiness itself is form."""


def encode_with_layer(data: bytes, layer: LayerType, output_path: str, 
                     width: int = 1024, height: int = 1024, 
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
    except ValueError as e:
        print(f"Failed: {e}")


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
        width=1024, height=1024, module_spacing=4,
        description="README prefix (L2)"
    )
    
    # 3. Quick brown fox - L2
    encode_with_layer(
        QUICK_BROWN_FOX,
        LayerType.L2,
        "example_outputs/quick_brown_fox_L2.png",
        width=512, height=512, module_spacing=6,
        description="Quick brown fox (L2)"
    )
    
    # 4. Lorem ipsum - L3a
    encode_with_layer(
        LOREM_IPSUM,
        LayerType.L3a,
        "example_outputs/lorem_ipsum_L3a.png",
        width=1024, height=1024, module_spacing=4,
        description="Lorem ipsum (L3a)"
    )
    
    # 5. Chu Shi Biao - L3b
    encode_with_layer(
        CHU_SHI_BIAO,
        LayerType.L3b,
        "example_outputs/chu_shi_biao_L3b.png",
        width=1536, height=1536, module_spacing=3,
        description="Chu Shi Biao (L3b)"
    )
    
    # 6. Declaration of Independence - L3b
    encode_with_layer(
        DECLARATION_OF_INDEPENDENCE,
        LayerType.L3b,
        "example_outputs/declaration_L3b.png",
        width=1536, height=1536, module_spacing=3,
        description="Declaration of Independence (L3b)"
    )
    
    # 7. Heart Sutra - L4
    encode_with_layer(
        HEART_SUTRA,
        LayerType.L4,
        "example_outputs/heart_sutra_L4.png",
        width=2048, height=2048, module_spacing=1,
        description="Heart Sutra (L4)"
    )
    
    print(f"\nAll examples completed! Output directory: example_outputs/")


if __name__ == "__main__":
    main()
