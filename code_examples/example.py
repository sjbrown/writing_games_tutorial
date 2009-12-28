def Debug( msg ):
	print msg

DIRECTION_UP = 0
DIRECTION_DOWN = 1
DIRECTION_LEFT = 2
DIRECTION_RIGHT = 3

from events import *

#------------------------------------------------------------------------------
class EventManager:
	"""this object is responsible for coordinating most communication
	between the Model, View, and Controller."""
	def __init__(self):
		from weakref import WeakKeyDictionary
		self.listeners = WeakKeyDictionary()
		self.eventQueue= []
		self.listenersToAdd = []
		self.listenersToRemove = []

	#----------------------------------------------------------------------
	def RegisterListener( self, listener ):
		self.listenersToAdd.append(listener)

	#----------------------------------------------------------------------
	def ActuallyUpdateListeners(self):
		for listener in self.listenersToAdd:
			self.listeners[ listener ] = 1
		for listener in self.listenersToRemove:
			if listener in self.listeners:
				del self.listeners[ listener ]

	#----------------------------------------------------------------------
	def UnregisterListener( self, listener ):
		self.listenersToRemove.append(listener)
		
	#----------------------------------------------------------------------
	def Post( self, event ):
		self.eventQueue.append(event)
		if isinstance(event, TickEvent):
			# Consume the event queue every Tick.
			self.ActuallyUpdateListeners()
			self.ConsumeEventQueue()
		else:
			Debug( "     Message: " + event.name )

	#----------------------------------------------------------------------
	def ConsumeEventQueue(self):
		i = 0
		while i < len( self.eventQueue ):
			event = self.eventQueue[i]
			for listener in self.listeners:
				# Note: a side effect of notifying the listener
				# could be that more events are put on the queue
				# or listeners could Register / Unregister
				old = len(self.eventQueue)
				listener.Notify( event )
			i += 1
			if self.listenersToAdd:
				self.ActuallyUpdateListeners()
		#all code paths that could possibly add more events to 
		# the eventQueue have been exhausted at this point, so 
		# it's safe to empty the queue
		self.eventQueue= []


#------------------------------------------------------------------------------
class KeyboardController:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Handle Input Events
			for event in pygame.event.get():
				ev = None
				if event.type == QUIT:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_ESCAPE:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_UP:
					direction = DIRECTION_UP
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_DOWN:
					direction = DIRECTION_DOWN
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_LEFT:
					direction = DIRECTION_LEFT
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_RIGHT:
					direction = DIRECTION_RIGHT
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN:
					ev = GameStartRequest()

				if ev:
					self.evManager.Post( ev )


#------------------------------------------------------------------------------
class CPUSpinnerController:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.keepGoing = 1

	#----------------------------------------------------------------------
	def Run(self):
		while self.keepGoing:
			event = TickEvent()
			self.evManager.Post( event )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, QuitEvent ):
			#this will stop the while loop from running
			self.keepGoing = False


import pygame
from pygame.locals import *
#------------------------------------------------------------------------------
class SectorSprite(pygame.sprite.Sprite):
	def __init__(self, sector, group=None):
		pygame.sprite.Sprite.__init__(self, group)
		self.image = pygame.Surface( (128,128) )
		self.image.fill( (0,255,128) )

		self.sector = sector

#------------------------------------------------------------------------------
class CharactorSprite(pygame.sprite.Sprite):
	def __init__(self, group=None):
		pygame.sprite.Sprite.__init__(self, group)

		charactorSurf = pygame.Surface( (64,64) )
		charactorSurf = charactorSurf.convert_alpha()
		charactorSurf.fill((0,0,0,0)) #make transparent
		pygame.draw.circle( charactorSurf, (255,0,0), (32,32), 32 )
		self.image = charactorSurf
		self.rect  = charactorSurf.get_rect()

		self.moveTo = None

	#----------------------------------------------------------------------
	def update(self):
		if self.moveTo:
			self.rect.center = self.moveTo
			self.moveTo = None

