"""Shortcut: python run_label_tool.py"""
from dataset.label_tool.app import app, _get_sources
import os, sys

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"  Annotation tool: http://localhost:{port}")
    print(f"  Ctrl+C để dừng\n")
    print("  Đang load corpus...", end=" ", flush=True)
    try:
        print(f"{len(_get_sources()):,} câu")
    except FileNotFoundError as e:
        print(f"\n  Lỗi: {e}")
        sys.exit(1)
    app.run(host="0.0.0.0", port=port, debug=False)
