#!/bin/sh
# Test script to verify cron setup is working

echo "Testing cron setup..."
echo "Current time: $(date)"
echo "Scripts directory contents:"
ls -la /scripts/
echo "Cron jobs:"
crontab -l
echo "Docker containers:"
docker ps
echo "Test completed at: $(date)"
