from core.config import Settings

print("Checking for feature flags in Settings.model_fields...")
print(f"RELATED_INCIDENTS_ENABLED: {'RELATED_INCIDENTS_ENABLED' in Settings.model_fields}")
print(f"PLATFORM_DETECTION_ENABLED: {'PLATFORM_DETECTION_ENABLED' in Settings.model_fields}")
print(f"ARCHIVE_EXPANDED_FORMATS_ENABLED: {'ARCHIVE_EXPANDED_FORMATS_ENABLED' in Settings.model_fields}")

try:
    s = Settings()
    print("\n✓ Settings instance created successfully")
    print(f"RELATED_INCIDENTS_ENABLED = {s.RELATED_INCIDENTS_ENABLED}")
    print(f"PLATFORM_DETECTION_ENABLED = {s.PLATFORM_DETECTION_ENABLED}")
    print(f"ARCHIVE_EXPANDED_FORMATS_ENABLED = {s.ARCHIVE_EXPANDED_FORMATS_ENABLED}")
except Exception as e:
    print(f"\n✗ Error: {e}")
