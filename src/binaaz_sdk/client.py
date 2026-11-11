from __future__ import annotations

from typing import Any, Mapping, Optional

from ._core import AsyncEngine, Op, SyncEngine
from .resources import Auth, Catalog, Items, Photos


class _Namespaces:
    settings: Any

    def _mount(self) -> None:
        self.auth = Auth(self)
        self.items = Items(self)
        self.photos = Photos(self)
        self.catalog = Catalog(self)

    @staticmethod
    def _query(query: str, variables: Optional[Mapping[str, Any]], operation_name: Optional[str],
               safe: bool) -> Op:
        body: dict[str, Any] = {"query": query, "variables": dict(variables or {})}
        if operation_name:
            body["operationName"] = operation_name
        return Op("POST", "base_url", "graphql", body=body, safe=safe)


class BinaAz(SyncEngine, _Namespaces):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._mount()

    def profile(self) -> Any:
        return self.auth.profile()

    def graphql(self, query: str, variables: Optional[Mapping[str, Any]] = None, *,
                operation_name: Optional[str] = None, safe: bool = False) -> Any:
        return self._run(self._query(query, variables, operation_name, safe))


class AsyncBinaAz(AsyncEngine, _Namespaces):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._mount()

    async def profile(self) -> Any:
        return await self.auth.profile()

    async def graphql(self, query: str, variables: Optional[Mapping[str, Any]] = None, *,
                      operation_name: Optional[str] = None, safe: bool = False) -> Any:
        return await self._run(self._query(query, variables, operation_name, safe))
