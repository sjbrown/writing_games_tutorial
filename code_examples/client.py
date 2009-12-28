import network
from twisted.spread import pb
from twisted.internet.selectreactor import SelectReactor
from twisted.internet.main import installReactor
from events import *
from example1 import (EventManager,
                      Game,
                      KeyboardController,
                      CPUSpinnerController,
                      PygameView)

serverHost, serverPort = 'localhost', 8000

#------------------------------------------------------------------------------
class NetworkServerView(pb.Root):
	"""We SEND events to the server through this object"""
	STATE_PREPARING = 0
	STATE_CONNECTING = 1
	STATE_CONNECTED = 2
	STATE_DISCONNECTING = 3
	STATE_DISCONNECTED = 4

	#----------------------------------------------------------------------
	def __init__(self, evManager, sharedObjectRegistry):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.pbClientFactory = pb.PBClientFactory()
		self.state = NetworkServerView.STATE_PREPARING
		self.reactor = None
		self.server = None

		self.sharedObjs = sharedObjectRegistry

	#----------------------------------------------------------------------
	def AttemptConnection(self):
		print "attempting a connection to", serverHost, serverPort
		self.state = NetworkServerView.STATE_CONNECTING
		if self.reactor:
			self.reactor.stop()
			self.PumpReactor()
		else:
			self.reactor = SelectReactor()
			installReactor(self.reactor)
		connection = self.reactor.connectTCP(serverHost, serverPort,
		                                     self.pbClientFactory)
		deferred = self.pbClientFactory.getRootObject()
		deferred.addCallback(self.Connected)
		deferred.addErrback(self.ConnectFailed)
		self.reactor.startRunning()

	#----------------------------------------------------------------------
	def Disconnect(self):
		print "disconnecting"
		if not self.reactor:
			return
		print 'stopping the reactor'
		self.reactor.stop()
                self.PumpReactor()
		self.state = NetworkServerView.STATE_DISCONNECTING

	#----------------------------------------------------------------------
	def Connected(self, server):
		print "CONNECTED"
		self.server = server
		self.state = NetworkServerView.STATE_CONNECTED
		ev = ServerConnectEvent( server )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def ConnectFailed(self, server):
		print "CONNECTION FAILED"
		#self.state = NetworkServerView.STATE_PREPARING
		self.state = NetworkServerView.STATE_DISCONNECTED

	#----------------------------------------------------------------------
	def PumpReactor(self):
		self.reactor.runUntilCurrent()
		self.reactor.doIteration(0)

	#----------------------------------------------------------------------
	def Notify(self, event):
		NSV = NetworkServerView
		if isinstance( event, TickEvent ):
			if self.state == NSV.STATE_PREPARING:
				self.AttemptConnection()
			elif self.state in [NSV.STATE_CONNECTED,
			                    NSV.STATE_DISCONNECTING,
			                    NSV.STATE_CONNECTING]:
				self.PumpReactor()
			return

		if isinstance( event, QuitEvent ):
			self.Disconnect()
			return

		ev = event
		if not isinstance( event, pb.Copyable ):
			evName = event.__class__.__name__
			copyableClsName = "Copyable"+evName
			if not hasattr( network, copyableClsName ):
				return
			copyableClass = getattr( network, copyableClsName )
			ev = copyableClass( event, self.sharedObjs )

		if ev.__class__ not in network.clientToServerEvents:
			#print "CLIENT NOT SENDING: " +str(ev)
			return
			
		if self.server:
			print " ====   Client sending", str(ev)
			remoteCall = self.server.callRemote("EventOverNetwork",
			                                    ev)
		else:
			print " =--= Cannot send while disconnected:", str(ev)




#------------------------------------------------------------------------------
class NetworkServerController(pb.Referenceable):
	"""We RECEIVE events from the server through this object"""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def remote_ServerEvent(self, event):
		print " ====  GOT AN EVENT FROM SERVER:", str(event)
		self.evManager.Post( event )
		return 1

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, ServerConnectEvent ):
			#tell the server that we're listening to it and
			#it can access this object
			event.server.callRemote("ClientConnect", self)


#------------------------------------------------------------------------------
class PhonyEventManager(EventManager):
	#----------------------------------------------------------------------
	def Post( self, event ):
		pass

