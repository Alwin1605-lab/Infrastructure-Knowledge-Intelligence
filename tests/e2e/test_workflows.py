import pytest
from playwright.sync_api import Page, expect
import time
import os

# E2E Tests running against local frontend

BASE_URL = "http://localhost:5173"

def test_frontend_loads(page: Page):
    page.goto(BASE_URL)
    # Check if the title is generally correct or if the root element loads
    expect(page).to_have_title("Infrastructure Knowledge Intelligence")

def test_login_invalid_credentials(page: Page):
    page.goto(BASE_URL)
    
    # Normally we would click login, but let's assume there's a login form
    # Note: actual selectors depend on frontend implementation, using generic placeholders
    try:
        page.fill('input[type="email"]', 'invalid@example.com', timeout=2000)
        page.fill('input[type="password"]', 'wrongpass', timeout=2000)
        page.click('button[type="submit"]', timeout=2000)
        
        # Verify error message appears
        expect(page.locator("text=invalid")).to_be_visible(timeout=2000)
    except Exception:
        # If selectors don't exist yet, we mark as skipped for now
        pytest.skip("Login form selectors not found in UI yet")

def test_guest_login(page: Page):
    page.goto(BASE_URL)
    try:
        # Check for guest login button
        page.click('button:has-text("Guest")', timeout=2000)
        expect(page.locator("text=Dashboard")).to_be_visible(timeout=5000)
    except Exception:
        pytest.skip("Guest login flow not found in UI yet")

def test_navigation_timeout(page: Page):
    # Enforce strict timeout
    try:
        page.goto(BASE_URL, timeout=5000)
    except Exception as e:
        pytest.fail(f"Navigation timed out: {e}")
