"""
screen_streamer.py - Real-time Screen Streaming Service

Continuously captures and streams device screenshots via WebSocket.
"""

import logging
import asyncio
from typing import Optional, Callable
from pathlib import Path
import base64
from datetime import datetime

logger = logging.getLogger(__name__)


class ScreenStreamer:
    """Real-time screen streaming service."""
    
    def __init__(self, fps: int = 2, quality: int = 70, max_width: int = 720):
        """
        Initialize screen streamer.
        
        Args:
            fps: Frames per second (1-5)
            quality: JPEG quality (1-100)
            max_width: Max image width for streaming
        """
        self.fps = max(1, min(fps, 5))  # Clamp to 1-5
        self.quality = quality
        self.max_width = max_width
        self.interval = 1.0 / self.fps
        
        # State
        self.active = False
        self.task: Optional[asyncio.Task] = None
        self.frame_count = 0
        self.error_count = 0
        
        # Callback for new frames
        self.on_frame: Optional[Callable] = None
        
        # Screenshot tool (lazy load)
        self._screenshot_tool = None
        
        logger.info(f"ScreenStreamer created: {self.fps} FPS, quality={self.quality}")
    
    @property
    def screenshot_tool(self):
        """Lazy load screenshot tool."""
        if self._screenshot_tool is None:
            from backend.tools import toolkit
            self._screenshot_tool = toolkit.screenshot
        return self._screenshot_tool
    
    async def start(self, on_frame: Optional[Callable] = None):
        """
        Start streaming.
        
        Args:
            on_frame: Callback function for new frames
                     Signature: async def callback(frame_data: dict)
        """
        if self.active:
            logger.warning("⚠️ Streamer already active")
            return
        
        self.on_frame = on_frame
        self.active = True
        self.frame_count = 0
        self.error_count = 0
        
        # Start streaming task
        self.task = asyncio.create_task(self._stream_loop())
        
        logger.info(f"▶️ Screen streaming started: {self.fps} FPS")
    
    async def stop(self):
        """Stop streaming."""
        if not self.active:
            return
        
        self.active = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"⏹️ Screen streaming stopped")
        logger.info(f"   Frames captured: {self.frame_count}")
        logger.info(f"   Errors: {self.error_count}")
    
    async def _stream_loop(self):
        """Main streaming loop."""
        try:
            while self.active:
                try:
                    # Capture frame
                    frame_data = await self._capture_frame()
                    
                    if frame_data:
                        self.frame_count += 1
                        
                        # Call callback if provided
                        if self.on_frame:
                            await self.on_frame(frame_data)
                    else:
                        self.error_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Frame capture error: {e}")
                    self.error_count += 1
                
                # Wait for next frame
                await asyncio.sleep(self.interval)
                
        except asyncio.CancelledError:
            logger.info("🛑 Streaming cancelled")
            raise
        except Exception as e:
            logger.error(f"❌ Streaming error: {e}")
            self.active = False
    
    async def _capture_frame(self) -> Optional[dict]:
        """
        Capture single frame.
        
        Returns:
            Frame data dict or None
        """
        try:
            # Capture screenshot (in thread to avoid blocking)
            screenshot_path = await asyncio.to_thread(
                self.screenshot_tool.capture
            )
            
            if not screenshot_path:
                return None
            
            # Read and encode image
            from PIL import Image
            import io
            
            # Resize and compress
            img = Image.open(screenshot_path)
            
            # Resize if needed
            if img.width > self.max_width:
                ratio = self.max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((self.max_width, new_height), Image.Resampling.LANCZOS)
            
            # Convert to JPEG bytes
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=self.quality, optimize=True)
            jpeg_bytes = buffer.getvalue()
            
            # Encode to base64
            base64_data = base64.b64encode(jpeg_bytes).decode('utf-8')
            
            # Build frame data
            frame_data = {
                "frame_number": self.frame_count + 1,
                "timestamp": datetime.now().isoformat(),
                "width": img.width,
                "height": img.height,
                "format": "jpeg",
                "quality": self.quality,
                "size_bytes": len(jpeg_bytes),
                "data": base64_data
            }
            
            return frame_data
            
        except Exception as e:
            logger.error(f"❌ Capture frame error: {e}")
            return None
    
    def get_stats(self) -> dict:
        """Get streaming statistics."""
        return {
            "active": self.active,
            "fps": self.fps,
            "quality": self.quality,
            "max_width": self.max_width,
            "frame_count": self.frame_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.frame_count, 1)
        }


class StreamManager:
    """Manages multiple screen streamers."""
    
    def __init__(self):
        """Initialize stream manager."""
        self.streamers: dict[str, ScreenStreamer] = {}
        logger.info("StreamManager initialized")
    
    def create_streamer(
        self,
        stream_id: str,
        fps: int = 2,
        quality: int = 70,
        max_width: int = 720
    ) -> ScreenStreamer:
        """
        Create new streamer.
        
        Args:
            stream_id: Unique streamer ID
            fps: Frames per second
            quality: JPEG quality
            max_width: Max width
            
        Returns:
            ScreenStreamer instance
        """
        if stream_id in self.streamers:
            logger.warning(f"⚠️ Streamer {stream_id} already exists")
            return self.streamers[stream_id]
        
        streamer = ScreenStreamer(fps=fps, quality=quality, max_width=max_width)
        self.streamers[stream_id] = streamer
        
        logger.info(f"✅ Created streamer: {stream_id}")
        return streamer
    
    def get_streamer(self, stream_id: str) -> Optional[ScreenStreamer]:
        """Get streamer by ID."""
        return self.streamers.get(stream_id)
    
    async def stop_all(self):
        """Stop all streamers."""
        for stream_id, streamer in self.streamers.items():
            if streamer.active:
                await streamer.stop()
        
        logger.info(f"⏹️ Stopped all {len(self.streamers)} streamers")
    
    def get_all_stats(self) -> dict:
        """Get stats for all streamers."""
        return {
            stream_id: streamer.get_stats()
            for stream_id, streamer in self.streamers.items()
        }


# Global stream manager instance
_stream_manager: Optional[StreamManager] = None


def get_stream_manager() -> StreamManager:
    """Get global stream manager instance."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamManager()
    return _stream_manager