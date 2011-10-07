import time
import pygame
import pygame.constants as c

score = 0

screenDimensions = pygame.Rect((0,0,400,100))

black = (0,0,0)
white = (255,255,255)
blue  = (0,0,255)
red   = (255,0,0)

class Monkey(pygame.sprite.Sprite):
    def __init__(self):
        self.stunTimeout = None
        self.velocity = 2
        super(Monkey, self).__init__()
        self.image = pygame.Surface((60,60))
        self.rect = self.image.get_rect()
        self.render(blue)

    def render(self, color):
        self.image.fill(color)
        pygame.draw.circle(self.image, white, (10,10), 10, 2)
        pygame.draw.circle(self.image, white, (50,10), 10, 2)
        pygame.draw.circle(self.image, white, (30,60), 20, 2)

    def attemptPunch(self, event):
        if self.stunTimeout:
            return # already stunned
        if self.rect.collidepoint(event.pos):
            self.stunTimeout = time.time() + 2 # 2 seconds from now
            global score
            score += 1
            self.render(red)

    def update(self):
        if self.stunTimeout:
            if time.time() > self.stunTimeout:
                self.stunTimeout = None
                self.render(blue)
        else:
            self.rect.x += self.velocity
            if self.rect.right > screenDimensions.right:
                self.velocity = -2
            elif self.rect.left < screenDimensions.left:
                self.velocity = 2


def main():
    pygame.init()
    clock = pygame.time.Clock()
    displayImg = pygame.display.set_mode(screenDimensions.size)
    monkey = Monkey()

    while True:
        for event in pygame.event.get():
            if event.type == c.QUIT:
                return
            elif event.type == c.MOUSEBUTTONDOWN:
                monkey.attemptPunch(event)

        clock.tick(60) # aim for 60 FPS
        monkey.update()

        displayImg.fill(black)
        displayImg.blit(monkey.image, monkey.rect)
        pygame.display.flip()


if __name__ == '__main__':
    main()
    print 'Your score was', score
