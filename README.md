# dfr-ac-udp-streaming

Python UDP telemetry bridge for Assetto Corsa that streams decoded telemetry channels to Kafka.

## Overview

This project:
- Connects to Assetto Corsa over UDP (`127.0.0.1:9996`)
- Subscribes to real-time telemetry updates
- Decodes packet fields into typed values
- Publishes each field as a channelized message to Kafka
- Emits session lifecycle events (`session_start`, `session_end`)

## Requirements

- Python 3.9+ (recommended)
- Assetto Corsa running with UDP telemetry enabled
- Reachable Kafka broker

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Update values in `main.py` as needed:

- `KAFKA_CONFIG['bootstrap.servers']`: Kafka bootstrap endpoint
- `KAFKA_TOPIC`: destination topic
- `SENSOR_ID`: stable sensor identifier
- `SENSOR_NAME`: sensor display name
- `STREAM_NAME`: stream name written into each payload

Network constants are defined in `constants.py`:
- UDP port: `9996`
- Socket buffer size: `65536`
- Socket timeout: `5.0s`

## Run

```bash
python main.py
```

Expected startup sequence:
- Connect to Assetto Corsa and print car/driver/track metadata
- Subscribe to telemetry updates
- Begin streaming to Kafka
- Print one-line live status in the console (speed, RPM, gear, throttle, lap time)

Stop with `Ctrl+C`; the app will send a `session_end` event and flush Kafka messages.

## Output Format

All Kafka records are JSON-encoded UTF-8 messages with this envelope:

```json
{
  "payload": {
    "id": "2b0f9a3d-08ee-4dc2-8d55-0ed8a2b9f6ef",
    "body": {
      "...": "..."
    },
    "stream": "ac-telemetry"
  }
}
```

### Telemetry event shape (`event_type = "telemetry"`)

Each telemetry channel is emitted as a separate Kafka message:

```json
{
  "payload": {
    "id": "uuid-v4",
    "body": {
      "timestamp": 1714100000.123,
      "source": "Assetto Corsa",
      "sensor_id": "ac-telemetry-1",
      "sensor_name": "Assetto Corsa",
      "event_type": "telemetry",
      "channel": "speed_Kmh",
      "value": 132.4
    },
    "stream": "ac-telemetry"
  }
}
```

Base fields in every telemetry message:
- `timestamp` (float, Unix epoch seconds)
- `source` (string)
- `sensor_id` (string)
- `sensor_name` (string)
- `event_type` = `telemetry`
- `channel` (string; channel key)
- `value` (number or boolean depending on channel)

### Session lifecycle events

`session_start` message body:

```json
{
  "timestamp": "2026-04-26T06:00:00.000000+00:00",
  "sensor_id": "ac-telemetry-1",
  "sensor_name": "Assetto Corsa",
  "event_type": "session_start",
  "identifier": 1,
  "version": 1,
  "carName": "car_model",
  "driverName": "driver_name",
  "trackName": "track_name",
  "trackConfig": "track_config"
}
```

`session_end` message body:

```json
{
  "timestamp": "2026-04-26T06:10:00.000000+00:00",
  "sensor_id": "ac-telemetry-1",
  "sensor_name": "Assetto Corsa",
  "event_type": "session_end"
}
```

Both lifecycle messages are wrapped with the same top-level `payload` envelope.

## Channel Naming

Scalar channels:
- `identifier`, `size`
- `speed_Kmh`, `speed_Mph`, `speed_Ms`
- `isAbsEnabled`, `isAbsInAction`, `isTcInAction`, `isTcEnabled`, `isInPit`, `isEngineLimiterOn`
- `accG_vertical`, `accG_horizontal`, `accG_frontal`
- `lapTime`, `lastLap`, `bestLap`, `lapCount`
- `gas`, `brake`, `clutch`, `engineRPM`, `steer`, `gear`, `cgHeight`
- `carPositionNormalized`, `carSlope`

Indexed channels:
- `carCoordinates_0..2`
- `wheelAngularSpeed_0..3`
- `slipAngle_0..3`
- `slipAngle_ContactPatch_0..3`
- `slipRatio_0..3`
- `tyreSlip_0..3`
- `ndSlip_0..3`
- `load_0..3`
- `Dy_0..3`
- `Mz_0..3`
- `tyreDirtyLevel_0..3`
- `camberRAD_0..3`
- `tyreRadius_0..3`
- `tyreLoadedRadius_0..3`
- `suspensionHeight_0..3`

## Notes

- The producer sends asynchronously and calls `poll(0)` on each produce.
- Final delivery is forced on shutdown with `flush()`.
- If Kafka publish fails for a message, the exception is printed to console.