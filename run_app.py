import os
import sys

# CRITICAL: Set up paths BEFORE any imports
# When bundled with py2app, packages are zipped. We need to:
# 1. Use extracted site-packages directory for sounddevice (has dylib)
# 2. Set DYLD_LIBRARY_PATH for PortAudio

# Get the path to extracted site-packages
app_resources = os.path.dirname(os.path.abspath(__file__))
if app_resources.endswith('.app/Contents/Resources'):
    # Running as bundled app
    site_packages_extracted = os.path.join(app_resources, "lib/python3.13/site-packages")
    site_packages_zip = os.path.join(app_resources, "lib/python3.13/site-packages.zip")
    
    # Insert extracted site-packages BEFORE the zip file in sys.path
    # This makes Python prefer the extracted directory
    if os.path.exists(site_packages_extracted):
        # Remove site-packages.zip from sys.path if present
        sys.path = [p for p in sys.path if not p.endswith('site-packages.zip')]
        # Insert extracted directory at the beginning
        sys.path.insert(0, site_packages_extracted)
    
    # Set DYLD_LIBRARY_PATH for PortAudio dylib
    portaudio_dir = os.path.join(site_packages_extracted, "_sounddevice_data/portaudio-binaries")
    if os.path.exists(portaudio_dir):
        os.environ["DYLD_LIBRARY_PATH"] = portaudio_dir + ":" + os.environ.get("DYLD_LIBRARY_PATH", "")

from app.main import main


if __name__ == "__main__":
    main()
