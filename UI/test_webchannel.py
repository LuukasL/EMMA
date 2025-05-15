# test_webchannel.py - Save this as a separate file and run it
import sys

print("Checking for QWebChannel...")

try:
    from PyQt6.QtWebChannel import QWebChannel
    print("✓ Found QWebChannel in QtWebChannel")
except ImportError:
    print("✗ Not found in QtWebChannel")

try:
    from PyQt6.QtWebEngineCore import QWebChannel
    print("✓ Found QWebChannel in QtWebEngineCore")
except ImportError:
    print("✗ Not found in QtWebEngineCore")

print("Done checking")