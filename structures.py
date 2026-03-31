import struct
from constants import *

# Initial connection
class Handshaker:    
    def __init__(self, identifier=DEFAULT_IDENTIFIER, version=DEFAULT_VERSION, operationId=HANDSHAKE):
        self.identifier = identifier
        self.version = version
        self.operationId = operationId
    
    # Convert to bytes
    def pack(self) -> bytes:
        return struct.pack('<iii', self.identifier, self.version, self.operationId)


# Response from Asessto Corsa
class HandshackerResponse:    
    def __init__(self, data: bytes):
        self.carName = self.get_string(data, 0, 50)
        self.driverName = self.get_string(data, 50, 100)
        self.identifier = struct.unpack('<i', data[100:104])[0]
        self.version = struct.unpack('<i', data[104:108])[0]
        self.trackName = self.get_string(data, 108, 158)
        self.trackConfig = self.get_string(data, 158, 208)

    # Get text from bytes    
    def get_string(self, data: bytes, start: int, end: int) -> str:
        return data[start:end].decode('utf-8', errors='ignore').split('\x00')[0].strip()
    
    # Check if connected
    def is_valid(self) -> bool:
        return len(self.carName) > 0

#Main telemetry data
class RTCarInfo:
    def __init__(self, data: bytes):
        self.parse(data)
    
    def parse(self, data: bytes):
        offset = 8 # Skip identifier and size
        
        # Speeds
        self.speed_Kmh = self.get_float(data, offset); offset += 4
        self.speed_Mph = self.get_float(data, offset); offset += 4
        self.speed_Ms = self.get_float(data, offset); offset += 4
        
        # Driver aids
        self.isAbsEnabled = bool(data[offset]); offset += 1
        self.isAbsInAction = bool(data[offset]); offset += 1
        self.isTcInAction = bool(data[offset]); offset += 1
        self.isTcEnabled = bool(data[offset]); offset += 1
        self.isInPit = bool(data[offset]); offset += 1
        self.isEngineLimiterOn = bool(data[offset]); offset += 1
        offset += 2 # Padding
        
        # G-Forces
        self.accG_vertical = self.get_float(data, offset); offset += 4
        self.accG_horizontal = self.get_float(data, offset); offset += 4
        self.accG_frontal = self.get_float(data, offset); offset += 4
        
        # Lap times
        self.lapTime = self.get_int(data, offset); offset += 4
        self.lastLap = self.get_int(data, offset); offset += 4
        self.bestLap = self.get_int(data, offset); offset += 4
        self.lapCount = self.get_int(data, offset); offset += 4
        
        # Controls
        self.gas = self.get_float(data, offset); offset += 4
        self.brake = self.get_float(data, offset); offset += 4
        self.clutch = self.get_float(data, offset); offset += 4
        self.engineRPM = self.get_float(data, offset); offset += 4
        self.steer = self.get_float(data, offset); offset += 4
        self.gear = self.get_int(data, offset); offset += 4
        self.cgHeight = self.get_float(data, offset); offset += 4
        
        # Wheel data (4 values each)
        self.wheelAngularSpeed = self.get_floats(data, offset, 4); offset += 16
        self.slipAngle = self.get_floats(data, offset, 4); offset += 16
        self.slipAngle_ContactPatch = self.get_floats(data, offset, 4); offset += 16
        self.slipRatio = self.get_floats(data, offset, 4); offset += 16
        self.tyreSlip = self.get_floats(data, offset, 4); offset += 16
        self.ndSlip = self.get_floats(data, offset, 4); offset += 16
        self.load = self.get_floats(data, offset, 4); offset += 16
        self.Dy = self.get_floats(data, offset, 4); offset += 16
        self.Mz = self.get_floats(data, offset, 4); offset += 16
        self.tyreDirtyLevel = self.get_floats(data, offset, 4); offset += 16
        
        # Tyre geometry
        self.camberRAD = self.get_floats(data, offset, 4); offset += 16
        self.tyreRadius = self.get_floats(data, offset, 4); offset += 16
        self.tyreLoadedRadius = self.get_floats(data, offset, 4); offset += 16
        
        # Suspension
        self.suspensionHeight = self.get_floats(data, offset, 4); offset += 16
        
        # Position
        self.carPositionNormalized = self.get_float(data, offset); offset += 4
        self.carSlope = self.get_float(data, offset); offset += 4
        self.carCoordinates = self.get_floats(data, offset, 3)
    
    # Get float from bytes
    def get_float(self, data: bytes, offset: int) -> float:
        return struct.unpack('<f', data[offset:offset + 4])[0]
    
    # Get int from bytes
    def get_int(self, data: bytes, offset: int) -> int:
        return struct.unpack('<i', data[offset:offset + 4])[0]
    
    # Get multiple floats from bytes
    def get_floats(self, data: bytes, offset: int, count: int) -> list:
        return [self.get_float(data, offset + i * 4) for i in range(count)]
    
    # Show gear
    def gear_text(self) -> str:
        if self.gear == 0:
            return "R"
        if self.gear == 1:
            return "N"
        return str(self.gear - 1)
    
    def __repr__(self) -> str:
        return (f"RTCarInfo(speed={self.speed_Kmh:.1f}km/h, "
                f"rpm={self.engineRPM:.0f}, "
                f"gear={self.gear_text()}, "
                f"lap={self.lapTime/1000:.2f}s)")

# Lap completion event
class RTLap:    
    def __init__(self, data: bytes):
        self.carIdentifierNumber = struct.unpack('<i', data[0:4])[0]
        self.lap = struct.unpack('<i', data[4:8])[0]
        self.driverName = self.get_text(data, 8, 58)
        self.carName = self.get_text(data, 58, 108)
        self.time = struct.unpack('<i', data[108:112])[0]
    
    # Get text from bytes
    def get_text(self, data: bytes, start: int, end: int) -> str:
        return data[start:end].decode('utf-8', errors='ignore').split('\x00')[0]
    
    # Get lap time in seconds
    def lap_seconds(self) -> float:
        return self.time / 1000.0
    
    def __repr__(self) -> str:
        return (f"RTLap(lap={self.lap}, driver='{self.driverName}', "
                f"car='{self.carName}', time={self.lap_seconds():.3f}s)")