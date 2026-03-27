from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import require_authenticated
from app.core.db import get_db
from app.models import VideoFile
from app.services.video_stream import iter_file_range, parse_range_header

router = APIRouter(dependencies=[Depends(require_authenticated)])


@router.get("/api/videos/{file_id}/stream")
def stream_video(
    file_id: int,
    request: Request,
    session: Session = Depends(get_db),
):
    file_record = session.get(VideoFile, file_id)
    if file_record is None:
        raise HTTPException(status_code=404, detail="video not found")

    file_path = Path(file_record.file_path)
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="video not found")

    range_header = request.headers.get("range")
    common_headers = {"accept-ranges": "bytes"}

    if range_header is None:
        return FileResponse(
            path=file_path,
            media_type="video/mp4",
            headers=common_headers,
        )

    try:
        byte_range = parse_range_header(range_header, file_path.stat().st_size)
    except ValueError as exc:
        raise HTTPException(
            status_code=416,
            detail="invalid range",
            headers={"content-range": f"bytes */{file_path.stat().st_size}"},
        ) from exc

    headers = {
        **common_headers,
        "content-length": str(byte_range.content_length),
        "content-range": (
            f"bytes {byte_range.start}-{byte_range.end}/{file_path.stat().st_size}"
        ),
    }
    return StreamingResponse(
        iter_file_range(file_path, byte_range),
        status_code=206,
        media_type="video/mp4",
        headers=headers,
    )
