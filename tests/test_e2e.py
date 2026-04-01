"""End-to-end tests for the Runeform generation pipeline via the web UI."""

import re
from pathlib import Path

from playwright.sync_api import Page, expect

BRAND_DATA_DIR = Path(__file__).parent.parent / "brand_data"
TEST_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40">
  <rect width="100" height="40" fill="#333"/>
  <text x="50" y="25" text-anchor="middle" fill="white" font-size="14">TEST</text>
</svg>
"""


# ── Brand Kit ──────────────────────────────────────────────────────────────


def test_brand_kit_page_loads(page: Page, server_url: str):
    page.goto(f"{server_url}/brand")
    expect(page.locator("h1")).to_have_text("Runeform")
    expect(page.get_by_label("Brand Name")).to_be_visible()
    expect(page.get_by_label("Address")).to_be_visible()
    expect(page.get_by_text("Brand Colors")).to_be_visible()


def test_save_brand_kit(page: Page, server_url: str):
    page.goto(f"{server_url}/brand")

    page.get_by_label("Brand Name").fill("Test Venue")
    page.get_by_label("Address").fill("123 Test St")
    page.get_by_label("Brand Description").fill("A cozy test venue")

    page.get_by_role("button", name="Save Brand Kit").click()
    expect(page.get_by_text("Brand kit saved")).to_be_visible()


def test_save_brand_kit_with_svg_logo(page: Page, server_url: str, tmp_path: Path):
    logo_path = tmp_path / "logo.svg"
    logo_path.write_text(TEST_SVG)

    page.goto(f"{server_url}/brand")
    page.get_by_label("Brand Name").fill("SVG Brand")
    page.get_by_label("Logo").set_input_files(str(logo_path))
    page.get_by_role("button", name="Save Brand Kit").click()

    expect(page.get_by_text("Brand kit saved")).to_be_visible()
    expect(page.get_by_text("Current logo:")).to_be_visible()


def test_brand_kit_export_download(page: Page, server_url: str):
    # Ensure a brand exists first
    page.goto(f"{server_url}/brand")
    page.get_by_label("Brand Name").fill("Export Test")
    page.get_by_role("button", name="Save Brand Kit").click()
    expect(page.get_by_text("Brand kit saved")).to_be_visible()

    with page.expect_download() as download_info:
        page.get_by_role("link", name="Download Brand Kit").click()
    download = download_info.value
    assert download.suggested_filename.endswith("_brand.zip")


def test_brand_kit_import_zip(page: Page, server_url: str):
    # First export
    page.goto(f"{server_url}/brand")
    page.get_by_label("Brand Name").fill("Import Source")
    page.get_by_role("button", name="Save Brand Kit").click()
    expect(page.get_by_text("Brand kit saved")).to_be_visible()

    with page.expect_download() as download_info:
        page.get_by_role("link", name="Download Brand Kit").click()
    zip_path = download_info.value.path()

    # Now import
    page.goto(f"{server_url}/brand")
    page.locator('input[name="brand_zip"]').set_input_files(str(zip_path))
    page.get_by_role("button", name="Import from Zip").click()
    expect(page.get_by_text("Imported brand kit")).to_be_visible()


# ── Generate ───────────────────────────────────────────────────────────────


def test_generate_page_loads(page: Page, server_url: str):
    page.goto(server_url)
    expect(page.locator("h1")).to_have_text("Runeform")
    expect(page.get_by_label("Event Title")).to_be_visible()
    expect(page.get_by_role("button", name="Generate Graphics")).to_be_visible()


def test_generate_text_event(page: Page, server_url: str):
    """Text-only event: title + date + time + location + description, no image."""
    page.goto(server_url)

    page.get_by_label("Event Title").fill("Spring Woodworking Workshop")
    page.get_by_label("Date").fill("Saturday April 12")
    page.get_by_label("Time").fill("10:00 AM")
    page.get_by_label("Location").fill("Main Floor")
    page.get_by_label("Description").fill("Learn dovetail joints. All levels welcome.")

    page.get_by_role("button", name="Generate Graphics").click()
    page.wait_for_selector("h1:has-text('Generated Layouts')", timeout=30_000)

    # Diagnostics visible
    expect(page.get_by_text("Single Event Text")).to_be_visible()
    expect(page.get_by_text("PIPELINE DIAGNOSTICS")).to_be_visible()

    # At least one layout rendered
    cards = page.locator(".card")
    assert cards.count() >= 2

    # One card marked BEST
    expect(page.get_by_text("BEST")).to_be_visible()


def test_generate_title_only(page: Page, server_url: str):
    """Minimal input: title only should produce text_announcement layouts."""
    page.goto(server_url)

    page.get_by_label("Event Title").fill("Grand Opening")
    page.get_by_role("button", name="Generate Graphics").click()
    page.wait_for_selector("h1:has-text('Generated Layouts')", timeout=30_000)

    expect(page.get_by_text("Text Announcement")).to_be_visible()
    cards = page.locator(".card")
    assert cards.count() >= 2


def test_generate_with_brand_colors(page: Page, server_url: str):
    """Brand colors should influence the rendered output."""
    # Set up a brand first
    page.goto(f"{server_url}/brand")
    page.get_by_label("Brand Name").fill("Color Test Brand")
    page.get_by_role("button", name="Save Brand Kit").click()
    expect(page.get_by_text("Brand kit saved")).to_be_visible()

    # Generate
    page.goto(server_url)
    expect(page.get_by_text("Color Test Brand")).to_be_visible()

    page.get_by_label("Event Title").fill("Color Check Event")
    page.get_by_role("button", name="Generate Graphics").click()
    page.wait_for_selector("h1:has-text('Generated Layouts')", timeout=30_000)

    cards = page.locator(".card")
    assert cards.count() >= 2


def test_generate_shows_z3_typography_variation(page: Page, server_url: str):
    """Z3 should produce multiple distinct typography solutions per template."""
    page.goto(server_url)

    page.get_by_label("Event Title").fill("Workshop")
    page.get_by_label("Date").fill("April 1")
    page.get_by_label("Time").fill("5 PM")
    page.get_by_role("button", name="Generate Graphics").click()
    page.wait_for_selector("h1:has-text('Generated Layouts')", timeout=30_000)

    # Collect all headline sizes from the typography info
    typo_texts = page.locator(".typo").all_text_contents()
    headline_sizes = set()
    for text in typo_texts:
        match = re.search(r"headline:\s*(\d+)px", text)
        if match:
            headline_sizes.add(int(match.group(1)))

    # Z3 should produce at least 2 distinct headline sizes
    assert len(headline_sizes) >= 2, f"Expected varied headlines, got: {headline_sizes}"


def test_generate_empty_title_rejected(page: Page, server_url: str):
    """Submitting without a title should not produce results."""
    page.goto(server_url)
    # Don't fill title — it's required, browser will block submission
    page.get_by_role("button", name="Generate Graphics").click()

    # Should still be on the form page (HTML5 validation prevents submission)
    expect(page.get_by_label("Event Title")).to_be_visible()


# ── Navigation ─────────────────────────────────────────────────────────────


def test_nav_between_pages(page: Page, server_url: str):
    page.goto(server_url)
    page.get_by_role("link", name="Brand Kit").click()
    expect(page.get_by_label("Brand Name")).to_be_visible()

    page.get_by_role("link", name="Generate").click()
    expect(page.get_by_label("Event Title")).to_be_visible()


def test_results_back_link(page: Page, server_url: str):
    page.goto(server_url)
    page.get_by_label("Event Title").fill("Back Link Test")
    page.get_by_role("button", name="Generate Graphics").click()
    page.wait_for_selector("h1:has-text('Generated Layouts')", timeout=30_000)

    page.get_by_role("link", name="New generation").click()
    expect(page.get_by_label("Event Title")).to_be_visible()
