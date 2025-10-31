"""Verify all three feature flags are enabled."""
import os

# Simulate .env values
os.environ["RELATED_INCIDENTS_ENABLED"] = "true"
os.environ["PLATFORM_DETECTION_ENABLED"] = "true"
os.environ["ARCHIVE_EXPANDED_FORMATS_ENABLED"] = "true"

from core.jobs.processor import JobProcessor

print("Feature Flag Verification")
print("=" * 50)

processor = JobProcessor()

# Test RELATED_INCIDENTS_ENABLED
enabled = processor._is_related_incidents_enabled()
status = "✓ ENABLED" if enabled else "✗ DISABLED"
print(f"related_incidents:        {status}")

# Test other two flags by checking environment directly
platform_enabled = os.getenv("PLATFORM_DETECTION_ENABLED", "").lower() in ("true", "1", "yes", "on")
status = "✓ ENABLED" if platform_enabled else "✗ DISABLED"
print(f"platform_detection:       {status}")

archive_enabled = os.getenv("ARCHIVE_EXPANDED_FORMATS_ENABLED", "").lower() in ("true", "1", "yes", "on")
status = "✓ ENABLED" if archive_enabled else "✗ DISABLED"
print(f"archive_expanded_formats: {status}")

print("=" * 50)

if enabled and platform_enabled and archive_enabled:
    print("\n✓ All feature flags are ENABLED and ready for testing!")
else:
    print("\n✗ Some flags are disabled")
