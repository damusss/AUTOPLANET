import pygame

from src import shared
from src import constants
from src.server import god
from src.timerc import timerc
from src.shared import Slot
from src.object_data import ItemOD, ResearchNodeOD, BuildingOD
from src.server.building import StaticBuildingExt
from src.server.inventory import BuildingInventory


class Laboratory(StaticBuildingExt, name_id="laboratory"):
    def init(self):
        self.slot = Slot(
            None, 0, filter_=[constants.INVENTORY_FILTER_CATEGORY, ["research_chips"]]
        )
        self.inventories["in"] = BuildingInventory(self, self.slot)
        self.working = False
        self.work_start_time = 0
        self.working_for: Computer | None = None
        self.near_computers: set[Computer] = set()
        self.last_amount = -1

    def stop_working(self):
        self.working = False
        self.working_for = None
        self.building.change_state("off")

    def can_work_for_computer(self, computer: "Computer"):
        return (
            self.building.has_energy
            and not self.building.moldy
            and (not self.working or self.working_for is computer)
            and computer.active_node is not None
            and self.in_inv.has(computer.active_node.required_chip, 1)
        )

    def is_busy(self, computer: "Computer"):
        return self.working and not self.working_for is computer

    def missing_resources(self, computer: "Computer"):
        return (
            not self.building.has_energy
            or self.building.moldy
            or computer.active_node is None
            or not self.in_inv.has(computer.active_node.required_chip, 1)
        )

    def start_working_for_computer(self, computer: "Computer"):
        self.working = True
        self.work_start_time = god.world.get_ticks()
        self.working_for = computer
        self.in_inv.remove(computer.active_node.required_chip, 1)
        self.building.change_state("on")
        self.building.chunk.refresh()

    def notify_computers_ready_to_work(self):
        for computer in self.near_computers:
            if not computer.working:
                computer.try_to_work()
                if self.working:
                    return

    def on_energy_awake(self):
        if not self.working:
            self.notify_computers_ready_to_work()

    def on_mold_purge(self):
        if not self.working:
            self.notify_computers_ready_to_work()

    def on_inventory_dirty(self):
        if not self.working:
            self.notify_computers_ready_to_work()
        self.building.refresh_interact()
        if self.in_inv.empty or self.slot.amount != self.last_amount:
            self.building.chunk.refresh()
            self.last_amount = self.slot.amount

    def on_place(self):
        super().on_place()
        for computer in self.building.chunk.computers:
            area_hitbox = computer.area_hitbox
            if self.building.hitbox.colliderect(area_hitbox):
                computer.near_laboratories.add(self)
                self.near_computers.add(computer)
                computer.building.chunk.refresh()

    def on_destroy(self):
        self.drop_inventories()
        for computer in self.near_computers:
            computer.near_laboratories.discard(self)

    def get_client_data(self):
        data = self.get_inventories_data()
        data["working"] = self.working
        data["work_start_time"] = shared.eval_delta(self.work_start_time)
        data["contribute_node_uid"] = ResearchNodeOD.uid_or_none(
            self.working_for.work_active_node if self.working_for is not None else None
        )
        return data

    def get_extra_data(self):
        if self.working:
            return {"chip_uid": self.working_for.work_active_node.required_chip.uid}
        return None if self.in_inv.empty else {"chip_uid": self.slot.item.uid}

    def get_extra_raycast_data(self):
        sections = [
            [
                "Contains",
                [
                    ["text", constants.UI_INFO_DESCR_COL, "(empty)"]
                    if self.in_inv.empty
                    else ["item", self.slot.item.uid, self.slot.amount]
                ],
            ]
        ]
        if self.working:
            node = self.working_for.work_active_node
            sections.append(
                [
                    "Research",
                    [
                        [
                            "research",
                            node.uid,
                            god.research.research_progress[node] / node.cost,
                        ],
                        [
                            "progress",
                            (god.world.get_ticks() - self.work_start_time)
                            / 1000
                            / node.required_chip.research_time,
                            "research",
                        ],
                    ],
                ]
            )
        return sections


