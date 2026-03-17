"""
Celery tasks for browser worker — health checks and browser authentication.
"""
import logging

logger = logging.getLogger(__name__)


def _register_browser_tasks():
    """Register browser-specific Celery tasks."""
    from app.celery_app import celery_app

    @celery_app.task(bind=True, name="app.tasks.check_session_health", queue="browser")
    def check_session_health(self, session_id: str):
        """Check if a browser session is still authenticated."""
        import asyncio
        import time
        from app.services.session_manager import get_session_manager

        mgr = get_session_manager()
        session = mgr.get_session(session_id)
        if not session:
            return {"status": "error", "message": "Session not found"}

        provider_name = session["provider_name"]
        user_data_dir = session["user_data_dir"]

        async def _check():
            if provider_name == "doubao":
                from app.services.llm.doubao_provider import DoubaoProvider
                provider = DoubaoProvider(user_data_dir=user_data_dir, headless=True)
            elif provider_name == "deepseek":
                from app.services.llm.deepseek_provider import DeepSeekProvider
                provider = DeepSeekProvider(user_data_dir=user_data_dir, headless=True)
            else:
                return False

            try:
                await provider._start()
                is_healthy = await provider.check_login_status()
                return is_healthy
            finally:
                await provider._close()

        # Try up to 2 times with a pause between attempts
        is_healthy = False
        for attempt in range(2):
            loop = asyncio.new_event_loop()
            try:
                is_healthy = loop.run_until_complete(_check())
            except Exception as e:
                logger.warning(f"[Session {session_id}] Health check attempt {attempt+1} error: {e}")
            finally:
                loop.close()

            if is_healthy:
                break
            if attempt == 0:
                logger.info(f"[Session {session_id}] Health check failed, retrying in 3s...")
                time.sleep(3)

        message = "登录状态有效，会话可正常使用" if is_healthy else "登录已过期或失效，请重新认证"
        mgr.update_health_check(session_id, is_healthy, message)
        logger.info(f"[Session {session_id}] Health check: {'healthy' if is_healthy else 'expired'}")
        return {"session_id": session_id, "is_healthy": is_healthy, "message": message}

    @celery_app.task(bind=True, name="app.tasks.start_browser_auth", queue="browser")
    def start_browser_auth(self, session_id: str, phone_number: str):
        """Drive the browser login flow for a session."""
        import asyncio
        from app.services.session_manager import get_session_manager
        from app.services.auth_flow import (
            set_auth_state, set_auth_error, set_auth_screenshot,
            poll_verification_code,
        )

        mgr = get_session_manager()
        session = mgr.get_session(session_id)
        if not session:
            set_auth_error(session_id, "会话不存在")
            return {"status": "error", "message": "Session not found"}

        provider_name = session["provider_name"]
        user_data_dir = session["user_data_dir"]

        mgr.update_status(session_id, "authenticating")

        async def _auth_flow():
            if provider_name == "doubao":
                from app.services.llm.doubao_provider import DoubaoProvider
                provider = DoubaoProvider(user_data_dir=user_data_dir, headless=True)
            elif provider_name == "deepseek":
                from app.services.llm.deepseek_provider import DeepSeekProvider
                provider = DeepSeekProvider(user_data_dir=user_data_dir, headless=True)
            else:
                set_auth_error(session_id, f"不支持的平台: {provider_name}")
                return False

            try:
                set_auth_state(session_id, "starting", "正在启动浏览器...")
                await provider._start()

                # ── Check if already logged in before attempting login ──
                set_auth_state(session_id, "navigating", "正在检查登录状态...")
                already_logged_in = False
                try:
                    already_logged_in = await provider.check_login_status()
                except Exception as e:
                    logger.warning(f"[Auth {session_id}] Login status check failed: {e}")

                if already_logged_in:
                    logger.info(f"[Auth {session_id}] Already logged in, skipping auth flow")
                    try:
                        screenshot = await provider._page.screenshot(type="jpeg", quality=50)
                        import base64
                        set_auth_screenshot(session_id, base64.b64encode(screenshot).decode())
                    except Exception:
                        pass
                    set_auth_state(session_id, "success", "会话已是登录状态，无需重新认证。")
                    mgr.update_status(session_id, "active")
                    mgr.update_health_check(session_id, True, "认证检查：会话已处于登录状态")
                    return True

                set_auth_state(session_id, "navigating", "正在打开登录页面...")
                await provider.navigate_to_login()

                try:
                    screenshot = await provider._page.screenshot(type="jpeg", quality=50)
                    import base64
                    set_auth_screenshot(session_id, base64.b64encode(screenshot).decode())
                except Exception:
                    pass

                set_auth_state(session_id, "sending_code", f"正在输入手机号 {phone_number[:3]}****...")
                await provider.fill_phone_number(phone_number)
                await provider.click_send_code()

                # Check for CAPTCHA with polling wait (DeepSeek only)
                # CAPTCHA popup may take several seconds to render after clicking send code
                if provider_name == "deepseek":
                    set_auth_state(session_id, "solving_captcha", "正在检测图形验证码...")
                    captcha_el = await provider.wait_for_captcha(timeout=8.0)
                    if captcha_el:
                        set_auth_state(session_id, "solving_captcha", "正在自动识别图形验证码...")
                        try:
                            screenshot = await provider._page.screenshot(type="jpeg", quality=50)
                            import base64
                            set_auth_screenshot(session_id, base64.b64encode(screenshot).decode())
                        except Exception:
                            pass

                        solved = await provider.detect_and_solve_captcha(session_id=session_id)
                        if not solved:
                            set_auth_error(session_id, "验证码识别失败（自动+人工均未成功），请重试")
                            mgr.update_status(session_id, "error")
                            return False
                    else:
                        # No CAPTCHA appeared — check if countdown started (code sent successfully)
                        if await provider.is_countdown_active():
                            logger.info(f"[Auth {session_id}] No CAPTCHA, countdown active — code sent")
                        else:
                            logger.info(f"[Auth {session_id}] No CAPTCHA detected, proceeding")

                try:
                    screenshot = await provider._page.screenshot(type="jpeg", quality=50)
                    import base64
                    set_auth_screenshot(session_id, base64.b64encode(screenshot).decode())
                except Exception:
                    pass

                set_auth_state(session_id, "waiting_for_code", "验证码已发送，请在页面中输入收到的短信验证码")

                code = poll_verification_code(session_id, timeout=180)
                if not code:
                    set_auth_error(session_id, "等待验证码超时（3分钟），请重试")
                    mgr.update_status(session_id, "error")
                    return False

                set_auth_state(session_id, "submitting_code", "正在提交验证码...")
                await provider.fill_verification_code(code)

                try:
                    screenshot = await provider._page.screenshot(type="jpeg", quality=50)
                    import base64
                    set_auth_screenshot(session_id, base64.b64encode(screenshot).decode())
                except Exception:
                    pass

                set_auth_state(session_id, "verifying", "正在验证登录状态...")
                success = await provider.verify_login_success()

                if success:
                    set_auth_state(session_id, "success", "登录成功！会话已激活。")
                    mgr.update_status(session_id, "active")
                    mgr.update_health_check(session_id, True, "通过系统内认证登录成功")
                    return True
                else:
                    set_auth_error(session_id, "验证码可能错误或已过期，登录失败。请重试。")
                    mgr.update_status(session_id, "error")
                    return False

            except Exception as e:
                logger.exception(f"[Auth {session_id}] Auth flow error: {e}")
                set_auth_error(session_id, f"认证流程出错: {str(e)}")
                mgr.update_status(session_id, "error")
                return False
            finally:
                await provider._close()

        loop = asyncio.new_event_loop()
        try:
            success = loop.run_until_complete(_auth_flow())
        except Exception as e:
            logger.exception(f"[Auth {session_id}] Unexpected error: {e}")
            set_auth_error(session_id, f"系统错误: {str(e)}")
            mgr.update_status(session_id, "error")
            success = False
        finally:
            loop.close()

        return {"session_id": session_id, "success": success}

    return check_session_health, start_browser_auth


try:
    check_session_health, start_browser_auth = _register_browser_tasks()
except ImportError:
    check_session_health = None
    start_browser_auth = None
