from fastapi import APIRouter
from typing import Callable

class CalDAVRouter(APIRouter):
    def report(self, path: str, **kwargs) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_api_route(
                path,
                endpoint=func,
                methods=["REPORT"],
                **kwargs,
            )
            return func
        return decorator
    
    def propfind(self, path: str, **kwargs) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_api_route(
                path,
                endpoint=func,
                methods=["PROPFIND"],
                **kwargs,
            )
            return func
        return decorator

    def proppatch(self, path: str, **kwargs) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_api_route(
                path,
                endpoint=func,
                methods=["PROPPATCH"],
                **kwargs,
            )
            return func
        return decorator

    def mkcalendar(self, path: str, **kwargs) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.add_api_route(
                path,
                endpoint=func,
                methods=["MKCALENDAR"],
                **kwargs,
            )
            return func
        return decorator
