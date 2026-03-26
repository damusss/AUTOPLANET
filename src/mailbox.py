def _id() -> int:
    _id._id += 1
    return _id._id


_id._id = 0

MAIL_ABORT = _id()
MAIL_HEARTBEAT = _id()
MAIL_CONNECT = _id()
MAIL_CONNECTION_ACCEPTED = _id()
MAIL_DISCONNECT = _id()
MAIL_FORCE_DISCONNECT = _id()
MAIL_NAME = _id()
MAIL_PLAYER_PHYSICS = _id()
MAIL_PLAYER_STATS = _id()
MAIL_OTHER_PLAYER_CONNECT = _id()
MAIL_OTHER_PLAYER_DISCONNECT = _id()
MAIL_ANIMATION_UPDATE = _id()
MAIL_CHUNK_LOAD = _id()
MAIL_CHUNK_UNLOAD = _id()
MAIL_CHUNK_UPDATE = _id()
MAIL_INPUT_DIR = _id()
MAIL_INPUT_EVENT = _id()
MAIL_MOUSE_POS = _id()
MAIL_BREAK_START = _id()
MAIL_INVENTORY_ACTION = _id()
MAIL_CRAFT_REQUEST = _id()
MAIL_BUILDING_AVAILABLE = _id()
MAIL_PLACE_BUILDING = _id()


class Mail:
    def __init__(self, type, client_id, **data):
        self.type = type
        self.client_id = client_id
        self.data: dict = data
        for attr, val in self.data.items():
            setattr(self, attr, val)
