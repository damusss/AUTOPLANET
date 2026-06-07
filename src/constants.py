import pygame
import string

# connection
MULTIPLAYER = False
OFFLINE_LOCALHOST = "offline_localhost"
ONLINE_LOCALHOST = "online_localhost"

CONNECT_MODE = OFFLINE_LOCALHOST

if CONNECT_MODE == OFFLINE_LOCALHOST:
    SERVER_SOCKET_ADDR = "localhost"
    CLIENT_SOCKET_ADDR = SERVER_SOCKET_ADDR
    SERVER_SOCKET_PORT = 5555
    CLIENT_SOCKET_PORT = SERVER_SOCKET_PORT
elif CONNECT_MODE == ONLINE_LOCALHOST:
    SERVER_SOCKET_ADDR = "localhost"
    SERVER_SOCKET_PORT = 5555
    CLIENT_SOCKET_ADDR = None  # "2.tcp.eu.ngrok.io"
    CLIENT_SOCKET_PORT = None  # 17812

SOCKET_RECV = 4096

HEARTBEAT_TIMEOUT = 10
HEARTBEAT = 1
CLIENT_PID_COOLDOWN = 3
CLIENT_TIMEOUT = 10

# camera
UNIT_DIV = 30
ZOOM_CLAMP = (0.4, 4)
CAMERA_LIMIT_DIV = 3

RESEARCH_ZOOM_CLAMP = (0.5, 2)

# physics
CLIENT_FPS = 244
SERVER_FPS = 144

GRAVITY = 9.81 * 5
ZERO = 1e-6
DIGIT_PRECISION = 5

# player
PLAYER_SIZE = 1
PLAYER_SPAWN_Y = -25
PLAYER_REACH_RADIUS = 10
PLAYER_BUILD_RADIUS = 18
PLAYER_INTERACT_RADIUS = 20

PLAYER_LIGHT_RADIUS = 14
PLAYER_LIGHT_INTENSITY = 200
PLAYER_LIGHT_COLOR = (255, 255, 255)

PLAYER_HITBOX = 0.75, 0.9
PLAYER_HITBOX_OFFSET = 0, 0.05

PLAYER_BREAK_SPEED = 1
PLAYER_SPEED = 10
PLAYER_JUMP_SPEED = 120
PLAYER_MAX_VEL = -16
PLAYER_TERMINAL_VEL = 40

PLAYER_MAX_ENERGY = 100
PLAYER_ENERGY_DEPLEAT_SPEED = 65
PLAYER_ENERGY_REGEN_SPEED = 300

PLAYER_MAX_HEALTH = 100
PLAYER_HEALTH_REGEN_COOLDOWN = 2000
PLAYER_HEALTH_REGEN_AMOUNT = 2

MOLD_BREAK_DAMAGE_COOLDOWN = 500
MOLD_BREAK_DAMAGE = 10
SAFE_FALL_VEL = 25
FALL_DAMAGE = 10
FALL_DAMAGE_PER_TILE = 1

IDLE_FRAME_SPEED = 0.35
RUN_FRAME_SPEED = 0.1

REITERATE_BREAK_TIME_MULT = 0.5

# inventory
INVENTORY_COLS = 8
INVENTORY_ROWS = 5
INVENTORY_HOTBAR_SIZE = 8
INVENTORY_HAND_I: int = INVENTORY_COLS * INVENTORY_ROWS

INVENTORY_ACTION_SWAP = "swap"
INVENTORY_ACTION_MOVE = "move"
INVENTORY_ACTION_DROP = "drop"
INVENTORY_ACTION_CONCENTRATE = "concentrate"

INVENTORY_FILTER_WHITELIST = "whitelist"
INVENTORY_FILTER_CATEGORY = "category"
INVENTORY_FILTER_READONLY = "readonly"
INVENTORY_FILTER_SENTINEL_SHORTCUT = "shortcut"

ITEM_CATEGORY_NAMES = {
    "tools": "Tools",
    "bot_upgrades": "Bot Upgrades",
    "equipment": "Equipment",
    "pets": "Pets",
    "smeltables": "Smeltables",
    "smelter_smeltables": "Smelter-only Smeltables",
    "research_chips": "Research Chips #2, #3, #4",
}

CRAFT_READY = "ready"
CRAFT_READY_SUBSTEP = "ready_substep"
CRAFT_NOT_READY = "not_ready"
CRAFT_UNAVAILABLE = "unavailable"

