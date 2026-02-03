"""Loading screen route for desktop app."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

LOADING_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backlogia - Loading</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #ffffff;
            overflow: hidden;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .container {
            text-align: center;
            animation: fadeIn 0.5s ease-in;
        }
        
        @keyframes fadeIn {
            from { 
                opacity: 0;
                transform: translateY(20px);
            }
            to { 
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .logo {
            font-size: 3.5rem;
            font-weight: 700;
            margin-bottom: 3rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.02em;
        }
        
        .loader {
            position: relative;
            width: 150px;
            height: 150px;
            margin: 0 auto 3rem;
        }
        
        .loader-circle {
            position: absolute;
            border: 4px solid transparent;
            border-radius: 50%;
            border-top-color: rgba(102, 126, 234, 0.8);
            border-right-color: rgba(102, 126, 234, 0.4);
        }
        
        .loader-circle-outer {
            width: 150px;
            height: 150px;
            animation: spin 1.2s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
        }
        
        .loader-circle-inner {
            width: 100px;
            height: 100px;
            top: 25px;
            left: 25px;
            border-top-color: rgba(118, 75, 162, 0.8);
            border-right-color: rgba(118, 75, 162, 0.4);
            animation: spin 0.8s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite reverse;
        }
        
        @keyframes spin {
            0% { 
                transform: rotate(0deg);
            }
            100% { 
                transform: rotate(360deg);
            }
        }
        
        .message {
            font-size: 1.5rem;
            font-weight: 500;
            opacity: 0.9;
            animation: pulse 2s ease-in-out infinite;
            letter-spacing: 0.02em;
        }
        
        @keyframes pulse {
            0%, 100% { 
                opacity: 0.7;
                transform: scale(1);
            }
            50% { 
                opacity: 1;
                transform: scale(1.02);
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">Backlogia</div>
        <div class="loader">
            <div class="loader-circle loader-circle-outer"></div>
            <div class="loader-circle loader-circle-inner"></div>
        </div>
        <p class="message">Starting Backlogia</p>
    </div>
    
    <script>
        // Check periodically if the server is ready
        let checkCount = 0;
        const maxChecks = 50; // 10 seconds max (50 * 200ms)
        
        function checkServer() {
            fetch('/')
                .then(response => {
                    if (response.ok) {
                        // Server ready, redirect
                        window.location.href = '/';
                    }
                })
                .catch(() => {
                    // Server not ready yet, try again
                    checkCount++;
                    if (checkCount < maxChecks) {
                        setTimeout(checkServer, 200);
                    }
                });
        }
        
        // Start checking after a short delay
        setTimeout(checkServer, 500);
    </script>
</body>
</html>
"""

@router.get("/loading", response_class=HTMLResponse)
async def loading_screen():
    """Serve the loading screen."""
    return LOADING_HTML
