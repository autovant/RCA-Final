"""
Quick verification script for feature flag integration.
Tests that don't require a running backend.
"""

import os
import sys
from pathlib import Path


def check_env_file():
    """Verify .env file has the feature flags."""
    print("\n" + "=" * 60)
    print(" .env File Check")
    print("=" * 60)
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        return False
    
    content = env_file.read_text()
    flags = {
        "RELATED_INCIDENTS_ENABLED": None,
        "PLATFORM_DETECTION_ENABLED": None,
        "ARCHIVE_EXPANDED_FORMATS_ENABLED": None,
    }
    
    for line in content.split("\n"):
        line = line.strip()
        for flag in flags:
            if line.startswith(flag + "="):
                value = line.split("=", 1)[1].strip()
                flags[flag] = value
    
    all_found = True
    for flag, value in flags.items():
        if value:
            print(f"✓ {flag}={value}")
        else:
            print(f"❌ {flag} not found")
            all_found = False
    
    return all_found


def check_code_integration():
    """Verify code has feature flag checks."""
    print("\n" + "=" * 60)
    print(" Code Integration Check")
    print("=" * 60)
    
    checks = []
    
    # Check incidents.py
    incidents_file = Path("apps/api/routers/incidents.py")
    if incidents_file.exists():
        content = incidents_file.read_text()
        has_import = "import os" in content
        has_func = "_is_related_incidents_enabled" in content
        has_guard = "if not _is_related_incidents_enabled()" in content
        
        if has_import and has_func and has_guard:
            print("✓ incidents.py has feature flag integration")
            checks.append(True)
        else:
            print(f"❌ incidents.py missing: import={has_import}, func={has_func}, guard={has_guard}")
            checks.append(False)
    else:
        print("❌ incidents.py not found")
        checks.append(False)
    
    # Check jobs.py
    jobs_file = Path("apps/api/routers/jobs.py")
    if jobs_file.exists():
        content = jobs_file.read_text()
        has_import = "import os" in content
        has_func = "_is_platform_detection_enabled" in content
        has_guard = "if not _is_platform_detection_enabled()" in content
        
        if has_import and has_func and has_guard:
            print("✓ jobs.py has feature flag integration")
            checks.append(True)
        else:
            print(f"❌ jobs.py missing: import={has_import}, func={has_func}, guard={has_guard}")
            checks.append(False)
    else:
        print("❌ jobs.py not found")
        checks.append(False)
    
    # Check service.py
    service_file = Path("core/files/service.py")
    if service_file.exists():
        content = service_file.read_text()
        has_import = "import os" in content
        has_enhanced = "get_enhanced_extractor" in content
        has_func = "_is_archive_expanded_formats_enabled" in content
        has_guard = "if _is_archive_expanded_formats_enabled()" in content
        
        if has_import and has_enhanced and has_func and has_guard:
            print("✓ service.py has archive format integration")
            checks.append(True)
        else:
            print(f"❌ service.py missing: import={has_import}, enhanced={has_enhanced}, func={has_func}, guard={has_guard}")
            checks.append(False)
    else:
        print("❌ service.py not found")
        checks.append(False)
    
    # Check processor.py
    processor_file = Path("core/jobs/processor.py")
    if processor_file.exists():
        content = processor_file.read_text(encoding="utf-8")
        has_related_func = "_is_related_incidents_enabled" in content
        has_platform_func = "_is_platform_detection_enabled" in content
        has_guard = "if not self._is_platform_detection_enabled()" in content
        
        if has_related_func and has_platform_func and has_guard:
            print("✓ processor.py has platform detection integration")
            checks.append(True)
        else:
            print(f"❌ processor.py missing: related={has_related_func}, platform={has_platform_func}, guard={has_guard}")
            checks.append(False)
    else:
        print("❌ processor.py not found")
        checks.append(False)
    
    return all(checks)


def test_environment_loading():
    """Test that environment variables load correctly."""
    print("\n" + "=" * 60)
    print(" Environment Variable Loading")
    print("=" * 60)
    
    # Set test variables
    os.environ["RELATED_INCIDENTS_ENABLED"] = "true"
    os.environ["PLATFORM_DETECTION_ENABLED"] = "true"
    os.environ["ARCHIVE_EXPANDED_FORMATS_ENABLED"] = "true"
    
    try:
        # Import and test
        sys.path.insert(0, str(Path.cwd()))
        from core.jobs.processor import JobProcessor
        
        processor = JobProcessor()
        
        related_enabled = processor._is_related_incidents_enabled()
        platform_enabled = processor._is_platform_detection_enabled()
        
        print(f"Related Incidents: {related_enabled}")
        print(f"Platform Detection: {platform_enabled}")
        
        if related_enabled and platform_enabled:
            print("✓ JobProcessor reads environment variables correctly")
            return True
        else:
            print("❌ JobProcessor not reading environment variables")
            return False
            
    except Exception as e:
        print(f"❌ Error testing processor: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification checks."""
    print("\n" + "=" * 60)
    print(" FEATURE INTEGRATION VERIFICATION")
    print("=" * 60)
    
    results = []
    
    results.append(("Environment File", check_env_file()))
    results.append(("Code Integration", check_code_integration()))
    results.append(("Runtime Loading", test_environment_loading()))
    
    print("\n" + "=" * 60)
    print(" SUMMARY")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL CHECKS PASSED - Features are integrated!")
    else:
        print("❌ SOME CHECKS FAILED - Review errors above")
    print("=" * 60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
