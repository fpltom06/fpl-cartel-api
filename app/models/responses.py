from typing import Any,Literal
from pydantic import BaseModel,Field

class Player(BaseModel):
    playerId:int
    name:str
    club:str
    position:str
    price:float

class MissingPlayer(BaseModel):
    playerId:int
    name:str
    club:str
    position:str

class Diagnostics(BaseModel):
    squadCount:int
    matchedCount:int
    missingPlayers:list[MissingPlayer]
    squadPlayerIds:list[int]

class TeamResponse(BaseModel):
    teamId:int
    bank:float
    squadSourceGw:int
    freeHitDetected:bool
    players:list[Player]
    modelUpdatedAt:str
    loadedAt:str
    gameweeks:list[int]
    sourceGameweek:int
    planningGameweek:int
    ignoredFreeHitGameweeks:list[int]
    sourceNote:str
    diagnostics:Diagnostics
    transfers:Literal[0]=0
    weeks:list[Any]=[]
    overall:None=None

class PitchPlayer(Player):
    fixture:str
    projectedPoints:float
    isCaptain:bool
    isViceCaptain:bool

class WeeklySheet(BaseModel):
    gameweek:int
    formation:str
    startingXI:list[PitchPlayer]
    bench:list[PitchPlayer]
    captainPlayerId:int
    viceCaptainPlayerId:int
    xiProjection:float
    captainBonus:float
    projectedTotal:float

class MostCaptained(BaseModel):
    playerId:int
    name:str
    count:int
class HighestGameweek(BaseModel):
    gameweek:int
    projectedTotal:float
class Overall(BaseModel):
    total:float
    average:float
    mostCaptained:MostCaptained
    highestGameweek:HighestGameweek
class TeamSheetResponse(BaseModel):
    team:TeamResponse
    gameweeks:list[WeeklySheet]
    overall:Overall

class Move(BaseModel):
    out:Player
    # 'in' is a JSON field; use an alias.
    incoming:Player=Field(alias="in")
    model_config={"populate_by_name":True}

class Breakdown(BaseModel):
    gameweek:int
    out:float
    incoming:float=Field(alias="in")
    gain:float
    model_config={"populate_by_name":True}

class Recommendation(BaseModel):
    id:str
    moves:list[Move]
    outgoingProjection:float
    incomingProjection:float
    grossGain:float
    transferCost:int
    netGain:float
    cost:float
    bankAfter:float
    breakdown:list[Breakdown]
    updatedSquadIds:list[int]

class TransferResponse(BaseModel):
    originalSquad:TeamResponse
    moneyInBank:float
    bankUsed:float
    gameweeks:list[int]
    recommendations:list[Recommendation]
    originalTeamSheet:TeamSheetResponse
    searchNote:str

class PreviewResponse(BaseModel):
    updatedTeamSheet:TeamSheetResponse
    originalTotal:float
    updatedTotal:float
    grossTeamGain:float
    netTeamGain:float


