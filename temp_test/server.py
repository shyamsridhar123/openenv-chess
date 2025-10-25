import os
import base64
import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from openai import AsyncAzureOpenAI
import uvicorn

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def get_client():
    with open("client.html", "r") as f:
        return f.read()


class RealtimeAudioServer:
    def __init__(self):
        self.deployment = os.getenv("AZURE_OPENAI_AUDIO_DEPLOYMENT_NAME", "gpt-realtime-mini")
        self.client = AsyncAzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version="2024-10-01-preview",
        )
        print(f"Using deployment: {self.deployment}")
    
    async def process_audio_stream(self, websocket: WebSocket, user_message: str):
        """Process user message and stream audio back via WebSocket"""
        try:
            print(f"Connecting to Azure OpenAI with deployment: {self.deployment}")
            async with self.client.beta.realtime.connect(
                model=self.deployment,
            ) as connection:
                print("Connected to realtime API")
                
                # Configure session for audio output
                await connection.session.update(
                    session={"output_modalities": ["text", "audio"]}
                )
                print("Session configured")
                
                # Send user message
                await connection.conversation.item.create(
                    item={
                        "type": "message",
                        "role": "user",
                        "content": [{"type": "input_text", "text": user_message}],
                    }
                )
                print("User message sent")
                
                # Create response
                await connection.response.create()
                print("Response created, streaming events...")
                
                # Stream events back to client
                async for event in connection:
                    print(f"Event: {event.type}")
                    if event.type == "response.text.delta":
                        await websocket.send_json({
                            "type": "text_delta",
                            "content": event.delta
                        })
                    elif event.type == "response.audio.delta":
                        # Send base64 encoded audio data
                        await websocket.send_json({
                            "type": "audio_delta",
                            "content": event.delta  # Already base64 encoded
                        })
                    elif event.type == "response.audio_transcript.delta":
                        await websocket.send_json({
                            "type": "transcript_delta",
                            "content": event.delta
                        })
                    elif event.type == "response.done":
                        print("Response complete")
                        await websocket.send_json({
                            "type": "done"
                        })
                        break
                        
        except Exception as e:
            print(f"Error in process_audio_stream: {e}")
            import traceback
            traceback.print_exc()
            await websocket.send_json({
                "type": "error",
                "content": str(e)
            })


server = RealtimeAudioServer()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("Client connected")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "user_message":
                user_text = message_data.get("content", "")
                print(f"Received: {user_text}")
                
                # Process and stream audio back
                await server.process_audio_stream(websocket, user_text)
                
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
