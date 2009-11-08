import network
import twisted.internet
from twisted.spread import pb
from twisted.internet.task import LoopingCall
from twisted.internet.selectreactor import SelectReactor
from twisted.internet.main import installReactor
from events import *
import example1
from example1 import (EventManager,
                      MenuKeyboardController,
                      GameKeyboardController,
                      PygameView)

serverHost, serverPort = 'localhost', 8000

#------------------------------------------------------------------------------
class CPUSpinnerController:
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.keepGoing = 1
		self.replacementSpinner = None

	#----------------------------------------------------------------------
	def Run(self):
		while self.keepGoing:
			event = TickEvent()
			self.evManager.Post( event )
		print 'CPU spinner done'
		if self.replacementSpinner:
			print 'replacement spinner run()'
			self.replacementSpinner.Run()

	#----------------------------------------------------------------------
	def SwitchToReactorSpinner(self):
		self.keepGoing = False
		self.replacementSpinner = ReactorSpinController(self.evManager)

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, QuitEvent ):
			self.keepGoing = False


#------------------------------------------------------------------------------
class ReactorSpinController:
	STATE_STOPPED = 0
	STATE_STARTED = 1
	STATE_SHUTTING_DOWN = 2

	def __init__(self, evManager):
		self.state = ReactorSpinController.STATE_STOPPED
		self.evManager = evManager
		self.evManager.RegisterListener( self )
		self.reactor = SelectReactor()
		installReactor(self.reactor)
		self.loopingCall = LoopingCall(self.FireTick)

	#----------------------------------------------------------------------
	def FireTick(self):
		self.evManager.Post( TickEvent() )

	#----------------------------------------------------------------------
	def Run(self):
		self.state = ReactorSpinController.STATE_STARTED
		framesPerSecond = 10
		interval = 1.0 / framesPerSecond
		self.loopingCall.start(interval)
		self.reactor.run()

	#----------------------------------------------------------------------
	def Stop(self):
		print 'stopping the reactor'
		self.state = ReactorSpinController.STATE_SHUTTING_DOWN
		self.reactor.addSystemEventTrigger('after', 'shutdown',
		                                   self.onReactorStop)
		self.reactor.stop()

	#----------------------------------------------------------------------
	def onReactorStop(self):
		print 'reactor is now totally stopped'
		self.state = ReactorSpinController.STATE_STOPPED
		self.reactor = None

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, QuitEvent ):
			self.Stop()


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
		self.server = None
		self.connection = None

		self.sharedObjs = sharedObjectRegistry

	#----------------------------------------------------------------------
	def AttemptConnection(self):
		print "attempting a connection to", serverHost, serverPort
		try:
			reactor = twisted.internet.reactor
		except AttributeError:
			print 'Reactor not yet installed!'
			return
		self.state = NetworkServerView.STATE_CONNECTING
		self.connection = reactor.connectTCP(serverHost, serverPort,
		                                     self.pbClientFactory)
		deferred = self.pbClientFactory.getRootObject()
		deferred.addCallback(self.Connected)
		deferred.addErrback(self.ConnectFailed)

	#----------------------------------------------------------------------
	def Disconnect(self):
		print 'disconnecting', self.connection
		self.connection.disconnect()
		self.state = NetworkServerView.STATE_DISCONNECTED

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
		self.state = NetworkServerView.STATE_DISCONNECTED
		self.evManager.Post(ConnectFail(server))

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, RequestServerConnectEvent ):
			if self.state == NetworkServerView.STATE_PREPARING:
				self.AttemptConnection()
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
			print "CLIENT NOT SENDING: " +str(ev)
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
		self.server = None
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def remote_ServerEvent(self, event):
		print " ====  GOT AN EVENT FROM SERVER:", str(event)
		self.evManager.Post( event )
		return 1

	#----------------------------------------------------------------------
	def OnSelfAddedToServer(self, *args):
		print 'success callback triggered'
		event = BothSidesConnectedEvent()
		self.evManager.Post( event )

	#----------------------------------------------------------------------
	def OnServerAddSelfFailed(self, *args):
		print 'fail callback triggered', args
		print dir(args[0])
		print args[0].printDetailedTraceback()
		event = ConnectFail( self.server )
		self.evManager.Post( event )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, ServerConnectEvent ):
			print 'connecting serv controller'
			#tell the server that we're listening to it and
			#it can access this object
			self.server = event.server
			d = self.server.callRemote("ClientConnect", self)
			d.addCallback(self.OnSelfAddedToServer)
			d.addErrback(self.OnServerAddSelfFailed)


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
	def __init__(self, evManager, sharedObjectRegistry,
	             controller, spinner):
		self.sharedObjs = sharedObjectRegistry
		self.controller = controller
		self.spinner = spinner
		self.game = None
		self.server = None
		self.phonyEvManager = PhonyEventManager()
		self.realEvManager = evManager
		self.onConnectEvents = []

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
				self.game = example1.Game( self.phonyEvManager )
				self.sharedObjs[gameID] = self.game
			print 'sending the gse to the real em.'
			ev = GameStartedEvent( self.game )
			self.realEvManager.Post( ev )

		if isinstance( event, network.CopyableMapBuiltEvent ):
			mapID = event.mapID
			if not self.game:
				self.game = example1.Game( self.phonyEvManager )
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

		if isinstance( event, MenuMultiPlayerEvent ):
			self.StartMultiplayer()

		if isinstance( event, BothSidesConnectedEvent ):
			self.OnServerConnectSuccess()

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

	#----------------------------------------------------------------------
	def OnServerConnectSuccess(self):
		# now that we're connected, post all the queued events
		while self.onConnectEvents:
			ev = self.onConnectEvents.pop(0)
			self.realEvManager.Post(ev)

	#----------------------------------------------------------------------
	def OnServerConnectFail(self):
		self.onConnectEvents = []

	#----------------------------------------------------------------------
	def StartMultiplayer(self):
		self.spinner.SwitchToReactorSpinner()
		self.serverController = \
		                    NetworkServerController(self.realEvManager)
		self.serverView = \
		    NetworkServerView(self.realEvManager, self.sharedObjs)
		self.controller = GameKeyboardController( self.realEvManager )
		self.realEvManager.Post(RequestServerConnectEvent())
		self.onConnectEvents.append(GameStartRequest())


#------------------------------------------------------------------------------
def main():
	sharedObjectRegistry = {}
	evManager = EventManager()

	spinner = CPUSpinnerController( evManager )
	pygameView = PygameView( evManager )
	controller = MenuKeyboardController( evManager )
	phonyModel = PhonyModel( evManager, sharedObjectRegistry,
	                         controller, spinner )

	#from twisted.spread.jelly import globalSecurity
	#globalSecurity.allowModules( network )
	
	spinner.Run()
	print 'Done Run'
	print evManager.eventQueue

if __name__ == "__main__":
	main()