CRAFT_STATUS_MISSING_REQUIREMENTS = "missing_requirements"
CRAFT_STATUS_NOT_CRAFTABLE = "not_craftable"
CRAFT_STATUS_NO_HANDS = "no_hands"

DEFAULT_STACK_SIZE = 200
BUILDING_DEFAULT_STACK_SIZE = 50
PLATFORM_DEFAULT_STACK_SIZE = 120

INVENTORY_KIND_INPUT = "input"
INVENTORY_KIND_OUTPUT = "output"
INVENTORY_KIND_IN_OUT = "in_out"

DROP_SIZE = 0.35
DROP_IMAGE_SIZE = 0.4
DROP_ANIM_H = 0.05
DROP_ANIM_TIME_MULT = 1 / 150

CREATE_HANDS = "hands"

CRAFTER_INVENTORY_SIZE = 6
CRAFTER_NOZZLE_LERP_SPEED = 30

# chunk
CHUNK_SIZE = 12
RENDER_DISTANCE = (10, 8)
AMBIENT_COLOR = (20, 20, 20, 255)

TILE_NOT_SOLID_COLOR_MULT = (80, 80, 80)

RAYCAST_EMPTY = "empty"
RAYCAST_DROP = "drop"
RAYCAST_TILE = "tile"
RAYCAST_BUILDING = "building"
RAYCAST_VEGETATION = "vegetation"
RAYCAST_UI_ITEM = "item"
RAYCAST_UI_SLOT_FILTER = "slot_filter"

RAYCASTFLAG_CHUNK = "chunk"
RAYCASTFLAG_DEFAULT = "default"
RAYCASTFLAG_COLLIDER = "collider"
RAYCASTFLAG_VEGETATION = "vegetation"
RAYCASTFLAG_INFO = "info"
RAYCASTFLAG_ALL = "all"

BUILDING_ID_LEN = 10
BUILDING_ID_ALPHABET = string.ascii_letters + string.digits + string.punctuation

BUILDING_MAX_SIZE = 3

BOT_SPEED_PS = 3.5
BOT_TRAJECTORY_MAX_SIZE = 30
TRAJECTORY_STEP_SIZE = 1
BOT_ANIM_H = 0.3
BOT_ANIM_TIME_MULT = 1 / 150

DEFAULT_BUILDING_BREAK_TIME_S = 3
DEFAULT_PLATFORM_BREAK_TIME_S = 0.5

BUILDING_STATUS_WRONG_ALTITUDE = "wa"
BUILDING_STATUS_MISSING_FLOOR = "mf"
BUILDING_STATUS_WRONG_FLOOR = "wf"
BUILDING_STATUS_WRONG_AND_MISSING_FLOOR = "wmf"
BUILDING_STATUS_COULD_BE_MISSING_FLOOR_OR_TILE = "cmft"
BUILDING_STATUS_MISSING_FLOOR_AND_TILE = "mft"
BUILDING_STATUS_OBSTRUCTED = "o"
BUILDING_STATUS_PLAYER_IN_THE_WAY = "pitw"
BUILDING_STATUS_TOO_FAR = "tf"
BUILDING_STATUS_MISSING_VEGETATION = "mv"
BUILDING_STATUS_AVAILABLE = "a"

TILE_PLACED = "p"
TILE_BACKGROUND_FLIP = "b"
TILE_PLACED_BACKGROUND_FLIP = "pb"

VEGETATION_MAX_SIZE = 4

ENDPOINT_MACHINE = "machine"
ENDPOINT_RESEARCH = "research"

COMPUTER_SQUARE_RADIUS = 4

# ui generic
DOUBLE_CLICK_TIME = 0.3

FONT_MIN_SIZE = 9 + 7

UI_RAYCAST_EMPTY = object()

CURSOR_IDLE_WORLD = pygame.SYSTEM_CURSOR_CROSSHAIR
CURSOR_IDLE_UI = pygame.SYSTEM_CURSOR_ARROW
CURSOR_HOVER = pygame.SYSTEM_CURSOR_HAND
UI_CURSOR_OFFSET = 10

DRAG_PLACE_START_COOLDOWN = 500
DAMAGE_OVERLAY_DISAPPEAR_COOLDOWN = 600
DAMAGE_OVERLAY_SHOW_IF_DAMAGE_ATLEAST = 5

# ui colors
GREEN_GOOD = "#00DD93"
RED_BAD = "#EE0055"
YELLOW_WARNING = "#ffc800"

