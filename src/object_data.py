import os
import json
import typing
from dataclasses import dataclass

from src import constants


class ObjectDataInstanceGetter[T]:
    def __init__(self, cls):
        self._cls: type["ObjectData"] = cls

    def __getattr__(self, name: str) -> T:
        return self._cls.get(name)

    def __dir__(self):
        return list(self._cls.get_all().keys())


class ObjectSingleton:
    _registered_types_ = {}

    @classmethod
    def _init_(cls, attributes: dict):
        for name in cls.__annotations__.keys():
            setattr(cls, name, attributes[name])

    def __init_subclass__(cls):
        ObjectSingleton._registered_types_[cls.__name__] = cls


class ObjectData:
    uid: int
    name_id: str
    data_type: type

    display_name: str
    description: str

    _registered_types_ = {}

    def __init__(self, attributes: dict):
        if not hasattr(self, "_required_attributes_"):
            raise TypeError(
                "Cannot instantiate 'ObjectData' directly. Instantiate a valid subclass instead"
            )
        for name in self._required_attributes_:
            if name not in attributes:
                if name in self.__class__.DEFAULTS:
                    value = self.__class__.DEFAULTS[name]
                else:
                    raise KeyError(
                        f"Failed to instantiate '{self.__class__.__name__}' object data: missing attribute '{name}' (attributes: {attributes})"
                    )
            else:
                value = attributes[name]
            setattr(self, name, value)
            if name in self.__class__._registered_properties_:
                self.__class__._registered_properties_[name][value] = self
        self.__class__._registered_instances_[self.name_id] = self
        self.__class__._registered_uid_instances_[self.uid] = self
        self.setup()

    def __init_subclass__(cls, **arguments):
        if "type_name" not in arguments:
            raise TypeError(
                "Failed to create an ObjectData subclass. Missing argument 'type_name'"
            )
        cls._required_attributes_ = list(ObjectData.__annotations__.keys()) + list(
            cls.__annotations__.keys()
        )
        ObjectData._registered_types_[arguments["type_name"]] = cls
        cls.type_name = arguments["type_name"]
        cls._registered_instances_ = {}
        cls._registered_uid_instances_ = {}
        cls._registered_properties_ = {
            prop: {} for prop in arguments.get("registered_properties", [])
        }
        cls.objects = ObjectDataInstanceGetter[cls](cls)

    def __str__(self):
        res = f"[Object Data] {self.__class__.type_name}(\n"
        longest = max([len(attr) for attr in self._required_attributes_]) + 1
        for name in self._required_attributes_:
            value = getattr(self, name)
            if isinstance(value, type):
                continue
            if isinstance(value, ObjectData):
                value = repr(value)
            res += f"\t{name}".ljust(longest) + f": {value}\n"
        res += ")"
        return res

    def __repr__(self):
        return f"<Object Data '{self.__class__.type_name}': {self.name_id}:{self.uid}>"

    def __eq__(self, other: typing.Self):
        if not isinstance(other, ObjectData):
            return False
        return self.uid == other.uid and self.type_name == other.type_name

    def __hash__(self):
        return hash(self.uid)

    def setup(self): ...

    def post_setup(self): ...

    @classmethod
    def exists(cls, name_id_or_uid: str | int) -> bool:
        return (
            name_id_or_uid in cls._registered_instances_
            or name_id_or_uid in cls._registered_uid_instances_
        )

    @classmethod
    def get(cls, name_id_or_uid: str | int) -> typing.Self:
        if isinstance(name_id_or_uid, int):
            return cls.get_by_id(name_id_or_uid)
        return cls.get_by_name(name_id_or_uid)

    @classmethod
    def get_or[DT](cls, name_id_or_uid: str | int, default: DT) -> typing.Self | DT:
        if cls.exists(name_id_or_uid):
            return cls.get(name_id_or_uid)
        return default

    @classmethod
    def get_by_name(cls, name_id: str) -> typing.Self:
        if name_id in cls._registered_instances_:
            return cls._registered_instances_[name_id]
        raise KeyError(
            f"No object data instance '{name_id}' of type '{cls.type_name}' exists"
        )

    @classmethod
    def get_by_id(cls, uid: int) -> typing.Self:
        if uid in cls._registered_uid_instances_:
            return cls._registered_uid_instances_[uid]
        raise KeyError(f"No object with UID '{uid}' of type '{cls.type_name}' exists")

    @classmethod
    def get_by_prop(cls, property_name: str, prop) -> typing.Self:
        if property_name not in cls._registered_properties_:
            raise KeyError(
                f"Property '{property_name}' was not registered for '{cls.type_name}'"
            )
        if prop in cls._registered_properties_[property_name]:
            return cls._registered_properties_[property_name][prop]
        raise KeyError(
            f"No object data instance with property '{prop}' of type '{cls.type_name}' exists"
        )

    @classmethod
    def get_all(cls) -> dict[str, typing.Self]:
        return cls._registered_instances_

    @classmethod
    def get_list(cls) -> list[typing.Self]:
        return list(cls._registered_instances_.values())

    @staticmethod
    def get_type(type_name: str) -> "type[ObjectData]":
        return ObjectData._registered_types_[type_name]

    @staticmethod
    def global_setup(): ...


