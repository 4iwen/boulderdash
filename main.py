from game.cfg.config import Config
from game.game import Game

if __name__ == "__main__":
    config = Config("game/cfg/config.yaml")
    game = Game(config)
    game.run()
