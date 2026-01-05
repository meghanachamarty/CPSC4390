#!/usr/bin/env python3
"""
Setup script for Canvas to Supabase scraper
"""
import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def main():
    print("=== Canvas to Supabase Scraper Setup ===")
    
    # Check if .env file exists
    if not os.path.exists(".env"):
        print("\n❌ .env file not found!")
        print("Please create a .env file with your Supabase credentials:")
        print("SUPABASE_ANON_KEY='your_anon_key_here'")
        print("SUPABASE_URL='your_supabase_url_here'")
        print("STORAGE_BUCKET='your_bucket_name_here'")
        return False
    else:
        print("✓ .env file found")
    
    # Install Python dependencies
    if not run_command("pip install -r requirements-test.txt", "Installing Python dependencies"):
        return False
    
    # Install Playwright browsers
    if not run_command("playwright install chromium", "Installing Playwright browser"):
        return False
    
    # Test Supabase connection
    print("\n=== Testing Supabase Connection ===")
    if not run_command("python test_supabase_connection.py", "Testing Supabase connection"):
        print("⚠️  Supabase connection test failed. Please check your .env file.")
        return False
    
    print("\n=== Setup Complete ===")
    print("✓ All dependencies installed")
    print("✓ Supabase connection verified")
    print("\nNext steps:")
    print("1. Run: python login_once.py")
    print("2. Run: python crawl_canvas_to_supabase.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)