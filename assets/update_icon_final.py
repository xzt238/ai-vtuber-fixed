#!/usr/bin/env python3
"""
Update Windows exe icon using Windows API via ctypes.
Final version - safely update icon without breaking the exe.
"""

import os
import sys
import ctypes
from ctypes import wintypes

# Windows API constants
RT_ICON = 3
RT_GROUP_ICON = 14

# Load Windows API functions
kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

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
                RT_ICON,
                str(res_id),
                LANGID,
                res_data,
                size
            ):
                raise WindowsError(f"Failed to update icon resource {res_id}")

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
            if width == 0:  # 256 maps to 0 in ICO but should be 256 in GRPICONDIRENTRY
                width = 256
            if height == 0:
                height = 256

            group_icon_data += struct.pack(
                '<BBBBHHH',  # H is 2 bytes (WORD) for res_id
                width, height, colors, reserved, planes, bpp, res_id
            )

        # Update RT_GROUP_ICON resource (ID = 1, which is standard for main icon)
        group_data = ctypes.create_string_buffer(group_icon_data)
        if not UpdateResourceW(
            h_update,
            RT_GROUP_ICON,
            "1",  # Main icon group ID
            LANGID,
            group_data,
            len(group_icon_data)
        ):
            raise WindowsError("Failed to update group icon resource")

        print(f"  Updated group icon resource")

        # Commit changes
        if not EndUpdateResourceW(h_update, False):
            raise WindowsError("Failed to commit resource update")

        print(f"✓ Successfully updated icon for {exe_path}")

    except Exception as e:
        # Discard changes on error
        EndUpdateResourceW(h_update, True)
        raise e

if __name__ == '__main__':
    import struct

    if len(sys.argv) != 3:
        print("Usage: python update_icon_final.py <exe_path> <ico_path>")
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
