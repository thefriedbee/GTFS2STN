mermaid_text = """
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
"""