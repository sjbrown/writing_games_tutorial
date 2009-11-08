def Debug( msg ):
	print msg

DIRECTION_UP = 0
DIRECTION_DOWN = 1
DIRECTION_LEFT = 2
DIRECTION_RIGHT = 3

from events import *
import events

#------------------------------------------------------------------------------
class EventManager:
	"""this object is responsible for coordinating most communication
	between the Model, View, and Controller."""
	def __init__(self ):
		from weakref import WeakKeyDictionary
		self.listeners = WeakKeyDictionary()
		self.eventQueue= []

	#----------------------------------------------------------------------
	def RegisterListener( self, listener ):
		self.listeners[ listener ] = 1

	#----------------------------------------------------------------------
	def UnregisterListener( self, listener ):
		if listener in self.listeners.keys():
			del self.listeners[ listener ]
		
	#----------------------------------------------------------------------
	def Notify( self, event ):
		#if not isinstance(event, TickEvent): Debug( "     Mess: " + str(event) )
		if not isinstance(event, TickEvent): Debug( "     Message: " + event.name )
		for listener in self.listeners.keys():
			#If the weakref has died, remove it and continue 
			#through the list
			if listener is None:
				del self.listeners[ listener ]
				continue
			listener.Notify( event )

#from copy import copy
#import types
#------------------------------------------------------------------------------
#class NetworkWrapping:
	#"""..."""
	##----------------------------------------------------------------------
	#def __init__(self):
		#self.sharedObjs = {}
	##----------------------------------------------------------------------
	#def Wrap(self, event):
		#ev = copy(event.__dict__)
		#for attr in ev:
			#if type(ev[attr]) is types.InstanceType:
				#idNum = id(ev[attr])
				#ev[attr] = idNum
				#self.sharedObjs[idNum] = ev[attr]
		#ev['__name__'] = event.__class__.__name__
		#return ev
	##----------------------------------------------------------------------
	#def Unwrap(self, ev):
		#eventClass = getattr( events, ev['__name__'] )
		#event = eventClass()
		#return event

#------------------------------------------------------------------------------
class NetworkWrapping:
	"""..."""
	#----------------------------------------------------------------------
	def __init__(self):
		self.sharedObjs = {}
	#----------------------------------------------------------------------
	#def Wrap(self, event):
		#from twisted.spread.flavors import Referenceable
		##Very simple security checking
		#if events.Event not in event.__class__.__bases__:
			#return 0
		##Mix in the class that lets the event be sent over the network
		#if Referenceable not in event.__class__.__bases__:
			#event.__class__.__bases__ += (Referenceable ,)
		#return event
	#----------------------------------------------------------------------
	#def Wrap(self, event):
		#from twisted.spread.flavors import Copyable
		###Very simple security checking
		#if events.Event not in event.__class__.__bases__:
			#return 0
		##Mix in the class that lets the event be sent over the network
		#if Copyable not in event.__class__.__bases__:
			#event.__class__.__bases__ += (Copyable ,)
		#return event
	#----------------------------------------------------------------------
	def Wrap(self, event):
		#Very simple security checking
		if events.Event not in event.__class__.__bases__:
			return 0
		#Mix in the class that lets the event be sent over the network
		print "Copyable" + event.__class__.__name__
		mess = getattr(events, "Copyable" + event.__class__.__name__)(event)
		return mess
	#----------------------------------------------------------------------
	def Unwrap(self, event):
		return event


netWrap = NetworkWrapping()

from twisted.spread import pb
#------------------------------------------------------------------------------
class NetworkServerController(pb.Referenceable):
	"""We RECEIVE events from the server through this object"""
	def __init__(self, evManager, twistedReactor):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.reactor = twistedReactor


	#----------------------------------------------------------------------
	def remote_ServerEvent(self, event):
		print "======================GOT AN EVENT FROM SERVER:", str(event)
		ev = netWrap.Unwrap( event )
		self.evManager.Notify( ev )
		return 1

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, ServerConnectEvent ):
			#tell the server that we're listening to it and
			#it can access this object
			event.server.callRemote("ClientConnect", self)
		if isinstance( event, TickEvent ):
			#print "PUMPING NETWORK"
			self.reactor.iterate()


