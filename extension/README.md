# CourseKey Browser Extension

A Chrome/Firefox browser extension that adds CourseKey as a sidebar widget on Canvas pages. The sidebar can be collapsed, expanded, and opened in fullscreen mode.

## Features

- **Sidebar Widget**: Appears as a collapsible sidebar on all Canvas pages
- **Fullscreen Mode**: Expand the chat to fullscreen for focused conversations
- **Seamless Integration**: Works alongside Canvas without interfering with navigation
- **Keyboard Shortcuts**: 
  - `Ctrl/Cmd + K` - Toggle sidebar
  - `Esc` - Close fullscreen

## Setup Instructions

### Prerequisites

1. **Backend and Frontend Running**: 
   - Backend must be running on `http://localhost:8000`
   - Frontend must be running on `http://localhost:3000`
   - See main [README.md](../README.md) for setup instructions

2. **Icons**: Create extension icons (or use placeholders):
   - `icons/icon16.png` (16x16)
   - `icons/icon48.png` (48x48)
   - `icons/icon128.png` (128x128)

### Loading the Extension (Chrome/Edge)

1. **Open Chrome Extensions Page**:
   - Navigate to `chrome://extensions/`
   - Or: Menu → More Tools → Extensions

2. **Enable Developer Mode**:
   - Toggle "Developer mode" switch in the top-right corner

3. **Load Unpacked Extension**:
   - Click "Load unpacked"
   - Select the `extension/` folder from this project

4. **Verify Installation**:
   - You should see "CourseKey" in your extensions list
   - The extension icon should appear in your toolbar

### Loading the Extension (Firefox)

1. **Open Firefox Extensions Page**:
   - Navigate to `about:debugging`
   - Click "This Firefox" in the left sidebar

2. **Load Temporary Extension**:
   - Click "Load Temporary Add-on..."
   - Select the `manifest.json` file from the `extension/` folder

3. **Note**: Firefox requires manifest v2 for now, so you may need to adjust the manifest.json

### Using the Extension

1. **Navigate to Canvas**:
   - Go to any Canvas page (e.g., `https://canvas.yale.edu` or your Canvas instance)

2. **Open CourseKey**:
   - Click the floating chat button (💬) in the bottom-right corner
   - Or press `Ctrl/Cmd + K`

3. **Use Fullscreen**:
   - Click the expand button (⛶) in the sidebar header
   - Or use the fullscreen button in the chat header

4. **Close Sidebar**:
   - Click the ✕ button in the sidebar header
   - Or press `Ctrl/Cmd + K` again

## Development

### File Structure

```
extension/
├── manifest.json          # Extension configuration
├── content-script.js      # Injects sidebar into Canvas pages
├── content-styles.css     # Styles for sidebar and fullscreen overlay
├── background.js          # Background service worker
├── icons/                 # Extension icons
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── README.md             # This file
```

### How It Works

1. **Content Script** (`content-script.js`):
   - Detects Canvas pages (instructure.com domains)
   - Injects sidebar HTML into the page
   - Creates iframe pointing to your React app (`http://localhost:3000`)
   - Handles sidebar toggle and fullscreen overlay

2. **Background Script** (`background.js`):
   - Service worker for extension lifecycle
   - Currently minimal, can be extended for scraping logic

3. **React App Integration**:
   - React app runs in an iframe
   - Detects iframe mode and adjusts UI accordingly
   - Communicates with extension via `postMessage`

### Customization

#### Change Backend/Frontend URLs

Edit `content-script.js`:
```javascript
const BACKEND_URL = 'http://localhost:8000';  // Your backend URL
const FRONTEND_URL = 'http://localhost:3000'; // Your frontend URL
```

#### Adjust Sidebar Width

Edit `content-styles.css`:
```css
#coursekey-sidebar {
  width: 400px;  /* Change this value */
}
```

#### Customize Colors

The sidebar uses the same gradient as your React app. Edit `content-styles.css` to change:
- Sidebar header gradient
- Toggle button colors
- Fullscreen overlay background

## Troubleshooting

### Sidebar Doesn't Appear

1. **Check Console**: Open browser DevTools (F12) and check for errors
2. **Verify URLs**: Ensure backend and frontend are running on correct ports
3. **Check Canvas URL**: Extension only works on `instructure.com` domains
4. **Reload Extension**: Go to extensions page and click reload

### React App Not Loading in Iframe

1. **CORS Issues**: Ensure backend CORS allows extension origins (already configured)
2. **Network Tab**: Check if requests are being blocked
3. **Iframe Permissions**: Verify `web_accessible_resources` in manifest.json

### Extension Not Loading

1. **Manifest Errors**: Check for syntax errors in `manifest.json`
2. **Icons Missing**: Create placeholder icons or remove icon references temporarily
3. **Permissions**: Ensure all required permissions are in manifest.json

## Production Deployment

For production, you'll need to:

1. **Update URLs**: Change localhost URLs to production backend/frontend
2. **Create Icons**: Design proper extension icons
3. **Bundle Extension**: Package extension for Chrome Web Store or Firefox Add-ons
4. **Update Manifest**: Set proper version numbers
5. **Submit for Review**: Submit to Chrome Web Store / Firefox Add-ons

## Future Enhancements

- [ ] Canvas page context detection (which course/page user is on)
- [ ] Automatic data scraping from current Canvas page
- [ ] Settings page for extension configuration
- [ ] Support for multiple Canvas instances
- [ ] Offline mode with cached data

