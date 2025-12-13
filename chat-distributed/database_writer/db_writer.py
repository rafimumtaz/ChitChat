# db_writer.py
"""
DB Writer module for RabbitMQ consumer.
- Uses PyMySQL with a small connection pool (thread-safe).
- Provides write_message(msg: dict) -> bool
- Expects msg fields: publisher_msg_id (str), room_id (int), sender_id (int|None),
  content (str), seq (int|None), ts (float|None)  (ts = unix timestamp in seconds, optional)
"""

import os
import time
import logging
import pymysql
import pymysql.cursors
from queue import Queue, Empty
from threading import Lock

# ---------- Configuration (env or defaults) ----------
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "chat_distributed_db")
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 5))
POOL_TIMEOUT = float(os.getenv("DB_POOL_TIMEOUT", 5.0))  # seconds

# ---------- Logging ----------
logger = logging.getLogger("db_writer")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ---------- Simple connection pool ----------
class MySQLPool:
    def __init__(self, size=5):
        self.size = size
        self._pool = Queue(maxsize=size)
        self._created = 0
        self._lock = Lock()

    def _create_conn(self):
        conn = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
            connect_timeout=5,
        )
        return conn

    def get_conn(self, timeout=POOL_TIMEOUT):
        try:
            return self._pool.get(block=True, timeout=timeout)
        except Empty:
            with self._lock:
                if self._created < self.size:
                    conn = self._create_conn()
                    self._created += 1
                    return conn
            # if pooling full, block until released or timeout
            return self._pool.get(block=True, timeout=timeout)

    def release(self, conn):
        try:
            # check connection alive
            conn.ping(reconnect=True)
            self._pool.put(conn, block=False)
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            with self._lock:
                self._created -= 1

    def close_all(self):
        while True:
            try:
                conn = self._pool.get_nowait()
                try:
                    conn.close()
                except Exception:
                    pass
            except Empty:
                break


_pool = MySQLPool(size=POOL_SIZE)

# ---------- SQL (idempotent insert) ----------
# Uses publisher_msg_id UNIQUE constraint to avoid duplicates.
# We intentionally do a no-op in ON DUPLICATE KEY UPDATE (keep existing row intact).
INSERT_SQL = """
INSERT INTO messages (
    publisher_msg_id, room_id, sender_id, seq, content, created_at, broker_received_at,
    attachment_url, attachment_type, original_name
) VALUES (
    %s, %s, %s, %s, %s, FROM_UNIXTIME(%s), NOW(), %s, %s, %s
)
ON DUPLICATE KEY UPDATE
    broker_received_at = broker_received_at;
"""

# ---------- Additional SQL for Notifications/Friends ----------
INSERT_NOTIF_SQL = """
INSERT INTO notifications (type, sender_id, receiver_id, reference_id, status)
VALUES (%s, %s, %s, %s, 'unread')
"""

INSERT_FRIEND_SQL = """
INSERT INTO friends (user_id, friend_id, status) VALUES (%s, %s, 'PENDING')
"""

UPDATE_FRIEND_SQL = """
UPDATE friends SET status = 'ACCEPTED' WHERE user_id = %s AND friend_id = %s
"""

INSERT_MEMBER_SQL = """
INSERT INTO room_members (room_id, user_id) VALUES (%s, %s)
"""

UPDATE_NOTIF_STATUS_SQL = """
UPDATE notifications SET status = 'read' WHERE notif_id = %s
"""

# ---------- Utility: validate incoming message ----------
def _validate_msg(msg):
    if not isinstance(msg, dict):
        return False, "msg must be dict"
    if "publisher_msg_id" not in msg or not msg["publisher_msg_id"]:
        return False, "publisher_msg_id missing"
    if "room_id" not in msg:
        return False, "room_id missing"
    if "content" not in msg:
        return False, "content missing"
    # optionally more validation
    return True, None

# ---------- Public function ----------
def write_message(msg):
    """
    Write a single message to DB.
    Returns True if success (inserted or duplicate already existed), False on permanent failure.
    Raise exceptions only for fatal/unexpected issues (consumer should catch).
    """
    ok, err = _validate_msg(msg)
    if not ok:
        logger.error("Invalid message payload: %s", err)
        return False

    conn = None
    try:
        conn = _pool.get_conn()
        with conn.cursor() as cur:
            ts = msg.get("ts")  # publisher timestamp (unix seconds)
            if ts is None:
                ts = time.time()
            params = (
                str(msg["publisher_msg_id"]),
                int(msg["room_id"]),
                int(msg["sender_id"]) if msg.get("sender_id") is not None else None,
                int(msg["seq"]) if msg.get("seq") is not None else None,
                str(msg["content"]),
                float(ts),
                msg.get("attachment_url"),
                msg.get("attachment_type"),
                msg.get("original_name")
            )
            cur.execute(INSERT_SQL, params)
            conn.commit()
        # success (either inserted or duplicate hit -> ON DUPLICATE did no-op)
        return True
    except pymysql.MySQLError as e:
        # Log details. For transient errors, caller (consumer) may choose to requeue.
        logger.exception("MySQL error while inserting message: %s", e)
        try:
            if conn is not None:
                conn.rollback()
        except Exception:
            pass
        return False
    except Exception as e:
        logger.exception("Unexpected error in write_message: %s", e)
        try:
            if conn is not None:
                conn.rollback()
        except Exception:
            pass
        return False
    finally:
        if conn is not None:
            _pool.release(conn)


