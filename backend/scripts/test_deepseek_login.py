"""
Test DeepSeek login flow step-by-step (headed browser for visual verification).

Usage:
    python scripts/test_deepseek_login.py
    python scripts/test_deepseek_login.py --phone 13800138000

Tests each step of the login flow and takes screenshots.
Does NOT actually send SMS (stops before clicking send code by default).
Add --send-code to actually trigger SMS.
"""
import asyncio
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_login(phone: str, send_code: bool):
    from app.services.llm.deepseek_provider import DeepSeekProvider

    # Use a temp dir for this test
    import tempfile
    user_data_dir = tempfile.mkdtemp(prefix="deepseek_test_")
    print(f"User data dir: {user_data_dir}")

    provider = DeepSeekProvider(user_data_dir=user_data_dir, headless=False)

    try:
        # Step 1: Start browser
        print("\n[Step 1] Starting browser...")
        await provider._start()
        print(f"  OK — page url: {provider._page.url}")

        # Step 2: Check login status (should be False)
        print("\n[Step 2] Checking login status...")
        is_logged_in = await provider.check_login_status()
        print(f"  Login status: {is_logged_in}")
        await provider._page.screenshot(path="test_ds_step2_login_check.png")

        if is_logged_in:
            print("  Already logged in! Test complete.")
            return True

        # Step 3: Navigate to login
        print("\n[Step 3] Navigating to login page...")
        await provider.navigate_to_login()
        current_url = provider._page.url
        print(f"  URL: {current_url}")
        await provider._page.screenshot(path="test_ds_step3_login_page.png")

        if "/sign_in" not in current_url:
            print(f"  WARNING: Expected /sign_in in URL, got: {current_url}")

        # Step 4: Fill phone number
        print(f"\n[Step 4] Filling phone number: {phone[:3]}****{phone[-4:]}...")
        await provider.fill_phone_number(phone)
        await asyncio.sleep(1)
        await provider._page.screenshot(path="test_ds_step4_phone_filled.png")
        print("  OK — phone filled")

        # Verify the phone was actually typed
        phone_value = await provider._page.evaluate("""
            () => {
                const input = document.querySelector('input[type="tel"]');
                return input ? input.value : 'NOT FOUND';
            }
        """)
        print(f"  Phone input value: '{phone_value}'")

        if not send_code:
            print("\n[Step 5] SKIPPED — Add --send-code flag to actually send SMS")
            print("  Screenshots saved: test_ds_step*.png")
            await asyncio.sleep(5)
            return True

        # Step 5: Click send code
        print("\n[Step 5] Clicking '发送验证码'...")
        await provider.click_send_code()
        await asyncio.sleep(2)
        await provider._page.screenshot(path="test_ds_step5_code_sent.png")
        print("  OK — code sent (check your phone)")

        # Step 6: Wait for manual code input
        print("\n[Step 6] Enter the verification code you received:")
        code = input("  Code: ").strip()
        if not code:
            print("  No code entered, aborting.")
            return False

        # Step 7: Fill code and submit
        print(f"\n[Step 7] Filling verification code: {code}...")
        await provider.fill_verification_code(code)
        await provider._page.screenshot(path="test_ds_step7_code_submitted.png")

        # Step 8: Verify login
        print("\n[Step 8] Verifying login success...")
        success = await provider.verify_login_success()
        await provider._page.screenshot(path="test_ds_step8_result.png")
        print(f"  Login success: {success}")
        print(f"  Final URL: {provider._page.url}")

        return success

    except Exception as e:
        print(f"\nERROR: {e}")
        try:
            await provider._page.screenshot(path="test_ds_error.png")
            print("  Error screenshot saved: test_ds_error.png")
        except Exception:
            pass
        raise
    finally:
        await provider._close()
        print("\nBrowser closed.")


def main():
    parser = argparse.ArgumentParser(description="Test DeepSeek login flow")
    parser.add_argument("--phone", default="13800138000", help="Phone number to test with")
    parser.add_argument("--send-code", action="store_true", help="Actually send SMS code")
    args = parser.parse_args()

    result = asyncio.run(test_login(args.phone, args.send_code))
    print(f"\n{'SUCCESS' if result else 'FAILED'}")
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
