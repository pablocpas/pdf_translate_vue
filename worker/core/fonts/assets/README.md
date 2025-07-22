# Font Assets

This directory contains font files used for PDF generation.

## Required Fonts

Place the following font files in this directory:

- `OpenSans-Regular.ttf` - For Latin-based languages
- `OpenSans-Bold.ttf` - Bold variant for emphasis

## Font Sources

### OpenSans
- **Source**: Google Fonts
- **License**: Apache License 2.0
- **Download**: https://fonts.google.com/specimen/Open+Sans

### Installation

1. Download OpenSans from Google Fonts
2. Extract the font files
3. Copy `OpenSans-Regular.ttf` and `OpenSans-Bold.ttf` to this directory

## CJK Fonts

CJK (Chinese, Japanese, Korean) fonts are provided by ReportLab's built-in CID fonts:
- HeiseiMin-W3 (Japanese)
- HYSMyeongJo-Medium (Korean) 
- STSong-Light (Chinese)

These fonts are registered automatically and don't require file installation.

## Font Usage

Fonts are automatically selected based on target language:
- Latin languages (English, Spanish, French, etc.) → OpenSans
- Japanese → HeiseiMin-W3
- Korean → HYSMyeongJo-Medium
- Chinese → STSong-Light

## Troubleshooting

If fonts are not working:
1. Verify font files are in this directory
2. Check file permissions
3. Ensure ReportLab is installed with CID font support
4. Check logs for font registration errors