#------------------------------------------------------------------------------
class PygameView:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		pygame.init()
		self.window = pygame.display.set_mode( (424,440) )
		pygame.display.set_caption( 'Example Game' )
		self.background = pygame.Surface( self.window.get_size() )
		self.background.fill( (0,0,0) )
		font = pygame.font.Font(None, 30)
		textImg = font.render( "Press SPACE BAR to start", 1, (255,0,0))
		self.background.blit( textImg, (0,0) )
		self.window.blit( self.background, (0,0) )
		pygame.display.flip()

		self.backSprites = pygame.sprite.RenderUpdates()
		self.frontSprites = pygame.sprite.RenderUpdates()


	#----------------------------------------------------------------------
	def ShowMap(self, gameMap):
		squareRect = pygame.Rect( (-128,10, 128,128 ) )

		i = 0
		for sector in gameMap.sectors:
			if i < 3:
				squareRect = squareRect.move( 138,0 )
			else:
				i = 0
				squareRect = squareRect.move( -(138*2), 138 )
			i += 1
			newSprite = SectorSprite( sector, self.backSprites )
			newSprite.rect = squareRect
			newSprite = None

	#----------------------------------------------------------------------
 	def ShowCharactor(self, charactor):
		sector = charactor.sector
		if not sector:
			print "Charactor is not in a sector.  cannot show"
			return

		charactorSprite = self.GetCharactorSprite( charactor )
		if not charactorSprite:
			charactorSprite = CharactorSprite( self.frontSprites )
		sectorSprite = self.GetSectorSprite( sector )
		charactorSprite.rect.center = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def MoveCharactor(self, charactor):
		charactorSprite = self.GetCharactorSprite( charactor )

		sector = charactor.sector
		sectorSprite = self.GetSectorSprite( sector )

		charactorSprite.moveTo = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def GetCharactorSprite(self, charactor):
		#there will be only one
		for s in self.frontSprites:
			return s
		return None

	#----------------------------------------------------------------------
	def GetSectorSprite(self, sector):
		for s in self.backSprites:
			if hasattr(s, "sector") and s.sector == sector:
				return s


	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Draw Everything
			self.backSprites.clear( self.window, self.background )
			self.frontSprites.clear( self.window, self.background )

			self.backSprites.update()
			self.frontSprites.update()

			dirtyRects1 = self.backSprites.draw( self.window )
			dirtyRects2 = self.frontSprites.draw( self.window )
			
			dirtyRects = dirtyRects1 + dirtyRects2
			pygame.display.update( dirtyRects )


		elif isinstance( event, MapBuiltEvent ):
			gameMap = event.map
			self.ShowMap( gameMap )

		elif isinstance( event, CharactorPlaceEvent ):
			self.ShowCharactor( event.charactor )

		elif isinstance( event, CharactorMoveEvent ):
			self.MoveCharactor( event.charactor )

		elif isinstance( event, GameSyncEvent ):
			print "VIEW gets SYNC event"
			game = event.game
			self.ShowMap( game.map )
			for player in game.players:
				for charactor in player.charactors:
					self.ShowCharactor( charactor )

#------------------------------------------------------------------------------
class Game:
	"""..."""

	STATE_PREPARING = 0
	STATE_RUNNING = 1
	STATE_PAUSED = 2

	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.state = Game.STATE_PREPARING
		
		self.players = [ Player(evManager) ]
		self.map = Map( evManager )

	#----------------------------------------------------------------------
	def Start(self):
		self.map.Build()
		self.state = Game.STATE_RUNNING
		ev = GameStartedEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, GameStartRequest ):
		        print 'Game object gets game start req'
			if self.state == Game.STATE_PREPARING:
				self.Start()

#------------------------------------------------------------------------------
class Player:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.charactors = [ Charactor(evManager) ]

