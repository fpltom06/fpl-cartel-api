from fastapi import APIRouter,Depends
from app.dependencies import service
from app.models.requests import TeamSheetRequest
from app.models.responses import TeamSheetResponse
router=APIRouter(tags=["Team Sheet"])
@router.post("/optimize/team-sheet",response_model=TeamSheetResponse)
def team_sheet(body:TeamSheetRequest,optimizer=Depends(service)):
    return optimizer.team_sheet(body)


from app.models.requests import BestSquadRequest
from app.models.responses import BestSquadResponse

@router.post("/optimize/best-squad",response_model=BestSquadResponse,tags=["Best Squad"])
def best_squad(body:BestSquadRequest,optimizer=Depends(service)):
    return optimizer.best_squad(body)
