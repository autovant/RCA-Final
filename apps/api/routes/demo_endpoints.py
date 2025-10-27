"""API endpoints for demo feedback, analytics, and sharing."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import secrets

from core.db.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa


router = APIRouter(prefix="/api", tags=["demo"])


# --- Models ---

class DemoFeedback(BaseModel):
    """Feedback submission model."""
    demo_id: str = Field(..., description="Demo identifier")
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    comments: Optional[str] = Field(None, description="User comments")
    user_email: Optional[str] = Field(None, description="Optional email")
    feature_requests: Optional[list[str]] = Field(None, description="Feature requests")


class DemoAnalyticsEvent(BaseModel):
    """Analytics event model."""
    demo_id: str = Field(..., description="Demo identifier")
    event_type: str = Field(..., description="Event type (click, view, export, etc.)")
    metadata: Optional[dict] = Field(None, description="Additional metadata")
    session_id: Optional[str] = Field(None, description="Session tracking")


class ShareDemoRequest(BaseModel):
    """Share demo configuration request."""
    demo_config: dict = Field(..., description="Demo configuration to share")
    title: str = Field(..., description="Demo title")
    description: Optional[str] = Field(None, description="Demo description")
    expires_hours: Optional[int] = Field(24, ge=1, le=168, description="Expiry in hours")


class ShareDemoResponse(BaseModel):
    """Share demo response."""
    share_id: str
    share_url: str
    expires_at: datetime


# --- Endpoints ---

@router.post("/feedback/demo", status_code=201)
async def submit_demo_feedback(
    feedback: DemoFeedback,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Submit feedback for a demo.
    
    Stores user feedback including ratings, comments, and feature requests.
    """
    try:
        # Store in database
        query = sa.text("""
            INSERT INTO demo_feedback 
            (demo_id, rating, comments, user_email, feature_requests, created_at)
            VALUES (:demo_id, :rating, :comments, :user_email, :feature_requests, :created_at)
            RETURNING id
        """)
        
        result = await db.execute(
            query,
            {
                "demo_id": feedback.demo_id,
                "rating": feedback.rating,
                "comments": feedback.comments,
                "user_email": feedback.user_email,
                "feature_requests": feedback.feature_requests or [],
                "created_at": datetime.utcnow(),
            },
        )
        
        feedback_id = result.scalar_one()
        await db.commit()
        
        return {
            "id": feedback_id,
            "message": "Feedback submitted successfully",
            "demo_id": feedback.demo_id,
        }
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")


