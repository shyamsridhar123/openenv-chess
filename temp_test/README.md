# Azure OpenAI Realtime Audio Test

This is a test client-server application demonstrating real-time speech using Azure OpenAI's Realtime API with WebSocket.

## Setup

1. Make sure your environment variables are set (AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY)

2. Install dependencies (if needed):
   ```bash
   pip install fastapi uvicorn openai websockets
   ```

## Running

1. Start the server:
   ```bash
   cd temp_test
   python server.py
   ```
   The server will run on `http://localhost:8001`

2. Open the client in your browser:
   ```bash
   xdg-open client.html
   ```
   Or simply open `client.html` in your web browser.

3. Type a message and hit Enter or click Send. You should:
   - See the text response in real-time
   - Hear streaming audio from gpt-realtime-mini
   - See the audio transcript

## Features

- Real-time text streaming
- Real-time audio streaming with playback
- Volume control
- Visual wave animation during audio playback
- Automatic reconnection
- Clean, modern UI

## Notes

- The server uses port 8001 to avoid conflicts with your main app on 8000
- Audio is streamed in base64-encoded chunks and played immediately
- The client uses Web Audio API for low-latency audio playback
