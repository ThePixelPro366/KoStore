# KOReader Store

A desktop application for automatic installation of plugins and patches to your KOReader device.

**Still in Early Beta! Bugs are expected. Please report all issues under the ‘Issues’ tab!**

## Project Structure

```
koreader_store/
├── main.py                 # Main entry point
├── ui/                     # User interface components
│   ├── main_window.py      # Main application window
│   ├── plugin_card.py      # Plugin card widget
│   ├── themes.py           # UI themes and design tokens
│   └── loading_overlay.py  # Loading screen overlay
├── api/                    # External API integrations
│   └── github.py          # GitHub API handler
├── workers/                # Background workers
│   └── download_worker.py # Download and installation worker
├── services/               # Business logic services
│   ├── device_detection.py # KOReader device detection
│   ├── plugin_installer.py # Plugin installation service
│   └── cache.py          # Caching service
└── utils/                  # Utility functions
    ├── markdown.py        # Markdown to HTML conversion
    └── versioning.py     # Version comparison utilities
```
**Many buttons and actions may take some time to respond. Please be patient — even if it says “Not Responding,” just click “Wait.”**
## Features

- **Plugin Management**: Browse, install, and update KOReader plugins
- **Patch Management**: Download and install KOReader patches
- **Device Detection**: Automatically detect KOReader devices
- **Caching**: Local caching for faster loading
- **Theme Support**: Light and dark themes
- **Search & Filter**: Advanced search and filtering options

## Installation

**Windows**:
1. Go to the releases tab and download the exe
2. Run the exe(there might be a application not responding message just wait).


0. Make sure python is installed(https://www.python.org/downloads/)
1. Click on Code then download zip
2. Extract the zip and open it(until you see a lot of folders and files)
3. Right click and press open a terminal here

4. Install dependencies:
   ```bash
   pip install PyQt6 requests markdown
   ```

5. Run the application:
   ```bash
   python main.py
   ```

**Tip: Inital start can take some time as it fetches all plugins!**

## Usage

1. **Device Connection**: The app will automatically detect KOReader devices, or you can manually select the path
2. **Browse Plugins**: Use the search and filter options to find plugins
3. **Install**: Click the install button on any plugin card
4. **Updates**: The app will show available updates for installed plugins

**Tip: The Check for Updates can take some time be patient!**
## Architecture

### UI Components (`ui/`)
- **main_window.py**: Contains the main application window with all UI logic
- **plugin_card.py**: Individual plugin card widget for displaying plugin information
- **themes.py**: Design tokens and theme definitions (light/dark mode)
- **loading_overlay.py**: Loading screen overlay for better UX

### API Layer (`api/`)
- **github.py**: GitHub API integration for fetching plugins and patches

### Workers (`workers/`)
- **download_worker.py**: Background thread for downloading and installing plugins

### Services (`services/`)
- **device_detection.py**: Cross-platform KOReader device detection
- **plugin_installer.py**: Plugin installation and management logic
- **cache.py**: Local caching service for offline functionality

### Utils (`utils/`)
- **markdown.py**: Markdown to HTML conversion for README display
- **versioning.py**: Version comparison utilities

## Configuration

- **Cache Duration**: 4 weeks (configurable in `services/cache.py`)
- **GitHub Token**: Optional but recommended for higher API rate limits
- **Log File**: `koreader_store.log` in the application directory

## Development

The application follows a modular architecture with clear separation of concerns:

1. **UI Layer**: Pure presentation logic
2. **Service Layer**: Business logic and data management
3. **API Layer**: External integrations
4. **Worker Layer**: Background operations
5. **Utils Layer**: Reusable utilities

## License

This project is licensed under the MIT License.

You are free to:
- Use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the software
- Permit persons to whom the software is furnished to do so

**Attribution (Shoutout) Appreciated!**
While not required, I would love to get a shoutout if you find this project useful. You can:
- Star the repository on GitHub
- Mention it in your project's credits
- Link back to this project
- Just let me know you're using it!

The full license text is below:

```
MIT License

Copyright (c) 2026 KOReader Store

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```





