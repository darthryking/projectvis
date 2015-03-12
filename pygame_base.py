import os
import sys

import pygame

WIDTH = 1024
HEIGHT = 768

FRAMERATE = 60

COLOR_BLACK = (0, 0, 0)
COLOR_GRAY = (128, 128, 128)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (255, 0, 0)
COLOR_MAGENTA = (255, 0, 255)
COLOR_CYAN = (0, 255, 255)


def main():
    os.environ['SDL_VIDEO_WINDOW_POS'] = '{},{}'.format(100, 100)
    
    # Pygame setup
    pygame.init()
    pygame.display.set_caption("Project VIS Main Runtime")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    
    playerPos = (100, 100)
    
    while 1:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                return 0
                
        screen.fill(COLOR_BLACK)
        
        # Blah
        
        pygame.display.update()
        
        clock.tick(FRAMERATE)
        
    return 0
    
    
if __name__ == '__main__':
    sys.exit(main())
    