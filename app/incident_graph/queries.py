"""Domain queries over the Incident Graph store."""

from datetime import datetime

from app.incident_graph.models import GraphNode, NodeType
from app.incident_graph.store import NetworkXIncidentGraph


class IncidentGraphQueries:
    def __init__(self, graph: NetworkXIncidentGraph) -> None:
        self.graph = graph

    def dependencies(self, service_id: str, *, max_depth: int = 3) -> list[GraphNode]:
        found = []
        seen = {service_id}
        frontier = [service_id]
        for _depth in range(max_depth):
            next_frontier = []
            for node_id in frontier:
                for _edge, node in self.graph.outgoing(node_id, "depends_on"):
                    if node.id in seen:
                        continue
                    seen.add(node.id)
                    found.append(node)
                    next_frontier.append(node.id)
            frontier = next_frontier
            if not frontier:
                break
        return found

    def impacted_services(self, failed_service_id: str) -> list[GraphNode]:
        return [
            node
            for _edge, node in self.graph.incoming(
                failed_service_id,
                "depends_on",
            )
            if node.type is NodeType.SERVICE
        ]

    def correlated_changes(
        self,
        service_id: str,
        *,
        start: str | datetime,
        end: str | datetime,
    ) -> list[GraphNode]:
        start_at = datetime.fromisoformat(start) if isinstance(start, str) else start
        end_at = datetime.fromisoformat(end) if isinstance(end, str) else end
        output = []
        for _edge, node in self.graph.outgoing(service_id, "changed_by"):
            timestamp = node.properties.get("timestamp")
            if not isinstance(timestamp, str):
                continue
            changed_at = datetime.fromisoformat(timestamp)
            if start_at <= changed_at <= end_at:
                output.append(node)
        return output

    def similar_incidents(self, incident_id: str) -> list[GraphNode]:
        current = self.graph.get_node(incident_id)
        if current is None or current.type is not NodeType.INCIDENT:
            return []
        error_code = current.properties.get("error_code")
        return [
            node
            for node in self.graph.nodes(NodeType.INCIDENT)
            if node.id != incident_id
            and error_code is not None
            and node.properties.get("error_code") == error_code
        ]
