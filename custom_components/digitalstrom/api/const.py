SSL_FINGERPRINT_REGEX = r"[^0-9a-fA-F]|0[xX]"
SESSION_TOKEN_TIMEOUT = 50
EVENT_LISTENER_TIMEOUT = 120
BUTTON_BUS_EVENT_TIMEOUT = 10
INVERTED_BINARY_INPUTS = {
    "EnOcean single contact (D5-00-01)": "always_invert",
    "IC Alarm 400 Modul": "always_invert",
    "IC PIR Sensor": "never_invert",
}
NOT_DIMMABLE_OUTPUT_MODES = [16, 35, 39, 40, 41]