#------------------------------------------------------------------------------
class Charactor:
	"""..."""

	STATE_INACTIVE = 0
	STATE_ACTIVE = 1

	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.sector = None
		self.state = Charactor.STATE_INACTIVE

	#----------------------------------------------------------------------
	def Move(self, direction):
		if self.state == Charactor.STATE_INACTIVE:
			return

		if self.sector.MovePossible( direction ):
			newSector = self.sector.neighbors[direction]
			self.sector = newSector
			ev = CharactorMoveEvent( self )
			self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Place(self, sector):
		self.sector = sector
		self.state = Charactor.STATE_ACTIVE

		ev = CharactorPlaceEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, GameStartedEvent ):
			gameMap = event.game.map
			self.Place( gameMap.sectors[gameMap.startSectorIndex] )

		elif isinstance( event, CharactorMoveRequest ):
			self.Move( event.direction )

#------------------------------------------------------------------------------
class Map:
	"""..."""

	STATE_PREPARING = 0
	STATE_BUILT = 1


	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.state = Map.STATE_PREPARING

		self.sectors = range(9)
		self.startSectorIndex = 0

	#----------------------------------------------------------------------
	def Build(self):
		for i in range(9):
			self.sectors[i] = Sector( self.evManager )

		self.sectors[3].neighbors[DIRECTION_UP] = self.sectors[0]
		self.sectors[4].neighbors[DIRECTION_UP] = self.sectors[1]
		self.sectors[5].neighbors[DIRECTION_UP] = self.sectors[2]
		self.sectors[6].neighbors[DIRECTION_UP] = self.sectors[3]
		self.sectors[7].neighbors[DIRECTION_UP] = self.sectors[4]
		self.sectors[8].neighbors[DIRECTION_UP] = self.sectors[5]

		self.sectors[0].neighbors[DIRECTION_DOWN] = self.sectors[3]
		self.sectors[1].neighbors[DIRECTION_DOWN] = self.sectors[4]
		self.sectors[2].neighbors[DIRECTION_DOWN] = self.sectors[5]
		self.sectors[3].neighbors[DIRECTION_DOWN] = self.sectors[6]
		self.sectors[4].neighbors[DIRECTION_DOWN] = self.sectors[7]
		self.sectors[5].neighbors[DIRECTION_DOWN] = self.sectors[8]

		self.sectors[1].neighbors[DIRECTION_LEFT] = self.sectors[0]
		self.sectors[2].neighbors[DIRECTION_LEFT] = self.sectors[1]
		self.sectors[4].neighbors[DIRECTION_LEFT] = self.sectors[3]
		self.sectors[5].neighbors[DIRECTION_LEFT] = self.sectors[4]
		self.sectors[7].neighbors[DIRECTION_LEFT] = self.sectors[6]
		self.sectors[8].neighbors[DIRECTION_LEFT] = self.sectors[7]

		self.sectors[0].neighbors[DIRECTION_RIGHT] = self.sectors[1]
		self.sectors[1].neighbors[DIRECTION_RIGHT] = self.sectors[2]
		self.sectors[3].neighbors[DIRECTION_RIGHT] = self.sectors[4]
		self.sectors[4].neighbors[DIRECTION_RIGHT] = self.sectors[5]
		self.sectors[6].neighbors[DIRECTION_RIGHT] = self.sectors[7]
		self.sectors[7].neighbors[DIRECTION_RIGHT] = self.sectors[8]

		self.state = Map.STATE_BUILT

		ev = MapBuiltEvent( self )
		self.evManager.Post( ev )

#------------------------------------------------------------------------------
class Sector:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.neighbors = range(4)

		self.neighbors[DIRECTION_UP] = None
		self.neighbors[DIRECTION_DOWN] = None
		self.neighbors[DIRECTION_LEFT] = None
		self.neighbors[DIRECTION_RIGHT] = None

	#----------------------------------------------------------------------
	def MovePossible(self, direction):
		if self.neighbors[direction]:
			return 1


#------------------------------------------------------------------------------
def main():
	"""..."""
	evManager = EventManager()

	keybd = KeyboardController( evManager )
	spinner = CPUSpinnerController( evManager )
	pygameView = PygameView( evManager )
	game = Game( evManager )
	
	spinner.Run()

if __name__ == "__main__":
	main()
