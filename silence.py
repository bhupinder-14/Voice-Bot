import logging
import asyncio
import time
from typing import Optional

logger = logging.getLogger("voice-agent")

class SilenceDisconnector:
    def __init__(self, agent, hangup_func, timeout_sec=7.0):
        """
        Initialize the silence detector to disconnect after specified timeout
        
        Args:
            agent: VoicePipelineAgent instance
            hangup_func: Function to call to hang up the call
            timeout_sec: Timeout in seconds before disconnecting (default: 7.0)
        """
        self.agent = agent
        self.hangup_func = hangup_func
        self.timeout_sec = timeout_sec
        self.silence_timer: Optional[asyncio.Task] = None
        self.is_speaking = False
        self.last_speech_time = time.time()
        self.active = True
        self.disconnected = False
        self.warned = False  # Flag to track if we've already warned the user
        
    def start(self):
        """Start silence detection"""
        # Start the initial silence timer
        self._reset_silence_timer()
        logger.info(f"Silence disconnector started with {self.timeout_sec}s timeout")
        
    def stop(self):
        """Stop silence detection"""
        self.active = False
        if self.silence_timer and not self.silence_timer.done():
            self.silence_timer.cancel()
            self.silence_timer = None
        logger.info("Silence disconnector stopped")
        
    async def _handle_silence(self):
        """Handle silence after timeout - warn first, then disconnect"""
        if not self.active or self.disconnected:
            return
            
        # Get current time and time since last speech
        current_time = time.time()
        time_since_speech = current_time - self.last_speech_time
        
        # Check if we've been silent for the required duration
        if time_since_speech >= self.timeout_sec and not self.is_speaking:
            if not self.warned:
                # First timeout - ask if user is there
                logger.info(f"Silence detected for {time_since_speech:.2f}s, warning user")
                self.warned = True
                await self.agent.say("Are you there?", allow_interruptions=True)
                self._reset_silence_timer()
            else:
                # Second timeout - disconnect
                logger.info(f"Silence detected for {time_since_speech:.2f}s after warning, disconnecting call")
                self.disconnected = True
                
                # Use the provided hangup function
                asyncio.create_task(self.hangup_func())
        else:
            # If speech was detected during our wait, reset the timer
            self._reset_silence_timer()
    
    def _reset_silence_timer(self):
        """Reset the silence timer"""
        if not self.active:
            return
            
        # Cancel existing timer if it exists
        if self.silence_timer and not self.silence_timer.done():
            self.silence_timer.cancel()
            
        # Create a new timer
        self.silence_timer = asyncio.create_task(self._wait_and_handle_silence())
    
    async def _wait_and_handle_silence(self):
        """Wait for timeout_sec seconds and then handle silence"""
        try:
            await asyncio.sleep(self.timeout_sec)
            await self._handle_silence()
        except asyncio.CancelledError:
            # Timer was cancelled, which is expected when speech is detected
            pass
    
    def on_user_started_speaking(self):
        """Handle user started speaking event"""
        # Check if we're already disconnected
        if self.disconnected:
            logger.info("User started speaking after disconnection")
            self.disconnected = False
            
        self.is_speaking = True
        self.last_speech_time = time.time()
        self._reset_silence_timer()
        
        # Reset the warning flag since the user responded
        if self.warned:
            self.warned = False
            logger.info("User responded after warning, resetting warning flag")
    
    def on_user_stopped_speaking(self):
        """Handle user stopped speaking event"""
        # Check if we're already disconnected
        if self.disconnected:
            logger.info("User stopped speaking after disconnection")
            self.disconnected = False
            
        self.is_speaking = False
        self.last_speech_time = time.time()
        self._reset_silence_timer()
    
    def on_agent_started_speaking(self):
        """Handle agent started speaking event"""
        # Check if we're already disconnected
        if self.disconnected:
            logger.info("Agent started speaking after disconnection")
            self.disconnected = False
            
        self.is_speaking = True
        self.last_speech_time = time.time()
        self._reset_silence_timer()
    
    def on_agent_stopped_speaking(self):
        """Handle agent stopped speaking event"""
        # Check if we're already disconnected
        if self.disconnected:
            logger.info("Agent stopped speaking after disconnection")
            self.disconnected = False
            
        self.is_speaking = False
        self.last_speech_time = time.time()
        self._reset_silence_timer()