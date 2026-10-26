from typing import Annotated
from fastapi import APIRouter,Depends,Path,Query
from app.dependencies import service
from app.models.responses import TeamResponse
router=APIRouter(tags=["Team"])
@router.get("/team/{team_id}",response_model=TeamResponse)
def team(team_id:Annotated[int,Path(ge=1,le=2147483647)],
    modelUpdatedAt:Annotated[str|None,Query(max_length=100)]=None,optimizer=Depends(service)):
    return optimizer.team(team_id,modelUpdatedAt)

