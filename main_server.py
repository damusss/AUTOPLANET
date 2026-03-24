import sys

import pygame

from src.server.server import Server


class Main:
    def __init__(self):
        client_PID = None
        if len(sys.argv) > 1 and sys.argv[1] == "-client_PID":
            client_PID = int(sys.argv[2])
        pygame.init()
        self.server = Server(client_PID)

    def run(self):
        self.server.run()


if __name__ == "__main__":
    main = Main()
    main.run()
