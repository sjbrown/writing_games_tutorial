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
        '''draw onto self.image the face of a monkey in the specified color'''
        self.image.fill(color)
        pygame.draw.circle(self.image, white, (10,10), 10, 2)
        pygame.draw.circle(self.image, white, (50,10), 10, 2)
        pygame.draw.circle(self.image, white, (30,60), 20, 2)

    def attempt_punch(self, pos):
        '''If the given position (pos) is inside the monkey's rect, the monkey
        has been "punched".  A successful punch will stun the monkey and
        increment the global score.
        The monkey cannot be punched if he is already stunned
        '''
        if self.stunTimeout:
            return # already stunned
        if self.rect.collidepoint(pos):
            # Argh!  The punch intersected with my face!
            self.stunTimeout = time.time() + 2 # 2 seconds from now
            global score
            score += 1
            self.render(red)

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
            if self.rect.right > screenDimensions.right:
                self.velocity = -2
            elif self.rect.left < screenDimensions.left:
                self.velocity = 2

    def do_special(self):
        print 'monkey does special'

    def on_event(self, event):
        if event == 'ClockTick':
            self.update()
        elif event == 'SpecialEvent':
            self.do_special()
        elif event.type == c.MOUSEBUTTONDOWN:
            self.attempt_punch(event.pos)
        # notice that Monkey doesn't do anything on event_type_B
        elif event.type == event_type_C:
            pass
        elif event.type == event_type_D:
            pass


class Trap(pygame.sprite.Sprite):
    def __init__(self):
        self.image = pygame.Surface((20,20))
        self.rect = self.image.get_rect()
        self.render(red)

    def render(self, color):
        '''draw onto self.image the face of a monkey in the specified color'''
        self.image.fill(color)
        pygame.draw.circle(self.image, white, (10,10), 10, 2)
        pygame.draw.circle(self.image, white, (50,10), 10, 2)
        pygame.draw.circle(self.image, white, (30,60), 20, 2)

    def do_special(self):
        print 'trap does special'
    def add_some_honey(self):
        print 'trap adds honey'

    def on_event(self, event):
        if event == 'ClockTick':
            self.update()
        elif event == 'SpecialEvent':
            self.do_special()
        # notice that Trap doesn't do anything on MOUSEBUTTONDOWN
        elif event.type == event_type_B:
            self.add_some_honey()
        elif event.type == event_type_C:
            pass
        elif event.type == event_type_D:
            pass


sprites = pygame.sprite.Group()

def init():
    # Necessary Pygame set-up...
    pygame.init()
    clock = pygame.time.Clock()
    displayImg = pygame.display.set_mode(screenDimensions.size)
    monkey = Monkey()
    sprites.add(monkey)

    return (clock, displayImg)

def some_other_events():
    return []

def from_somewhere():
    return "yeah, this is pretty special alright"

def generate_events(clock):
    for event in pygame.event.get():
        yield event

    clock.tick(60) # aim for 60 frames per second
    yield 'ClockTick'

    for event in some_other_events():
        yield event

    specialEvent = from_somewhere()
    yield 'SpecialEvent'

event_type_B, event_type_C, event_type_D = 1,2,3

def handle_events(clock):
    for event in generate_events(clock):
        if hasattr(event, 'type') and event.type == c.QUIT:
            return False
        for sprite in sprites:
            sprite.on_event(event)
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
    print 'Your score was', score
