# D:/GitHub/BD_Python_AI/BD_Finance/FlowchartStocks/stock-evaluator/mobile_config.py
# Mobile configuration and APK preparation utilities
# 20251507 BDLRA

import os
import json
from typing import Dict, Any


class MobileConfig:
    """
    Configuration class for mobile deployment and APK generation.
    Handles responsive design, offline capabilities, and mobile-specific features.
    """

    @staticmethod
    def generate_pwa_manifest() -> Dict[str, Any]:
        """Generate Progressive Web App manifest for mobile installation"""
        return {
            "name": "Stock Evaluator - Investment Analysis Tool",
            "short_name": "StockEval",
            "description": "Professional stock evaluation tool with AI-powered analysis",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#f8f9fa",
            "theme_color": "#007bff",
            "orientation": "portrait-primary",
            "categories": ["finance", "business", "productivity"],
            "lang": "en",
            "icons": [
                {
                    "src": "/static/icons/icon-72x72.png",
                    "sizes": "72x72",
                    "type": "image/png",
                    "purpose": "maskable any",
                },
                {
                    "src": "/static/icons/icon-96x96.png",
                    "sizes": "96x96",
                    "type": "image/png",
                    "purpose": "maskable any",
                },
                {
                    "src": "/static/icons/icon-128x128.png",
                    "sizes": "128x128",
                    "type": "image/png",
                    "purpose": "maskable any",
                },
                {
                    "src": "/static/icons/icon-144x144.png",
                    "sizes": "144x144",
                    "type": "image/png",
                    "purpose": "maskable any",
                },
                {
                    "src": "/static/icons/icon-152x152.png",
                    "sizes": "152x152",
                    "type": "image/png",
                    "purpose": "maskable any",
                },
                {
                    "src": "/static/icons/icon-192x192.png",
                    "sizes": "192x192",
                    "type": "image/png",
                    "purpose": "maskable any",
                },
                {
                    "src": "/static/icons/icon-384x384.png",
                    "sizes": "384x384",
                    "type": "image/png",
                    "purpose": "maskable any",
                },
                {
                    "src": "/static/icons/icon-512x512.png",
                    "sizes": "512x512",
                    "type": "image/png",
                    "purpose": "maskable any",
                },
            ],
            "screenshots": [
                {
                    "src": "/static/screenshots/desktop.png",
                    "sizes": "1280x720",
                    "type": "image/png",
                    "form_factor": "wide",
                },
                {
                    "src": "/static/screenshots/mobile.png",
                    "sizes": "375x667",
                    "type": "image/png",
                    "form_factor": "narrow",
                },
            ],
        }

    @staticmethod
    def generate_service_worker() -> str:
        """Generate service worker for offline functionality"""
        return """
// Stock Evaluator Service Worker
// Provides offline functionality and caching

const CACHE_NAME = 'stock-evaluator-v1.0.0';
const STATIC_CACHE_URLS = [
    '/',
    '/static/flowchart.js',
    '/static/icons/icon-192x192.png',
    'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js'
];

// Install event - cache static resources
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Service Worker: Caching static files');
                return cache.addAll(STATIC_CACHE_URLS);
            })
            .then(() => {
                console.log('Service Worker: Installation complete');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('Service Worker: Installation failed', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Service Worker: Deleting old cache', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            console.log('Service Worker: Activation complete');
            return self.clients.claim();
        })
    );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', event => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }
    
    // Skip external API calls (let them fail gracefully)
    if (event.request.url.includes('yfinance') || 
        event.request.url.includes('googleapis') ||
        event.request.url.includes('generativeai')) {
        return;
    }
    
    event.respondWith(
        caches.match(event.request)
            .then(cachedResponse => {
                // Return cached version if available
                if (cachedResponse) {
                    console.log('Service Worker: Serving from cache', event.request.url);
                    return cachedResponse;
                }
                
                // Otherwise fetch from network
                return fetch(event.request)
                    .then(response => {
                        // Don't cache non-successful responses
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }
                        
                        // Clone the response for caching
                        const responseToCache = response.clone();
                        
                        caches.open(CACHE_NAME)
                            .then(cache => {
                                cache.put(event.request, responseToCache);
                            });
                        
                        return response;
                    })
                    .catch(error => {
                        console.log('Service Worker: Network request failed', error);
                        
                        // Return offline page for navigation requests
                        if (event.request.destination === 'document') {
                            return caches.match('/offline.html');
                        }
                        
                        throw error;
                    });
            })
    );
});

// Background sync for offline form submissions
self.addEventListener('sync', event => {
    if (event.tag === 'stock-evaluation') {
        console.log('Service Worker: Background sync triggered');
        event.waitUntil(
            // Handle offline stock evaluations when connection is restored
            handleOfflineEvaluations()
        );
    }
});

async function handleOfflineEvaluations() {
    // Implementation for handling queued evaluations
    console.log('Service Worker: Processing offline evaluations');
    // This would integrate with IndexedDB to store/retrieve offline requests
}

// Push notifications (for future features)
self.addEventListener('push', event => {
    if (event.data) {
        const data = event.data.json();
        const options = {
            body: data.body,
            icon: '/static/icons/icon-192x192.png',
            badge: '/static/icons/icon-72x72.png',
            vibrate: [200, 100, 200],
            data: data.data,
            actions: [
                {
                    action: 'view',
                    title: 'View Details',
                    icon: '/static/icons/view.png'
                },
                {
                    action: 'dismiss',
                    title: 'Dismiss',
                    icon: '/static/icons/dismiss.png'
                }
            ]
        };
        
        event.waitUntil(
            self.registration.showNotification(data.title, options)
        );
    }
});
"""

    @staticmethod
    def generate_cordova_config() -> str:
        """Generate Cordova config.xml for APK generation"""
        return """<?xml version='1.0' encoding='utf-8'?>
<widget id="com.brunodias.stockevaluator" version="1.0.0" xmlns="http://www.w3.org/ns/widgets" xmlns:cdv="http://cordova.apache.org/ns/1.0">
    <name>Stock Evaluator</name>
    <description>
        Professional stock evaluation tool with AI-powered analysis and flowchart visualization.
    </description>
    <author email="bruno@example.com" href="https://www.linkedin.com/in/brunosimaodias">
        Bruno Dias
    </author>
    <content src="index.html" />
    <access origin="*" />
    <allow-intent href="http://*/*" />
    <allow-intent href="https://*/*" />
    <allow-intent href="tel:*" />
    <allow-intent href="sms:*" />
    <allow-intent href="mailto:*" />
    <allow-intent href="geo:*" />
    
    <!-- Android Configuration -->
    <platform name="android">
        <allow-intent href="market:*" />
        <icon density="ldpi" src="www/res/icon/android/drawable-ldpi-icon.png" />
        <icon density="mdpi" src="www/res/icon/android/drawable-mdpi-icon.png" />
        <icon density="hdpi" src="www/res/icon/android/drawable-hdpi-icon.png" />
        <icon density="xhdpi" src="www/res/icon/android/drawable-xhdpi-icon.png" />
        <icon density="xxhdpi" src="www/res/icon/android/drawable-xxhdpi-icon.png" />
        <icon density="xxxhdpi" src="www/res/icon/android/drawable-xxxhdpi-icon.png" />
        <splash density="land-ldpi" src="www/res/screen/android/drawable-land-ldpi-screen.png" />
        <splash density="land-mdpi" src="www/res/screen/android/drawable-land-mdpi-screen.png" />
        <splash density="land-hdpi" src="www/res/screen/android/drawable-land-hdpi-screen.png" />
        <splash density="land-xhdpi" src="www/res/screen/android/drawable-land-xhdpi-screen.png" />
        <splash density="land-xxhdpi" src="www/res/screen/android/drawable-land-xxhdpi-screen.png" />
        <splash density="land-xxxhdpi" src="www/res/screen/android/drawable-land-xxxhdpi-screen.png" />
        <splash density="port-ldpi" src="www/res/screen/android/drawable-port-ldpi-screen.png" />
        <splash density="port-mdpi" src="www/res/screen/android/drawable-port-mdpi-screen.png" />
        <splash density="port-hdpi" src="www/res/screen/android/drawable-port-hdpi-screen.png" />
        <splash density="port-xhdpi" src="www/res/screen/android/drawable-port-xhdpi-screen.png" />
        <splash density="port-xxhdpi" src="www/res/screen/android/drawable-port-xxhdpi-screen.png" />
        <splash density="port-xxxhdpi" src="www/res/screen/android/drawable-port-xxxhdpi-screen.png" />
        
        <!-- Android Permissions -->
        <uses-permission android:name="android.permission.INTERNET" />
        <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
        <uses-permission android:name="android.permission.VIBRATE" />
        
        <!-- Android Preferences -->
        <preference name="android-minSdkVersion" value="22" />
        <preference name="android-targetSdkVersion" value="33" />
        <preference name="AndroidLaunchMode" value="singleTop" />
        <preference name="AndroidPersistentFileLocation" value="Compatibility" />
    </platform>
    
    <!-- Global Preferences -->
    <preference name="DisallowOverscroll" value="true" />
    <preference name="BackgroundColor" value="0xfff8f9fa" />
    <preference name="HideKeyboardFormAccessoryBar" value="true" />
    <preference name="Orientation" value="portrait" />
    <preference name="Fullscreen" value="false" />
    <preference name="StatusBarOverlaysWebView" value="false" />
    <preference name="StatusBarBackgroundColor" value="#007bff" />
    <preference name="StatusBarStyle" value="lightcontent" />
    
    <!-- Plugins -->
    <plugin name="cordova-plugin-whitelist" spec="1" />
    <plugin name="cordova-plugin-statusbar" spec="2" />
    <plugin name="cordova-plugin-device" spec="2" />
    <plugin name="cordova-plugin-splashscreen" spec="5" />
    <plugin name="cordova-plugin-network-information" spec="2" />
    <plugin name="cordova-plugin-vibration" spec="3" />
    <plugin name="cordova-plugin-inappbrowser" spec="4" />
</widget>
"""

    @staticmethod
    def create_mobile_deployment_files(base_path: str):
        """Create all necessary files for mobile deployment"""

        # Create directories
        static_dir = os.path.join(base_path, "static")
        icons_dir = os.path.join(static_dir, "icons")
        os.makedirs(icons_dir, exist_ok=True)

        # Generate PWA manifest
        manifest_path = os.path.join(static_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(MobileConfig.generate_pwa_manifest(), f, indent=2)

        # Generate service worker
        sw_path = os.path.join(static_dir, "sw.js")
        with open(sw_path, "w") as f:
            f.write(MobileConfig.generate_service_worker())

        # Generate Cordova config
        config_path = os.path.join(base_path, "config.xml")
        with open(config_path, "w") as f:
            f.write(MobileConfig.generate_cordova_config())

        print(f"Mobile deployment files created in {base_path}")
        print("Files created:")
        print(f"  - {manifest_path}")
        print(f"  - {sw_path}")
        print(f"  - {config_path}")

        return {
            "manifest": manifest_path,
            "service_worker": sw_path,
            "cordova_config": config_path,
        }


if __name__ == "__main__":
    # Create mobile deployment files
    base_path = os.path.dirname(__file__)
    MobileConfig.create_mobile_deployment_files(base_path)
