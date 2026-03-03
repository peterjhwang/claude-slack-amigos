"""
Persistent state manager for the 3 Amigos workflow.

Two SQLite tables:
  thread_states — one row per @amigos task (keyed by Slack thread_ts)
  message_map   — maps agent message timestamps → thread_ts for reaction routing

LangGraph's own AsyncSqliteSaver handles graph checkpointing separately
(in CHECKPOINT_DB). This module handles application-level state only.
"""
from __future__ import annotations

import json
import logging
import os

import aiosqlite

from config import DB_PATH

logger = logging.getLogger(__name__)


# ── Initialisation ─────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create tables if they don't exist. Called once on app startup."""
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS thread_states (
                thread_ts   TEXT PRIMARY KEY,
                channel_id  TEXT NOT NULL,
                task        TEXT NOT NULL,
                phase       TEXT NOT NULL DEFAULT 'archie',
                metadata    TEXT NOT NULL DEFAULT '{}',
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Tracks which messages were posted by an agent so that reactions
        # on those messages can be routed back to the right workflow thread.
        await db.execute("""
            CREATE TABLE IF NOT EXISTS message_map (
                msg_ts      TEXT PRIMARY KEY,
                thread_ts   TEXT NOT NULL,
                channel_id  TEXT NOT NULL,
                agent       TEXT NOT NULL,          -- 'archie' | 'builder' | 'eval'
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
    logger.info("State DB initialised at %s", DB_PATH)


# ── Thread state CRUD ──────────────────────────────────────────────────────────

async def create_thread_state(
    thread_ts: str,
    channel_id: str,
    task: str,
) -> None:
    """Insert (or replace) a thread record when a new @amigos task starts."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO thread_states
                (thread_ts, channel_id, task, phase, updated_at)
            VALUES (?, ?, ?, 'archie', CURRENT_TIMESTAMP)
            """,
            (thread_ts, channel_id, task),
        )
        await db.commit()


async def get_thread_state(thread_ts: str) -> dict | None:
    """Return the thread state dict, or None if not found."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT thread_ts, channel_id, task, phase, metadata "
            "FROM thread_states WHERE thread_ts = ?",
            (thread_ts,),
        ) as cur:
            row = await cur.fetchone()
    if row is None:
        return None
    return {
        "thread_ts": row[0],
        "channel_id": row[1],
        "task": row[2],
        "phase": row[3],
        "metadata": json.loads(row[4]),
    }


async def update_thread_phase(thread_ts: str, phase: str) -> None:
    """Advance the recorded phase of a thread workflow."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            UPDATE thread_states
            SET phase = ?, updated_at = CURRENT_TIMESTAMP
            WHERE thread_ts = ?
            """,
            (phase, thread_ts),
        )
        await db.commit()


# ── Message map (for reaction routing) ────────────────────────────────────────

async def register_agent_message(
    msg_ts: str,
    thread_ts: str,
    channel_id: str,
    agent: str,
) -> None:
    """
    Store a mapping from an agent's approval-message ts to its parent thread.
    This lets us resume the workflow when someone reacts 👍 to the message.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO message_map (msg_ts, thread_ts, channel_id, agent)
            VALUES (?, ?, ?, ?)
            """,
            (msg_ts, thread_ts, channel_id, agent),
        )
        await db.commit()


async def get_thread_by_msg_ts(msg_ts: str) -> dict | None:
    """
    Look up the thread context for a given message ts.
    Returns {"thread_ts": ..., "channel_id": ..., "agent": ...} or None.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT thread_ts, channel_id, agent FROM message_map WHERE msg_ts = ?",
            (msg_ts,),
        ) as cur:
            row = await cur.fetchone()
    if row is None:
        return None
    return {"thread_ts": row[0], "channel_id": row[1], "agent": row[2]}
