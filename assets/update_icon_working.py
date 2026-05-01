#!/usr/bin/env python3
"""
Update Windows exe icon using Windows API via ctypes.
Fixed version - correctly handle resource type parameters.
"""

import os
import sys
import ctypes
from ctypes import wintypes
import struct

# Windows API constants
RT_ICON = 3
RT_GROUP_ICON = 14

# Load Windows API functions
kernel32 = ctypes.windll.kernel32

# Define function prototypes
BeginUpdateResourceW = kernel32.BeginUpdateResourceW
BeginUpdateResourceW.argtypes = [wintypes.LPCWSTR, wintypes.BOOL]
BeginUpdateResourceW.restype = wintypes.HANDLE

UpdateResourceW = kernel32.UpdateResourceW
UpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.WORD, wintypes.LPVOID, wintypes.DWORD]
UpdateResourceW.restype = wintypes.BOOL

EndUpdateResourceW = kernel32.EndUpdateResourceW
EndUpdateResourceW.argtypes = [wintypes.HANDLE, wintypes.BOOL]
EndUpdateResourceW.restype = wintypes.BOOL

# Helper function to convert integer resource ID to LPCWSTR
def MAKEINTRESOURCE(i):
    """Convert integer resource ID to LPCWSTR (via MAKEINTRESOURCE macro)."""
    return ctypes.c_wchar_p(i)

MAKELANGID = lambda p, s: (s << 10) | p
LANG_NEUTRAL = 0
SUBLANG_NEUTRAL = 0
LANGID = MAKELANGID(LANG_NEUTRAL, SUBLANG_NEUTRAL)

def update_exe_icon(exe_path, ico_path):
    """Update exe icon using Windows API."""

    # Read ICO file
    with open(ico_path, 'rb') as f:
        ico_data = f.read()

    # Parse ICO file
    # ICO header: 2 bytes reserved, 2 bytes type (1 for ICO), 2 bytes count
    reserved, ico_type, count = struct.unpack('<HHH', ico_data[:6])

    print(f"ICO file contains {count} images")

    # Begin update resource
    h_update = BeginUpdateResourceW(exe_path, False)
    if not h_update:
        raise WindowsError(f"Failed to begin update resource for {exe_path}")

    try:
        # Process each icon image
        for i in range(count):
            # Read directory entry
            entry_offset = 6 + i * 16
            width, height, colors, reserved, planes, bpp, size, offset = struct.unpack(
                '<BBBBHHII', ico_data[entry_offset:entry_offset+16]
            )

            # Read image data
            image_data = ico_data[offset:offset+size]

            # Resource ID starts from 1
            res_id = i + 1

            # Update icon resource
            res_data = ctypes.create_string_buffer(image_data)
            if not UpdateResourceW(
                h_update,
                MAKEINTRESOURCE(RT_ICON),  # Use MAKEINTRESOURCE for integer resource types
                MAKEINTRESOURCE(res_id),
                LANGID,
                res_data,
                size
            ):
                error = kernel32.GetLastError()
                raise WindowsError(f"Failed to update icon resource {res_id}, error code: {error}")

            print(f"  Updated icon resource {res_id} (size: {width}x{height}, data: {size} bytes)")

        # Create RT_GROUP_ICON resource
        # GRPICONDIR structure
        group_icon_data = struct.pack('<HHH', 0, 1, count)

        for i in range(count):
            entry_offset = 6 + i * 16
            width, height, colors, reserved, planes, bpp, size, offset = struct.unpack(
                '<BBBBHHII', ico_data[entry_offset:entry_offset+16]
            )

            # GRPICONDIRENTRY (uses WORD for ID instead of DWORD for offset)
            res_id = i + 1

            # In GRPICONDIRENTRY, width/height of 0 means 256
            # But if original width is 0 (meaning 256 in ICO), we keep it as 0 for GRPICONDIRENTRY
            # Actually, for GRPICONDIRENTRY:
            # - If width >= 256, set to 0
            # - If height >= 256, set to 0
            if width == 0:
                width = 0  # 256 pixels represented as 0 in GRPICONDIRENTRY
            if height == 0:
                height = 0  # 256 pixels represented as 0 in GRPICONDIRENTRY

            # Ensure all values are in valid range for 'B' format (0-255)
            width = width & 0xFF
            height = height & 0xFF
            colors = colors & 0xFF
            reserved = reserved & 0xFF

            group_icon_data += struct.pack(
                '<BBBBHHH',  # H is 2 bytes (WORD) for res_id
                width, height, colors, reserved, planes, bpp, res_id
            )

        # Update RT_GROUP_ICON resource (ID = 1, which is standard for main icon)
        group_data = ctypes.create_string_buffer(group_icon_data)
        if not UpdateResourceW(
            h_update,
            MAKEINTRESOURCE(RT_GROUP_ICON),  # Use MAKEINTRESOURCE for integer resource types
            MAKEINTRESOURCE(1),  # Main icon group ID
            LANGID,
            group_data,
            len(group_icon_data)
        ):
            error = kernel32.GetLastError()
            raise WindowsError(f"Failed to update group icon resource, error code: {error}")

        print(f"  Updated group icon resource")

        # Commit changes
        if not EndUpdateResourceW(h_update, False):
            error = kernel32.GetLastError()
            raise WindowsError(f"Failed to commit resource update, error code: {error}")

        print(f"✓ Successfully updated icon for {exe_path}")

    except Exception as e:
        # Discard changes on error
        EndUpdateResourceW(h_update, True)
        raise e

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python update_icon_working.py <exe_path> <ico_path>")
        sys.exit(1)

    exe_path = sys.argv[1]
    ico_path = sys.argv[2]

    # Check files exist
    if not os.path.exists(exe_path):
        print(f"Error: EXE file not found: {exe_path}")
        sys.exit(1)

    if not os.path.exists(ico_path):
        print(f"Error: ICO file not found: {ico_path}")
        sys.exit(1)

    # Backup original exe
    backup_path = exe_path + ".icon_backup"
    if not os.path.exists(backup_path):
        import shutil
        shutil.copy2(exe_path, backup_path)
        print(f"✓ Created backup: {backup_path}")

    # Update icon
    update_exe_icon(exe_path, ico_path)
