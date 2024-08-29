
#!/usr/bin/env python3
import argparse

from livesync import Folder, sync

# parser = argparse.ArgumentParser(description='Sync local code with robot.')
# parser.add_argument('robot', help='Robot hostname')

# args = parser.parse_args()
# touch = 'touch /main.py'
# , on_change=touch
sync(
    # Folder('.', 'zauberzeug@192.168.178.27:~/zedxmini'),
    Folder('.', 'zauberzeug@192.168.1.252:~/zedxmini'),


    # Uncomment the following lines to sync additional folders and thereby make them available on the robot:
    # Folder('../rosys/rosys', f'{args.robot}:~/field_friend/rosys', on_change=touch),
    # Folder('../nicegui/nicegui', f'{args.robot}:~/field_friend/nicegui', on_change=touch),
    # Folder('../lizard', f'{args.robot}:~/lizard', on_change=touch),
)
