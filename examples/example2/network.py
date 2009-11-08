
from example1 import *
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
		self.name = "Copyable Charactor Move Event"
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorMoveEvent, CopyableCharactorMoveEvent)
serverToClientEvents.append( CopyableCharactorMoveEvent )

#------------------------------------------------------------------------------
# CharactorPlaceEvent
# Direction: Server to Client only
class CopyableCharactorPlaceEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable Charactor Placement Event"
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorPlaceEvent, CopyableCharactorPlaceEvent)
serverToClientEvents.append( CopyableCharactorPlaceEvent )



#------------------------------------------------------------------------------
class CopyableCharactor:
	def getStateToCopy(self):
		d = self.__dict__.copy()
		del d['evManager']
		d['sector'] = id( self.sector )
		return d





	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = 1
		if not registry.has_key( stateDict['sector'] ):
			neededObjIDs.append( stateDict['sector'] )
			success = 0
		else:
			self.sector = registry[stateDict['sector']]
		return [success, neededObjIDs]
		


MixInClass( Charactor, CopyableCharactor )

#------------------------------------------------------------------------------
class CopyableMap:
	def getStateToCopy(self):
		sectorIDList = []
		for sect in self.sectors:
			sectorIDList.append( id(sect) )
		return {'ninegrid':1, 'sectorIDList':sectorIDList}





	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = 1

		if self.state != Map.STATE_BUILT:
			self.Build()

		for i, sectID in enumerate(stateDict['sectorIDList']):
			registry[sectID] = self.sectors[i]

		return [success, neededObjIDs]

MixInClass( Map, CopyableMap )


