from flask import Flask, request, Response, render_template_string, stream_with_context
import base64
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import re
import os

app = Flask(__name__)

# HTML Player Template
PLAYER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>M3U8 AES Player</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
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
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 1000px;
            width: 100%;
            padding: 30px;
        }
        h1 {
            text-align: center;
            color: #667eea;
            margin-bottom: 30px;
            font-size: 2.5em;
        }
        .input-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
        }
        input[type="text"] {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: border 0.3s;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .btn:hover {
            transform: translateY(-2px);
        }
        .btn:active {
            transform: translateY(0);
        }
        #videoContainer {
            display: none;
            margin-top: 30px;
        }
        video {
            width: 100%;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .info {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            display: none;
        }
        .info p {
            margin: 5px 0;
            color: #666;
        }
        .loading {
            display: none;
            text-align: center;
            margin-top: 20px;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .error {
            background: #fee;
            color: #c33;
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 M3U8 AES Player</h1>
        
        <div class="input-group">
            <label for="urlInput">📎 Enter M3U8 URL with Key (format: url.m3u8#base64key)</label>
            <input type="text" id="urlInput" placeholder="https://example.com/video.m3u8#N2Y1ODJhYTBiM2QyNGY3OGFhMmM5ZDQ0NjRlOThiNzA=">
        </div>
        
        <button class="btn" onclick="playVideo()">▶️ Play Video</button>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Loading video...</p>
        </div>
        
        <div class="error" id="error"></div>
        
        <div id="videoContainer">
            <video id="video" controls autoplay></video>
        </div>
        
        <div class="info" id="info">
            <p><strong>Status:</strong> <span id="status">Ready</span></p>
            <p><strong>Encryption:</strong> <span id="encryption">AES-128-CBC</span></p>
        </div>
    </div>

    <script>
        function playVideo() {
            const input = document.getElementById('urlInput').value.trim();
            const loading = document.getElementById('loading');
            const error = document.getElementById('error');
            const videoContainer = document.getElementById('videoContainer');
            const info = document.getElementById('info');
            const video = document.getElementById('video');
            
            // Reset
            error.style.display = 'none';
            videoContainer.style.display = 'none';
            info.style.display = 'none';
            
            if (!input || !input.includes('#')) {
                error.textContent = '❌ Invalid URL format. Must be: url.m3u8#base64key';
                error.style.display = 'block';
                return;
            }
            
            loading.style.display = 'block';
            
            // Encode the full URL
            const encodedUrl = encodeURIComponent(input);
            const proxyUrl = `/proxy?url=${encodedUrl}`;
            
            // Use HLS.js for playback
            if (Hls.isSupported()) {
                const hls = new Hls({
                    xhrSetup: function(xhr, url) {
                        // Add headers if needed
                        xhr.setRequestHeader('User-Agent', 'Mozilla/5.0');
                    }
                });
                
                hls.loadSource(proxyUrl);
                hls.attachMedia(video);
                
                hls.on(Hls.Events.MANIFEST_PARSED, function() {
                    loading.style.display = 'none';
                    videoContainer.style.display = 'block';
                    info.style.display = 'block';
                    document.getElementById('status').textContent = '✅ Playing';
                    video.play();
                });
                
                hls.on(Hls.Events.ERROR, function(event, data) {
                    loading.style.display = 'none';
                    error.textContent = '❌ Error: ' + data.type + ' - ' + data.details;
                    error.style.display = 'block';
                });
                
            } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
                // Native HLS support (Safari)
                video.src = proxyUrl;
                video.addEventListener('loadedmetadata', function() {
                    loading.style.display = 'none';
                    videoContainer.style.display = 'block';
                    info.style.display = 'block';
                    document.getElementById('status').textContent = '✅ Playing';
                });
                
                video.addEventListener('error', function() {
                    loading.style.display = 'none';
                    error.textContent = '❌ Error loading video';
                    error.style.display = 'block';
                });
            }
        }
    </script>
</body>
</html>
"""

def decrypt_segment(data, key):
    """Decrypt AES-CBC encrypted data"""
    try:
        cipher = AES.new(key, AES.MODE_CBC, b'\x00' * 16)
        decrypted = cipher.decrypt(data)
        # Try to unpad, if fails return as-is
        try:
            return unpad(decrypted, AES.block_size)
        except:
            return decrypted
    except Exception as e:
        print(f"Decryption error: {e}")
        return data

@app.route('/')
def index():
    """Serve the player page"""
    return render_template_string(PLAYER_HTML)

@app.route('/proxy')
def proxy():
    """Proxy and decrypt M3U8 content on-the-fly"""
    full_url = request.args.get('url')
    
    if not full_url or '#' not in full_url:
        return "Invalid URL format", 400
    
    try:
        # Split URL and key
        m3u8_url, key_b64 = full_url.split('#', 1)
        
        # Decode key
        key_hex = base64.b64decode(key_b64).decode()
        key = bytes.fromhex(key_hex)
        
        print(f"🔗 M3U8 URL: {m3u8_url}")
        print(f"🔑 Key: {key_hex}")
        
        # Fetch M3U8 content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://shankariasoptional.testpress.in/',
            'Origin': 'https://shankariasoptional.testpress.in',
            'Accept': '*/*'
        }
        
        resp = requests.get(m3u8_url, headers=headers)
        
        if resp.status_code != 200:
            return f"Failed to fetch M3U8: {resp.status_code}", 400
        
        m3u8_content = resp.text
        print(f"📄 M3U8 Content Length: {len(m3u8_content)}")
        
        # Parse and modify M3U8
        base_url = m3u8_url.rsplit('/', 1)[0] + '/'
        modified_m3u8 = []
        
        for line in m3u8_content.split('\n'):
            line = line.strip()
            
            # If it's a segment URL, proxy it
            if line and not line.startswith('#'):
                if line.startswith('http'):
                    segment_url = line
                else:
                    segment_url = base_url + line
                
                # Create proxy URL for segment
                proxy_segment = f"/segment?url={requests.utils.quote(segment_url)}&key={key_b64}"
                modified_m3u8.append(proxy_segment)
            else:
                # Keep comments and tags as-is (but remove encryption tags)
                if not line.startswith('#EXT-X-KEY'):
                    modified_m3u8.append(line)
        
        final_m3u8 = '\n'.join(modified_m3u8)
        
        return Response(final_m3u8, mimetype='application/vnd.apple.mpegurl')
        
    except Exception as e:
        print(f"❌ Proxy error: {e}")
        return f"Error: {str(e)}", 500

@app.route('/segment')
def segment():
    """Fetch and decrypt video segment"""
    segment_url = request.args.get('url')
    key_b64 = request.args.get('key')
    
    if not segment_url or not key_b64:
        return "Missing parameters", 400
    
    try:
        # Decode key
        key_hex = base64.b64decode(key_b64).decode()
        key = bytes.fromhex(key_hex)
        
        # Fetch encrypted segment
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://shankariasoptional.testpress.in/',
            'Origin': 'https://shankariasoptional.testpress.in'
        }
        
        resp = requests.get(segment_url, headers=headers)
        
        if resp.status_code != 200:
            print(f"❌ Segment fetch failed: {resp.status_code}")
            return f"Segment fetch failed: {resp.status_code}", 400
        
        encrypted_data = resp.content
        
        # Decrypt
        decrypted_data = decrypt_segment(encrypted_data, key)
        
        print(f"✅ Segment decrypted: {len(decrypted_data)} bytes")
        
        return Response(decrypted_data, mimetype='video/mp2t')
        
    except Exception as e:
        print(f"❌ Segment error: {e}")
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))  # Heroku assigns a PORT; fallback to 5000 for local
    print("🚀 Starting M3U8 AES Player API...")
    print(f"📺 Open: http://localhost:{port}")
    app.run(debug=True, host='0.0.0.0', port=port)
