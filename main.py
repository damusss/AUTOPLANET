import pygame

from src.client.client import Client


class Main:
    def __init__(self):
        pygame.init()
        self.client = Client()

    def run(self):
        while not self.client.abort:
            self.client.frame()


if __name__ == "__main__":
    main = Main()
    main.run()
