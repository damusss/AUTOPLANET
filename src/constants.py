# connection
OFFLINE_LOCALHOST = True
SOCKET_ADDR = "localhost"
SOCKET_PORT = 5555
SOCKET_RECV = 4096
HEARTBEAT_TIMEOUT = 10
HEARTBEAT = 1
CLIENT_PID_COOLDOWN = 5
CLIENT_TIMEOUT = 10

# camera
UNIT_DIV = 30
ZOOM_CLAMP = (0.4, 4)
CAMERA_LIMIT_DIV = 3

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

PLAYER_LIGHT_RADIUS = 15
PLAYER_LIGHT_INTENSITY = 255
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

IDLE_FRAME_SPEED = 0.35
RUN_FRAME_SPEED = 0.1

# inventory
INVENTORY_COLS = 8
INVENTORY_ROWS = 5
INVENTORY_HAND_I = INVENTORY_COLS * INVENTORY_ROWS

INVENTORY_ACTION_SWAP = "swap"
INVENTORY_ACTION_MOVE = "move"

INVENTORY_FILTER_WHITELIST = "whitelist"
INVENTORY_FILTER_CATEGORY = "category"
ITEM_CATEGORY_NAMES = {"tools": "Tools"}

# chunk
CHUNK_SIZE = 12
RENDER_DISTANCE = (10, 8)
AMBIENT_COLOR = (20, 20, 20, 255)

NYLIUM_HEIGHT = 6
HEIGHT_MULT = 30
UNDERGROUND_OFFSET = -1
NOISE_IS_BLOCK = 0.45
UNDERGROUND_HEIGHT = 100
UNDERGROUND_MULT = 10
TILE_NOT_SOLID_COLOR_MULT = (80, 80, 80)

RAYCAST_EMPTY = "empty"
RAYCAST_TILE = "tile"
RAYCAST_UI_ITEM = "item"
RAYCAST_UI_SLOT_FILTER = "slot_filter"

RAYCASTFLAG_CHUNK = "chunk"
RAYCASTFLAG_INFO = "info"
RAYCASTFLAG_COLLIDER = "collider"
RAYCASTFLAG_ALL = "all"

# items
CRAFT_HANDS = "hands"
CRAFT_FURNACE = "furnace"
CRAFT_CRAFTER = "crafter"
CRAFT_NONE = None

DEFAULT_STACK_SIZE = 200
BUILDING_DEFAULT_STACK_SIZE = 50
PLATFORM_DEFAULT_STACK_SIZE = 120
DROP_SIZE = 0.3
DROP_IMAGE_SIZE = 0.4

# ui
GREEN_GOOD = "#00DD93"
RED_BAD = "#EE0055"

HOVERING_TILE_COLOR = "#FFC800"
HOVERING_TILE_UNAVAILABLE_COLOR = "#ff0000"

FONT_MIN_SIZE = 9 + 7

CRAFTING_INTERFACE_SECTIONS = [
    {
        "icon": "bricks",
        "rows": [
            [
                "nylium_platform",
                "stone_platform",
                "deep_stone_platform",
                "bricks_platform",
                "iron_platform",
                "copper_platform",
                "titanium_platform",
            ],  # platforms
            [
                "hopper",
                "storage",
                "furnace",
                "smelter",
                "miner",
                "laser_miner",
            ],  # survival
            ["bot", "crafter", "builder"],  # automation
            ["mold_sanitizer", "mold_miner"],
            ["energy_plant", "energy_transmitter"],  # energy
            ["computer", "laboratory"],  # research
            ["satellite", "observatory", "satellite_antennas"],  # space research
            ["lamp", "fan"],  # misc
        ],
    },
    {
        "icon": "gear",
        "rows": [
            ["copper", "copper_wires", "copper_pipe"],  # copper
            ["iron", "iron_gear", "iron_tank"],  # iron
            ["titanium"],  # titanium
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
            ["light", "laser", "solar_panels"],  # lighting
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
            ["collector_pet", "lamp_pet"],  # pets
            ["bot_upgrade_speed", "bot_upgrade_mold"],  # bot upgrades
        ],
    },
]

PLAYER_NAME_UI_HEIGHT = 0.2
PLAYER_NAME_UI_COLOR = "#00BB93"
OTHER_PLAYER_NAME_UI_COLOR = "#888888"
PLAYER_NAME_UI_ALPHA = 150

UI_BORDER_PERCENT = 0.28
UI_RAYCAST_EMPTY = object()

UI_PANEL_BG_ALPHA = 150
UI_PANEL_BG_OPAQUE_ALPHA = 200
UI_PANEL_OUTLINE_ALPHA = 130
UI_PANEL_OUTLINE_HOVER_ALPHA = 255

UI_BARS_W_MULT = 0.14
UI_BARS_H_MULT = 0.08
UI_HEALTH_COL = "#FF1000"
UI_ENERGY_COL = "#B62AFF"
UI_BARS_OUTLINE_COL = (100, 100, 100, 255)

UI_RAYCAST_INFO_W_MULT = 0.09
UI_RAYCAST_INFO_TITLE_H_MULT = 0.17
UI_RAYCAST_INFO_DESCR_MULT = 0.7
UI_RAYCAST_INFO_MSG_H_MULT = 0.14
UI_RAYCAST_INFO_SUBTITLE_H_MULT = 0.15
UI_RAYCAST_INFO_DESCR_COL = (180, 180, 180)
UI_RAYCAST_INFO_CORNER_SIZE_MULT = 0.1

UI_INVENTORY_W_MULT = 0.6
UI_INVENTORY_H_MULT = 0.6
UI_INVENTORY_CORNER_SIZE_MULT = 0.025
UI_INVENTORY_TITLE_H_MULT = 0.06
UI_INVENTORY_PADDING_MULT = 0.03

UI_SLOT_CORNER_SIZE_MULT = 0.2
UI_SLOT_AMOUNT_H_MULT = 0.38
UI_SLOT_IMAGE_SIZE_MULT = 0.8
UI_SLOT_IMAGE_OFFSET_Y_MULT = 0.05
UI_SLOT_GHOST_ALPHA = int(255 / 2.5)

# rendering
RENDER_FPS = 240
TILE_PX = 16
STAR_TEX_MULT = 10

# debug
DEBUG_PLAYER_HITBOX_COL = "green"
DEBUG_TILE_HITBOX_COL = "blue"

# python
JSON_SEPS = (",", ":")
NEW_RENDER = True
