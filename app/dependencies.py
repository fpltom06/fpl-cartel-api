from fastapi import Request
def service(request:Request):
    return request.app.state.optimizer

