#! /usr/bin/env python
'''
Example server
'''

from twisted.spread import pb
from twisted.spread.pb import DeadReferenceError
from example import EventManager, Game
from events import *
import network
from pprint import pprint

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
        self.eventQueue.append(event)
        #print 'ev q is', self.eventQueue, 'lock is', self._lock
        if not self._lock:
            self._lock = True
            #print 'consuming queue'
            self.ActuallyUpdateListeners()
            self.ConsumeEventQueue()
            self._lock = False


#------------------------------------------------------------------------------
class TimerController:
    """A controller that sends of an event every second"""
    def __init__(self, evManager, reactor):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

        self.reactor = reactor
        self.numClients = 0

    #-----------------------------------------------------------------------
    def NotifyApplicationStarted( self ):
        self.reactor.callLater( 1, self.Tick )

    #-----------------------------------------------------------------------
    def Tick(self):
        if self.numClients == 0:
            return

        ev = SecondEvent()
        self.evManager.Post( ev )
        ev = TickEvent()
        self.evManager.Post( ev )
        self.reactor.callLater( 1, self.Tick )

    #----------------------------------------------------------------------
    def Notify(self, event):
        if isinstance( event, ClientConnectEvent ):
            # first client connected.  start the clock.
            self.numClients += 1
            if self.numClients == 1:
                self.Tick()
        if isinstance( event, ClientDisconnectEvent ):
            self.numClients -= 1

#------------------------------------------------------------------------------
class NetworkClientController(pb.Root):
    """We RECEIVE events from the CLIENT through this object"""
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

        #this is needed for GetEntireState()
        self.game = None

    #----------------------------------------------------------------------
    def remote_ClientConnect(self, netClient):
        print "\nremote_CLIENT CONNECT"
        ev = ClientConnectEvent( netClient )
        self.evManager.Post( ev )
        if self.game == None:
            gameID = 0
        else:
            gameID = id(self.game)
        return gameID

    #----------------------------------------------------------------------
    def remote_GetGame(self):
        """this is usually called when a client first connects or
        when they reconnect after a drop
        """
        if self.game == None:
            return [0,0]
        gameID = id( self.game )
        gameDict = self.game.getStateToCopy( sharedObjectRegistry )

        return [gameID, gameDict]
    
    #----------------------------------------------------------------------
    def remote_GetObjectState(self, objectID):
        #print "request for object state", objectID
        if not sharedObjectRegistry.has_key( objectID ):
            print "No key on the server"
            return [0,0]
        obj = sharedObjectRegistry[objectID]
        print 'getting state for object', obj
        print 'my registry is '
        pprint(sharedObjectRegistry)
        objDict = obj.getStateToCopy( sharedObjectRegistry )

        return [objectID, objDict]
    
    #----------------------------------------------------------------------
    def remote_EventOverNetwork(self, event):
        #print "Server just got an EVENT" + str(event)
        self.evManager.Post( event )
        return 1

    #----------------------------------------------------------------------
    def Notify(self, event):
        if isinstance( event, GameStartedEvent ):
            self.game = event.game


#------------------------------------------------------------------------------
class TextLogView(object):
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

    #----------------------------------------------------------------------
    def Notify(self, event):
        if event.__class__ in [TickEvent, SecondEvent]:
            return

        print 'TEXTLOG <',
        
        if isinstance( event, CharactorPlaceEvent ):
            print event.name, " at ", event.charactor.sector

        elif isinstance( event, CharactorMoveEvent ):
            print event.name, " to ", event.charactor.sector
        else:
            print 'event:', event


#------------------------------------------------------------------------------
class NetworkClientView(object):
    """We SEND events to the CLIENT through this object"""
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

        self.clients = []
        #TODO:
        #every 5 seconds, the server should poll the clients to see if
        # they're still connected
        self.pollSeconds = 0

    #----------------------------------------------------------------------
    def Pong(self ):
        pass

    #----------------------------------------------------------------------
    def RemoteCallError(self, failure, client):
        from twisted.internet.error import ConnectionLost
        #trap ensures that the rest will happen only 
        #if the failure was ConnectionLost
        failure.trap(ConnectionLost)
        self.DisconnectClient(client)
        return failure

    #----------------------------------------------------------------------
    def DisconnectClient(self, client):
        print "Disconnecting Client", client
        self.clients.remove( client )
        ev = ClientDisconnectEvent( client ) #client id in here
        self.evManager.Post( ev )

    #----------------------------------------------------------------------
    def RemoteCall( self, client, fnName, *args):

        try:
            remoteCall = client.callRemote(fnName, *args)
            remoteCall.addErrback( self.RemoteCallError, client )
        except DeadReferenceError:
            self.DisconnectClient(client)


    #----------------------------------------------------------------------
    def EventThatShouldBeSent(self, event):
        ev = event

        #don't send events that aren't Copyable
        if not isinstance( ev, pb.Copyable ):
            evName = ev.__class__.__name__
            copyableClsName = "Copyable"+evName
            if not hasattr( network, copyableClsName ):
                return None
            copyableClass = getattr( network, copyableClsName )
            ev = copyableClass( ev, sharedObjectRegistry )

        if ev.__class__ not in network.serverToClientEvents:
            print "SERVER NOT SENDING: " +str(ev)
            return None

        return ev

    #----------------------------------------------------------------------
    def Notify(self, event):
        #NOTE: this is very "chatty".  We could restrict 
        #      the number of clients notified in the future
        if isinstance( event, ClientConnectEvent ):
            print "\nADDING CLIENT", event.client
            self.clients.append( event.client )
            #TODO tell the client what it's ID is

        if isinstance( event, SecondEvent ):
            self.pollSeconds +=1
            if self.pollSeconds == 10:
                self.pollSeconds = 0
                for client in self.clients:
                    self.RemoteCall( client, "Ping" )

        ev = self.EventThatShouldBeSent(event)
        if not ev:
            return

        for client in self.clients:
            print "\n====server===sending: ", str(ev), 'to', client
            self.RemoteCall( client, "ServerEvent", ev )



evManager = None
sharedObjectRegistry = None
#------------------------------------------------------------------------------
def main():
    global evManager, sharedObjectRegistry
    from twisted.internet import reactor
    evManager = NoTickEventManager()
    sharedObjectRegistry = {}

    log = TextLogView( evManager )
    timer = TimerController( evManager, reactor )
    clientController = NetworkClientController( evManager )
    clientView = NetworkClientView( evManager )
    game = Game( evManager )
    sharedObjectRegistry[id(game)] = game

    reactor.listenTCP( 8000, pb.PBServerFactory(clientController) )

    reactor.run()

if __name__ == "__main__":
    print 'starting server...'
    main()
