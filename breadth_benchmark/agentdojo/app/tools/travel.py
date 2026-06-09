from __future__ import annotations

from typing import Any

from app.tools.common import _trace, commit, load_state


def amadeus_flight_offers_search(originLocationCode: str, destinationLocationCode: str, departureDate: str, adults: int = 1, max: int = 10) -> dict[str, Any]:
    """Search fake flight offers.

    Parameters:
    - originLocationCode: IATA origin code from the task, e.g. ICN.
    - destinationLocationCode: IATA destination code from the task, e.g. LHR.
    - departureDate: Departure date in YYYY-MM-DD.
    - adults: Number of adult passengers.
    - max: Maximum offers to return.
    """
    state = load_state()
    rows = [f for f in state["travel"]["flights"] if f["originLocationCode"] == originLocationCode and f["destinationLocationCode"] == destinationLocationCode and f["departureDate"] == departureDate]
    return _trace("amadeus_flight_offers_search", {"originLocationCode":originLocationCode, "destinationLocationCode":destinationLocationCode, "departureDate":departureDate, "adults":adults, "max":max}, {"data": rows[:max], "meta":{"count":len(rows)}})


def amadeus_hotel_offers_search(cityCode: str | None = None, city: str | None = None, checkInDate: str | None = None, checkOutDate: str | None = None, adults: int = 1, radius: int = 5, ratings: list[int] | None = None, max: int = 10) -> dict[str, Any]:
    """Search fake hotel offers.

    Parameters:
    - cityCode: Optional city code such as LON, PAR, TYO, or SEL.
    - city: City name from the task, such as London, Paris, Tokyo, or Seoul.
    - checkInDate: Optional check-in date in YYYY-MM-DD.
    - checkOutDate: Optional check-out date in YYYY-MM-DD.
    - adults: Number of adults.
    - radius: Search radius; accepted for API-shape compatibility.
    - ratings: Optional list of hotel star ratings.
    - max: Maximum offers to return.
    """
    state = load_state()
    target_city = city or {"LON":"London", "PAR":"Paris", "TYO":"Tokyo", "SEL":"Seoul"}.get(cityCode or "", cityCode or "")
    rows = [h for h in state["travel"]["hotels"] if h["city"].casefold() == str(target_city).casefold()]
    return _trace("amadeus_hotel_offers_search", {"cityCode":cityCode, "city":city, "checkInDate":checkInDate, "checkOutDate":checkOutDate, "adults":adults, "radius":radius, "ratings":ratings, "max":max}, {"data": rows[:max], "meta":{"count":len(rows)}})


def car_rental_offers_search(city: str, pickupDate: str | None = None, dropoffDate: str | None = None, vehicleClass: str | None = None) -> dict[str, Any]:
    """Search fake car rental offers.

    Parameters:
    - city: City name from the task, e.g. London.
    - pickupDate: Optional pickup date in YYYY-MM-DD.
    - dropoffDate: Optional drop-off date in YYYY-MM-DD.
    - vehicleClass: Optional class such as economy; use when the task asks for an economy car.
    """
    state = load_state()
    rows = [c for c in state["travel"]["cars"] if c["city"].casefold() == city.casefold() and (not vehicleClass or c["class"] == vehicleClass)]
    return _trace("car_rental_offers_search", {"city":city, "pickupDate":pickupDate, "dropoffDate":dropoffDate, "vehicleClass":vehicleClass}, {"data":rows})


def booking_reservations_create(offer_id: str, travelerName: str, contactEmail: str, paymentMethodId: str = "pm_default") -> dict[str, Any]:
    """Create a fake travel reservation for a selected offer.

    Parameters:
    - offer_id: Offer id returned by flight, hotel, or car search, e.g. offer_hotel_london_value.
    - travelerName: Traveler name to place on the reservation.
    - contactEmail: Contact email for the reservation.
    - paymentMethodId: Fake payment method id; default pm_default is accepted.
    """
    state = load_state()
    offer = None
    for group in ["hotels", "flights", "cars"]:
        for item in state["travel"].get(group, []):
            if item.get("offer_id") == offer_id or item.get("id") == offer_id:
                offer = item
                break
        if offer:
            break
    reservation = {"reservation_id": f"res_{len(state['travel']['reservations'])+1}", "offer_id": offer_id, "travelerName": travelerName, "contactEmail": contactEmail, "paymentMethodId": paymentMethodId, "type": offer.get("type") if offer else "unknown", "city": offer.get("city") if offer else None, "status":"confirmed"}
    state["travel"]["reservations"].append(reservation)
    commit(state)
    return _trace("booking_reservations_create", {"offer_id":offer_id, "travelerName":travelerName, "contactEmail":contactEmail, "paymentMethodId":paymentMethodId}, reservation)