class TileOD(ObjectData, type_name="Tile"):
    DEFAULTS = {"miner_time_s": 0}

    item_drop: list[tuple["ItemOD", int]]
    break_requirements: list["ItemOD"]
    break_time_s: float
    miner_time_s: float

    def setup(self):
        if self.miner_time_s == 0:
            self.miner_time_s = self.break_time_s

    def post_setup(self):
        drop = []
        for name_id, amount in self.item_drop:
            drop.append((ItemOD.get(name_id), amount))
        self.item_drop = drop
        if self.break_requirements is not None:
            self.break_requirements = [
                ItemOD.get(req) for req in self.break_requirements
            ]


@dataclass
class ItemCreateData:
    type: str
    time_s: float
    amount: int
    recipe: list[tuple["ItemOD", int]]


class ItemOD(ObjectData, type_name="Item"):
    DEFAULTS = {
        "dropped_by": None,
        "category": None,
        "stack_size": "default",
        "smelt_result": None,
    }

    stack_size: int
    create_data: ItemCreateData | None
    smelt_result: "ItemOD|None"
    dropped_by: "TileOD|None"
    category: str | None

    @property
    def building(self):
        return BuildingOD.get_or(self.name_id, None)

    def setup(self):
        if self.description == "":
            self.description = "NOT IMPLEMENTED"
        if self.stack_size == "default":
            self.stack_size = constants.DEFAULT_STACK_SIZE
        elif self.stack_size == "default_building":
            self.stack_size = constants.BUILDING_DEFAULT_STACK_SIZE
        elif self.stack_size == "default_platform":
            self.stack_size = constants.PLATFORM_DEFAULT_STACK_SIZE
        if self.create_data is not None:
            self.create_data = ItemCreateData(
                self.create_data["type"],
                self.create_data["time_s"],
                self.create_data.get("amount", 1),
                self.create_data["recipe"],
            )

    def post_setup(self):
        if self.create_data is not None:
            recipe = self.create_data.recipe
            recipe_od = []
            for name_id, amount in recipe:
                recipe_od.append((ItemOD.get(name_id), amount))
            self.create_data.recipe = recipe_od
        if self.smelt_result is not None:
            self.smelt_result = ItemOD.get(self.smelt_result)
        if self.dropped_by is not None:
            self.dropped_by = TileOD.get(self.dropped_by)


@dataclass
class LightData:
    radius: float
    intensity: int
    color: str | list[int]


@dataclass
class BuildingStateData:
    default: bool
    default_image: bool
    name: str
    image_name: str
    light: LightData | None


