# GTFS2STN application
An application loads General Transit Feed Specification (GTFS) transit file and convert it to spatio-temporal
network (STN) for shortest path analysis.

If you use the tool, consider cite the following paper:
- [*GTFS2STN: Analyzing GTFS Transit Data By Generating Spatiotemporal Transit Network*](https://arxiv.org/abs/2405.02760)

## Quick explore online (please visit: https://gtfs2stn.streamlit.app/): 

## Run app using docker (recommended way)

Download the docker file from DockerHub with the following command:
```
docker pull friedbee/gtfs2stn:latest
```

You could view the image settings using the following link: https://hub.docker.com/layers/friedbee/gtfs2stn/latest/images/sha256:fe81c3cfdcf022fe6b56b540e44f5a8c37e62aa0c99f912484469ec452a21f91?uuid=4F0A5E81-8B5D-4335-8A84-199956C16020

Then, run the docker container using the command:
```
docker run -p 8501:8501 friedbee/gtfs2stn
```

After that, visit the following website (http://localhost:8501)

# Recent updates
- October, 2024 (version 2.0)
  - use rustworkx to substitute networkx for better running efficiency
  - write pytest code to safeguard core code

# GTFS core structure

```mermaid
classDiagram
    Agency "1" -- "*" Route
    Route "1" -- "*" Trip
    Trip "1" -- "*" StopTime
    Stop "1" -- "*" StopTime
    Calendar "1" -- "*" Trip
    CalendarDate "0..*" -- "*" Trip
    FareAttribute "1" -- "*" FareRule
    Route "1" -- "*" FareRule
    Shape "0..1" -- "*" Trip
    Frequency "0..*" -- "1" Trip
    Transfer "0..*" -- "2" Stop

    class Agency {
        agency_id
        agency_name
        agency_url
        agency_timezone
    }
    class Route {
        route_id
        route_short_name
        route_long_name
        route_type
    }
    class Trip {
        trip_id
        route_id
        service_id
        trip_headsign
    }
    class Stop {
        stop_id
        stop_name
        stop_lat
        stop_lon
    }
    class StopTime {
        trip_id
        arrival_time
        departure_time
        stop_id
        stop_sequence
    }
    class Calendar {
        service_id
        monday
        tuesday
        wednesday
        thursday
        friday
        saturday
        sunday
        start_date
        end_date
    }
    class CalendarDate {
        service_id
        date
        exception_type
    }
    class FareAttribute {
        fare_id
        price
        currency_type
        payment_method
        transfers
    }
    class FareRule {
        fare_id
        route_id
        origin_id
        destination_id
        contains_id
    }
    class Shape {
        shape_id
        shape_pt_lat
        shape_pt_lon
        shape_pt_sequence
    }
    class Frequency {
        trip_id
        start_time
        end_time
        headway_secs
    }
    class Transfer {
        from_stop_id
        to_stop_id
        transfer_type
        min_transfer_time
    }
```
