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

HLC Code is an innovative 2D graphic code system that uses a hexagonal grid design and supports a layered architecture. Each layer shares the same geometric framework but uses symbol tables of different sizes, ranging from 1-bit black and white to 24-bit true color mode. The layers are interoperable and can be degraded smoothly, adapting to different channel capacities.

## Features

- Hexagonal grid: Using flat-top regular hexagon, about 15.5% more modules than square grid
- Layered architecture: 5 layers, from L1 (2-state black and white) to L4 (24bit true color)
- Smooth degradation: High-layer readers can naturally read low-layer codes, and automatically downgrade decoding when needed
- Multi-channel adaptation: Screen display, printing, bar code scanning, black and white printing, pure digital transmission
- Complete calibration system: Gray scale calibration blocks, black and white calibration blocks, color calibration blocks, etc.
- Strong error correction: Reed-Solomon encoding, different layers have different redundancy
- Aesthetic mode: Small data volume automatically selects the largest module spacing, presenting as large color blocks when viewed from a distance"""

# 3. The quick brown fox jumps over the lazy dog - English pangram
QUICK_BROWN_FOX = b"The quick brown fox jumps over the lazy dog"

# 4. Lorem ipsum - Classic placeholder text from Wikipedia
# Source: https://en.wikipedia.org/wiki/Lorem_ipsum
LOREM_IPSUM = b"""Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."""

# 5. Chu Shi Biao (前出师表) - Classic Chinese text by Zhuge Liang
# Source: https://zh.wikipedia.org/wiki/出师表
CHU_SHI_BIAO = b"""先帝创业未半而中道崩殂，今天下三分，益州疲弊，此诚危急存亡之秋也。然侍卫之臣不懈于内，忠志之士忘身于外者，盖追先帝之殊遇，欲报之于陛下也。诚宜开张圣听，以光先帝遗德，恢弘志士之气，不宜妄自菲薄，引喻失义，以塞忠谏之路也。

宫中府中，俱为一体，陟罚臧否，不宜异同。若有作奸犯科及为忠善者，宜付有司论其刑赏，以昭陛下平明之理，不宜偏私，使内外异法也。

侍中侍郎郭攸之、费祎、董允等，此皆良实，志虑忠纯，是以先帝简拔以遗陛下。愚以为宫中之事，事无大小，悉以咨之，然后施行，必能裨补阙漏，有所广益。

将军向宠，性行淑均，晓畅军事，试用于昔日，先帝称之曰能，是以众议举宠为督。愚以为营中之事，悉以咨之，必能使行阵和睦，优劣得所。

亲贤臣，远小人，此先汉所以兴隆也；亲小人，远贤臣，此后汉所以倾颓也。先帝在时，每与臣论此事，未尝不叹息痛恨于桓、灵也。侍中、尚书、长史、参军，此悉贞良死节之臣，愿陛下亲之信之，则汉室之隆，可计日而待也。

臣本布衣，躬耕于南阳，苟全性命于乱世，不求闻达于诸侯。先帝不以臣卑鄙，猥自枉屈，三顾臣于草庐之中，咨臣以当世之事，由是感激，遂许先帝以驱驰。后值倾覆，受任于败军之际，奉命于危难之间，尔来二十有一年矣。

先帝知臣谨慎，故临崩寄臣以大事也。受命以来，夙夜忧叹，恐托付不效，以伤先帝之明，故五月渡泸，深入不毛。今南方已定，兵甲已足，当奖率三军，北定中原，庶竭驽钝，攘除奸凶，兴复汉室，还于旧都。此臣所以报先帝而忠陛下之职分也。至于斟酌损益，进尽忠言，则攸之、祎、允之任也。

愿陛下托臣以讨贼兴复之效，不效则治臣之罪，以告先帝之灵。若无兴德之言，则责攸之、祎、允等之慢，以彰其咎；陛下亦宜自谋，以咨诹善道，察纳雅言。深追先帝遗诏，臣不胜受恩感激。

今当远离，临表涕零，不知所言。"""

# 6. Declaration of Independence - Opening paragraph
# Source: https://en.wikipedia.org/wiki/United_States_Declaration_of_Independence
DECLARATION_OF_INDEPENDENCE = b"""In Congress, July 4, 1776.

The unanimous Declaration of the thirteen united States of America,

