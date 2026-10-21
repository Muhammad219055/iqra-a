"""
Launcher for Quran Recitation & Memorization Tutor Server.
Starts local FastAPI server on http://127.0.0.1:8000
"""

import sys
import uvicorn

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  QURAN RECITATION & MEMORIZATION TUTOR (Local-First)")
    print("=" * 65)
    print("  Server running at:")
    print("    • Local Mac: http://127.0.0.1:8000")
    print("    • iPhone on Wi-Fi: http://192.168.19.137:8000")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 65 + "\n")
    uvicorn.run("src.server.app:app", host="0.0.0.0", port=8000, log_level="info")
