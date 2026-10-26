from starlette.responses import JSONResponse

class RequestSizeLimit:
    def __init__(self,app,max_bytes):
        self.app=app;self.max_bytes=max_bytes
    async def __call__(self,scope,receive,send):
        if scope["type"]!="http" or scope["method"] not in {"POST","PUT","PATCH"}:
            return await self.app(scope,receive,send)
        data=bytearray()
        while True:
            message=await receive()
            if message["type"]=="http.disconnect":return
            data.extend(message.get("body",b""))
            if len(data)>self.max_bytes:
                response=JSONResponse(status_code=413,content={"error":{"code":"request_too_large","message":"Request body is too large."}})
                return await response(scope,receive,send)
            if not message.get("more_body",False):break
        sent=False
        async def replay():
            nonlocal sent
            if not sent:
                sent=True
                return {"type":"http.request","body":bytes(data),"more_body":False}
            return await receive()
        await self.app(scope,replay,send)