# ---------- Health check / administrative helpers ----------
def health_check():
    try:
        conn = _pool.get_conn(timeout=2)
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            _ = cur.fetchone()
        _pool.release(conn)
        return True
    except Exception as e:
        logger.exception("DB health check failed: %s", e)
        return False

def close_pool():
    _pool.close_all()


# ---------- New Writer Functions ----------

def write_friend_request(msg):
    """
    Handle FRIEND_REQUEST.
    Expects msg: { sender_id, receiver_id }
    """
    conn = None
    try:
        conn = _pool.get_conn()
        with conn.cursor() as cur:
            # 1. Friend Table (Pending)
            # Check if exists first to avoid duplicate errors? Or let it fail/catch?
            # Assuming idempotent or check before logic in consumer, but safe to try.
            # Use INSERT IGNORE or try-except for duplicate key?
            # Prompt says "Backend saves to DB".
            # For robustness, we check exists.
            cur.execute("SELECT 1 FROM friends WHERE user_id=%s AND friend_id=%s", (msg['sender_id'], msg['receiver_id']))
            if not cur.fetchone():
                cur.execute(INSERT_FRIEND_SQL, (msg['sender_id'], msg['receiver_id']))

                # 2. Notification
                # Reference ID for friend request is usually sender_id (profile link)
                cur.execute(INSERT_NOTIF_SQL, ('FRIEND_REQUEST', msg['sender_id'], msg['receiver_id'], msg['sender_id']))
                conn.commit()
        return True
    except Exception as e:
        logger.exception("Error writing friend request: %s", e)
        if conn: conn.rollback()
        return False
    finally:
        if conn: _pool.release(conn)

def write_group_invite(msg):
    """
    Handle GROUP_INVITE.
    Expects msg: { sender_id, receiver_id, room_id }
    """
    conn = None
    try:
        conn = _pool.get_conn()
        with conn.cursor() as cur:
            cur.execute(INSERT_NOTIF_SQL, ('GROUP_INVITE', msg['sender_id'], msg['receiver_id'], msg['room_id']))
            conn.commit()
        return True
    except Exception as e:
        logger.exception("Error writing group invite: %s", e)
        if conn: conn.rollback()
        return False
    finally:
        if conn: _pool.release(conn)

def write_friend_accept(msg):
    """
    Handle FRIEND_ACCEPTED.
    Expects msg: { initiator_id, acceptor_id, notif_id (optional) }
    initiator_id: The one who sent the request.
    acceptor_id: The one who accepted it.
    """
    conn = None
    try:
        conn = _pool.get_conn()
        with conn.cursor() as cur:
            cur.execute(UPDATE_FRIEND_SQL, (msg['initiator_id'], msg['acceptor_id']))
            if msg.get('notif_id'):
                cur.execute(UPDATE_NOTIF_STATUS_SQL, (msg['notif_id'],))
            conn.commit()
        return True
    except Exception as e:
        logger.exception("Error writing friend accept: %s", e)
        if conn: conn.rollback()
        return False
    finally:
        if conn: _pool.release(conn)

def write_group_join(msg):
    """
    Handle GROUP_JOINED (Accept Invite).
    Expects msg: { room_id, user_id, notif_id (optional) }
    """
    conn = None
    try:
        conn = _pool.get_conn()
        with conn.cursor() as cur:
            # Check if member exists
            cur.execute("SELECT 1 FROM room_members WHERE room_id=%s AND user_id=%s", (msg['room_id'], msg['user_id']))
            if not cur.fetchone():
                cur.execute(INSERT_MEMBER_SQL, (msg['room_id'], msg['user_id']))

            if msg.get('notif_id'):
                cur.execute(UPDATE_NOTIF_STATUS_SQL, (msg['notif_id'],))
            conn.commit()
        return True
    except Exception as e:
        logger.exception("Error writing group join: %s", e)
        if conn: conn.rollback()
        return False
    finally:
        if conn: _pool.release(conn)

# If run directly, demo health check
if __name__ == "__main__":
    ok = health_check()
    print("DB health:", ok)