TRAJECTORY_COLOR = GREEN_GOOD
TRAJECTORY_ERROR_COLOR = RED_BAD

CRAFTING_SLOT_COLORS = {
    CRAFT_READY: GREEN_GOOD,
    CRAFT_UNAVAILABLE: RED_BAD,
    CRAFT_NOT_READY: "#C345AA",
    CRAFT_READY_SUBSTEP: "#B8DD73",
}

HOVERING_TILE_COLOR = "#FFC800"
HOVERING_TILE_FAR_COLOR = "#FF5404"
HOVERING_TILE_UNAVAILABLE_COLOR = RED_BAD

ENERGY_DEBUG_COLOR = "#00CCFF"
NO_ENERGY_DEBUG_COLOR = RED_BAD

PLAYER_NAME_UI_COLOR = "#00BB93"
OTHER_PLAYER_NAME_UI_COLOR = "#888888"

UI_HEALTH_COL = "#FF1000"
UI_ENERGY_COL = "#9C24FF"
UI_BARS_OUTLINE_COL = (100, 100, 100, 255)

UI_INFO_DESCR_COL = (180, 180, 180)

OUTLINE_DIRECTIONS = [
    (-1, -1),
    (1, 1),
    (-1, 1),
    (1, -1),
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1),
]

UI_PAUSE_OVERLAY_COL = (22, 22, 22, 255)

UI_RESEARCH_PROGRESS_COL = "#9C24FF"
UI_RESEARCH_PROGRESS_BG_COL = "#300a4f"
COMPUTER_DEBUG_COLOR = UI_RESEARCH_PROGRESS_COL
UI_COMPUTER_DEBUG_INDICATOR_COLOR = "#ac05fa"

# ui alpha

OPAQUE = 255

BUILDING_PREVIEW_ALPHA = 220
ENERGY_DEBUG_ALPHA = 20
COMPUTER_DEBUG_ALPHA = 40
PLAYER_NAME_UI_ALPHA = 150

UI_PANEL_BG_ALPHA = 150
UI_PANEL_BG_OPAQUE_ALPHA = 200
UI_PANEL_OUTLINE_ALPHA = 130
UI_PANEL_OUTLINE_HOVER_ALPHA = 255

UI_SLOT_GHOST_ALPHA = 100
UI_SLOT_PROGRESS_ALPHA = 170
UI_INTERFACE_ICON_ALPHA = 40

GHOST_INDICATOR_ALPHA = 110
OPAQUE_INDICATOR_ALPHA = 220

UI_ICON_BTN_ALPHA = 185
UI_PAUSE_OVERLAY_ALPHA = 150

# ui size

PLAYER_NAME_UI_HEIGHT = 0.2
TRAJECTORY_ARROW_SIZE = 1

UI_BORDER_PERCENT = 0.28
UI_OUTLINE_W = 2

UI_DEBUG_INDICATORS_H_MULT = 0.035

UI_BARS_W_MULT = 0.14
UI_BARS_H_MULT = 0.08

UI_RAYCAST_INFO_W_MULT = 0.11
UI_RAYCAST_INFO_TITLE_H_MULT = 0.15
UI_RAYCAST_INFO_DESCR_MULT = 0.7
UI_RAYCAST_INFO_MSG_H_MULT = 0.12
UI_RAYCAST_INFO_SUBTITLE_H_MULT = 0.13
UI_RAYCAST_INFO_SMALL_NOTE_H_MULT = 0.10
UI_RAYCAST_INFO_CORNER_SIZE_MULT = 0.1

UI_INVENTORY_W_MULT = 0.6
UI_INVENTORY_H_MULT = 0.6
UI_INVENTORY_CORNER_SIZE_MULT = 0.025
UI_INVENTORY_TITLE_H_MULT = 0.06
UI_INVENTORY_PADDING_MULT = 0.03
UI_INVENTORY_TEXT_H_MULT = 0.05

UI_RESEARCH_TREE_W_MULT = 0.8
UI_RESEARCH_TREE_H_MULT = 0.8
UI_RESEARCH_TREE_CORNER_SIZE_MULT = 0.018
UI_RESEARCH_TREE_CARD_W_MULT = 1 / 5
UI_RESEARCH_TREE_HORIZ_SPACE_MULT = 1 / 4
UI_RESEARCH_TREE_VERT_SPACE_MULT = 1 / 25

UI_SLOT_CORNER_SIZE_MULT = 0.2
UI_SLOT_AMOUNT_H_MULT = 0.38
UI_SLOT_IMAGE_SIZE_MULT = 0.75
UI_SLOT_IMAGE_OFFSET_Y_MULT = 0.05

