from fastapi import APIRouter,Depends
from app.dependencies import service
from app.models.requests import TeamSheetRequest
from app.models.responses import TeamSheetResponse
router=APIRouter(tags=["Team Sheet"])
@router.post("/optimize/team-sheet",response_model=TeamSheetResponse)
def team_sheet(body:TeamSheetRequest,optimizer=Depends(service)):
    return optimizer.team_sheet(body)

