#!/bin/bash

# Replace these with your actual Supabase values
export SUPABASE_URL="https://your-actual-project-id.supabase.co"
export SUPABASE_ANON_KEY="your-actual-anon-key"

echo "Environment variables set:"
echo "SUPABASE_URL=$SUPABASE_URL"
echo "SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY:0:20}..."

# Run the scraper
python3 crawl_canvas_to_supabase.py