#------------------------------------------------------------------------------
class PhonyModel(object):
	'''This isn't the authouritative model.  That one exists on the
	server.  This is a model to store local state and to interact with
	the local EventManager.
	'''
	def __init__(self, evManager, sharedObjectRegistry):
		self.sharedObjs = sharedObjectRegistry
		self.game = None
		self.server = None
		self.phonyEvManager = PhonyEventManager()
		self.realEvManager = evManager

		self.realEvManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def StateReturned(self, response):
		if response[0] == 0:
			print "GOT ZERO -- better error handler here"
			return None
		objID = response[0]
		objDict = response[1]
		obj = self.sharedObjs[objID]

		retval = obj.setCopyableState(objDict, self.sharedObjs)
		if retval[0] == 1:
			return obj
		for remainingObjID in retval[1]:
			remoteResponse = self.server.callRemote("GetObjectState", remainingObjID)
			remoteResponse.addCallback(self.StateReturned)

		#TODO: look under the Twisted Docs for "Chaining Defferreds"
		retval = obj.setCopyableState(objDict, self.sharedObjs)
		if retval[0] == 0:
			print "WEIRD!!!!!!!!!!!!!!!!!!"
			return None

		return obj

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, ServerConnectEvent ):
			self.server = event.server
		elif isinstance( event, network.CopyableGameStartedEvent ):
			gameID = event.gameID
			if not self.game:
				# give a phony event manager to the local game
				# object so it won't be able to fire events
				self.game = Game( self.phonyEvManager )
				self.sharedObjs[gameID] = self.game
			#------------------------
			#note: we shouldn't really be calling methods on our
			# phony model, instead we should be copying the state
			# from the server.
			#self.game.Start()
			#------------------------
			print 'sending the gse to the real em.'
			ev = GameStartedEvent( self.game )
			self.realEvManager.Post( ev )

		if isinstance( event, network.CopyableMapBuiltEvent ):
			mapID = event.mapID
			if not self.game:
				self.game = Game( self.phonyEvManager )
			if self.sharedObjs.has_key(mapID):
				map = self.sharedObjs[mapID]
				ev = MapBuiltEvent( map )
				self.realEvManager.Post( ev )
			else:
				map = self.game.map
				self.sharedObjs[mapID] = map
				remoteResponse = self.server.callRemote("GetObjectState", mapID)
				remoteResponse.addCallback(self.StateReturned)
				remoteResponse.addCallback(self.MapBuiltCallback)

		if isinstance( event, network.CopyableCharactorPlaceEvent ):
			charactorID = event.charactorID
			if self.sharedObjs.has_key(charactorID):
				charactor = self.sharedObjs[charactorID]
				ev = CharactorPlaceEvent( charactor )
				self.realEvManager.Post( ev )
			else:
				charactor = self.game.players[0].charactors[0]
				self.sharedObjs[charactorID] = charactor
				remoteResponse = self.server.callRemote("GetObjectState", charactorID)
				remoteResponse.addCallback(self.StateReturned)
				remoteResponse.addCallback(self.CharactorPlaceCallback)

		if isinstance( event, network.CopyableCharactorMoveEvent ):
			charactorID = event.charactorID
			if self.sharedObjs.has_key(charactorID):
				charactor = self.sharedObjs[charactorID]
			else:
				charactor = self.game.players[0].charactors[0]
				self.sharedObjs[charactorID] = charactor
			remoteResponse = self.server.callRemote("GetObjectState", charactorID)
			remoteResponse.addCallback(self.StateReturned)
			remoteResponse.addCallback(self.CharactorMoveCallback)

	#----------------------------------------------------------------------
	def CharactorPlaceCallback(self, charactor):
		ev = CharactorPlaceEvent( charactor )
		self.realEvManager.Post( ev )
	#----------------------------------------------------------------------
	def MapBuiltCallback(self, map):
		ev = MapBuiltEvent( map )
		self.realEvManager.Post( ev )
	#----------------------------------------------------------------------
	def CharactorMoveCallback(self, charactor):
		ev = CharactorMoveEvent( charactor )
		self.realEvManager.Post( ev )


#------------------------------------------------------------------------------
def main():
	evManager = EventManager()
	sharedObjectRegistry = {}

	keybd = KeyboardController( evManager )
	spinner = CPUSpinnerController( evManager )
	pygameView = PygameView( evManager )

	phonyModel = PhonyModel( evManager, sharedObjectRegistry )

	#from twisted.spread.jelly import globalSecurity
	#globalSecurity.allowModules( network )

	serverController = NetworkServerController( evManager )
	serverView = NetworkServerView( evManager, sharedObjectRegistry )
	
	spinner.Run()
	print 'Done Run'
	print evManager.eventQueue

if __name__ == "__main__":
	main()
