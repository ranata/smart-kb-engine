from fastapi import APIRouter
from controllers.sample.index import sample_demo_controller

router = APIRouter()


@router.get("/sample-demo")
def sample_demo():
    return sample_demo_controller()
