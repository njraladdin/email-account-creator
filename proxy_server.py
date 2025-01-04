from flask import Flask, request, Response
import requests
import socket
import logging
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        logger.error(f"Error getting local IP: {e}")
        return socket.gethostbyname(socket.gethostname())

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'CONNECT'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'CONNECT'])
def proxy(path):
    client_ip = request.remote_addr
    method = request.method
    
    logger.debug(f"Raw path: {path}")
    logger.debug(f"Raw request: {request.url}")
    logger.debug(f"Request method: {method}")
    logger.debug(f"Request headers: {dict(request.headers)}")
    
    url = request.environ.get('REQUEST_URI', '')
    if not url and path:
        url = path
    
    logger.debug(f"Using URL: {url}")
    
    if method == 'CONNECT':
        host = urlparse(url).netloc if url else path
        logger.debug(f"CONNECT request for host: {host}")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, 80))
            logger.info(f"Successfully connected to {host}")
            return Response("Connection established", 200)
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return str(e), 500
    
    if not url:
        error_msg = "No URL provided"
        logger.error(error_msg)
        return error_msg, 400
    
    try:
        logger.info(f"Making request to: {url}")
        logger.debug(f"With headers: {dict(request.headers)}")
        
        # Forward the request
        resp = requests.request(
            method=method,
            url=url,
            headers={k: v for k, v in request.headers.items() if k.lower() not in ('host', 'proxy-connection')},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=True,
            stream=True,
            timeout=10
        )
        
        logger.info(f"Response received. Status: {resp.status_code}")
        logger.debug(f"Response headers: {dict(resp.headers)}")
        
        # Get the content and decode if it's JSON
        content = resp.content
        if resp.headers.get('content-type', '').startswith('application/json'):
            try:
                content = content.decode('utf-8')
            except UnicodeDecodeError:
                pass
        
        # Create response with proper headers
        response = Response(
            content,
            status=resp.status_code,
            content_type=resp.headers.get('content-type')
        )
        
        # Copy all headers except those we handle specially
        for k, v in resp.headers.items():
            if k.lower() not in ('content-length', 'transfer-encoding', 'content-encoding'):
                response.headers[k] = v
        
        return response
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Request failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg, 500
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg, 500

if __name__ == '__main__':
    public_ip = requests.get('https://api.ipify.org').text
    local_ip = get_local_ip()
    
    logger.info(f"Local IP: {local_ip}")
    logger.info(f"Public IP: {public_ip}")
    logger.info(f"Starting proxy server on port 8080")
    logger.info("Try testing with: curl -x http://127.0.0.1:8080 http://ipinfo.io")
    
    app.run(host='0.0.0.0', port=8080, debug=True) 