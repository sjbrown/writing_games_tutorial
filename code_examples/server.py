#! /usr/bin/env python
'''
Example server
'''

from twisted.spread import pb
from twisted.spread.pb import DeadReferenceError
from twisted.cred import checkers, portal
from zope.interface import implements
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
    """A controller that sends an event every second"""
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
        if isinstance( event, FatalEvent ):
            PostMortem(event, self.reactor)

#------------------------------------------------------------------------------
def PostMortem(fatalEvent, reactor):
    print "\n\nFATAL EVENT.  STOPPING REACTOR"
    reactor.stop()
    from pprint import pprint
    print 'Shared Objects at the time of the fatal event:'
    pprint( sharedObjectRegistry )

#------------------------------------------------------------------------------
class RegularAvatar(pb.IPerspective): pass
#class DisallowedAvatar(pb.IPerspective): pass
#------------------------------------------------------------------------------
class MyRealm:
    implements(portal.IRealm)
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener( self )
        # keep track of avatars that have been given out
        self.claimedAvatarIDs = []
        # we need to hold onto views so they don't get garbage collected
        self.clientViews = []
        # maps avatars to player(s) they control
        self.playersControlledByAvatar = {}

    #----------------------------------------------------------------------
    def requestAvatar(self, avatarID, mind, *interfaces):
        print ' v'*30
        print 'requesting avatar id: ', avatarID
        print ' ^'*30
        if pb.IPerspective not in interfaces:
            print 'TWISTED FAILURE'
            raise NotImplementedError
        avatarClass = RegularAvatar
        if avatarID in self.claimedAvatarIDs:
            #avatarClass = DisallowedAvatar
            raise Exception( 'Another client is already connected'
                             ' to this avatar (%s)' % avatarID )

        self.claimedAvatarIDs.append(avatarID)
        ev = ClientConnectEvent( mind, avatarID )
        self.evManager.Post( ev )

        # TODO: this should be ok when avatarID is checkers.ANONYMOUS
        if avatarID not in self.playersControlledByAvatar:
            self.playersControlledByAvatar[avatarID] = []
        view = NetworkClientView( self.evManager, avatarID, mind )
        controller = NetworkClientController(self.evManager,
                                             avatarID,
                                             self)
        self.clientViews.append(view)
        return avatarClass, controller, controller.clientDisconnect

    #----------------------------------------------------------------------
    def knownPlayers(self):
        allPlayers = []
        for pList in self.playersControlledByAvatar.values():
            allPlayers.extend(pList)
        return allPlayers

    #----------------------------------------------------------------------
    def Notify(self, event):
        if isinstance(event, ClientDisconnectEvent):
            print 'got cli disconnect'
            self.claimedAvatarIDs.remove(event.avatarID)
            removee = None
            for view in self.clientViews:
                if view.avatarID == event.avatarID:
                    removee = view
            if removee:
                self.clientViews.remove(removee)

            print 'after disconnect, state is:'
            pprint (self.__dict__)


