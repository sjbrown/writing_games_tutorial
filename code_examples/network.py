
from example import *
from twisted.spread import pb

# A list of ALL possible events that a server can send to a client
serverToClientEvents = []
# A list of ALL possible events that a client can send to a server
clientToServerEvents = []

#------------------------------------------------------------------------------
#Mix-In Helper Functions
#------------------------------------------------------------------------------
def MixInClass( origClass, addClass ):
	if addClass not in origClass.__bases__:
		origClass.__bases__ += (addClass,)

#------------------------------------------------------------------------------
def MixInCopyClasses( someClass ):
	MixInClass( someClass, pb.Copyable )
	MixInClass( someClass, pb.RemoteCopy )




#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# For each event class, if it is sendable over the network, we have 
# to Mix In the "copy classes", or make a replacement event class that is 
# copyable

#------------------------------------------------------------------------------
# TickEvent
# Direction: don't send.
#The Tick event happens hundreds of times per second.  If we think we need
#to send it over the network, we should REALLY re-evaluate our design

#------------------------------------------------------------------------------
# QuitEvent
# Direction: Client to Server only
MixInCopyClasses( QuitEvent )
pb.setUnjellyableForClass(QuitEvent, QuitEvent)
clientToServerEvents.append( QuitEvent )

#------------------------------------------------------------------------------
# GameStartRequest
# Direction: Client to Server only
MixInCopyClasses( GameStartRequest )
pb.setUnjellyableForClass(GameStartRequest, GameStartRequest)
clientToServerEvents.append( GameStartRequest )

#------------------------------------------------------------------------------
# CharactorMoveRequest
# Direction: Client to Server only
# this has an additional attribute, direction.  it is an int, so it's safe
MixInCopyClasses( CharactorMoveRequest )
pb.setUnjellyableForClass(CharactorMoveRequest, CharactorMoveRequest)
clientToServerEvents.append( CharactorMoveRequest )


#------------------------------------------------------------------------------
# ServerConnectEvent
# Direction: don't send.
# we don't need to send this over the network.

#------------------------------------------------------------------------------
# ClientConnectEvent
# Direction: don't send.
# we don't need to send this over the network.


#------------------------------------------------------------------------------
# GameStartedEvent
# Direction: Server to Client only
class CopyableGameStartedEvent(pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry):
		self.name = "Copyable Game Started Event"
		self.gameID = id(event.game)
		registry[self.gameID] = event.game
		#TODO: put this in a Player Join Event or something
		for p in event.game.players:
			registry[id(p)] = p

pb.setUnjellyableForClass(CopyableGameStartedEvent, CopyableGameStartedEvent)
serverToClientEvents.append( CopyableGameStartedEvent )

#------------------------------------------------------------------------------
# MapBuiltEvent
# Direction: Server to Client only
class CopyableMapBuiltEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable Map Finished Building Event"
		self.mapID = id( event.map )
		registry[self.mapID] = event.map

pb.setUnjellyableForClass(CopyableMapBuiltEvent, CopyableMapBuiltEvent)
serverToClientEvents.append( CopyableMapBuiltEvent )

#------------------------------------------------------------------------------
# CharactorMoveEvent
# Direction: Server to Client only
class CopyableCharactorMoveEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable " + event.name
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorMoveEvent, CopyableCharactorMoveEvent)
serverToClientEvents.append( CopyableCharactorMoveEvent )

#------------------------------------------------------------------------------
# CharactorPlaceEvent
# Direction: Server to Client only
class CopyableCharactorPlaceEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable " + event.name
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorPlaceEvent, CopyableCharactorPlaceEvent)
serverToClientEvents.append( CopyableCharactorPlaceEvent )


#------------------------------------------------------------------------------
class CopyableCharactor:
	def getStateToCopy(self, registry):
		d = self.__dict__.copy()
		del d['evManager']

		sID = id( self.sector )
		d['sector'] = sID
		registry[sID] = self.sector

		return d

	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = 1
		if stateDict['sector'] not in registry:
			registry[stateDict['sector']] = Sector(self.evManager)
			neededObjIDs.append( stateDict['sector'] )
			success = 0
		else:
			self.sector = registry[stateDict['sector']]
		return [success, neededObjIDs]


MixInClass( Charactor, CopyableCharactor )

#------------------------------------------------------------------------------
class CopyableMap:
	def getStateToCopy(self, registry):
		sectorIDList = []
		for sect in self.sectors:
			sID = id(sect)
			sectorIDList.append( sID )
			registry[sID] = sect

		return {'ninegrid':1, 'sectorIDList':sectorIDList}


	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = True

		if self.state != Map.STATE_BUILT:
			self.Build()

		for i, sectID in enumerate(stateDict['sectorIDList']):
			registry[sectID] = self.sectors[i]

		return [success, neededObjIDs]

MixInClass( Map, CopyableMap )


#------------------------------------------------------------------------------
class CopyableGame:
	def getStateToCopy(self, registry):
		d = self.__dict__.copy()
		del d['evManager']

		mID = id( self.map )
		d['map'] = mID
		registry[mID] = self.map

		playerIDList = []
		for player in self.players:
			pID = id( player )
			playerIDList.append( pID )
			registry[pID] = player
		d['players'] = playerIDList

		return d

	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = True

		self.state = stateDict['state']

		if stateDict['map'] not in registry:
			registry[stateDict['map']] = Map( self.evManager )
			neededObjIDs.append( stateDict['map'] )
			success = False
		else:
			self.map = registry[stateDict['map']]

		self.players = []
		for pID in stateDict['players']:
			if pID not in registry:
				registry[pID] = Player( self.evManager )
				neededObjIDs.append( pID )
				success = False
			else:
				self.players.append( registry[pID] )

		return [success, neededObjIDs]

MixInClass( Game, CopyableGame )

#------------------------------------------------------------------------------
class CopyablePlayer:
	def getStateToCopy(self, registry):
		d = self.__dict__.copy()
		del d['evManager']

		charactorIDList = []
		for charactor in self.charactors:
			cID = id( charactor )
			charactorIDList.append( cID )
			registry[cID] = charactor
		d['charactors'] = charactorIDList

		return d

	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = True

		self.name = stateDict['name']

		if not registry.has_key( stateDict['game'] ):
			print "Something is wrong. should already be a game"
		else:
			self.game = registry[stateDict['game']]

		self.charactors = []
		for cID in stateDict['charactors']:
			if not cID in registry:
				registry[cID] = Charactor( self.evManager )
				neededObjIDs.append( cID )
				success = False
			else:
				self.charactors.append( registry[cID] )

		return [success, neededObjIDs]

MixInClass( Player, CopyablePlayer )
