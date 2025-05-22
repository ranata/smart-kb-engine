from fastapi import HTTPException, status
from services.sample.index import sample_demo


def sample_demo_controller():
    data = sample_demo()
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return {"data": data["message"], "status": "success"}
