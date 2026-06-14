from src.server.building import StaticBuildingExt


class Lamp(StaticBuildingExt, name_id="lamp"):
    def on_energy_awake(self):
        if not self.building.moldy:
            self.building.change_state("on")

    def on_mold_purge(self):
        if self.building.has_energy:
            self.building.change_state("on")

    def on_energy_sleep(self):
        self.building.change_state("off")

    def on_mold_infect(self):
        self.building.change_state("off")
