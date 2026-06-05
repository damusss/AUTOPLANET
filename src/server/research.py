from src import constants
from src import object_data
from src.server import god
from src.object_data import ResearchNodeOD, ItemOD
from src.server.player import Player


class Research:
    def __init__(self):
        god.research = self
        self.researched_nodes: set[ResearchNodeOD] = set()
        self.unlocked_items: set[ItemOD] = object_data.ITEMS_STARTER_PACK.copy()
        self.research_progress: dict = dict.fromkeys(ResearchNodeOD.get_iter(), 0)
        self.future_research_progress: dict = self.research_progress.copy()
        self.subscribed_client_players: set[Player] = set()

    def future_advance_research(self, node: ResearchNodeOD, amount: int):
        if node in self.researched_nodes:
            return
        self.future_research_progress[node] += amount

    def advance_research(self, node: ResearchNodeOD, amount: int):
        if node in self.researched_nodes:
            return
        self.research_progress[node] += amount
        if self.research_progress[node] >= node.cost:
            self.research_progress[node] = node.cost
            self.future_research_progress[node] = node.cost
            self.researched_nodes.add(node)
            for item in node.unlocks:
                self.unlocked_items.add(item)
            self.notify_research_progress(node)
            self.notify_research_info()
        else:
            self.notify_research_progress(node)

    def notify_research_info(
        self,
        players: list[Player] | None = None,
        include_progress=False,
        only_progress=False,
    ):
        if players is None:
            players = god.world.players.values()
        for player in players:
            player.client.conn.mail(
                constants.MAIL_UPDATE_RESEARCH,
                unlocked_items_uids=None
                if only_progress
                else [item.uid for item in self.unlocked_items],
                researched_nodes_uids=None
                if only_progress
                else [node.uid for node in self.researched_nodes],
                research_progress={
                    node.uid: progress
                    for node, progress in self.research_progress.items()
                }
                if include_progress or only_progress
                else None,
            )

    def subscribe_player(self, player: Player, unsubscribe: bool):
        if unsubscribe:
            self.subscribed_client_players.discard(player)
            return
        self.subscribed_client_players.add(player)
        self.notify_research_info([player], only_progress=True)

    def notify_research_progress(self, node: ResearchNodeOD):
        for player in self.subscribed_client_players:
            player.client.conn.mail(
                constants.MAIL_UPDATE_RESEARCH_PROGRESS,
                node_uid=node.uid,
                progress=self.research_progress[node],
            )

    def get_available_nodes_for_computer(self):
        available = []
        for node in ResearchNodeOD.get_iter():
            if (
                all((req in self.researched_nodes for req in node.required_nodes))
                and node not in self.researched_nodes
            ):
                available.append(node)
        return available
