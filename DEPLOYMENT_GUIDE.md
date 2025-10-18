# Stock Evaluator - Mobile Deployment Guide

## Overview
This guide covers converting your Flask-based Stock Evaluator application into an Android APK using Apache Cordova/PhoneGap.

## Prerequisites

### Required Software
1. **Node.js** (v14 or higher)
2. **Apache Cordova CLI**
3. **Android Studio** (for Android SDK)
4. **Java Development Kit (JDK 8 or 11)**
5. **Python 3.8+** (for the Flask backend)

### Installation Commands
```bash
# Install Node.js (download from nodejs.org)

# Install Cordova CLI
npm install -g cordova

# Install Android Studio (download from developer.android.com)
# Make sure to install Android SDK and set ANDROID_HOME environment variable
```

## Step-by-Step APK Creation

### 1. Prepare the Flask Application

First, create a production-ready version of your Flask app:

```python
# Create production_app.py
from app import app
import os

if __name__ == '__main__':
    # Use environment variables for production
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
```

### 2. Generate Mobile Configuration Files

Run the mobile configuration script:

```bash
cd BD_Finance/FlowchartStocks/stock-evaluator
python mobile_config.py
```

This creates:
- `static/manifest.json` - PWA manifest
- `static/sw.js` - Service worker for offline functionality
- `config.xml` - Cordova configuration

### 3. Create Cordova Project

```bash
# Create new Cordova project
cordova create StockEvaluatorApp com.brunodias.stockevaluator "Stock Evaluator"

# Navigate to project directory
cd StockEvaluatorApp

# Add Android platform
cordova platform add android

# Copy your Flask app files to www directory
# (Replace the default www content with your Flask app's static files and templates)
```

### 4. Configure the Hybrid Architecture

Since Flask is a server-side framework, you'll need to choose one of these approaches:

#### Option A: Progressive Web App (PWA) - Recommended
Convert to a PWA that can be installed on mobile devices:

1. **Update your HTML template** to include PWA meta tags:
```html
<!-- Add to <head> section of index.html -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="manifest" href="/static/manifest.json">
<link rel="apple-touch-icon" href="/static/icons/icon-192x192.png">

<!-- Service Worker Registration -->
<script>
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js')
        .then(registration => console.log('SW registered'))
        .catch(error => console.log('SW registration failed'));
}
</script>
```

2. **Deploy your Flask app** to a cloud service (Heroku, PythonAnywhere, etc.)

3. **Create a simple Cordova wrapper** that loads your web app:

```html
<!-- www/index.html for Cordova -->
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stock Evaluator</title>
</head>
<body>
    <script>
        // Redirect to your deployed Flask app
        window.location.href = 'https://your-flask-app-url.herokuapp.com';
    </script>
</body>
</html>
```

#### Option B: Client-Side JavaScript Version
Convert the core functionality to client-side JavaScript:

1. **Create a JavaScript version** of your stock evaluation logic
2. **Use a financial data API** that supports CORS (like Alpha Vantage, IEX Cloud)
3. **Implement the evaluation logic** in JavaScript

### 5. Build the APK

```bash
# Build for Android
cordova build android

# For release build (requires signing)
cordova build android --release

# Install on connected device
cordova run android
```

## Alternative Approaches

### 1. Using Kivy (Python-based)
Convert your Flask app to a Kivy application:

```bash
pip install kivy buildozer

# Create buildozer.spec file
buildozer init

# Build APK
buildozer android debug
```

### 2. Using React Native with Python Backend
1. Create a React Native frontend
2. Keep your Flask app as a backend API
3. Deploy Flask to cloud and connect via API calls

### 3. Using Flutter with Python Backend
1. Create a Flutter frontend
2. Use your Flask app as a REST API backend
3. Deploy both separately

## Recommended Architecture for Your Use Case

Given your application's complexity and AI integration, I recommend:

### Hybrid PWA + Native Wrapper Approach

1. **Keep Flask backend** deployed on cloud (Heroku, AWS, etc.)
2. **Create PWA frontend** with offline capabilities
3. **Use Cordova wrapper** for app store distribution
4. **Implement caching** for offline stock data viewing

### Implementation Steps:

1. **Deploy Flask app to cloud**:
```bash
# For Heroku deployment
pip install gunicorn
echo "web: gunicorn app:app" > Procfile
git init
git add .
git commit -m "Initial commit"
heroku create your-stock-evaluator-app
git push heroku main
```

2. **Create mobile-optimized templates**
3. **Add offline functionality** with service workers
4. **Build Cordova wrapper** pointing to your deployed app

## Testing

### Local Testing
```bash
# Test Flask app locally
python app.py

# Test Cordova app in browser
cordova serve

# Test on Android emulator
cordova emulate android
```

### Performance Optimization

1. **Minimize API calls** - cache stock data locally
2. **Optimize images** - use WebP format for icons
3. **Enable compression** - gzip responses from Flask
4. **Implement lazy loading** - load analysis sections on demand

## Security Considerations

1. **API Key Protection** - use environment variables
2. **HTTPS Only** - ensure all communications are encrypted
3. **Input Validation** - sanitize all user inputs
4. **Rate Limiting** - prevent API abuse

## Deployment Checklist

- [ ] Flask app deployed to cloud platform
- [ ] PWA manifest and service worker configured
- [ ] Mobile-responsive design tested
- [ ] Offline functionality implemented
- [ ] Cordova project created and configured
- [ ] Android platform added and tested
- [ ] APK built and signed for release
- [ ] App tested on physical devices
- [ ] Performance optimized
- [ ] Security measures implemented

## Troubleshooting

### Common Issues:

1. **CORS Errors**: Configure Flask-CORS for cross-origin requests
2. **API Key Exposure**: Use environment variables and server-side proxy
3. **Slow Loading**: Implement progressive loading and caching
4. **Memory Issues**: Optimize JavaScript and limit concurrent requests

### Debug Commands:
```bash
# Check Cordova requirements
cordova requirements

# Debug on device
cordova run android --debug

# View device logs
adb logcat
```

## Next Steps

1. **Implement the recommended PWA approach**
2. **Deploy Flask backend to cloud**
3. **Create Cordova wrapper**
4. **Test thoroughly on multiple devices**
5. **Optimize performance**
6. **Prepare for app store submission**

This approach gives you the best of both worlds: the power of your Python backend with the accessibility of a mobile app.