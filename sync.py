
#!/usr/bin/env python3
import argparse

from livesync import Folder, sync

parser = argparse.ArgumentParser(description='Sync local code with robot.')
parser.add_argument('robot', help='Robot hostname')

args = parser.parse_args()
touch = 'touch ~/zedxmini/main.py'
sync(
    Folder('.', f'{args.robot}:~/zedxmini_ros', on_change=touch)
)
