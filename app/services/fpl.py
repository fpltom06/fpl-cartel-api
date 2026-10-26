from collections import OrderedDict
from copy import deepcopy
from threading import RLock
import time
import httpx
from app.errors import ApiError

class FplClient:
    def __init__(self,settings,client=None):
        self.settings=settings
        self.client=client or httpx.Client(base_url=settings.fpl_base_url,timeout=settings.timeout,
            headers={"User-Agent":"FPL-Cartel-personalized-api/1.0"},follow_redirects=False)
        self.cache=OrderedDict()
        self.lock=RLock()

    def get(self,path,ttl):
        # Small per-worker bounded cache; avoids a burst of duplicate upstream requests.
        with self.lock:
            cached=self.cache.get(path)
            if cached and cached[0]>time.monotonic():
                self.cache.move_to_end(path)
                return deepcopy(cached[1])
            try:
                response=self.client.get(path)
                if response.status_code==404:
                    raise ApiError(404,"team_not_found","FPL team or published picks were not found.")
                if response.status_code==429:
                    raise ApiError(503,"fpl_rate_limited","FPL is rate limiting requests. Please retry later.")
                response.raise_for_status()
                data=response.json()
            except ApiError:raise
            except (httpx.HTTPError,ValueError):
                raise ApiError(503,"fpl_unavailable","FPL data is unavailable. Please retry.") from None
            if not isinstance(data,dict):
                raise ApiError(503,"fpl_unavailable","FPL returned an unexpected response.")
            self.cache[path]=(time.monotonic()+ttl,data)
            self.cache.move_to_end(path)
            while len(self.cache)>256:self.cache.popitem(last=False)
            return deepcopy(data)

    def bootstrap(self):
        data=self.get("bootstrap-static/",self.settings.metadata_ttl)
        if not isinstance(data.get("elements"),list) or not isinstance(data.get("teams"),list):
            raise ApiError(503,"fpl_unavailable","FPL player metadata is unavailable.")
        return data

    def history(self,team_id):
        data=self.get(f"entry/{team_id}/history/",self.settings.manager_ttl)
        if not isinstance(data.get("chips"),list):
            raise ApiError(503,"chip_history_unavailable","Chip history could not be verified. No Free Hit fallback was used.")
        return data

    def picks(self,team_id,gw):
        data=self.get(f"entry/{team_id}/event/{gw}/picks/",self.settings.manager_ttl)
        picks=data.get("picks")
        if not isinstance(picks,list):
            raise ApiError(503,"picks_unavailable","Published FPL squad picks are unavailable.")
        ids=[pick.get("element") for pick in picks if isinstance(pick,dict)]
        if len(ids)!=15 or len(set(ids))!=15 or any(type(i) is not int or i<=0 for i in ids):
            raise ApiError(503,"invalid_squad","FPL did not return 15 unique squad players.")
        if not isinstance(data.get("entry_history"),dict) or type(data["entry_history"].get("bank")) is not int or data["entry_history"]["bank"]<0:
            raise ApiError(503,"bank_unavailable","FPL squad bank is unavailable.")
        return data

    def close(self):self.client.close()

