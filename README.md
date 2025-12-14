# PhotoOrganizer - Free Photo Organization Software

> **Automatic photo sorting and EXIF metadata extraction tool** - Organize thousands of photos by date, camera, or GPS location in seconds.

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/Kiriiaq/PhotoOrganizer/releases/tag/v1.0.0)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://github.com/Kiriiaq/PhotoOrganizer/releases)
[![License](https://img.shields.io/badge/license-MIT%20+%20Commons%20Clause-orange.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-stable-brightgreen.svg)](https://github.com/Kiriiaq/PhotoOrganizer/releases/tag/v1.0.0)

---

## What is PhotoOrganizer?

**PhotoOrganizer** is a **free photo organization software** designed to help photographers and enthusiasts manage large photo collections efficiently. It automatically sorts photos using **EXIF metadata extraction**, organizing files by date, camera model, or GPS coordinates.

### The Problem It Solves

- **Messy photo libraries** with thousands of unsorted images
- **Time-consuming manual sorting** of photos from multiple cameras
- **Lost photos** buried in unorganized folders
- **No easy way to sort RAW files** alongside JPEGs

### The Solution

PhotoOrganizer provides **automatic photo sorting** with support for **45 file formats** including RAW files (CR2, NEF, RW2, ARW, DNG). Simply point it at your photo folder and let it organize everything in seconds.

---

## Key Features

### Complete Photo Analysis
- **45 supported formats**: Images (JPG, PNG, HEIC), RAW (CR2, NEF, RW2, DNG), Videos (MP4, MOV)
- **Full EXIF extraction**: Date, camera model, GPS coordinates, dimensions
- **Detailed statistics**: Distribution by type, date, camera, location
- **Smart recommendations**: Organization suggestions based on your data

### Intelligent Organization
- **By date**: YYYY-MM-DD or YYYY/MM/DD folder structure
- **By camera**: Canon EOS 5D, LUMIX GH5, iPhone, etc.
- **By GPS location**: Geographic coordinates
- **Multi-layer sorting**: Combine multiple criteria (e.g., Date > Camera)
- **Copy or move**: Preserve your originals or relocate files

### Modern Interface
- **CustomTkinter UI**: Clean, professional dark/light theme
- **Progress tracking**: Real-time progress bar
- **Scrollable results**: Detailed analysis with icons
- **Cancel operation**: Stop any operation instantly

---

## Quick Start

### Windows Executable (Recommended)

1. **Download** [PhotoManager.exe](https://github.com/Kiriiaq/PhotoOrganizer/releases/download/v1.0.0/PhotoManager.exe) from the latest release
2. **Run** the executable - no installation required
3. **Select** your photo folder and start organizing

### Python Installation

```bash
# Clone the repository
git clone https://github.com/Kiriiaq/PhotoOrganizer.git
cd PhotoOrganizer

# Install dependencies
pip install customtkinter exifread piexif Pillow darkdetect

# Run the application
python main.py
```

---

## How to Use

### 1. Analyze Your Photos

1. Click **"Browse"** to select your photo folder
2. Choose file types: Images, RAW, Videos
3. Enable **"Recursive search"** for subfolders
4. Click **"Analyze files"**

**Results include:**
- Total file count and types
- Date distribution (year, month)
- Camera models detected
- GPS data availability
- Organization recommendations

### 2. Organize Your Photos

1. Select **source** and **destination** folders
2. Choose organization criteria:
   - By date (YYYY-MM-DD)
   - By camera model
   - By GPS location
3. Enable **"Multi-layer organization"** to combine criteria
4. Choose **"Copy instead of move"** to preserve originals
5. Click **"Organize files"**

**Example output structure:**
```
Destination/
├── 2024-10/
│   ├── Canon EOS 5D/
│   │   ├── IMG_0001.jpg
│   │   └── IMG_0002.CR2
│   └── LUMIX GH5/
│       ├── P1200001.RW2
│       └── P1200002.JPG
└── 2024-11/
    └── iPhone 15 Pro/
        └── IMG_0003.HEIC
```

---

## Supported Formats (45 Total)

### Images (15)
`.jpg` `.jpeg` `.png` `.gif` `.bmp` `.tiff` `.tif` `.webp` `.heic` `.heif` `.svg` `.psd` `.jfif` `.jp2` `.avif`

### RAW Files (17)
`.raw` `.arw` `.cr2` `.cr3` `.nef` `.orf` `.rw2` `.dng` `.3fr` `.raf` `.pef` `.srw` `.sr2` `.x3f` `.mef` `.iiq` `.rwl`

### Videos (13)
`.mp4` `.mov` `.avi` `.mkv` `.wmv` `.flv` `.webm` `.3gp` `.m4v` `.mpg` `.mpeg` `.mts` `.ts` `.vob`

---

## System Requirements

- **OS**: Windows 10/11
- **Python**: 3.11+ (for source installation)
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: ~150MB for executable

---

## Building from Source

```bash
# Install PyInstaller
pip install pyinstaller

# Build the executable
pyinstaller --noconfirm --onefile --windowed --name "PhotoManager" \
  --hidden-import "PIL._tkinter_finder" \
  --hidden-import "customtkinter" \
  --hidden-import "darkdetect" \
  --hidden-import "exifread" \
  --hidden-import "piexif" \
  main.py

# Output: dist/PhotoManager.exe (~100MB)
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| No files found | Check folder path, enable correct file types, enable recursive search |
| Results not showing | Wait for 100% completion, check console for errors |
| Organization fails | Verify destination folder exists, check write permissions |
| Slow performance | Large folders (10k+ files) may take 1-2 minutes |

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Report Issues

Open a [GitHub Issue](https://github.com/Kiriiaq/PhotoOrganizer/issues) with:
- Bug description
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS

---

## Changelog

### v1.0.0 (2025-12-14) - Initial Stable Release

**Features:**
- Modern CustomTkinter interface with dark/light theme
- Complete EXIF metadata extraction
- 45 supported file formats (Images, RAW, Videos)
- Multi-layer organization (Date > Camera > GPS)
- Copy or move operations
- Progress tracking with cancel button
- Scrollable results window
- Standalone Windows executable

---

## Project Structure

```
PhotoOrganizer/
├── main.py                  # Entry point
├── src/
│   └── version.py           # Version info
├── core/
│   ├── file_operations.py   # File operations
│   ├── metadata.py          # EXIF extraction
│   └── format_conversion.py # Format handling
├── gui/
│   ├── app.py               # Main application
│   ├── frames/
│   │   └── file_organization_frame.py
│   └── widgets/
│       └── scrollable_frame.py
├── utils/
│   ├── config_manager.py    # Configuration
│   ├── file_utils.py        # File utilities
│   ├── progress_utils.py    # Progress management
│   └── ui_utils.py          # UI helpers
└── dist/
    └── PhotoManager.exe     # Windows executable
```

---

## License

This project is licensed under **MIT License with Commons Clause**.

**You CAN:**
- Use the software for free (personal and internal commercial use)
- Modify the source code
- Distribute the software
- Create derivative works
- Contribute to the project

**You CANNOT:**
- Sell the software itself
- Sell hosted services primarily based on this software
- Charge for support/consulting where the primary value is this software

See [LICENSE](LICENSE) for full details.

---

## Support the Project

If PhotoOrganizer helps you organize your photos, consider supporting development:

- [Ko-fi](https://ko-fi.com/kiriiaq) - Buy me a coffee
- [GitHub Stars](https://github.com/Kiriiaq/PhotoOrganizer) - Star the repository
- [Share](https://twitter.com/intent/tweet?text=Check%20out%20PhotoOrganizer%20-%20Free%20photo%20organization%20software%20with%20EXIF%20metadata%20extraction!%20https://github.com/Kiriiaq/PhotoOrganizer) - Tell others about it

---

## Contact

- **Author**: Kiriiaq
- **Email**: manugrolleau48@gmail.com
- **Ko-fi**: [https://ko-fi.com/kiriiaq](https://ko-fi.com/kiriiaq)
- **GitHub**: [https://github.com/Kiriiaq/PhotoOrganizer](https://github.com/Kiriiaq/PhotoOrganizer)

---

## Acknowledgments

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - Modern Tkinter UI
- [ExifRead](https://github.com/ianare/exif-py) - EXIF metadata extraction
- [Pillow](https://python-pillow.org/) - Image processing
- [PyInstaller](https://pyinstaller.org/) - Executable creation

---

<div align="center">

**PhotoOrganizer** - Free Photo Organization Software

Developed by [Kiriiaq](https://github.com/Kiriiaq) | [Support on Ko-fi](https://ko-fi.com/kiriiaq)

**Keywords**: photo organizer, EXIF metadata extraction, automatic photo sorting, RAW photo manager, free photo organization tool, photo management software, image sorter, photo file organizer, camera roll organizer, picture organizer

</div>
