# PhotoOrganizer v1.0.0 - Release Notes

**Release Date:** December 14, 2025
**Type:** Initial Stable Release
**Download:** [PhotoManager.exe](https://github.com/Kiriiaq/PhotoOrganizer/releases/download/v1.0.0/PhotoManager.exe)

---

## What is PhotoOrganizer?

PhotoOrganizer is a **free, open-source photo organization software** that helps you automatically sort and manage large photo collections using EXIF metadata. Whether you're a professional photographer with thousands of RAW files or a casual user with years of accumulated photos, PhotoOrganizer makes organization effortless.

### The Problem We Solve

- **Chaotic photo libraries** - Photos scattered across folders with no logical structure
- **Manual sorting is tedious** - Renaming and moving files one by one takes hours
- **RAW files are ignored** - Most tools don't handle CR2, NEF, RW2 files properly
- **EXIF data goes unused** - Your photos contain valuable metadata that could organize them automatically

### Our Solution

PhotoOrganizer extracts EXIF metadata from your photos and automatically organizes them by:
- **Date taken** (YYYY-MM-DD folder structure)
- **Camera model** (Canon EOS 5D, iPhone 15 Pro, etc.)
- **GPS location** (when available)
- **Multi-layer combinations** (e.g., Date > Camera > Location)

---

## Key Features in v1.0.0

### Complete Photo Analysis
- **45 file formats supported**: JPG, PNG, HEIC, CR2, NEF, RW2, DNG, MP4, MOV, and more
- **Full EXIF extraction**: Date, time, camera make/model, GPS coordinates, dimensions
- **Detailed statistics**: File type distribution, date range, camera breakdown
- **Smart recommendations**: AI-powered suggestions for optimal organization

### Intelligent Organization
- **Flexible sorting**: By date, camera, GPS, or any combination
- **Preserve originals**: Copy files instead of moving them
- **Multi-layer structure**: Create nested folders (e.g., 2024-10/Canon EOS 5D/)
- **Batch processing**: Handle thousands of files in seconds

### Modern User Interface
- **CustomTkinter UI**: Clean, professional look with dark/light theme support
- **Real-time progress**: Watch your files being organized
- **Scrollable results**: Easy-to-read analysis reports
- **Cancel anytime**: Stop operations without losing progress

### Performance & Reliability
- **Fast processing**: Optimized for large photo libraries (10,000+ files)
- **Memory efficient**: Low RAM usage even with huge collections
- **Error handling**: Graceful handling of corrupted or unsupported files
- **Logging**: Detailed logs for troubleshooting

---

## Installation

### Option 1: Windows Executable (Recommended)

1. Download `PhotoManager.exe` from this release
2. Run the executable - no installation required
3. Windows Defender may show a warning (click "More info" > "Run anyway")

### Option 2: Python Source

```bash
git clone https://github.com/Kiriiaq/PhotoOrganizer.git
cd PhotoOrganizer
pip install customtkinter exifread piexif Pillow darkdetect
python main.py
```

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS | Windows 10 | Windows 11 |
| RAM | 4 GB | 8 GB |
| Disk Space | 150 MB | 200 MB |
| Python | 3.11+ | 3.12+ |

---

## Supported File Formats

### Images (15 formats)
JPG, JPEG, PNG, GIF, BMP, TIFF, TIF, WEBP, HEIC, HEIF, SVG, PSD, JFIF, JP2, AVIF

### RAW Files (17 formats)
RAW, ARW, CR2, CR3, NEF, ORF, RW2, DNG, 3FR, RAF, PEF, SRW, SR2, X3F, MEF, IIQ, RWL

### Videos (13 formats)
MP4, MOV, AVI, MKV, WMV, FLV, WEBM, 3GP, M4V, MPG, MPEG, MTS, TS, VOB

---

## Known Limitations

- **Windows only** - macOS and Linux support planned for v1.1.0
- **No cloud integration** - Local files only (cloud sync planned for future)
- **GPS requires EXIF** - Photos without GPS metadata can't be sorted by location

---

## What's Next?

Planned for v1.1.0:
- macOS support
- Duplicate detection
- Face recognition grouping
- Cloud storage integration (Google Photos, iCloud)
- Batch rename with templates

---

## Feedback & Support

- **Bug Reports**: [GitHub Issues](https://github.com/Kiriiaq/PhotoOrganizer/issues)
- **Feature Requests**: [GitHub Discussions](https://github.com/Kiriiaq/PhotoOrganizer/discussions)
- **Email**: manugrolleau48@gmail.com
- **Support Development**: [Ko-fi](https://ko-fi.com/kiriiaq)

---

## License

MIT License with Commons Clause - Free to use, modify, and distribute. Not for commercial resale.

---

**Thank you for trying PhotoOrganizer!**

If this tool helps you organize your photos, please consider:
- Starring the repository on GitHub
- Sharing with friends and colleagues
- Supporting development on [Ko-fi](https://ko-fi.com/kiriiaq)

---

*Keywords: photo organizer software, EXIF metadata extraction, automatic photo sorting, RAW photo manager, free photo organization tool, image file organizer, photo management, picture sorter*
