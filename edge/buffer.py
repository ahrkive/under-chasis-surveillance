"""
Local Buffer — Offline-Resilient Image Queue
=============================================
Stores captured images on the local filesystem with a SQLite-backed
metadata queue. Ensures zero image loss during network outages.

Images are stored as JPEG files in the buffer directory.
SQLite tracks: filename, status (queued/sent/failed), timestamps, retries.
The transmitter drains this queue; images are deleted only after server ACK.
"""

import hashlib
import logging
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class BufferEntry:
    """Represents a single buffered image."""
    id: int
    filename: str
    filepath: str
    sha256: str
    size_bytes: int
    status: str          # queued | sent | failed
    retry_count: int
    created_at: float    # Unix timestamp
    sent_at: Optional[float]


class ImageBuffer:
    """
    SQLite-backed local image buffer for offline resilience.

    Flow:
    1. capture.py → buffer.enqueue(jpeg_bytes) → saves file + DB row (status=queued)
    2. transmitter.py → buffer.peek() → gets oldest queued entry
    3. transmitter sends image → on ACK → buffer.mark_sent(id) → deletes file
    4. on failure → buffer.mark_failed(id) → increments retry_count
    """

    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS outbox (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        filename    TEXT    NOT NULL UNIQUE,
        filepath    TEXT    NOT NULL,
        sha256      TEXT    NOT NULL,
        size_bytes  INTEGER NOT NULL,
        status      TEXT    NOT NULL DEFAULT 'queued',
        retry_count INTEGER NOT NULL DEFAULT 0,
        created_at  REAL    NOT NULL,
        sent_at     REAL
    );
    """

    CREATE_INDEX_SQL = """
    CREATE INDEX IF NOT EXISTS idx_outbox_status
    ON outbox (status, created_at ASC);
    """

    def __init__(self, buffer_dir: str, db_path: str, max_size_mb: int = 500):
        """
        Args:
            buffer_dir: Directory to store image files.
            db_path: Path to the SQLite database file.
            max_size_mb: Max total buffer size before pruning oldest images.
        """
        self.buffer_dir = Path(buffer_dir)
        self.db_path = db_path
        self.max_size_bytes = max_size_mb * 1024 * 1024

        # Ensure directory exists
        self.buffer_dir.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL;")  # Better concurrency
        self._conn.execute("PRAGMA synchronous=NORMAL;")  # Faster writes, still safe
        self._conn.execute(self.CREATE_TABLE_SQL)
        self._conn.execute(self.CREATE_INDEX_SQL)
        self._conn.commit()

        logger.info(
            "ImageBuffer initialized: dir=%s, db=%s, max_size=%dMB",
            self.buffer_dir, db_path, max_size_mb,
        )

    def enqueue(self, jpeg_data: bytes, bot_id: str = "bot-001") -> BufferEntry:
        """
        Save a JPEG image to the buffer and register it in the queue.

        Args:
            jpeg_data: Raw JPEG bytes.
            bot_id: Identifier for the bot (used in filename).

        Returns:
            The created BufferEntry.
        """
        now = time.time()
        sha256 = hashlib.sha256(jpeg_data).hexdigest()

        # Generate unique filename: <bot_id>_<timestamp>_<hash_prefix>.jpg
        filename = f"{bot_id}_{int(now * 1000)}_{sha256[:8]}.jpg"
        filepath = self.buffer_dir / filename

        # Write image file
        filepath.write_bytes(jpeg_data)
        size_bytes = len(jpeg_data)

        # Insert DB record
        cursor = self._conn.execute(
            """
            INSERT INTO outbox (filename, filepath, sha256, size_bytes, status, created_at)
            VALUES (?, ?, ?, ?, 'queued', ?)
            """,
            (filename, str(filepath), sha256, size_bytes, now),
        )
        self._conn.commit()

        entry = BufferEntry(
            id=cursor.lastrowid,
            filename=filename,
            filepath=str(filepath),
            sha256=sha256,
            size_bytes=size_bytes,
            status="queued",
            retry_count=0,
            created_at=now,
            sent_at=None,
        )

        logger.debug("Enqueued image: %s (%d bytes)", filename, size_bytes)

        # Prune if over size limit
        self._prune_if_needed()

        return entry

    def peek(self, count: int = 1) -> list[BufferEntry]:
        """
        Get the oldest queued entries without modifying their status.

        Args:
            count: Number of entries to return.

        Returns:
            List of BufferEntry objects.
        """
        rows = self._conn.execute(
            """
            SELECT id, filename, filepath, sha256, size_bytes,
                   status, retry_count, created_at, sent_at
            FROM outbox
            WHERE status = 'queued'
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (count,),
        ).fetchall()

        return [BufferEntry(*row) for row in rows]

    def get_image_data(self, entry: BufferEntry) -> Optional[bytes]:
        """
        Read the image file for a buffer entry.

        Returns:
            JPEG bytes, or None if file is missing.
        """
        try:
            return Path(entry.filepath).read_bytes()
        except FileNotFoundError:
            logger.error("Buffer file missing: %s", entry.filepath)
            self._conn.execute("DELETE FROM outbox WHERE id = ?", (entry.id,))
            self._conn.commit()
            return None

    def mark_sent(self, entry_id: int) -> None:
        """Mark an entry as successfully sent and delete the local file."""
        row = self._conn.execute(
            "SELECT filepath FROM outbox WHERE id = ?", (entry_id,)
        ).fetchone()

        if row:
            # Delete local file
            try:
                os.remove(row[0])
            except OSError:
                pass  # File already gone

            self._conn.execute(
                "UPDATE outbox SET status = 'sent', sent_at = ? WHERE id = ?",
                (time.time(), entry_id),
            )
            self._conn.commit()
            logger.debug("Marked as sent and cleaned up: entry_id=%d", entry_id)

    def mark_failed(self, entry_id: int) -> None:
        """Increment retry count for a failed transmission."""
        self._conn.execute(
            """
            UPDATE outbox
            SET status = 'queued', retry_count = retry_count + 1
            WHERE id = ?
            """,
            (entry_id,),
        )
        self._conn.commit()
        logger.debug("Marked as failed (will retry): entry_id=%d", entry_id)

    def queue_size(self) -> int:
        """Return the number of queued (unsent) entries."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM outbox WHERE status = 'queued'"
        ).fetchone()
        return row[0] if row else 0

    def total_size_bytes(self) -> int:
        """Return total size of all queued images in bytes."""
        row = self._conn.execute(
            "SELECT COALESCE(SUM(size_bytes), 0) FROM outbox WHERE status = 'queued'"
        ).fetchone()
        return row[0] if row else 0

    def _prune_if_needed(self) -> None:
        """Remove oldest sent entries if buffer exceeds max size."""
        total = self.total_size_bytes()
        if total <= self.max_size_bytes:
            return

        # First: remove all 'sent' entries (already transmitted)
        sent_rows = self._conn.execute(
            "SELECT id, filepath FROM outbox WHERE status = 'sent'"
        ).fetchall()
        for row_id, filepath in sent_rows:
            try:
                os.remove(filepath)
            except OSError:
                pass
            self._conn.execute("DELETE FROM outbox WHERE id = ?", (row_id,))

        self._conn.commit()

        # If still over limit, remove oldest queued entries
        total = self.total_size_bytes()
        if total > self.max_size_bytes:
            excess = total - self.max_size_bytes
            removed = 0
            oldest = self._conn.execute(
                """
                SELECT id, filepath, size_bytes FROM outbox
                WHERE status = 'queued'
                ORDER BY created_at ASC
                """
            ).fetchall()
            for row_id, filepath, size in oldest:
                if removed >= excess:
                    break
                try:
                    os.remove(filepath)
                except OSError:
                    pass
                self._conn.execute("DELETE FROM outbox WHERE id = ?", (row_id,))
                removed += size

            self._conn.commit()
            logger.warning(
                "Buffer pruned: removed %d bytes to stay under %dMB limit.",
                removed, self.max_size_bytes // (1024 * 1024),
            )

    def cleanup_sent(self, max_age_hours: int = 24) -> int:
        """
        Remove sent entries older than max_age_hours.
        Returns the number of entries removed.
        """
        cutoff = time.time() - (max_age_hours * 3600)
        rows = self._conn.execute(
            "SELECT id, filepath FROM outbox WHERE status = 'sent' AND sent_at < ?",
            (cutoff,),
        ).fetchall()

        for row_id, filepath in rows:
            try:
                os.remove(filepath)
            except OSError:
                pass
            self._conn.execute("DELETE FROM outbox WHERE id = ?", (row_id,))

        self._conn.commit()
        if rows:
            logger.info("Cleaned up %d sent entries older than %dh.", len(rows), max_age_hours)
        return len(rows)

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
        logger.info("ImageBuffer closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