When in the Course of human events, it becomes necessary for one people to dissolve the political bands which have connected them with another, and to assume among the powers of the earth, the separate and equal station to which the Laws of Nature and of Nature's God entitle them, a decent respect to the opinions of mankind requires that they should declare the causes which impel them to the separation.

We hold these truths to be self-evident, that all men are created equal, that they are endowed by their Creator with certain unalienable Rights, that among these are Life, Liberty and the pursuit of Happiness.

That to secure these rights, Governments are instituted among Men, deriving their just powers from the consent of the governed, That whenever any Form of Government becomes destructive of these ends, it is the Right of the People to alter or to abolish it, and to institute new Government, laying its foundation on such principles and organizing its powers in such form, as to them shall seem most likely to effect their Safety and Happiness."""

# 7. Heart Sutra (心经) - Mahayana Buddhist text
# Source: https://zh.wikipedia.org/wiki/心经
HEART_SUTRA = b"""观自在菩萨，行深般若波罗蜜多时，照见五蕴皆空，度一切苦厄。舍利子，色不异空，空不异色，色即是空，空即是色，受想行识，亦复如是。舍利子，是诸法空相，不生不灭，不垢不净，不增不减。是故空中无色，无受想行识，无眼耳鼻舌身意，无色声香味触法。无眼界，乃至无意识界。无无明，亦无无明尽，乃至无老死，亦无老死尽。无苦集灭道，无智亦无得。以无所得故，菩提萨埵，依般若波罗蜜多故，心无挂碍。无挂碍故，无有恐怖，远离颠倒梦想，究竟涅槃。三世诸佛，依般若波罗蜜多故，得阿耨多罗三藐三菩提。故知般若波罗蜜多，是大神咒，是大明咒，是无上咒，是无等等咒，能除一切苦，真实不虚。故说般若波罗蜜多咒，即说咒曰：揭谛揭谛，波罗揭谛，波罗僧揭谛，菩提萨婆诃。"""


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
    
    # 1. Hello World - L1 (2-state black and white, most compact)
    encode_with_layer(
        HELLO_WORLD,
        LayerType.L1,
        "example_outputs/hello_world_L1.png",
        width=512, height=512, module_spacing=8,
        description="Hello World (L1 - 2-state black and white)"
    )
    
    # 2. README prefix - L2 (16-level grayscale, screen display + printing)
    encode_with_layer(
        README_PREFIX,
        LayerType.L2,
        "example_outputs/readme_prefix_L2.png",
        width=1024, height=1024, module_spacing=4,
        description="README prefix (L2 - 16-level grayscale)"
    )
    
    # 3. Quick brown fox - L2
    encode_with_layer(
        QUICK_BROWN_FOX,
        LayerType.L2,
        "example_outputs/quick_brown_fox_L2.png",
        width=512, height=512, module_spacing=6,
        description="Quick brown fox (L2 - 16-level grayscale)"
    )
    
    # 4. Lorem ipsum - L3a (64-color CMYK, print preservation)
    encode_with_layer(
        LOREM_IPSUM,
        LayerType.L3a,
        "example_outputs/lorem_ipsum_L3a.png",
        width=1024, height=1024, module_spacing=4,
        description="Lorem ipsum (L3a - 64-color CMYK)"
    )
    
    # 5. Chu Shi Biao - L3b (256-color sRGB, screen scanning only)
    encode_with_layer(
        CHU_SHI_BIAO,
        LayerType.L3b,
        "example_outputs/chu_shi_biao_L3b.png",
        width=1536, height=1536, module_spacing=3,
        description="Chu Shi Biao (L3b - 256-color sRGB)"
    )
    
    # 6. Declaration of Independence - L3b
    encode_with_layer(
        DECLARATION_OF_INDEPENDENCE,
        LayerType.L3b,
        "example_outputs/declaration_L3b.png",
        width=1536, height=1536, module_spacing=3,
        description="Declaration of Independence (L3b - 256-color sRGB)"
    )
    
    # 7. Heart Sutra - L4 (24-bit true color, pure digital transmission)
    encode_with_layer(
        HEART_SUTRA,
        LayerType.L4,
        "example_outputs/heart_sutra_L4.png",
        width=2048, height=2048, module_spacing=1,
        description="Heart Sutra (L4 - 24-bit true color)"
    )
    
    print("\n" + "="*60)
    print("All examples completed!")
    print("Images saved in the 'example_outputs' directory.")


if __name__ == "__main__":
    main()
