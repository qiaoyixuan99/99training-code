# Height Maps for Squad Tactical Calculator V6

## How to Add Height Maps

Height maps are grayscale PNG images where each pixel represents elevation at that location.
- **White (255)** = highest elevation
- **Black (0)** = lowest elevation

## File Naming

Place height map PNG files in this directory using the map key as filename:
- `albasrah_height.png`
- `belaya_height.png`
- `chora_height.png`
- `gorodok_height.png`
- etc.

## Where to Get Height Maps

### Method 1: Squad SDK (recommended)
Use the Squad SDK to extract heightmaps from game files. The SDK can export grayscale height maps.

### Method 2: squad-mortar-helper (SMH)
SMH has a heightmap ripper built-in:
1. Download [squad-mortar-helper](https://github.com/WilliamVenner/squad-mortar-helper)
2. Run the heightmap ripper tool
3. Export heightmaps as PNG files
4. Rename to match the map keys above

### Method 3: Manual creation
For custom maps or scenarios, create a grayscale image where pixel intensity matches elevation.

## Height Map Metadata

Metadata for each map (scale, min/max elevation) is configured in the V6 HTML file's `HEIGHTMAP_META` object. 
If your height map has different parameters, edit the corresponding entry in v6-smh-capture-heightmap.html.

## Supported Maps (20 maps)

| Map Key | Map Name | Resolution (approx) |
|---------|----------|---------------------|
| albasrah | Al Basrah | 3200m |
| belaya | Belaya | 3900m |
| chora | Chora Valley | 4064m |
| fallujah | Fallujah | 3005m |
| foolsroad | Fool's Road | 1774m |
| forest | Operation First Light | 1200m |
| gorodok | Gorodok | 4340m |
| jensens | Jensen's Range | 1511m |
| kamdesh | Kamdesh Highlands | 4032m |
| kohat | Kohat Toi | 4617m |
| kokan | Kokan | 2496m |
| lashkar | Lashkar Valley | 4334m |
| logarvalley | Logar Valley | 1761m |
| mestia | Mestia | 2400m |
| mutaha | Mutaha | 2755m |
| narva | Narva | 2800m |
| skorpo | Skorpo | 7600m |
| sumari | Sumari Bala | 1300m |
| tallil | Tallil Outskirts | 4680m |
| yehorivka | Yehorivka | 5000m |

## Usage in V6

When a height map is loaded:
1. The toolbar shows "▲ HM" indicator
2. Hovering over the map shows elevation at cursor position
3. When mortar and target points are set, elevation difference is calculated and displayed
4. The elevation difference can be used to adjust mortar calculations

## Without Height Maps

V6 runs perfectly without height maps. All features work — the only difference is:
- No elevation data displayed
- No height difference in the results panel
- The "▲ HM" indicator remains hidden
