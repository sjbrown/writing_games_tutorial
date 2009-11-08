def Debug( msg ):
	return
	#print msg

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
		if not isinstance(event, TickEvent): Debug( "     Message: " + event.name )
		for listener in self.listeners.keys():
			#If the weakref has died, remove it and continue 
			#through the list
			if listener is None:
				del self.listeners[ listener ]
				continue
			listener.Notify( event )


from twisted.spread import pb
#------------------------------------------------------------------------------
class NetworkClientController(pb.Root):
	"""..."""
	def __init__(self, evManager):
		#pb.Root.__init__(self)
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def remote_ClientConnect(self, netClient):
		print "CLIENT CONNECT"
		ev = ClientConnectEvent( netClient )
		self.evManager.Notify( ev )
		return 1

	#----------------------------------------------------------------------
	def remote_GameStartRequest(self):
		print "GAME START REQ"
		ev = GameStartRequest( )
		self.evManager.Notify( ev )
		return 1

	#----------------------------------------------------------------------
	def remote_CharactorMoveRequest(self, direction):
		print "CHAR MOVE REQ"
		ev = CharactorMoveRequest( direction )
		self.evManager.Notify( ev )
		return 1

	#----------------------------------------------------------------------
	def Notify(self, event):
		pass

#------------------------------------------------------------------------------
class NetworkWrapping:
	"""..."""
	#----------------------------------------------------------------------
	def __init__(self):
		self.sharedObjs = {}
	#----------------------------------------------------------------------
	def Wrap(self, event):
		#Very simple security checking
		if events.Event not in event.__class__.__bases__:
			return 0
		#Mix in the class that lets the event be sent over the network
		print "Copyable" + event.__class__.__name__
		mess = getattr(events, "Copyable" + event.__class__.__name__)( event)
		return mess
	#----------------------------------------------------------------------
	def Unwrap(self, event):
		return event

netWrap = NetworkWrapping()

#------------------------------------------------------------------------------
class NetworkClientView:
	"""We SEND events to the CLIENT through this object"""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.clients = []


	#----------------------------------------------------------------------
 	def Notify(self, event):
		if isinstance( event, ClientConnectEvent ):
			print event.name, " at ", event.client
			self.clients.append( event.client )

		#don't broadcast network events, it could lead to an infinite
		#loop
		if isinstance( event, ClientConnectEvent ):
			return
		#don't necessarily need to pass on requests
		if isinstance( event, GameStartRequest) \
		   or isinstance( event, CharactorMoveRequest):
			return

		#NOTE: this is very "chatty".  We could restrict broadcasted
		#      events to just a subset of all events, but this is
		#      sufficient for now
		for client in self.clients:
			wrapEv = netWrap.Wrap(event)
			if wrapEv == 0:
				return
			print "======================sending: ", str(wrapEv)
			remoteCall = client.callRemote("ServerEvent", wrapEv)



#------------------------------------------------------------------------------
class TextLogView:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )


	#----------------------------------------------------------------------
 	def Notify(self, event):

		if isinstance( event, CharactorPlaceEvent ):
			print event.name, " at ", event.charactor.sector

		elif isinstance( event, CharactorMoveEvent ):
			print event.name, " to ", event.charactor.sector

		elif not isinstance( event, TickEvent ):
			print event.name

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

	STATE_INACTIVE = 0
	STATE_ACTIVE = 1

	"""..."""
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
			self.evManager.Notify( ev )

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
			self.state = Charactor.STATE_ACTIVE

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
	from server2 import EventManager, TextLogView, NetworkClientController, NetworkClientView, Game
	evManager = EventManager()

	log = TextLogView( evManager )
	clientController = NetworkClientController( evManager )
	clientView = NetworkClientView( evManager )
	game = Game( evManager )
	
	from twisted.internet.app import Application

	from twisted.spread.jelly import SecurityOptions
	s = SecurityOptions()
	s.allowModules( events )

	application = Application("myServer")
	application.listenTCP(8000, pb.BrokerFactory(clientController) )

	application.run()

if __name__ == "__main__":
	main()
