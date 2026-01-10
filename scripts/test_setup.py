#!/usr/bin/env python3
"""
Test Setup Script
Tests the project setup and ChromeDriver configuration
"""

import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def test_chromedriver():
    """Test if ChromeDriver is working properly"""
    print("Testing ChromeDriver setup...")
    
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://velourlive.com")
        
        title = driver.title
        driver.quit()
        
        print(f"✅ ChromeDriver working! Page title: {title}")
        return True
        
    except Exception as e:
        print(f"❌ ChromeDriver error: {e}")
        return False

def test_project_structure():
    """Test if project structure is correct"""
    print("\nTesting project structure...")
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    required_dirs = [
        'data/raw',
        'data/processed', 
        'data/exports',
        'scripts',
        'docs',
        'logs'
    ]
    
    all_good = True
    for dir_path in required_dirs:
        full_path = os.path.join(project_root, dir_path)
        if os.path.exists(full_path):
            print(f"✅ {dir_path}")
        else:
            print(f"❌ {dir_path} - Missing!")
            all_good = False
    
    return all_good

def test_data_files():
    """Test if data files exist"""
    print("\nTesting data files...")
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    data_files = [
        'data/processed/velour_parsed_shows_20251011_143618.json',
        'data/exports/velour_final_dataset_20251011_143729.tsv'
    ]
    
    all_good = True
    for file_path in data_files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"✅ {file_path} ({size} bytes)")
        else:
            print(f"❌ {file_path} - Missing!")
            all_good = False
    
    return all_good

def main():
    print("=== Provo Music Museum - Setup Test ===\n")
    
    # Test ChromeDriver
    chromedriver_ok = test_chromedriver()
    
    # Test project structure
    structure_ok = test_project_structure()
    
    # Test data files
    data_ok = test_data_files()
    
    print(f"\n=== Test Results ===")
    print(f"ChromeDriver: {'✅ Working' if chromedriver_ok else '❌ Failed'}")
    print(f"Project Structure: {'✅ Complete' if structure_ok else '❌ Incomplete'}")
    print(f"Data Files: {'✅ Present' if data_ok else '❌ Missing'}")
    
    if chromedriver_ok and structure_ok and data_ok:
        print(f"\n🎉 All tests passed! Project is ready to use.")
        return True
    else:
        print(f"\n⚠️  Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