UI_CRAFTING_CATEOGORIES_H_MULT = 1.1
UI_CRAFTING_CATEGORIES_CORNER_SIZE_MULT = 0.2

UI_CRAFT_QUEUE_SLOT_SIZE_MULT = 0.028
UI_HOTBAR_SLOT_SIZE_MULT = 0.028

UI_EDIT_TRAJECTORY_TEXT_H = 0.015
UI_DRAG_ENABLED_TEXT_H = 0.012

UI_PAUSE_OVERLAY_LINE_HEIGHT = 2
UI_DAMAGE_OVERLAY_ZOOM = 0.92

UI_RESEARCH_CARD_H_MULT = 0.45
UI_RESEARCH_CORNER_SIZE_MULT = 0.05
UI_RESEARCH_NAME_H_MULT = 0.09
UI_RESEARCH_EMPTY_H_MULT = 0.07
UI_RESEARCH_SPACING_MULT = 0.02
UI_RESEARCH_PROGRESS_H_MULT = 0.08
UI_RESEARCH_CARDS_PER_ROW = 4
UI_RESEARCH_CARD_SMALL_W = 190


# ui text
BUILDING_STATUS_MESSAGES = {
    BUILDING_STATUS_WRONG_ALTITUDE: "Can only be placed in a specific altitude range (from Y <r1> to Y <r2>)",
    BUILDING_STATUS_OBSTRUCTED: "Area is obstructed.",
    BUILDING_STATUS_WRONG_FLOOR: "Cannot be placed on this floor/terrain.",
    BUILDING_STATUS_TOO_FAR: "Player is too far from the building location.",
    BUILDING_STATUS_MISSING_FLOOR: "Cannot be placed mid air.",
    BUILDING_STATUS_WRONG_AND_MISSING_FLOOR: "Requires a floor and of the correct kind.",
    BUILDING_STATUS_MISSING_FLOOR_AND_TILE: "Can only be placed without flooring when on top of background tiles.",
    BUILDING_STATUS_PLAYER_IN_THE_WAY: "Player is obstructing the building.",
    BUILDING_STATUS_MISSING_VEGETATION: "Can only be placed on top of a <vegetation>",
}


CRAFTING_INTERFACE_SECTIONS = [
    {
        "icon": "bricks",
        "rows": [
            [
                "nylium_platform",
                "core_platform",
                "deep_platform",
                "bricks_platform",
                "iron_platform",
                "copper_platform",
                "titanium_platform",
            ],  # platforms
            [
                "hopper",
                "storage",
                "nylium_harvester",
                "furnace",
                "smelter",
                "miner",
                "laser_miner",
            ],  # survival
            ["bot", "crafter", "builder"],  # automation
            [
                "energy_plant",
                "energy_transmitter",
            ],  # energy
            ["lamp", "fan", "mold_sanitizer", "mold_miner"],  # misc & mold
            [
                "computer",
                "laboratory",
                "satellite",
                "observatory",
                "satellite_antennas",
            ],  # research
        ],
    },
    {
        "icon": "gear",
        "rows": [
            ["core_brick", "deep_brick"],  # bricks
            ["copper", "copper_wires", "copper_pipe"],  # copper
            ["iron", "iron_gear", "iron_tank", "iron_plate"],  # iron
            ["titanium", "titanium_bolt", "titanium_plate"],  # titanium
            ["plastic", "glass", "ammonia"],  # other
        ],
    },
    {
        "icon": "microchip",
        "rows": [
            [
                "research_chip_1",
                "research_chip_2",
                "research_chip_3",
                "research_chip_4",
            ],  # research chips
            ["light_source", "laser", "solar_panels"],  # lighting
            ["cables", "microchip", "motherboard"],  # better gears
            [
                "antennas",
                "remote_controller",
            ],  # communication
            ["thruster", "lenses"],  # mechanics
        ],
    },
    {
        "icon": "upgrade",
        "rows": [
            ["pickaxe", "recycler", "mold_spray"],  # tools
            ["jetpack_1", "jetpack_2"],  # jetpack upgrade
            ["pet_collector", "pet_lamp"],  # pets
            ["bot_upgrade_speed", "bot_upgrade_mold"],  # bot upgrades
        ],
    },
]