#------------------------------------------------------------------------------
class NetworkServerView(pb.Root):
	"""We SEND events to the server through this object"""
	STATE_PREPARING = 0
	STATE_CONNECTING = 1
	STATE_CONNECTED = 2
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.state = NetworkServerView.STATE_PREPARING
		self.serverReference = None

		self.stupidcount = 0

	#----------------------------------------------------------------------
	def Connected(self, serverReference):
		print "CONNECTED"
		self.serverReference = serverReference
		self.state = NetworkServerView.STATE_CONNECTED
		ev = ServerConnectEvent( serverReference )
		self.evManager.Notify( ev )

	#----------------------------------------------------------------------
	def ConnectFailed(self, serverReference):
		self.state = NetworkServerView.STATE_PREPARING
		print "CONNECTION FAILED"


	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ) \
		   and self.state == NetworkServerView.STATE_PREPARING:
		   	print "VIEW CONNECTING TO SERVER"
			self.state = NetworkServerView.STATE_CONNECTING
			remoteResponse = pb.getObjectAt("localhost", 8000, 30)
			remoteResponse.addCallback(self.Connected )
			                           #self.ConnectFailed)
		elif isinstance( event, TickEvent ):
			self.stupidcount += 1
			if self.stupidcount == 200:
				print "STUPIDD!!!!!!!!!!!!!!!!!!!!!!!!!!!"
				ev = GameStartRequest()
				self.evManager.Notify( ev )

		elif isinstance( event, GameStartRequest ):
			self.serverReference.callRemote("GameStartRequest") 




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

				if ev:
					self.evManager.Notify( ev )


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
			self.evManager.Notify( event )

	#----------------------------------------------------------------------
 	def Notify(self, event):
		if isinstance( event, QuitEvent ):
			#this will stop the while loop from running
			self.keepGoing = 0


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

		self.backSprites = pygame.sprite.RenderUpdates()
		self.frontSprites = pygame.sprite.RenderUpdates()


	#----------------------------------------------------------------------
 	def ShowMap(self, map):
		squareRect = pygame.Rect( (-128,10, 128,128 ) )

		i = 0
		for sector in map.sectors:
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
		charactorSprite = CharactorSprite( self.frontSprites )

		sector = charactor.sector
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
		for s in self.frontSprites.sprites():
			return s

	#----------------------------------------------------------------------
	def GetSectorSprite(self, sector):
		for s in self.backSprites.sprites():
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
			map = event.map
			self.ShowMap( map )

		elif isinstance( event, CharactorPlaceEvent ):
			self.ShowCharactor( event.charactor )

		elif isinstance( event, CharactorMoveEvent ):
			self.MoveCharactor( event.charactor )


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
		self.evManager.Notify( ev )

	#----------------------------------------------------------------------
 	def Notify(self, event):
		if isinstance( event, GameStartRequest ):
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
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )
		self.sector = None

	#----------------------------------------------------------------------
 	def Move(self, direction):
		return

	#----------------------------------------------------------------------
 	def Place(self, sector):
		self.sector = sector
		ev = CharactorPlaceEvent( self )
		self.evManager.Notify( ev )

	#----------------------------------------------------------------------
 	def Notify(self, event):
		if isinstance( event, GameStartedEvent ):
			map = event.game.map
			self.Place( map.sectors[map.startSectorIndex] )

		elif isinstance( event, CharactorMoveRequest ):
			self.Move( event.direction )

#------------------------------------------------------------------------------
class Map:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

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

		ev = MapBuiltEvent( self )
		self.evManager.Notify( ev )

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

	from twisted.spread.jelly import SecurityOptions
	s = SecurityOptions()
	s.allowModules( events )

	from twisted.internet import reactor
	serverController = NetworkServerController( evManager, reactor )
	serverView = NetworkServerView( evManager )
	
	spinner.Run()

if __name__ == "__main__":
	main()
