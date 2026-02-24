import asyncio
import json
import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)

class SSEManager:
    def __init__(self):
        # Maps user_id strictly to a set of queues.
        # This supports a single user being logged in from multiple tabs or devices.
        self.connections: Dict[str, Set[asyncio.Queue]] = {}
        # Keep track of active users to avoid infinite growth
        logger.info("Initializing SSE Manager")

    async def connect(self, user_id: str) -> asyncio.Queue:
        if user_id not in self.connections:
            self.connections[user_id] = set()
        
        # We use a Queue for each specific connection
        queue = asyncio.Queue()
        self.connections[user_id].add(queue)
        logger.debug(f"Client connected for user_id: {user_id}. Active sessions for user: {len(self.connections[user_id])}")
        return queue

    def disconnect(self, user_id: str, queue: asyncio.Queue):
        if user_id in self.connections and queue in self.connections[user_id]:
            self.connections[user_id].remove(queue)
            logger.debug(f"Client disconnected for user_id: {user_id}. Active sessions for user: {len(self.connections[user_id])}")
            if not self.connections[user_id]:
                del self.connections[user_id]

    async def send_to_user(self, user_id: str, data: dict):
        """
        Sends an SSE message to a specific user using all their active connections.
        """
        if user_id not in self.connections:
            return  # User not currently connected via SSE

        queues = self.connections[user_id]
        
        # Prepare the payload
        try:
            payload = json.dumps(data)
        except TypeError as e:
            logger.error(f"Failed to serialize SSE payload: {e}")
            return

        sse_message = f"data: {payload}\n\n"
        
        # Broadcast to all of this user's active connection queues
        for queue in queues:
            await queue.put(sse_message)
        logger.debug(f"Sent notification via SSE to user_id: {user_id} across {len(queues)} connection(s)")

# Global instance
sse_manager = SSEManager()
