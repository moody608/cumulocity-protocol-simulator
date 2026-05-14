def to_signed_16(value: int) -> int:
    ivalue = int(value)
    if not (-32768 <= ivalue <= 32767):
        raise ValueError(f"value {ivalue} exceeds signed 16-bit range")
    return ivalue


def split_u32_to_u16(value: int) -> tuple[int, int]:
    value = int(value) & 0xFFFFFFFF
    high = (value >> 16) & 0xFFFF
    low = value & 0xFFFF
    return high, low


def as_signed_word(word: int) -> int:
    return word if word < 32768 else word - 65536


def smart_meter_to_registers(state) -> dict[int, int]:
    t = state.telemetry

    voltage_v = float(t.get("voltageV", 0.0))
    current_a = float(t.get("currentA", 0.0))
    power_kw = float(t.get("powerKw", 0.0))
    pf = float(t.get("pf", t.get("powerFactor", 1.0)))
    frequency_hz = float(t.get("frequencyHz", 60.0))
    temp_c = float(t.get("tempC", t.get("temperatureC", 25.0)))
    energy_kwh = float(t.get("energyKwh", 0.0))

    energy_wh = int(round(energy_kwh * 1000))
    energy_hi, energy_lo = split_u32_to_u16(energy_wh)

    return {
        0: to_signed_16(int(round(voltage_v * 10))),
        1: to_signed_16(int(round(current_a * 100))),
        2: to_signed_16(int(round(power_kw * 1000))),
        3: to_signed_16(int(round(pf * 1000))),
        4: to_signed_16(int(round(frequency_hz * 100))),
        5: to_signed_16(int(round(temp_c * 10))),
        6: as_signed_word(energy_hi),
        7: as_signed_word(energy_lo),
    }