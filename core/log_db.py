from datetime import datetime
import traceback

from pytz import timezone
from models.LogSystem import LogSystem
from settings import TZ
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from core.logging_config import logger


async def set_log_in_db(db, username, action, ip_address, status, payload):
    try:
        log = LogSystem(
            username=username,
            action=action,
            ip_address=ip_address,
            status=status,
            created_at=datetime.now(timezone(TZ)),
            payload=payload
        )
        db.add(log)
        await db.commit()
    except Exception as e:
        traceback.print_exc()
        raise ValueError(e)

async def get_recent_logs_by_action(
    db: AsyncSession, 
    username: str, 
    action: str, 
    limit: int = 10
):
    """Get recent logs for specific user and action"""
    try:
        query = select(LogSystem).where(
            LogSystem.username == username,
            LogSystem.action == action
        ).order_by(desc(LogSystem.created_at)).limit(limit)
        
        result = await db.execute(query)
        logs = result.scalars().all()
        
        return [
            {
                "id": log.id,
                "action": log.action,
                "status": log.status,
                "created_at": log.created_at.isoformat(),
                "payload": log.payload
            }
            for log in logs
        ]
    except Exception as e:
        logger.error(f"Error fetching logs: {str(e)}")
        traceback.print_exc()
        return []