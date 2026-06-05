from src.server.building import BuildingExt


class Lamp(BuildingExt, name_id="lamp"):
    def on_energy_awake(self):
        self.building.change_state("on")

    def on_energy_sleep(self):
        self.building.change_state("off")
