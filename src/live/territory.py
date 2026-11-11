"""Versioned, source-backed territory tree and exact descendant filtering."""
from __future__ import annotations
from src.live.i18n import tr as _tr
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class Territory:
    id: str
    name: str
    parent_id: str | None
    region_id: str
    map_id: str = "teyvat"
    layer_id: str = "surface"
    kind: str = "area"


class TerritoryIndex:
    def __init__(self,nodes: list[Territory]):
        self.nodes={n.id:n for n in nodes}
        if len(self.nodes)!=len(nodes):
            raise ValueError(_tr("Território duplicado"))
        self.children={key:[] for key in self.nodes}
        for node in nodes:
            if node.parent_id is not None:
                if node.parent_id not in self.nodes:
                    raise ValueError(_tr('Área sem pai: {0}', node.id))
                parent=self.nodes[node.parent_id]
                if parent.region_id!=node.region_id:
                    raise ValueError(_tr("Área vinculada a outra região"))
                self.children[node.parent_id].append(node.id)
        self._descendants={}
        for node in nodes:
            self._walk(node.id,set())

    def _walk(self,identifier,visiting):
        if identifier in visiting:
            raise ValueError(_tr("Ciclo na hierarquia territorial"))
        if identifier in self._descendants:
            return self._descendants[identifier]
        result={identifier}
        for child in self.children[identifier]:
            result.update(self._walk(child,visiting|{identifier}))
        self._descendants[identifier]=frozenset(result)
        return self._descendants[identifier]

    def descendants(self,identifier):
        return self._descendants.get(identifier,frozenset())

    def path(self,identifier):
        names=[]
        while identifier in self.nodes:
            node=self.nodes[identifier];names.append(node.name);identifier=node.parent_id
        return " → ".join(reversed(names))

    def search(self,region_id,query=""):
        query=query.casefold().strip()
        return sorted((n for n in self.nodes.values() if n.region_id==region_id and
                       (not query or query in self.path(n.id).casefold())),key=lambda n:self.path(n.id))


def load_inventory(path: Path) -> tuple[dict,TerritoryIndex]:
    data=json.loads(path.read_text(encoding="utf-8"))
    return data,TerritoryIndex([Territory(**row) for row in data["territories"]])
