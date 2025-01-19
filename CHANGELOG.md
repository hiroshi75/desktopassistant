# Changelog

## [Unreleased]

### Added
- macOS menu bar integration
  - Added support for menu bar icon with Retina display compatibility
  - Implemented transparent background for menu bar icon
  - Created high-resolution icon (128x128) that scales down cleanly
  - Added proper menu items for chat window control

### Changed
- Threading model improvements
  - Modified system tray to run on main thread for macOS
  - Updated window management to ensure thread safety
  - Added proper cleanup procedures for application shutdown
  - Improved error handling and logging

### Disabled
- Wake word functionality for macOS platform
  - Temporarily disabled to focus on core UI functionality
  - Will be re-implemented in future updates

### Technical Details
#### Current Implementation
- System tray icon runs on main thread for macOS using AppHelper.callAfter
- WebView operations are properly handled on main thread
- Window state management has been improved with better synchronization
- Added comprehensive logging for debugging

#### Known Issues
1. Window visibility state changes need better synchronization
2. Application cleanup could be more robust
3. Some thread safety improvements still needed in window management

#### Remaining Tasks
1. Improve window state management synchronization
2. Enhance cleanup process reliability
3. Add more comprehensive error handling
4. Re-implement wake word functionality for macOS

### Developer Notes
- The application uses PyObjC for macOS integration
- Threading model requires careful consideration:
  - UI operations must run on main thread
  - System tray operations must run on main thread for macOS
  - Event processing should be non-blocking
- Current focus is on stability and proper macOS integration

### Testing Notes
- Basic functionality tests have been implemented
- Platform-specific tests have been added
- More comprehensive testing needed for:
  - Thread safety
  - Window state management
  - Application cleanup

### Environment Setup
- Python 3.12 required
- Additional dependencies:
  - PyObjC (macOS)
  - webview
  - pystray
  - Pillow

### References
- [PyObjC Documentation](https://pyobjc.readthedocs.io/)
- [pywebview Documentation](https://pywebview.flowrl.com/)
