#! /usr/bin/env python
'''
Example server
'''

from twisted.spread import pb
from example1 import EventManager, Game
from events import *
import network

#------------------------------------------------------------------------------
class NoTickEventManager(EventManager):
	'''This subclass of EventManager doesn't wait for a Tick event before
	it starts consuming its event queue.  The server module doesn't have
	a CPUSpinnerController, so Ticks will not get generated.
	'''
	def __init__(self):
		EventManager.__init__(self)
		self._lock = False
	def Post(self, event):
		EventManager.Post(self,event)
		if not self._lock:
			self._lock = True
			self.ConsumeEventQueue()
			self._lock = False



#------------------------------------------------------------------------------
class NetworkClientController(pb.Root):
	"""We RECEIVE events from the CLIENT through this object"""
	def __init__(self, evManager, sharedObjectRegistry):
		self.evManager = evManager
		self.evManager.RegisterListener( self )
		self.sharedObjs = sharedObjectRegistry

	#----------------------------------------------------------------------
	def remote_ClientConnect(self, netClient):
		print "CLIENT CONNECT"
		ev = ClientConnectEvent( netClient )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def remote_GetObjectState(self, objectID):
		print "request for object state", objectID
		if not self.sharedObjs.has_key( objectID ):
			return [0,0]
		objDict = self.sharedObjs[objectID].getStateToCopy()
		return [objectID, objDict]
	
	#----------------------------------------------------------------------
	def remote_EventOverNetwork(self, event):
		print "Server just got an EVENT" + str(event)
		self.evManager.Post( event )
		return 1

	#----------------------------------------------------------------------
	def Notify(self, event):
		pass


#------------------------------------------------------------------------------
class NetworkClientView(object):
	"""We SEND events to the CLIENT through this object"""
	def __init__(self, evManager, sharedObjectRegistry):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.clients = []
		self.sharedObjs = sharedObjectRegistry


	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, ClientConnectEvent ):
			print '== adding a client', event.client
			self.clients.append( event.client )

		ev = event

		#don't broadcast events that aren't Copyable
		if not isinstance( ev, pb.Copyable ):
			evName = ev.__class__.__name__
			copyableClsName = "Copyable"+evName
			if not hasattr( network, copyableClsName ):
				return
			copyableClass = getattr( network, copyableClsName )
			ev = copyableClass( ev, self.sharedObjs )

		if ev.__class__ not in network.serverToClientEvents:
			print "SERVER NOT SENDING: " +str(ev)
			return

		#NOTE: this is very "chatty".  We could restrict 
		#      the number of clients notified in the future
		for client in self.clients:
			print "=====server sending: ", str(ev)
			remoteCall = client.callRemote("ServerEvent", ev)


#------------------------------------------------------------------------------
class TextLogView(object):
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			return

		print 'TEXTLOG <',
		
		if isinstance( event, CharactorPlaceEvent ):
			print event.name, " at ", event.charactor.sector

		elif isinstance( event, CharactorMoveEvent ):
			print event.name, " to ", event.charactor.sector


		
#------------------------------------------------------------------------------
def main():
	evManager = NoTickEventManager()
	sharedObjectRegistry = {}

	log = TextLogView( evManager )
	clientController = NetworkClientController( evManager, sharedObjectRegistry )
	clientView = NetworkClientView( evManager, sharedObjectRegistry )
	game = Game( evManager )

	from twisted.internet import reactor
	reactor.listenTCP( 8000, pb.PBServerFactory(clientController) )

	reactor.run()

if __name__ == "__main__":
	main()