class BuildingOD(ObjectData, type_name="Building"):
    DEFAULTS = {
        "restore_tile": None,
        "break_requirements": ["pickaxe", "titanium_pickaxe", "recycler"],
        "break_time_s": 0,
        "static": True,
        "description": "",
        "display_name": "",
        "floor_whitelist": None,
        "floor": False,
        "air": False,
        "replace_tile": False,
        "interface": True,
        "need_energy": True,
        "altitude_range": None,
        "states": None,
        "energy_radius": 0,
        "energy_endpoint_type": "machine",
        "hitbox_multiplier": 1,
        "inventory_kind": None,
        "vegetation_requirement": None,
    }

    size: tuple[int, int]
    need_energy: bool
    air: bool
    floor: bool
    static: bool
    replace_tile: bool
    interface: bool
    break_time_s: float
    energy_radius: float
    hitbox_multiplier: float
    altitude_range: tuple[int, int] | None
    floor_whitelist: list["TileOD | BuildingOD"]
    vegetation_requirement: "VegetationOD|None"
    restore_tile: TileOD | None
    break_requirements: list[ItemOD]
    states: dict[str, BuildingStateData]
    energy_endpoint_type: str
    inventory_kind: str | None

    @property
    def item(self):
        return ItemOD.get(self.name_id)

    def setup(self):
        if self.floor_whitelist is None:
            self.floor_whitelist = []
        if self.break_time_s == 0:
            if self.floor:
                self.break_time_s = constants.DEFAULT_PLATFORM_BREAK_TIME_S
            else:
                self.break_time_s = constants.DEFAULT_BUILDING_BREAK_TIME_S

    def post_setup(self):
        if self.restore_tile is not None:
            self.restore_tile = TileOD.get(self.restore_tile)
        if self.states is None:
            self.states = {"": {"default": True, "default_image": True}}
        floor = []
        for name in self.floor_whitelist:
            if TileOD.exists(name):
                floor.append(TileOD.get(name))
            else:
                floor.append(BuildingOD.get(name))
        self.floor_whitelist = floor
        states = {}
        for state_name, state_data in self.states.items():
            light = state_data.get("light", None)
            default = state_data.get("default", False)
            default_image = state_data.get("default_image", False)
            if len(self.states) == 1:
                default = default_image = True
            image_name = self.name_id
            if not default_image:
                image_name = f"{image_name}_{state_name}"
            state = BuildingStateData(
                default,
                default_image,
                state_name,
                image_name,
                LightData(light["radius"], light["intensity"], light["color"])
                if light
                else None,
            )
            states[state_name] = state
            if default:
                states["default"] = state
        self.states = states
        self.break_requirements = [ItemOD.get(req) for req in self.break_requirements]
        if self.vegetation_requirement is not None:
            self.vegetation_requirement = VegetationOD.get(self.vegetation_requirement)
        self.description = self.item.description
        self.display_name = self.item.display_name


class VegetationOD(ObjectData, type_name="Vegetation"):
    DEFAULTS = {
        "break_requirements": None,
        "item_drop": None,
        "light": None,
        "require_floor": True,
    }

    size: tuple[float, float]
    break_time_s: float
    break_requirements: list[ItemOD]
    light: LightData | None
    item_drop: list[tuple["ItemOD", int]]
    require_floor: bool

    def setup(self):
        if self.light is not None:
            self.light = LightData(
                self.light["radius"], self.light["intensity"], self.light["color"]
            )

    def post_setup(self):
        if self.item_drop is None:
            self.item_drop = []
        drop = []
        for name_id, amount in self.item_drop:
            drop.append((ItemOD.get(name_id), amount))
        self.item_drop = drop
        if self.break_requirements is not None:
            self.break_requirements = [
                ItemOD.get(req) for req in self.break_requirements
            ]


ITEMS_STARTER_PACK: set[str] = set()


