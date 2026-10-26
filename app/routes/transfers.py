from fastapi import APIRouter,Depends
from app.dependencies import service
from app.models.requests import TransferRequest,TransferPreviewRequest
from app.models.responses import TransferResponse,PreviewResponse
router=APIRouter(tags=["Transfers"])
@router.post("/optimize/transfers",response_model=TransferResponse)
def transfers(body:TransferRequest,optimizer=Depends(service)):
    return optimizer.optimize_transfers(body)

@router.post("/optimize/transfers/preview",response_model=PreviewResponse)
def preview(body:TransferPreviewRequest,optimizer=Depends(service)):
    return optimizer.preview(body)

