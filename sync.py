
#!/usr/bin/env python3
import argparse

from livesync import Folder, sync

parser = argparse.ArgumentParser(description='Sync local code with robot.')
parser.add_argument('robot', help='Robot hostname')

args = parser.parse_args()
touch = 'touch ~/zedxmini/main.py'
folders = [Folder('.', f'{args.robot}:~/zedxmini', on_change=touch)]
sync(
    Folder('.', f'{args.robot}:~/zedxmini', on_change=touch)
)
