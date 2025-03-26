import json

CALIBRATION_FILE = "calibration_settings.json"

# Default values
DEFAULT_DEAD_ZONE = 0.02
DEFAULT_SMOOTHING = 0.8
DEFAULT_SENSITIVITY = 3.5

def load_calibration_settings():
    try:
        with open(CALIBRATION_FILE, "r") as f:
            settings = json.load(f)
            print("✅ Loaded Calibration Settings:", settings)
            return (
                settings.get("dead_zone", DEFAULT_DEAD_ZONE),
                settings.get("smoothing", DEFAULT_SMOOTHING),
                settings.get("sensitivity", DEFAULT_SENSITIVITY)
            )
    except FileNotFoundError:
        print("⚠️ No calibration file found! Using default settings.")
        return DEFAULT_DEAD_ZONE, DEFAULT_SMOOTHING, DEFAULT_SENSITIVITY

DEAD_ZONE, SMOOTHING_FACTOR, SENSITIVITY = load_calibration_settings()
