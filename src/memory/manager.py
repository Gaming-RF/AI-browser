"""
Memory Management System

Handles persistent memory for the AI agent.
"""

import json
import sqlite3
from typing import Optional, Dict, Any, List
from datetime import datetime
import os


class MemoryManager:
    """Manages persistent memory using SQLite."""

    def __init__(self, db_path: str = "memory.db"):
        """
        Initialize the memory manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        """Initialize the database if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_description TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                result TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)
        
        # Create interactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                interaction_type TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                task_id INTEGER,
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        
        # Create context table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create cached_deals table for Phase 16 Background Data Aggregator
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cached_deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT UNIQUE NOT NULL,
                data TEXT NOT NULL,
                fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()

    def log_task(self, description: str, metadata: Optional[Dict] = None) -> int:
        """Log a new task."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO tasks (task_description, metadata) VALUES (?, ?)",
            (description, json.dumps(metadata or {}))
        )
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()
        return task_id

    def update_task(self, task_id: int, status: str, result: Optional[str] = None):
        """Update task status and result."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE tasks SET status = ?, result = ? WHERE id = ?",
            (status, result, task_id)
        )
        conn.commit()
        conn.close()

    def log_interaction(
        self,
        interaction_type: str,
        data: Dict[str, Any],
        task_id: Optional[int] = None
    ):
        """Log an interaction."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO interactions (interaction_type, data, task_id) VALUES (?, ?, ?)",
            (interaction_type, json.dumps(data), task_id)
        )
        conn.commit()
        conn.close()

    def save_context(self, key: str, value: Any):
        """Save a context value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            INSERT OR REPLACE INTO context (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (key, json.dumps(value) if isinstance(value, (dict, list)) else str(value))
        )
        conn.commit()
        conn.close()

    def get_context(self, key: str) -> Optional[Any]:
        """Retrieve a context value."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM context WHERE key = ?", (key,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            try:
                return json.loads(result[0])
            except:
                return result[0]
        return None

    def get_all_context(self) -> Dict[str, Any]:
        """Retrieve all context values."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT key, value FROM context")
        results = cursor.fetchall()
        conn.close()
        
        context = {}
        for key, value in results:
            try:
                context[key] = json.loads(value)
            except:
                context[key] = value
        
        return context

    def get_task_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent task history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT id, task_description, status, result, timestamp
            FROM tasks
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,)
        )
        results = cursor.fetchall()
        conn.close()
        
        history = []
        for row in results:
            history.append({
                "id": row[0],
                "description": row[1],
                "status": row[2],
                "result": row[3],
                "timestamp": row[4]
            })
        
        return history

    def get_interactions_for_task(self, task_id: int) -> List[Dict[str, Any]]:
        """Get all interactions for a task."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT interaction_type, data, timestamp
            FROM interactions
            WHERE task_id = ?
            ORDER BY timestamp ASC
            """,
            (task_id,)
        )
        results = cursor.fetchall()
        conn.close()
        
        interactions = []
        for row in results:
            interactions.append({
                "type": row[0],
                "data": json.loads(row[1]),
                "timestamp": row[2]
            })
        
        return interactions

    def clear_memory(self):
        """Clear all memory (for testing)."""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self._initialize_db()

    def save_deals(self, deals: List[Dict[str, Any]]):
        """Save fetched game deals into the local cache."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear old deals
        cursor.execute("DELETE FROM cached_deals")
        
        # Insert new deals
        for deal in deals:
            game_id = str(deal.get('id', deal.get('title', 'unknown')))
            cursor.execute(
                "INSERT OR REPLACE INTO cached_deals (game_id, data, fetched_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (game_id, json.dumps(deal))
            )
            
        conn.commit()
        conn.close()
        
    def get_deals(self) -> List[Dict[str, Any]]:
        """Retrieve cached game deals."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT data FROM cached_deals ORDER BY fetched_at DESC")
        results = cursor.fetchall()
        conn.close()
        
        deals = []
        for row in results:
            try:
                deals.append(json.loads(row[0]))
            except:
                pass
        return deals