@router.post("/analytics/demo", status_code=202)
async def track_demo_analytics(
    event: DemoAnalyticsEvent,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Track demo analytics event.
    
    Records user interactions with demos for analytics purposes.
    """
    try:
        # Store analytics event
        query = sa.text("""
            INSERT INTO demo_analytics
            (demo_id, event_type, metadata, session_id, timestamp)
            VALUES (:demo_id, :event_type, :metadata, :session_id, :timestamp)
        """)
        
        await db.execute(
            query,
            {
                "demo_id": event.demo_id,
                "event_type": event.event_type,
                "metadata": event.metadata or {},
                "session_id": event.session_id,
                "timestamp": datetime.utcnow(),
            },
        )
        
        await db.commit()
        
        return {"message": "Analytics event tracked"}
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to track analytics: {str(e)}")


@router.post("/share/demo", response_model=ShareDemoResponse)
async def create_demo_share(
    request: ShareDemoRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Create a shareable link for a demo configuration.
    
    Generates a unique share ID and stores the demo configuration.
    """
    try:
        # Generate unique share ID
        share_id = secrets.token_urlsafe(16)
        expires_at = datetime.utcnow() + timedelta(hours=request.expires_hours)
        
        # Store share configuration
        query = sa.text("""
            INSERT INTO demo_shares
            (share_id, title, description, config, expires_at, created_at)
            VALUES (:share_id, :title, :description, :config, :expires_at, :created_at)
            RETURNING share_id
        """)
        
        result = await db.execute(
            query,
            {
                "share_id": share_id,
                "title": request.title,
                "description": request.description,
                "config": request.demo_config,
                "expires_at": expires_at,
                "created_at": datetime.utcnow(),
            },
        )
        
        await db.commit()
        
        # Build share URL
        share_url = f"/demo/shared/{share_id}"
        
        return ShareDemoResponse(
            share_id=share_id,
            share_url=share_url,
            expires_at=expires_at,
        )
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create share: {str(e)}")


@router.get("/share/{share_id}")
async def get_demo_share(
    share_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieve a shared demo configuration.
    
    Returns the demo configuration if the share is valid and not expired.
    """
    try:
        query = sa.text("""
            SELECT title, description, config, expires_at, created_at
            FROM demo_shares
            WHERE share_id = :share_id
        """)
        
        result = await db.execute(query, {"share_id": share_id})
        row = result.first()
        
        if not row:
            raise HTTPException(status_code=404, detail="Share not found")
        
        # Check expiry
        if row.expires_at < datetime.utcnow():
            raise HTTPException(status_code=410, detail="Share has expired")
        
        return {
            "title": row.title,
            "description": row.description,
            "config": row.config,
            "created_at": row.created_at,
            "expires_at": row.expires_at,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve share: {str(e)}")


@router.get("/analytics/demo/{demo_id}/summary")
async def get_demo_analytics_summary(
    demo_id: str,
    hours: int = 24,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get analytics summary for a demo.
    
    Returns aggregated analytics data for the specified time period.
    """
    try:
        from datetime import timedelta
        
        since = datetime.utcnow() - timedelta(hours=hours)
        
        query = sa.text("""
            SELECT 
                event_type,
                COUNT(*) as count,
                COUNT(DISTINCT session_id) as unique_sessions
            FROM demo_analytics
            WHERE demo_id = :demo_id 
                AND timestamp >= :since
            GROUP BY event_type
            ORDER BY count DESC
        """)
        
        result = await db.execute(
            query,
            {"demo_id": demo_id, "since": since},
        )
        
        events = [
            {
                "event_type": row.event_type,
                "count": row.count,
                "unique_sessions": row.unique_sessions,
            }
            for row in result
        ]
        
        # Get total views
        total_query = sa.text("""
            SELECT COUNT(DISTINCT session_id) as total_sessions
            FROM demo_analytics
            WHERE demo_id = :demo_id AND timestamp >= :since
        """)
        
        total_result = await db.execute(
            total_query,
            {"demo_id": demo_id, "since": since},
        )
        total_sessions = total_result.scalar_one()
        
        return {
            "demo_id": demo_id,
            "time_period_hours": hours,
            "total_sessions": total_sessions,
            "events": events,
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@router.get("/feedback/demo/{demo_id}/summary")
async def get_demo_feedback_summary(
    demo_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get feedback summary for a demo.
    
    Returns aggregated feedback metrics.
    """
    try:
        query = sa.text("""
            SELECT 
                COUNT(*) as total_feedback,
                AVG(rating) as avg_rating,
                COUNT(CASE WHEN rating >= 4 THEN 1 END) as positive_count,
                COUNT(CASE WHEN rating <= 2 THEN 1 END) as negative_count
            FROM demo_feedback
            WHERE demo_id = :demo_id
        """)
        
        result = await db.execute(query, {"demo_id": demo_id})
        row = result.first()
        
        # Get feature requests
        requests_query = sa.text("""
            SELECT feature_requests
            FROM demo_feedback
            WHERE demo_id = :demo_id 
                AND feature_requests IS NOT NULL
                AND array_length(feature_requests, 1) > 0
        """)
        
        requests_result = await db.execute(requests_query, {"demo_id": demo_id})
        
        all_requests = []
        for r in requests_result:
            if r.feature_requests:
                all_requests.extend(r.feature_requests)
        
        # Count feature request frequency
        from collections import Counter
        request_counts = Counter(all_requests).most_common(10)
        
        return {
            "demo_id": demo_id,
            "total_feedback": row.total_feedback,
            "avg_rating": float(row.avg_rating) if row.avg_rating else 0,
            "positive_count": row.positive_count,
            "negative_count": row.negative_count,
            "top_feature_requests": [
                {"feature": req, "count": count}
                for req, count in request_counts
            ],
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get feedback summary: {str(e)}")