class Computer(StaticBuildingExt, name_id="computer"):
    @property
    def area_hitbox(self):
        return pygame.FRect(
            0,
            0,
            constants.COMPUTER_SQUARE_RADIUS * 2 + self.building.hitbox.width,
            constants.COMPUTER_SQUARE_RADIUS * 2 + self.building.hitbox.height,
        ).move_to(center=self.building.hitbox.center)

    def init(self):
        self.slot = Slot(
            None,
            0,
            [
                constants.INVENTORY_FILTER_WHITELIST,
                ["remote_controller", "research_chip_1"],
            ],
        )
        self.inventories["in"] = BuildingInventory(self, self.slot)
        self.active_node: ResearchNodeOD | None = None
        self.work_active_node: ResearchNodeOD | None = None
        self.working = False
        self.work_start_time = 0
        self.work_advance_amount = 1
        self.near_laboratories: set[Laboratory] = set()
        self.registered_chunks: set = set()
        self.employed_laboratories: list[Laboratory] = []

    def on_energy_awake(self):
        if not self.working:
            self.try_to_work()

    def on_mold_purge(self):
        if not self.working:
            self.try_to_work()

    def on_inventory_dirty(self):
        if not self.working:
            self.try_to_work()
        self.building.refresh_interact()

    def stop_working(self):
        self.working = False
        for lab in self.employed_laboratories:
            lab.stop_working()
        self.employed_laboratories = []
        self.building.change_state("off", refresh_interact=True)

    def try_to_work(self):
        if not self.building.has_energy or self.building.moldy:
            return False
        if self.active_node is None:
            return False
        if (
            self.active_node in god.research.researched_nodes
            or god.research.future_research_progress[self.active_node]
            >= self.active_node.cost
        ):
            self.active_node = None
            return False
        if self.active_node.required_chip == ItemOD.objects.research_chip_1:
            if not self.in_inv.has(self.active_node.required_chip, 1):
                return False
            self.working = True
            self.work_start_time = god.world.get_ticks()
            self.work_active_node = self.active_node
            self.employed_laboratories = []
            self.work_advance_amount = 1
            self.in_inv.remove(self.active_node.required_chip, 1)
            god.research.future_advance_research(self.active_node, 1)
            self.building.change_state("on", refresh_interact=True)
            timerc.add(
                self.active_node.required_chip.research_time, self.on_finish_work
            )
            return True
        else:
            if not self.in_inv.has(ItemOD.objects.remote_controller, 1):
                return False
            free_labs = []
            for lab in self.near_laboratories:
                if lab.can_work_for_computer(self):
                    free_labs.append(lab)
            if len(free_labs) <= 0:
                return False
            labs_needed = min(
                len(free_labs),
                self.active_node.cost
                - god.research.future_research_progress[self.active_node],
            )
            if labs_needed != len(free_labs):
                free_labs = free_labs[:labs_needed]
            self.working = True
            self.work_start_time = god.world.get_ticks()
            self.work_active_node = self.active_node
            self.employed_laboratories = free_labs
            self.work_advance_amount = labs_needed
            god.research.future_advance_research(
                self.active_node, self.work_advance_amount
            )
            for lab in self.employed_laboratories:
                lab.start_working_for_computer(self)
            self.building.change_state("on", refresh_interact=True)
            timerc.add(
                self.active_node.required_chip.research_time, self.on_finish_work
            )
            return True

    def on_finish_work(self):
        if self.destroyed or self.work_active_node is None:
            return
        god.research.advance_research(self.work_active_node, self.work_advance_amount)
        self.work_active_node = None
        previously_emplyed = set(self.employed_laboratories)
        if not self.try_to_work():
            self.stop_working()
        else:
            not_employed_anymore = previously_emplyed.difference(
                set(self.employed_laboratories)
            )
            for lab in not_employed_anymore:
                lab.stop_working()

    def on_place(self):
        super().on_place()
        area_hitbox = self.area_hitbox
        chunks = god.world.get_chunks_colliding_aligned_rect(pygame.Rect(area_hitbox))
        for chunk in chunks:
            chunk.computers.add(self)
            self.registered_chunks.add(chunk)
            for bid in chunk.building_ids:
                building = god.world.buildings[bid]
                if building.building_od == BuildingOD.objects.laboratory:
                    if building.hitbox.colliderect(area_hitbox):
                        lab: Laboratory = building.ext
                        lab.near_computers.add(self)
                        self.near_laboratories.add(lab)

    def on_destroy(self):
        self.drop_inventories()
        for chunk in self.registered_chunks:
            chunk.computers.discard(self)
        for lab in self.near_laboratories:
            lab.near_computers.discard(self)

    def on_client_config(self, mail):
        if mail.missing_fields("active_node_uid"):
            return
        if mail.active_node_uid is None:
            self.active_node = None
        else:
            node = ResearchNodeOD.get(mail.active_node_uid)
            if node not in god.research.get_available_nodes_for_computer():
                return
            self.active_node = node
            if not self.working:
                self.try_to_work()
        self.building.refresh_interact()

    def get_config(self):
        return {"active_node_uid": ResearchNodeOD.uid_or_none(self.active_node)}

    def get_client_data(self):
        data = self.get_inventories_data()
        data.update(self.get_config())
        data["available_nodes_uids"] = [
            node.uid for node in god.research.get_available_nodes_for_computer()
        ]
        data["working"] = self.working
        data["work_start_time"] = shared.eval_delta(self.work_start_time)
        data["work_advance_amount"] = self.work_advance_amount
        available_count = busy_count = missing_count = 0
        for lab in self.near_laboratories:
            if lab.can_work_for_computer(self):
                available_count += 1
            elif lab.is_busy(self):
                busy_count += 1
            elif lab.missing_resources(self):
                missing_count += 1
        if len(self.near_laboratories) <= 0:
            data["labs"] = None
        else:
            data["labs"] = {
                "employed": len(self.employed_laboratories),
                "nearby": len(self.near_laboratories),
                "available": available_count,
                "busy": busy_count,
                "missing": missing_count,
            }
        return data

    def get_extra_data(self):
        return [lab.building.hitbox.center for lab in self.near_laboratories]

    def get_extra_raycast_data(self):
        sections = []
        progress = (
            0
            if self.active_node is None
            else (
                god.research.research_progress[self.active_node] / self.active_node.cost
            )
        )
        if self.working:
            progress += (
                (god.world.get_ticks() - self.work_start_time)
                / 1000
                / self.active_node.required_chip.research_time
                / self.active_node.cost
            ) * self.work_advance_amount
        node_indicator = (
            ["text", constants.YELLOW_WARNING, "Not selected"]
            if self.active_node is None
            else [
                "research",
                self.active_node.uid,
                progress,
            ]
        )
        research_indicators = [node_indicator]
        sections.append(["Research", research_indicators])
        if (
            self.active_node is None
            or self.active_node.required_chip == ItemOD.objects.research_chip_1
        ):
            sections.append(
                [
                    "Contains",
                    [
                        ["text", constants.UI_INFO_DESCR_COL, "(empty)"]
                        if self.in_inv.empty
                        else ["item", self.slot.item.uid, self.slot.amount]
                    ],
                ]
            )
        else:
            if not self.in_inv.has(ItemOD.objects.remote_controller, 1):
                research_indicators.append(
                    [
                        "text",
                        constants.RED_BAD,
                        "Missing remote controller",
                    ]
                )
            laboratory_indicators = []
            if len(self.near_laboratories) <= 0:
                laboratory_indicators.append(["text", constants.RED_BAD, "None nearby"])
            else:
                if self.working:
                    laboratory_indicators.append(
                        [
                            "text",
                            constants.GREEN_GOOD,
                            f"> {len(self.employed_laboratories)} employed",
                        ]
                    )
                else:
                    available_count = busy_count = missing_count = 0
                    for lab in self.near_laboratories:
                        if lab.can_work_for_computer(self):
                            available_count += 1
                        elif lab.is_busy(self):
                            busy_count += 1
                        elif lab.missing_resources(self):
                            missing_count += 1
                    if available_count > 0:
                        laboratory_indicators.append(
                            [
                                "text",
                                constants.GREEN_GOOD,
                                f"> {available_count} available",
                            ]
                        )
                    if busy_count > 0:
                        laboratory_indicators.append(
                            ["text", constants.YELLOW_WARNING, f"> {busy_count} busy"]
                        )
                    if missing_count > 0:
                        laboratory_indicators.append(
                            [
                                "text",
                                constants.RED_BAD,
                                f"> {missing_count} missing requirements",
                            ]
                        )
                laboratory_indicators.append(
                    ["text", "white", f"{len(self.near_laboratories)} nearby"]
                )

            sections.append(["Chip Processors", laboratory_indicators])
        return sections
