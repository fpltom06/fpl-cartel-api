from typing import Annotated,Literal
from pydantic import BaseModel,ConfigDict,Field,field_validator
PlayerId=Annotated[int,Field(strict=True,ge=1,le=2147483647)]
Gameweek=Annotated[int,Field(strict=True,ge=1,le=38)]

class TeamSheetRequest(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True,allow_inf_nan=False)
    teamId:PlayerId
    gameweeks:Annotated[list[Gameweek],Field(min_length=1,max_length=38)]
    modelUpdatedAt:Annotated[str|None,Field(max_length=100)]=None

    @field_validator("gameweeks")
    @classmethod
    def unique_weeks(cls,value):
        if len(value)!=len(set(value)):raise ValueError("Duplicate gameweeks are not allowed.")
        return sorted(value)

class TransferRequest(TeamSheetRequest):
    numberOfTransfers:Annotated[int,Field(strict=True,ge=0,le=3)]=1
    bankOverride:Annotated[float|None,Field(ge=0,le=1000)]=None
    transferHit:Literal[0,4,8,12]=0
    excludedPlayerIds:Annotated[list[PlayerId],Field(max_length=2000)]=Field(default_factory=list)

    @field_validator("transferHit",mode="before")
    @classmethod
    def strict_hit(cls,value):
        if type(value) is not int:raise ValueError("Transfer cost must be an integer.")
        return value

    @field_validator("excludedPlayerIds")
    @classmethod
    def unique_ids(cls,value):
        if len(value)!=len(set(value)):raise ValueError("Duplicate excluded Player IDs.")
        return value

class TransferMove(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    outId:PlayerId
    inId:PlayerId

class TransferPreviewRequest(TransferRequest):
    moves:Annotated[list[TransferMove],Field(max_length=3)]=Field(default_factory=list)


class BestSquadRequest(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True,allow_inf_nan=False)
    gameweek:Gameweek
    budget:Annotated[float,Field(ge=95,le=115)]=100.0
    banned_player_ids:Annotated[list[PlayerId],Field(max_length=2000)]=Field(default_factory=list)
    modelUpdatedAt:Annotated[str|None,Field(max_length=100)]=None

    @field_validator("budget")
    @classmethod
    def budget_step(cls,value):
        if abs(value*10-round(value*10))>1e-8:
            raise ValueError("Budget must use increments of 0.1 million.")
        return value

    @field_validator("banned_player_ids")
    @classmethod
    def unique_bans(cls,value):
        if len(value)!=len(set(value)):raise ValueError("Duplicate banned Player IDs.")
        return value
