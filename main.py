from confluent_kafka import Producer
from client import ACTelemetryClient
from constants import SUBSCRIBE_UPDATE
from datetime import datetime, timezone
import json
import time
import traceback
import uuid

# Kafka configuration
KAFKA_CONFIG = {
    'bootstrap.servers': '100.84.194.114:9092',
}

KAFKA_TOPIC = 'ic26-decoded-can'
SENSOR_ID = 'ac-telemetry-1'
SENSOR_NAME = 'Assetto Corsa'
STREAM_NAME = 'ac-telemetry'

def build_kafka_message(body: dict) -> dict:
    return {
        'payload': {
            'id': str(uuid.uuid4()),
            'body': body,
            'stream': STREAM_NAME,
        }
    }

def main():
    # Kafka producer
    kafka_producer = Producer(KAFKA_CONFIG)
    
    # Asessto Corsa client
    client = ACTelemetryClient("127.0.0.1")
    
    def send_to_kafka(message: dict):
        try:
            data_json = json.dumps(message)
            kafka_producer.produce(
                KAFKA_TOPIC,
                data_json.encode('utf-8'),
            )
            kafka_producer.poll(0)
        except Exception as e:
            print(f"Error sending to Kafka: {e}")
    
    def telemetry_channels(telemetry):
        return {
            'event_type': 'telemetry',
            'speed_Kmh': telemetry.speed_Kmh,
            'speed_Mph': telemetry.speed_Mph,
            'speed_Ms': telemetry.speed_Ms,
            'isAbsEnabled': telemetry.isAbsEnabled,
            'isAbsInAction': telemetry.isAbsInAction,
            'isTcInAction': telemetry.isTcInAction,
            'isTcEnabled': telemetry.isTcEnabled,
            'isInPit': telemetry.isInPit,
            'isEngineLimiterOn': telemetry.isEngineLimiterOn,
            'accG_vertical': telemetry.accG_vertical,
            'accG_horizontal': telemetry.accG_horizontal,
            'accG_frontal': telemetry.accG_frontal,
            'lapTime': telemetry.lapTime,
            'lastLap': telemetry.lastLap,
            'bestLap': telemetry.bestLap,
            'lapCount': telemetry.lapCount,
            'gas': telemetry.gas,
            'brake': telemetry.brake,
            'clutch': telemetry.clutch,
            'engineRPM': telemetry.engineRPM,
            'steer': telemetry.steer,
            'gear': telemetry.gear,
            'gear_display': telemetry.gear_text(),
            'cgHeight': telemetry.cgHeight,
            'wheelAngularSpeed': telemetry.wheelAngularSpeed,
            'slipAngle': telemetry.slipAngle,
            'slipRatio': telemetry.slipRatio,
            'load': telemetry.load,
            'suspensionHeight': telemetry.suspensionHeight,
            'carPositionNormalized': telemetry.carPositionNormalized,
            'carSlope': telemetry.carSlope,
            'carCoordinates': telemetry.carCoordinates
        }
    
    try:
        print(f"Connecting to Assetto Corsa...")
        response = client.connect()
        
        print(f"\nConnected to Assetto Corsa")
        print(f"Car: {response.carName}")
        print(f"Driver: {response.driverName}")
        print(f"Track: {response.trackName}")
        print(f"Kafka Broker: {KAFKA_CONFIG['bootstrap.servers']}")
        print(f"Kafka Topic: {KAFKA_TOPIC}")
        
        print("\nSubscribing to telemetry...")
        client.subscribe(SUBSCRIBE_UPDATE)
        
        # Send session start to Kafka
        session_body = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'sensor_id': SENSOR_ID,
            'sensor_name': SENSOR_NAME,
            'event_type': 'session_start',
            'car': response.carName,
            'driver': response.driverName,
            'track': response.trackName,
        }
        send_to_kafka(build_kafka_message(session_body))
        
        # Show data
        def on_telemetry(telemetry):
            gear = telemetry.gear_text()
            
            # Send to Kafka: one message per AC sample, many channels in body
            body = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'sensor_id': SENSOR_ID,
                'sensor_name': SENSOR_NAME,
                **telemetry_channels(telemetry),
            }
            send_to_kafka(build_kafka_message(body))
            
            # Print
            print(f"\rSpeed: {telemetry.speed_Kmh:6.1f} km/h | "
                  f"RPM: {telemetry.engineRPM:6.0f} | "
                  f"Gear: {gear:>2} | "
                  f"Gas: {telemetry.gas:3.0%} | "
                  f"Lap: {telemetry.lapTime/1000:6.2f}s", end='')
        
        client.add_callback('telemetry', on_telemetry)
        
        print("\nReceiving data...")
        client.start_receiving()
        
        # Keep running
        while True:
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n\nStopping...")
        
        end_body = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'sensor_id': SENSOR_ID,
            'sensor_name': SENSOR_NAME,
            'event_type': 'session_end',
        }
        send_to_kafka(build_kafka_message(end_body))
        kafka_producer.flush()
        print(f"Flushed messages to Kafka topic: {KAFKA_TOPIC}")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        traceback.print_exc()
        
    finally:
        client.dismiss()

if __name__ == "__main__":
    main()