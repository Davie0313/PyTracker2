import json
import os
import random
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime
import threading
import socket
import urllib.request

# Get local IP address
def get_local_ip():
    """Get the local IP address of the machine"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_ngrok_url():
    """Get the public ngrok URL if ngrok is running"""
    try:
        response = urllib.request.urlopen('http://localhost:4040/api/tunnels', timeout=2)
        data = json.loads(response.read().decode())
        for tunnel in data.get('tunnels', []):
            if tunnel.get('proto') == 'http':
                return tunnel.get('public_url')
    except:
        pass
    return None

def get_public_url():
    """Get the public URL for the server"""
    # Check environment variable first
    env_url = os.environ.get('SHORTENER_PUBLIC_URL')
    if env_url:
        return env_url.rstrip('/')
    
    # Try to get ngrok URL
    ngrok_url = get_ngrok_url()
    if ngrok_url:
        return ngrok_url.rstrip('/')
    
    # Fallback to local IP
    return f"http://{LOCAL_IP}:{SERVER_PORT}"

def get_geolocation(ip_address):
    """Get geolocation data based on IP address"""
    try:
        # Use ip-api.com free tier (educational purposes)
        url = f"http://ip-api.com/json/{ip_address}?fields=status,country,regionName,city,lat,lon,isp"
        response = urllib.request.urlopen(url, timeout=2)
        data = json.loads(response.read().decode())
        
        if data.get('status') == 'success':
            return {
                'country': data.get('country', 'Unknown'),
                'region': data.get('regionName', 'Unknown'),
                'city': data.get('city', 'Unknown'),
                'latitude': data.get('lat'),
                'longitude': data.get('lon'),
                'isp': data.get('isp', 'Unknown')
            }
    except:
        pass
    
    return None

LOCAL_IP = get_local_ip()
SERVER_PORT = 8001
PUBLIC_URL = None  # Will be set after server starts

# File to store URL mappings
URLS_FILE = 'shortened_urls.json'

# Word lists for generating random short names
ADJECTIVES = [
    'happy', 'quick', 'lazy', 'bright', 'calm', 'bold', 'cool', 'fast',
    'gentle', 'quiet', 'sharp', 'smooth', 'strong', 'swift', 'warm', 'wise',
    'ancient', 'clever', 'eager', 'fierce', 'golden', 'grand', 'jolly', 'keen'
]

NOUNS = [
    'cat', 'dog', 'bird', 'fish', 'lion', 'tiger', 'eagle', 'wolf',
    'bear', 'fox', 'deer', 'horse', 'snake', 'dragon', 'phoenix', 'whale',
    'mountain', 'river', 'forest', 'ocean', 'storm', 'flame', 'shadow', 'star'
]

class URLShortener:
    def __init__(self, filename=URLS_FILE):
        self.filename = filename
        self.urls = self.load_urls()
    
    def load_urls(self):
        """Load URL mappings from file"""
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                return json.load(f)
        return {}
    
    def save_urls(self):
        """Save URL mappings to file"""
        with open(self.filename, 'w') as f:
            json.dump(self.urls, f, indent=2)
    
    def generate_short_code(self):
        """Generate a random short code using adjective + noun"""
        adjective = random.choice(ADJECTIVES)
        noun = random.choice(NOUNS)
        code = f"{adjective}-{noun}"
        
        # If code already exists, regenerate
        while code in self.urls:
            adjective = random.choice(ADJECTIVES)
            noun = random.choice(NOUNS)
            code = f"{adjective}-{noun}"
        
        return code
    
    def shorten(self, original_url):
        """Shorten a URL and return the short code"""
        # Check if URL already exists
        for code, data in self.urls.items():
            if data['original_url'] == original_url:
                return code
        
        # Generate new short code
        short_code = self.generate_short_code()
        
        # Store the mapping
        self.urls[short_code] = {
            'original_url': original_url,
            'created_at': datetime.now().isoformat(),
            'clicks': []
        }
        
        self.save_urls()
        return short_code
    
    def expand(self, short_code, user_agent='Unknown', user_ip='Unknown'):
        """Expand a short code back to the original URL and record click"""
        if short_code in self.urls:
            # Convert old format (integer clicks) to new format (list of click records)
            if isinstance(self.urls[short_code]['clicks'], int):
                self.urls[short_code]['clicks'] = []
            
            # Parse user agent to get device info
            device_info = self.parse_user_agent(user_agent)
            
            # Get geolocation data
            location_info = get_geolocation(user_ip)
            
            # Record the click with timestamp, device info, IP, and location
            click_record = {
                'timestamp': datetime.now().isoformat(),
                'device': device_info,
                'ip': user_ip,
                'location': location_info
            }
            
            self.urls[short_code]['clicks'].append(click_record)
            self.save_urls()
            return self.urls[short_code]['original_url']
        return None
    
    def parse_user_agent(self, user_agent):
        """Extract device information from user agent"""
        ua_lower = user_agent.lower()
        
        # Detect OS
        if 'windows' in ua_lower:
            os_name = 'Windows'
        elif 'mac' in ua_lower:
            os_name = 'macOS'
        elif 'linux' in ua_lower:
            os_name = 'Linux'
        elif 'iphone' in ua_lower:
            os_name = 'iOS'
        elif 'android' in ua_lower:
            os_name = 'Android'
        else:
            os_name = 'Unknown'
        
        # Detect browser
        if 'chrome' in ua_lower:
            browser = 'Chrome'
        elif 'firefox' in ua_lower:
            browser = 'Firefox'
        elif 'safari' in ua_lower:
            browser = 'Safari'
        elif 'edge' in ua_lower:
            browser = 'Edge'
        else:
            browser = 'Other'
        
        # Detect device type
        if 'mobile' in ua_lower or 'android' in ua_lower or 'iphone' in ua_lower:
            device_type = 'Mobile'
        elif 'tablet' in ua_lower or 'ipad' in ua_lower:
            device_type = 'Tablet'
        else:
            device_type = 'Desktop'
        
        return {
            'os': os_name,
            'browser': browser,
            'type': device_type
        }
    
    def get_stats(self, short_code):
        """Get statistics for a shortened URL"""
        if short_code in self.urls:
            return self.urls[short_code]
        return None
    
    def list_all(self):
        """List all shortened URLs"""
        return self.urls
    
    def delete(self, short_code):
        """Delete a shortened URL"""
        if short_code in self.urls:
            del self.urls[short_code]
            self.save_urls()
            return True
        return False


shortener = URLShortener()

class URLShortenerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path
        
        # Check if it's a redirect request (e.g., /r/happy-tiger)
        if path.startswith('/r/'):
            short_code = path[3:]  # Remove '/r/' prefix
            user_agent = self.headers.get('User-Agent', 'Unknown')
            
            # Get user's IP address
            # Check for X-Forwarded-For header first (for proxies), then use remote address
            user_ip = self.headers.get('X-Forwarded-For', self.client_address[0])
            if ',' in user_ip:
                # If multiple IPs, take the first one
                user_ip = user_ip.split(',')[0].strip()
            
            original_url = shortener.expand(short_code, user_agent, user_ip)
            
            if original_url:
                # Check if it's a YouTube link
                if 'youtube.com' in original_url or 'youtu.be' in original_url:
                    # Show popup for YouTube links
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    
                    html = f'''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Redirecting...</title>
                        <style>
                            * {{
                                margin: 0;
                                padding: 0;
                                box-sizing: border-box;
                            }}
                            body {{
                                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                background: #f0f0f0;
                                display: flex;
                                justify-content: center;
                                align-items: center;
                                min-height: 100vh;
                            }}
                            .overlay {{
                                position: fixed;
                                top: 0;
                                left: 0;
                                right: 0;
                                bottom: 0;
                                background: rgba(0, 0, 0, 0.5);
                                display: flex;
                                justify-content: center;
                                align-items: center;
                                z-index: 1000;
                            }}
                            .popup {{
                                background: white;
                                border-radius: 12px;
                                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
                                padding: 40px;
                                text-align: center;
                                min-width: 300px;
                                animation: slideIn 0.3s ease-out;
                            }}
                            @keyframes slideIn {{
                                from {{
                                    transform: translateY(-20px);
                                    opacity: 0;
                                }}
                                to {{
                                    transform: translateY(0);
                                    opacity: 1;
                                }}
                            }}
                            .popup h2 {{
                                color: #333;
                                margin-bottom: 20px;
                                font-size: 24px;
                            }}
                            .popup button {{
                                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                color: white;
                                border: none;
                                padding: 12px 30px;
                                border-radius: 6px;
                                font-size: 14px;
                                font-weight: 600;
                                cursor: pointer;
                                transition: transform 0.2s, box-shadow 0.2s;
                            }}
                            .popup button:hover {{
                                transform: translateY(-2px);
                                box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="overlay">
                            <div class="popup">
                                <h2>Please turn on your location as of the new Youtube Guidelines. <br> This is to ensure no person uses a VPN to hide their age and/or view restricted content.</h2>
                                <button onclick="redirectToURL()">Okay</button>
                            </div>
                        </div>
                        <script>
                            function redirectToURL() {{
                                window.location.href = '{original_url}';
                            }}
                        </script>
                    </body>
                    </html>
                    '''
                    self.wfile.write(html.encode())
                else:
                    # Direct redirect for non-YouTube links
                    self.send_response(302)
                    self.send_header('Location', original_url)
                    self.end_headers()
            else:
                # Short code not found
                self.send_response(404)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<h1>404 - Short code not found</h1>')
        
        elif path == '/':
            # Main page
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html_content.encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        try:
            if self.path == '/api/shorten':
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode()
                data = parse_qs(body)
                
                url = data.get('url', [''])[0]
                
                if url:
                    short_code = shortener.shorten(url)
                    short_url = f"{PUBLIC_URL}/r/{short_code}"
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'success': True,
                        'short_code': short_code,
                        'short_url': short_url,
                        'original_url': url
                    }).encode())
                else:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': False, 'message': 'URL is required'}).encode())
            
            elif self.path == '/api/list':
                urls = shortener.list_all()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(urls).encode())
            
            elif self.path == '/api/delete':
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode()
                data = parse_qs(body)
                
                short_code = data.get('code', [''])[0]
                
                if shortener.delete(short_code):
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': True}).encode())
                else:
                    self.send_response(404)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'success': False, 'message': 'Short code not found'}).encode())
            
            else:
                self.send_response(404)
                self.end_headers()
        
        except Exception as e:
            print(f"[ERROR] {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'message': 'Internal server error'}).encode())
    
    def log_message(self, format, *args):
        pass  # Suppress logging

html_content = '''
<!DOCTYPE html>
<html>
<head>
    <title>URL Shortener</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            padding: 40px;
            max-width: 700px;
            width: 100%;
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }
        input[type="url"], input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        input[type="url"]:focus, input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .message {
            margin-top: 15px;
            padding: 12px;
            border-radius: 6px;
            display: none;
        }
        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            display: block;
        }
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            display: block;
        }
        .result {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin-top: 20px;
            display: none;
        }
        .result.show {
            display: block;
        }
        .result-row {
            margin-bottom: 10px;
        }
        .result-label {
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
        }
        .short-url {
            font-size: 16px;
            font-weight: 600;
            color: #667eea;
            word-break: break-all;
        }
        .short-url a {
            color: #667eea;
            text-decoration: none;
        }
        .short-url a:hover {
            text-decoration: underline;
        }
        .copy-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            margin-top: 10px;
            transition: background 0.3s;
        }
        .copy-btn:hover {
            background: #764ba2;
        }
        .copy-btn.copied {
            background: #28a745;
        }
        .urls-list {
            margin-top: 40px;
            padding-top: 30px;
            border-top: 2px solid #e0e0e0;
        }
        .urls-list h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 20px;
        }
        .url-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .url-info {
            flex: 1;
        }
        .url-code {
            color: #667eea;
            font-weight: 600;
            margin-bottom: 5px;
        }
        .url-original {
            color: #666;
            font-size: 12px;
            word-break: break-all;
        }
        .url-clicks {
            color: #999;
            font-size: 12px;
            margin-top: 5px;
        }
        .url-link {
            margin: 0 15px;
        }
        .url-link a {
            color: #667eea;
            text-decoration: none;
            font-size: 12px;
        }
        .url-link a:hover {
            text-decoration: underline;
        }
        .delete-btn {
            background: #dc3545;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            transition: background 0.3s;
        }
        .delete-btn:hover {
            background: #c82333;
        }
        .empty-message {
            text-align: center;
            color: #999;
            padding: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 URL Shortener</h1>
        <p class="subtitle">Shorten any URL to a memorable word combination</p>
        
        <form id="shortenForm">
            <div class="form-group">
                <label for="urlInput">Enter URL to shorten</label>
                <input type="url" id="urlInput" name="url" placeholder="https://example.com/very/long/url" required>
            </div>
            <button type="submit">Shorten URL</button>
        </form>
        
        <div id="message" class="message"></div>
        
        <div id="result" class="result">
            <div class="result-row">
                <div class="result-label">Shortened Link</div>
                <div class="short-url">
                    <a id="shortLink" href="" target="_blank"></a>
                </div>
                <div style="display: flex; gap: 10px; margin-top: 10px;">
                    <button class="copy-btn" id="copyBtn">📋 Copy Link</button>
                    <button class="copy-btn" id="shareBtn" style="background: #28a745;">📤 Share</button>
                </div>
            </div>
            <div class="result-row">
                <div class="result-label">Original URL</div>
                <div id="originalUrl" style="color: #333; word-break: break-all; margin-top: 5px;"></div>
            </div>
        </div>
        
        <div class="urls-list">
            <h2>Your Shortened URLs</h2>
            <div id="urlsList"></div>
        </div>
    </div>

    <script>
        const form = document.getElementById('shortenForm');
        const urlInput = document.getElementById('urlInput');
        const messageDiv = document.getElementById('message');
        const resultDiv = document.getElementById('result');
        const shortLinkElement = document.getElementById('shortLink');
        const originalUrlDiv = document.getElementById('originalUrl');
        const copyBtn = document.getElementById('copyBtn');
        const shareBtn = document.getElementById('shareBtn');
        const urlsListDiv = document.getElementById('urlsList');
        
        let currentShortUrl = '';

        // Share functionality
        async function shareLink() {
            const text = `Check out this shortened URL: ${currentShortUrl}`;
            
            if (navigator.share) {
                // Use Web Share API if available (mobile devices)
                try {
                    await navigator.share({
                        title: 'Shortened URL',
                        text: text,
                        url: currentShortUrl
                    });
                } catch (err) {
                    if (err.name !== 'AbortError') {
                        console.error('Error sharing:', err);
                    }
                }
            } else {
                // Fallback: copy to clipboard and show message
                navigator.clipboard.writeText(text).then(() => {
                    shareBtn.textContent = '✓ Copied to clipboard!';
                    shareBtn.style.background = '#28a745';
                    setTimeout(() => {
                        shareBtn.textContent = '📤 Share';
                        shareBtn.style.background = '#28a745';
                    }, 2000);
                });
            }
        }
        
        shareBtn.addEventListener('click', shareLink);

        // Load and display all URLs
        function loadURLs() {
            fetch('/api/list', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (Object.keys(data).length > 0) {
                        let html = '';
                        for (const [code, info] of Object.entries(data)) {
                            const shortUrl = `http://${window.location.hostname}:${window.location.port}/r/${code}`;
                            const clickCount = Array.isArray(info.clicks) ? info.clicks.length : 0;
                            
                            let clicksHtml = '';
                            if (clickCount > 0) {
                                clicksHtml = '<div style="margin-top: 10px; font-size: 11px; color: #666; border-top: 1px solid #ddd; padding-top: 10px;">';
                                info.clicks.forEach((click, index) => {
                                    const date = new Date(click.timestamp);
                                    const timeStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                                    clicksHtml += `<div style="margin-bottom: 6px;"><strong>Click ${index + 1}:</strong> ${timeStr}</div>`;
                                    clicksHtml += `<div style="margin-left: 10px; color: #999;">Device: ${click.device.type} • ${click.device.os} • ${click.device.browser}</div>`;
                                    clicksHtml += `<div style="margin-left: 10px; color: #999;">IP: ${click.ip}</div>`;
                                    
                                    // Display location info if available
                                    if (click.location) {
                                        const location = click.location;
                                        const city = location.city !== 'Unknown' ? location.city : '';
                                        const region = location.region !== 'Unknown' ? location.region : '';
                                        const country = location.country || 'Unknown';
                                        const locationStr = [city, region, country].filter(Boolean).join(', ');
                                        const coords = location.latitude && location.longitude ? ` (${location.latitude.toFixed(2)}, ${location.longitude.toFixed(2)})` : '';
                                        clicksHtml += `<div style="margin-left: 10px; color: #999;">Location: ${locationStr}${coords}</div>`;
                                        if (location.isp) {
                                            clicksHtml += `<div style="margin-left: 10px; color: #999;">ISP: ${location.isp}</div>`;
                                        }
                                    }
                                });
                                clicksHtml += '</div>';
                            }
                            
                            html += `
                                <div class="url-item">
                                    <div class="url-info" style="flex: 1;">
                                        <div class="url-code">${code}</div>
                                        <div class="url-original">${info.original_url}</div>
                                        <div class="url-clicks">Total Clicks: ${clickCount}</div>
                                        ${clicksHtml}
                                    </div>
                                    <div class="url-link">
                                        <a href="${shortUrl}" target="_blank">Visit</a>
                                    </div>
                                    <button class="delete-btn" onclick="deleteURL('${code}')">Delete</button>
                                </div>
                            `;
                        }
                        urlsListDiv.innerHTML = html;
                    } else {
                        urlsListDiv.innerHTML = '<div class="empty-message">No shortened URLs yet. Create one above!</div>';
                    }
                })
                .catch(error => console.error('Error:', error));
        }

        // Delete URL
        function deleteURL(code) {
            if (confirm(`Delete ${code}?`)) {
                fetch('/api/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: 'code=' + encodeURIComponent(code)
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        loadURLs();
                    }
                });
            }
        }

        // Handle form submission
        form.addEventListener('submit', function(e) {
            e.preventDefault();

            const url = urlInput.value;

            fetch('/api/shorten', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: 'url=' + encodeURIComponent(url)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    currentShortUrl = data.short_url;
                    shortLinkElement.href = data.short_url;
                    shortLinkElement.textContent = data.short_url;
                    originalUrlDiv.textContent = data.original_url;
                    resultDiv.classList.add('show');
                    messageDiv.style.display = 'none';
                    urlInput.value = '';
                    loadURLs();
                } else {
                    showMessage('Error: ' + (data.message || 'Failed to shorten URL'), 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showMessage('An error occurred', 'error');
            });
        });

        // Copy to clipboard
        copyBtn.addEventListener('click', function() {
            const text = shortLinkElement.textContent;
            navigator.clipboard.writeText(text).then(() => {
                copyBtn.textContent = 'Copied!';
                copyBtn.classList.add('copied');
                setTimeout(() => {
                    copyBtn.textContent = 'Copy Link';
                    copyBtn.classList.remove('copied');
                }, 2000);
            });
        });

        function showMessage(text, type) {
            messageDiv.textContent = text;
            messageDiv.className = `message ${type}`;
            messageDiv.style.display = 'block';
        }

        // Load URLs on page load
        window.addEventListener('load', loadURLs);
    </script>
</body>
</html>
'''

def main():
    global PUBLIC_URL
    
    try:
        server = HTTPServer(('0.0.0.0', SERVER_PORT), URLShortenerHandler)
    except Exception as e:
        print(f"[ERROR] Failed to bind server: {e}")
        return
    
    # Set the public URL
    PUBLIC_URL = get_public_url()
    
    print("=" * 70)
    print("URL Shortener - Multi-Network Edition")
    print("=" * 70)
    print(f"Local access:        http://localhost:{SERVER_PORT}")
    print(f"Network access:      http://{LOCAL_IP}:{SERVER_PORT}")
    print(f"Public URL for links: {PUBLIC_URL}")
    print(f"Mappings stored in:  {URLS_FILE}")
    print("=" * 70)
    print("\nSHARING LINKS:")
    print(f"   Share this URL with anyone: {PUBLIC_URL}")
    print("\nTO USE WITH NGROK (cross-network access):")
    print("   1. Download and install ngrok from https://ngrok.com")
    print("   2. Run: ngrok http 8001")
    print("   3. ngrok will provide a public URL - shortened links will use it!")
    print("\nOR set a custom public URL:")
    print("   Set SHORTENER_PUBLIC_URL environment variable:")
    print("   set SHORTENER_PUBLIC_URL=http://your-public-ip:8001")
    print("=" * 70 + "\n")
    
    # Don't open browser in server environment
    # webbrowser.open(f'http://localhost:{SERVER_PORT}')
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    except Exception as e:
        print(f"[ERROR] Server error: {e}")

if __name__ == '__main__':
    main()