class ResearchNodeOD(ObjectData, type_name="ResearchNode"):
    DEFAULTS = {"require_processor": True}

    path_name: str
    unlocks: list[ItemOD]
    required_chip: ItemOD
    required_nodes: list["ResearchNodeOD"]
    require_processor: bool

    def post_setup(self):
        self.required_chip = ItemOD.get(f"research_chip_{self.required_chip}")
        nodes = []
        for node_name in self.required_nodes:
            nodes.append(ResearchNodeOD.get(node_name))
        self.required_nodes = nodes
        unlocks = []
        for item in self.unlocks:
            unlocks.append(ItemOD.get(item))
        self.unlocks = unlocks

    @staticmethod
    def global_setup():
        all_item_names = set(ItemOD.get_all().keys())
        for research_node in ResearchNodeOD.get_list():
            for item in research_node.unlocks:
                all_item_names.discard(item.name_id)
        ITEMS_STARTER_PACK.update(all_item_names)


class BigStar(ObjectSingleton):
    size_range: tuple[float, float]
    dust_scale: float
    colors: list[str]
    chance: float


class Star(ObjectSingleton):
    size_range: tuple[float, float]
    chance: float


class BlackHole(ObjectSingleton):
    dust_scale: float
    size_range: tuple[float, float]
    chance: 0.007


class Dust(ObjectSingleton):
    num_range: tuple[int, int]
    size_range: tuple[float, float]
    gradient_a: str
    gradient_b: str


def load_all(objects_folder: str):
    with open(os.path.join(objects_folder, "_registry_.json"), "r") as reg_file:
        registry = json.load(reg_file)
    object_datas: list[ObjectData] = []
    object_types: list[type[ObjectData]] = []
    for folder in os.listdir(objects_folder):
        if folder.startswith("_registry_") or folder.startswith("_singletons_"):
            continue
        subdir_path = os.path.join(objects_folder, folder)
        if not os.path.isdir(subdir_path):
            raise FileExistsError(
                "Parent folder of object data should only contain subdirectories"
            )
        type_path = os.path.join(subdir_path, "_type_.json")
        if not os.path.exists(type_path):
            raise FileNotFoundError(
                f"Objects directory '{folder}' is missing '_type_.json'"
            )
        with open(type_path, "r") as type_file:
            type_name = json.load(type_file)
        if type_name not in ObjectData._registered_types_:
            raise KeyError(
                f"Object data type inside {type_path} '{type_name}' does not have a registered subclass"
            )
        if type_name not in registry:
            registry[type_name] = {}
            free_id = 0
        else:
            if len(registry[type_name]) <= 0:
                free_id = 0
            else:
                free_id = max(registry[type_name].values()) + 1
        data_type: type[ObjectData] = ObjectData._registered_types_[type_name]
        object_types.append(data_type)
        for cur_dir, _, files in os.walk(subdir_path):
            for file_name in files:
                if file_name.startswith("_type_"):
                    continue
                name_id = file_name.split(".")[0]
                if name_id not in registry[type_name]:
                    registry[type_name][name_id] = free_id
                    free_id += 1
                uid = registry[type_name][name_id]
                with open(os.path.join(cur_dir, file_name), "r") as file:
                    data_dict = json.load(file)
                    data_dict["uid"] = uid
                    data_dict["name_id"] = name_id
                    data_dict["data_type"] = data_type
                od = data_type(data_dict)
                object_datas.append(od)
    for od in object_datas:
        od.post_setup()
    for ot in object_types:
        ot.global_setup()
    for singleton_file in os.listdir(os.path.join(objects_folder, "_singletons_")):
        with open(
            os.path.join(objects_folder, "_singletons_", singleton_file), "r"
        ) as file:
            singleton_type = singleton_file.split(".")[0]
            singleton_data = json.load(file)
            if singleton_type not in ObjectSingleton._registered_types_:
                raise KeyError(
                    f"Singleton object '{singleton_file}' specifies an unregistered type '{singleton_type}'"
                )
            ObjectSingleton._registered_types_[singleton_type]._init_(singleton_data)
    with open(os.path.join(objects_folder, "_registry_.json"), "w") as reg_file:
        json.dump(registry, reg_file)