RESEARCH_TREE_LAYOUT = [
    [
        ["automation_begins", "_same_h_"],
        ["connections", "_same_h_"],
    ],
    [
        ["nylium_farming", "_next_"],
        ["auto_transport", "_next_"],
    ],
    [["better_chip", "_next_"]],
    [["dummy", None]],
]
RESEARCH_TREE_BIGGEST_VERTICAL_AMOUNT = 0
for horizontal_layer in RESEARCH_TREE_LAYOUT:
    if len(horizontal_layer) > RESEARCH_TREE_BIGGEST_VERTICAL_AMOUNT:
        RESEARCH_TREE_BIGGEST_VERTICAL_AMOUNT = len(horizontal_layer)


# rendering
TILE_PX = 16
STAR_TEX_MULT = 10
ICON_SVG_SIZE = 256

# debug
DEBUG_PLAYER_HITBOX_COL = "green"
DEBUG_TILE_HITBOX_COL = "blue"
DEBUG_VEGETATION_HITBOX_COLOR = "yellow"
DEBUG_CHUNK_BORDER_COLOR = "red"
DISPLAY_FPS_COOLDOWN = 2
MAX_CLIENT_CONNECTIONS_PER_BUILDING = 10


# mail
def _mail_id() -> int:
    _mail_id._id += 1
    return _mail_id._id


_mail_id._id = 0

MAIL_ABORT = _mail_id(), ()
MAIL_HEARTBEAT = _mail_id(), ()
MAIL_CONNECT = _mail_id(), ()
MAIL_CONNECTION_ACCEPTED = _mail_id(), ("other_players",)
MAIL_DISCONNECT = _mail_id(), ()
MAIL_FORCE_DISCONNECT = _mail_id(), ()
MAIL_NAME = _mail_id(), ("name",)
MAIL_PLAYER_PHYSICS = _mail_id(), ("p", "v", "e", "r", "ds", "ms", "cq", "op")
MAIL_PLAYER_STATS = _mail_id(), ("health", "inventory", "hotbar")
MAIL_OTHER_PLAYER_CONNECT = _mail_id(), ("player_id", "pos", "name")
MAIL_OTHER_PLAYER_DISCONNECT = _mail_id(), ("player_id",)
MAIL_ANIMATION_UPDATE = _mail_id(), ("frame_kind", "frame_index")
MAIL_CHUNK_LOAD = _mail_id(), ("chunks", "refresh")
MAIL_CHUNK_UNLOAD = _mail_id(), ("chunk_keys",)
MAIL_INPUT_DIR = _mail_id(), ("dir",)
MAIL_INPUT_EVENT = _mail_id(), ("input_type", "button")
MAIL_MOUSE_POS = _mail_id(), ("pos",)
MAIL_BREAK_START = _mail_id(), ("time", "mult")
MAIL_INVENTORY_ACTION = _mail_id(), ("action", "source", "dest", "amount")
MAIL_CRAFT_REQUEST = _mail_id(), ("item_uid",)
MAIL_BUILDING_AVAILABLE = _mail_id(), ("building_uid", "pos")
MAIL_BUILDING_AVAILABLE_RESPONSE = _mail_id(), ("available",)
MAIL_PLACE_BUILDING = _mail_id(), ("building_uid", "pos")
MAIL_BUILDING_INTERACT = _mail_id(), ("building_id", "unsubscribe")
MAIL_REFRESH_BUILDING_INTERACT = _mail_id(), ("broken", "base_data", "building_data")
MAIL_BOT_TRAJECTORY = _mail_id(), ("bot_id", "target_id", "kind")
MAIL_BUILDING_CONFIG = _mail_id(), ("building_id",)
MAIL_TOGGLE_PAUSE = _mail_id(), ()
MAIL_PAUSE_STATUS = _mail_id(), ("paused",)
MAIL_COPY_CONFIG = _mail_id(), ("reset",)
MAIL_PASTE_CONFIG = _mail_id(), ()
MAIL_UPDATE_CONFIG_CLIPBOARD = _mail_id(), ("clipboard",)
MAIL_HOTBAR_ACTION = _mail_id(), ("i", "item_uid")
MAIL_UPDATE_RESEARCH = (
    _mail_id(),
    ("unlocked_items_uids", "researched_nodes_uids", "research_progress"),
)
MAIL_UPDATE_RESEARCH_PROGRESS = _mail_id(), ("node_uid", "progress")
MAIL_SUBSCRIBE_RESEARCH = _mail_id(), ("unsubscribe",)

# python
JSON_SEPS = (",", ":")
NEW_RENDER = True