#------------------------------------------------------------------------------
class NetworkClientController(pb.Avatar):
    """We RECEIVE events from the CLIENT through this object
    There is an instance of NetworkClientController for each connected
    client.
    """
    def __init__(self, evManager, avatarID, realm):
        self.evManager = evManager
        self.evManager.RegisterListener( self )
        self.avatarID = avatarID
        self.realm = realm

    #----------------------------------------------------------------------
    def clientDisconnect(self):
        '''When a client disconnect is detected, this method
        gets called
        '''
        ev = ClientDisconnectEvent( self.avatarID )
        self.evManager.Post( ev )

    #----------------------------------------------------------------------
    def perspective_GetGameSync(self):
        """this is usually called when a client first connects or
        when they reconnect after a drop
        """
        game = sharedObjectRegistry.getGame()
        if game == None:
            print 'GetGameSync: game was none'
            raise Exception('Game should be set by this point')
        gameID = id( game )
        gameDict = game.getStateToCopy( sharedObjectRegistry )

        return [gameID, gameDict]
    
    #----------------------------------------------------------------------
    def perspective_GetObjectState(self, objectID):
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
    def perspective_EventOverNetwork(self, event):
        if isinstance(event, network.CopyableCharactorPlaceRequest):
            try:
                player = sharedObjectRegistry[event.playerID]
            except KeyError, ex:
                self.evManager.Post( FatalEvent( ex ) )
                raise
            pName = player.name
            if pName not in self.PlayersIControl():
                print 'i do not control', player
                print 'see?', self.PlayersIControl()
                print 'so i will ignore', event
                return
            try:
                charactor = sharedObjectRegistry[event.charactorID]
                sector = sharedObjectRegistry[event.sectorID]
            except KeyError, ex:
                self.evManager.Post( FatalEvent( ex ) )
                raise
            ev = CharactorPlaceRequest( player, charactor, sector )
        elif isinstance(event, network.CopyableCharactorMoveRequest):
            try:
                player = sharedObjectRegistry[event.playerID]
            except KeyError, ex:
                self.evManager.Post( FatalEvent( ex ) )
                raise
            pName = player.name
            if pName not in self.PlayersIControl():
                return
            try:
                charactor = sharedObjectRegistry[event.charactorID]
            except KeyError, ex:
                print 'sharedObjs did not have key:', ex
                print 'current sharedObjs:', sharedObjectRegistry
                print 'Did a client try to poison me?'
                self.evManager.Post( FatalEvent( ex ) )
                raise
            direction = event.direction
            ev = CharactorMoveRequest(player, charactor, direction)

        elif isinstance(event, PlayerJoinRequest):
            pName = event.playerDict['name']
            print 'got player join req.  known players:', self.realm.knownPlayers()
            if pName in self.realm.knownPlayers():
                print 'this player %s has already joined' % pName
                return
            self.ControlPlayer(pName)
            ev = event
        else:
            ev = event

        self.evManager.Post( ev )

        return 1

    #----------------------------------------------------------------------
    def Notify(self, event):
        if isinstance( event, GameStartedEvent ):
            self.game = event.game

    #----------------------------------------------------------------------
    def PlayersIControl(self):
        return self.realm.playersControlledByAvatar[self.avatarID]

    #----------------------------------------------------------------------
    def ControlPlayer(self, playerName):
        '''Note: this modifies self.realm.playersControlledByAvatar'''
        players = self.PlayersIControl()
        players.append(playerName)
        

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
    def __init__(self, evManager, avatarID, client):
        print "\nADDING CLIENT", client

        self.evManager = evManager
        self.evManager.RegisterListener( self )

        self.avatarID = avatarID
        self.client = client

    #----------------------------------------------------------------------
    def RemoteCallError(self, failure):
        from twisted.internet.error import ConnectionLost
        #trap ensures that the rest will happen only 
        #if the failure was ConnectionLost
        failure.trap(ConnectionLost)
        self.HandleFailure(self.client)
        return failure

    #----------------------------------------------------------------------
    def HandleFailure(self):
        print "Failing Client", self.client

    #----------------------------------------------------------------------
    def RemoteCall( self, fnName, *args):
        try:
            remoteCall = self.client.callRemote(fnName, *args)
            remoteCall.addErrback(self.RemoteCallError)
        except DeadReferenceError:
            self.HandleFailure()

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

        ev = self.EventThatShouldBeSent(event)
        if not ev:
            return

        print "\n====server===sending: ", str(ev), 'to',
        print self.avatarID, '(', self.client, ')'
        self.RemoteCall( "ServerEvent", ev )


class Model(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.gameKey = None

    def __setitem__(self, key, val):
        print 'setting', key, val
        dict.__setitem__(self, key, val)
        if isinstance(val, Game):
            self.gameKey = key

    def getGame(self):
        return self[self.gameKey]

evManager = None
sharedObjectRegistry = None
#------------------------------------------------------------------------------
def main():
    global evManager, sharedObjectRegistry
    from twisted.internet import reactor
    evManager = NoTickEventManager()
    sharedObjectRegistry = Model()

    log = TextLogView( evManager )
    timer = TimerController( evManager, reactor )
    game = Game( evManager )
    sharedObjectRegistry[id(game)] = game

    #factory = pb.PBServerFactory(clientController)
    #reactor.listenTCP( 8000, factory )

    realm = MyRealm(evManager)
    portl = portal.Portal(realm)
    checker = checkers.InMemoryUsernamePasswordDatabaseDontUse(
                                                           user1='pass1',
                                                           user2='pass1')
    portl.registerChecker(checker)
    reactor.listenTCP(8000, pb.PBServerFactory(portl))

    reactor.run()

if __name__ == "__main__":
    print 'starting server...'
    main()

