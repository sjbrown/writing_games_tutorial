import time
import random
import pygame
import pygame.constants as c

score = 0

screenDimensions = pygame.Rect((0,0,400,60))

sprites = pygame.sprite.Group()

black = (0,0,0)
white = (255,255,255)
blue  = (0,0,255)
red   = (255,0,0)

class Monkey(pygame.sprite.Sprite):
    def __init__(self):
        self.stunTimeout = None
        self.origVelocity = 2
        self.velocity = 2
        super(Monkey, self).__init__()
        self.image = pygame.Surface((60,60))
        self.rect = self.image.get_rect()
        self.render(blue)

    def render(self, color):
        '''draw onto self.image the face of a monkey in the specified color'''
        self.image.fill(color)
        pygame.draw.circle(self.image, white, (10,10), 10, 2)
        pygame.draw.circle(self.image, white, (50,10), 10, 2)
        pygame.draw.circle(self.image, white, (30,60), 20, 2)

    def attempt_punch(self, pos):
        '''If the given position (pos) is inside the monkey's rect, the monkey
        has been "punched".  A successful punch will stun the monkey and increment
        the global score.  The monkey cannot be punched if he is already stunned
        '''
        if self.stunTimeout:
            return # already stunned
        if self.rect.collidepoint(pos):
            # Argh!  The punch intersected with my face!
            self.stunTimeout = time.time() + 2 # 2 seconds from now
            global score
            score += 1
            self.render(red)

    def adjust_speed(self, multiplier):
        if self.velocity > 0:
            self.velocity = multiplier * self.origVelocity
        if self.velocity < 0:
            self.velocity = multiplier * -self.origVelocity

    def update(self):
        if self.stunTimeout:
            # If stunned, the monkey doesn't move
            if time.time() > self.stunTimeout:
                self.stunTimeout = None
                self.render(blue)
        else:
            # Move the monkey
            self.rect.x += self.velocity
            # Don't let the monkey run past the edge of the viewable area
            if (self.rect.right > screenDimensions.right or
                self.rect.left < screenDimensions.left):
                self.velocity = -self.velocity


def init():
    # Necessary Pygame set-up...
    pygame.init()
    clock = pygame.time.Clock()
    displayImg = pygame.display.set_mode(screenDimensions.size)
    monkey = Monkey()
    sprites.add(monkey)

    return (clock, displayImg)

def get_opponent_score():
    time.sleep(random.random())
    return score # just for pretend

def handle_events(clock):
    monkeys = []
    for sprite in sprites:
        if isinstance(sprite, Monkey):
            monkeys.append(sprite)

    for event in pygame.event.get():
        if event.type == c.QUIT:
            return False
        elif event.type == c.MOUSEBUTTONDOWN:
            for monkey in monkeys:
                monkey.attempt_punch(event.pos)

    opponentScore = get_opponent_score()
    difference = opponentScore - score
    if difference > 0:
        multiplier = 1.0 + difference/10.0
    else:
        multiplier = 1.0
    for monkey in monkeys:
        monkey.adjust_speed(multiplier)

    clock.tick(60) # aim for 60 frames per second
    for sprite in sprites:
        sprite.update()

    return True

def draw_to_display(displayImg):
    displayImg.fill(black)
    for sprite in sprites:
        displayImg.blit(sprite.image, sprite.rect)
    pygame.display.flip()

def main():
    clock, displayImg = init()

    keepGoing = True

    while keepGoing:
        keepGoing = handle_events(clock)
        draw_to_display(displayImg)

if __name__ == '__main__':
    main()
