export const searchConfig = {
  location: {
    iata: process.env.LOCATION_IATA ?? "ALC",
    name: process.env.LOCATION_NAME ?? "Alicante–Elche Miguel Hernández Airport",
    coordinates: process.env.LOCATION_COORDINATES ?? "38.28689956665039,-0.5599269866943359",
  },
  pickup: {
    day: parseInt(process.env.PICKUP_DAY ?? "25", 10),
    month: parseInt(process.env.PICKUP_MONTH ?? "2", 10),
    year: parseInt(process.env.PICKUP_YEAR ?? "2026", 10),
    hour: parseInt(process.env.PICKUP_HOUR ?? "14", 10),
    minute: parseInt(process.env.PICKUP_MINUTE ?? "30", 10),
  },
  dropoff: {
    day: parseInt(process.env.DROPOFF_DAY ?? "12", 10),
    month: parseInt(process.env.DROPOFF_MONTH ?? "3", 10),
    year: parseInt(process.env.DROPOFF_YEAR ?? "2026", 10),
    hour: parseInt(process.env.DROPOFF_HOUR ?? "14", 10),
    minute: parseInt(process.env.DROPOFF_MINUTE ?? "30", 10),
  },
  driversAge: parseInt(process.env.DRIVERS_AGE ?? "30", 10),
  transmission: process.env.FILTER_TRANSMISSION ?? "AUTOMATIC",
  carCategory: process.env.FILTER_CAR_CATEGORY ?? "small",
  cheapPercentile: parseFloat(process.env.CHEAP_PERCENTILE ?? "0.25"),
} as const;

export function buildSearchUrl(): string {
  const c = searchConfig;
  const params = new URLSearchParams({
    location: "",
    dropLocation: "",
    locationName: c.location.name,
    locationIata: c.location.iata,
    dropLocationName: c.location.name,
    dropLocationIata: c.location.iata,
    coordinates: c.location.coordinates,
    dropCoordinates: c.location.coordinates,
    driversAge: String(c.driversAge),
    puDay: String(c.pickup.day),
    puMonth: String(c.pickup.month),
    puYear: String(c.pickup.year),
    puMinute: String(c.pickup.minute),
    puHour: String(c.pickup.hour),
    doDay: String(c.dropoff.day),
    doMonth: String(c.dropoff.month),
    doYear: String(c.dropoff.year),
    doMinute: String(c.dropoff.minute),
    doHour: String(c.dropoff.hour),
    ftsType: "A",
    dropFtsType: "A",
    filterCriteria_transmission: c.transmission,
    filterCriteria_carCategory: c.carCategory,
  });
  return `https://www.rentalcars.com/search-results?${params.toString()}`;
}

export function getRentalDays(): number {
  const pu = searchConfig.pickup;
  const do_ = searchConfig.dropoff;
  const pickup = new Date(pu.year, pu.month - 1, pu.day);
  const dropoff = new Date(do_.year, do_.month - 1, do_.day);
  return Math.max(1, Math.ceil((dropoff.getTime() - pickup.getTime()) / (24 * 60 * 60 * 1000)));
}

export function getPickupDateStr(): string {
  const p = searchConfig.pickup;
  return `${p.year}-${String(p.month).padStart(2, "0")}-${String(p.day).padStart(2, "0")}`;
}

export function getDropoffDateStr(): string {
  const d = searchConfig.dropoff;
  return `${d.year}-${String(d.month).padStart(2, "0")}-${String(d.day).padStart(2, "0")}`;
}
