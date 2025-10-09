#!/bin/bash
# Fix permissions on existing Docker-generated files

echo "Fixing permissions on yt_notes files..."

# Fix ownership of files in /home/justin/Documents/vaults/yt_notes/
if [ -d "/home/justin/Documents/vaults/yt_notes" ]; then
    sudo chown -R justin:justin /home/justin/Documents/vaults/yt_notes/
    echo "✓ Fixed permissions on /home/justin/Documents/vaults/yt_notes/"
    echo ""
    echo "Current permissions:"
    ls -lah /home/justin/Documents/vaults/yt_notes/ | head -10
else
    echo "Directory /home/justin/Documents/vaults/yt_notes/ not found"
fi

echo ""
echo "Done! Files should now be readable and writable by your user."
