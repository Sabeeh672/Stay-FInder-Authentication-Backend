from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from database import get_auth_connection

router = APIRouter()


@router.get("/hostels/")
def list_hostels(
    search: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
):
    sql = """
        SELECT h.id, h.name, h.image_url, h.rent_per_room,
               COALESCE(ROUND(AVG(r.rating), 1), 0) AS rating,
               COUNT(r.id) AS rating_count
        FROM hostels h
        LEFT JOIN hostel_reviews r ON r.hostel_id = h.id
    """
    params = []
    if search and search.strip():
        like = f"%{search.strip()}%"
        sql += " WHERE h.name LIKE %s OR h.address LIKE %s"
        params += [like, like]
    sql += " GROUP BY h.id, h.name, h.image_url, h.rent_per_room ORDER BY h.name LIMIT %s OFFSET %s"
    params += [limit, offset]

    connection = get_auth_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [
            {
                "id": r["id"],
                "name": r["name"],
                "image_url": r["image_url"],
                "rent_per_room": r["rent_per_room"],
                "rating": float(r["rating"]),
                "rating_count": r["rating_count"],
            }
            for r in rows
        ]
    except Exception as e:
        print(f"Hostels Error: {e}")
        raise HTTPException(status_code=500, detail="Server error. Please try again.")
    finally:
        connection.close()