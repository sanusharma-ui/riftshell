from __future__ import annotations

import atexit
from concurrent.futures import Future
import os
from queue import Queue
import re
import threading
from urllib.parse import quote_plus, urljoin, urlparse


class BrowserError(RuntimeError):
    """Raised when a browser automation action fails or is invalid."""
    pass


def site_for_url(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower()
    if host == "youtube.com" or host.endswith(".youtube.com"):
        return "YouTube"
    if host in {"google.com", "www.google.com", "google.co.in", "www.google.co.in"}:
        return "Google"
    if host in {"bing.com", "www.bing.com"}:
        return "Bing"
    if host in {"duckduckgo.com", "www.duckduckgo.com"}:
        return "DuckDuckGo"
    return None


class BrowserSession:
    """An isolated, controlled browser session managed by Playwright."""

    def __init__(self, channel: str | None = None, headless: bool = False):
        self.channel = channel or os.environ.get("BROWSER_CHANNEL", "chrome").lower()
        self.headless = headless
        self.driver = None
        self.browser = None
        self.context = None
        self.page = None
        self._last_url = None
        self._last_dom_snapshot = None
        self._dom_update_callback = None

    def _start(self) -> None:
        if self.browser and self.browser.is_connected():
            return
        self.close()

        if self.channel not in {"chrome", "msedge", "chromium"}:
            self.channel = "chrome"

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise BrowserError(
                "Playwright is not installed. Run: python -m pip install playwright && python -m playwright install"
            ) from None

        try:
            self.driver = sync_playwright().start()
            options = {
                "headless": self.headless,
                "timeout": 20000,
                "args": ["--start-maximized"],
            }
            if self.channel != "chromium":
                options["channel"] = self.channel

            profile_dir = os.environ.get("BROWSER_USER_DATA_DIR")
            if profile_dir:
                try:
                    self.context = self.driver.chromium.launch_persistent_context(
                        user_data_dir=profile_dir,
                        no_viewport=True,
                        accept_downloads=False,
                        **options,
                    )
                    self.browser = None
                    self.context.set_default_timeout(10000)
                    self.context.set_default_navigation_timeout(20000)
                    return
                except Exception:
                    pass

            try:
                self.browser = self.driver.chromium.launch(**options)
            except Exception:
                # Fallback to Edge or Chromium if Chrome is not present
                if self.channel == "chrome":
                    options["channel"] = "msedge"
                    self.channel = "msedge"
                    try:
                        self.browser = self.driver.chromium.launch(**options)
                    except Exception:
                        options.pop("channel", None)
                        self.channel = "chromium"
                        self.browser = self.driver.chromium.launch(**options)
                else:
                    raise

            self.context = self.browser.new_context(no_viewport=True, accept_downloads=False)
            self.context.set_default_timeout(10000)
            self.context.set_default_navigation_timeout(20000)
        except Exception as exc:
            self.close()
            raise BrowserError(
                f"Could not launch browser ({self.channel}). Make sure Chrome, Edge, or Chromium is installed: {exc}"
            ) from None

    def _active_page(self):
        if not self.context or (self.browser is not None and not self.browser.is_connected()):
            raise BrowserError("No controlled browser session is open. Please open a website or search first.")
        if not self.page or self.page.is_closed():
            pages = [p for p in self.context.pages if not p.is_closed()]
            if not pages:
                raise BrowserError("All tabs are closed. Please open a website first.")
            self.page = pages[-1]
        self.page.bring_to_front()
        return self.page

    @staticmethod
    def _validate_url(url: str) -> str:
        url = url.strip()
        if not re.match(r"^[a-zA-Z]+://", url):
            url = "https://" + url
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise BrowserError("Please provide a valid http or https URL.")
        return url

    def open_url(self, url: str) -> str:
        valid_url = self._validate_url(url)
        self._start()
        if not self.page or self.page.is_closed():
            self.page = self.context.new_page()
        self.page.bring_to_front()
        self.page.goto(valid_url, wait_until="domcontentloaded")
        title = self.page.title() or valid_url
        return f"Opened {title[:60]} ({valid_url})"

    def search(self, query: str, engine: str = "Google") -> str:
        query = query.strip()
        if not query:
            raise BrowserError("Please specify a search query.")

        templates = {
            "YouTube": "https://www.youtube.com/results?search_query=",
            "Google": "https://www.google.com/search?q=",
            "Bing": "https://www.bing.com/search?q=",
            "DuckDuckGo": "https://duckduckgo.com/?q=",
        }

        engine_title = engine.title() if engine else "Google"
        if engine_title not in templates:
            engine_title = "Google"

        url = templates[engine_title] + quote_plus(query)
        self.open_url(url)
        return f"Searching {engine_title} for '{query}'"

    def control(self, action: str) -> str:
        action = action.lower().strip()
        if action == "new_tab":
            self._start()
            self.page = self.context.new_page()
            self.page.bring_to_front()
            return "Opened a new browser tab."

        page = self._active_page()

        if action in {"back", "forward"}:
            before = page.url
            result = page.go_back(wait_until="domcontentloaded") if action == "back" else page.go_forward(wait_until="domcontentloaded")
            if result is None and page.url == before:
                return f"No history to move {action} in this tab."
            return f"Navigated {action} in current tab."

        if action in {"refresh", "reload"}:
            page.reload(wait_until="domcontentloaded")
            return "Page reloaded."

        if action in {"scroll_up", "scroll_down", "top", "bottom"}:
            moved = page.evaluate("""action => {
                const before = window.scrollY;
                const amount = Math.round(window.innerHeight * 0.8);
                if (action === 'top') window.scrollTo({top: 0, behavior: 'instant'});
                else if (action === 'bottom') window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'instant'});
                else window.scrollBy({top: action === 'scroll_up' ? -amount : amount, behavior: 'instant'});
                return window.scrollY !== before;
            }""", action)
            return (f"Scrolled {action.replace('scroll_', '')}." if moved
                    else "Page is already at that edge.")

        if action == "tabs":
            return "Open browser tabs:\n" + "\n".join(
                f"{idx}. {'[ACTIVE] ' if tab == page else ''}{tab.title()[:80] or 'Untitled'} ({tab.url})"
                for idx, tab in enumerate(self.context.pages, 1) if not tab.is_closed()
            )

        if action == "close_tab":
            page.close()
            remaining = [p for p in self.context.pages if not p.is_closed()]
            self.page = remaining[-1] if remaining else None
            if self.page:
                self.page.bring_to_front()
            return "Closed current tab."

        if action in {"play", "pause"}:
            videos = page.locator("video")
            try:
                videos.first.wait_for(state="attached", timeout=6000)
                eval_script = (
                    "async video => { await video.play(); return !video.paused; }"
                    if action == "play"
                    else "video => { video.pause(); return video.paused; }"
                )
                state = videos.first.evaluate(eval_script)
            except Exception:
                raise BrowserError("No active video element found or playback could not be altered.") from None
            if not state:
                raise BrowserError("Video player did not confirm the requested playback state.")
            return "Resumed video playback." if action == "play" else "Paused video playback."

        raise BrowserError(f"Unsupported browser action: {action}")

    def switch_tab(self, number: int) -> str:
        self._active_page()
        pages = [p for p in self.context.pages if not p.is_closed()]
        if not 1 <= number <= len(pages):
            raise BrowserError(f"Invalid tab index. Choose between 1 and {len(pages)}.")
        self.page = pages[number - 1]
        self.page.bring_to_front()
        return f"Switched to tab {number}: {self.page.title()[:80] or 'Untitled'}"

    def open_result(self, number: int) -> str:
        page = self._active_page()
        site = site_for_url(page.url)
        if site == "YouTube" and urlparse(page.url).path == "/results":
            links = page.locator("ytd-video-renderer a#video-title[href]")
        elif site == "Google" and urlparse(page.url).path == "/search":
            links = page.locator("a:has(h3)")
        else:
            raise BrowserError("Open a YouTube or Google search first, then specify a result number.")

        try:
            links.first.wait_for(state="visible", timeout=8000)
        except Exception:
            raise BrowserError("Search results are still loading or unavailable.") from None

        count = links.count()
        if not 1 <= number <= min(count, 20):
            raise BrowserError(f"Result {number} not available (found {count} results).")

        link = links.nth(number - 1)
        href = link.get_attribute("href")
        if not href:
            raise BrowserError("Target result does not contain a valid URL link.")
        target_url = urljoin(page.url, href)
        return self.open_url(target_url)

    def play_result(self, number: int) -> str:
        page = self._active_page()
        if site_for_url(page.url) != "YouTube" or urlparse(page.url).path != "/results":
            raise BrowserError("Numbered video playback requires YouTube search results. Search on YouTube first.")
        self.open_result(number)
        try:
            self.control("play")
        except BrowserError:
            pass  # Autoplay might handle it
        return f"Playing YouTube result #{number}."

    def click_element(self, reference: str) -> str:
        if not re.fullmatch(r"e\d{1,3}", str(reference).strip()):
            raise BrowserError(f"Invalid element reference: {reference}")
        page = self._active_page()
        locator = page.locator(f'[data-riftshell-ref="{reference.strip()}"]')
        try:
            if locator.count() != 1 or not locator.is_visible():
                raise BrowserError(f"Element {reference} is no longer visible on the page.")
            locator.click()
            try:
                page.wait_for_load_state("domcontentloaded", timeout=4000)
            except Exception:
                pass
            return f"Clicked element {reference}."
        except BrowserError:
            raise
        except Exception as exc:
            raise BrowserError(f"Could not click element {reference}: {exc}") from None

    def click_matching(self, target: str) -> str:
        target_clean = str(target or "").strip()
        if re.fullmatch(r"e\d{1,3}", target_clean):
            return self.click_element(target_clean)
        # Clean common conversational words (e.g. "subscribe button" -> "subscribe")
        clean_target = re.sub(r"\s+(?:button|link|icon|tab)$", "", target_clean, flags=re.I).strip()
        page = self._active_page()
        try:
            match = page.evaluate("""target => {
                const normalize = val => (val || '').replace(/\\s+/g, ' ').trim().toLowerCase();
                const wanted = normalize(target);
                const selector = 'a,button,input[type="button"],input[type="submit"],[role="button"],[role="link"],[role="tab"],[role="menuitem"]';
                const visible = el => {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.visibility !== 'hidden' && style.display !== 'none'
                        && rect.width > 0 && rect.height > 0
                        && !el.disabled && el.getAttribute('aria-disabled') !== 'true';
                };
                const name = el => normalize(
                    el.innerText || el.getAttribute('aria-label') || el.title || el.value || el.placeholder
                );
                const candidates = Array.from(document.querySelectorAll(selector))
                    .filter(visible)
                    .map((element, index) => ({element, index, name: name(element)}))
                    .filter(item => item.name && (item.name === wanted || item.name.includes(wanted) || wanted.includes(item.name)));

                if (candidates.length === 0) {
                    return {count: 0};
                }

                // 1. Prefer exact name match
                const exact = candidates.filter(item => item.name === wanted);
                const pool = exact.length > 0 ? exact : candidates;

                // 2. Prefer elements in the current viewport
                const inView = pool.filter(item => {
                    const rect = item.element.getBoundingClientRect();
                    return rect.top < window.innerHeight && rect.bottom > 0 && rect.left < window.innerWidth && rect.right > 0;
                });
                const chosen = inView.length > 0 ? inView[0] : pool[0];

                chosen.element.setAttribute('data-riftshell-direct-ref', `direct-${chosen.index}`);
                return {count: 1, ref: `direct-${chosen.index}`, name: chosen.name};
            }""", clean_target or target_clean)

            if match.get("count", 0) == 0:
                raise BrowserError(f"No visible button or link found matching '{target}'.")

            locator = page.locator(f'[data-riftshell-direct-ref="{match["ref"]}"]')
            locator.first.click()
            try:
                page.wait_for_load_state("domcontentloaded", timeout=4000)
            except Exception:
                pass
        except BrowserError:
            raise
        except Exception as exc:
            raise BrowserError(f"Failed to click matching element '{target}': {exc}") from None
        return f"Clicked '{match['name']}'."

    def fill_element(self, reference: str, value: str) -> str:
        if not re.fullmatch(r"e[1-9][0-9]{0,2}", str(reference)):
            raise BrowserError("Invalid element reference format (expected e.g. e1, e2).")
        page = self._active_page()
        locator = page.locator(f'[data-riftshell-ref="{reference}"]')
        try:
            if locator.count() != 1 or not locator.is_visible():
                raise BrowserError(f"Element {reference} is no longer visible on the page.")
            input_type = (locator.get_attribute("type") or "text").lower()
            tag = locator.evaluate("el => el.tagName.toLowerCase()")
            if tag not in {"input", "textarea"} or input_type in {
                "password", "hidden", "file", "checkbox", "radio", "submit", "button"
            }:
                raise BrowserError("Only visible text input fields can be filled automatically.")
            locator.fill(value)
        except BrowserError:
            raise
        except Exception as exc:
            raise BrowserError(f"Could not fill form field {reference}: {exc}") from None
        return f"Filled form field {reference}."

    def _get_dom_data(self) -> dict:
        page = self._active_page()
        try:
            return page.evaluate("""() => {
                const visible = element => {
                    const style = window.getComputedStyle(element);
                    const rect = element.getBoundingClientRect();
                    return style.visibility !== 'hidden' && style.display !== 'none'
                        && rect.width > 0 && rect.height > 0;
                };
                const labelText = element => {
                    const id = element.id;
                    const label = id ? document.querySelector(`label[for="${CSS.escape(id)}"]`) : null;
                    return (label && label.innerText) || (element.closest('label') && element.closest('label').innerText) || '';
                };
                const text = element => (element.innerText || element.value || ''
                    || element.getAttribute('aria-label') || element.title || labelText(element))
                    .replace(/\\s+/g, ' ').trim().slice(0, 100);
                document.querySelectorAll('[data-riftshell-ref]').forEach(el => el.removeAttribute('data-riftshell-ref'));
                const selector = 'a,button,input,select,textarea,[role="button"],[role="link"],[role="tab"]';
                const rawElements = Array.from(document.querySelectorAll(selector)).filter(visible);
                const total = rawElements.length;
                const sorted = rawElements.map(el => {
                    const rect = el.getBoundingClientRect();
                    const in_view = rect.top < innerHeight && rect.bottom > 0 && rect.left < innerWidth && rect.right > 0;
                    return { el, rect, in_view };
                }).sort((a, b) => (b.in_view ? 1 : 0) - (a.in_view ? 1 : 0)).slice(0, 150);

                return {
                    title: document.title.slice(0, 150),
                    url: location.href,
                    body: (document.body ? document.body.innerText : '')
                        .replace(/\\s+/g, ' ').trim().slice(0, 800),
                    total: total,
                    elements: sorted.map((item, index) => {
                        const ref = `e${index + 1}`;
                        item.el.setAttribute('data-riftshell-ref', ref);
                        const rect = item.rect;
                        return {
                            ref,
                            tag: item.el.tagName.toLowerCase(),
                            role: item.el.getAttribute('role') || '',
                            type: item.el.getAttribute('type') || '',
                            name: item.el.getAttribute('name') || '',
                            href: item.el.getAttribute('href') || '',
                            text: text(item.el),
                            x: Math.round(rect.x + rect.width / 2),
                            y: Math.round(rect.y + rect.height / 2),
                            w: Math.round(rect.width),
                            h: Math.round(rect.height),
                            in_view: item.in_view,
                            disabled: Boolean(item.el.disabled || item.el.getAttribute('aria-disabled') === 'true'),
                            clickable: item.el.tagName === 'BUTTON' || item.el.tagName === 'A' || item.el.hasAttribute('onclick') || item.el.getAttribute('role') === 'button'
                        };
                    })
                };
            }""")
        except Exception as exc:
            raise BrowserError(f"Could not read page DOM: {exc}") from None

    def page_context(self) -> str:
        snapshot = self._get_dom_data()

        lines = [f"TITLE: {snapshot['title']}", f"URL: {snapshot['url']}"]
        if snapshot["body"]:
            lines.append(f"PAGE TEXT: {snapshot['body']}")
        lines.append("CONTROLS:")

        control_lines = []
        for el in snapshot["elements"]:
            text_part = f' "{el["text"]}"' if el["text"] else ""
            pos_part = f" (x={el['x']},y={el['y']})"
            view_part = "" if el["in_view"] else " [scroll]"
            control_lines.append(f"[{el['ref']}] {el['tag']}{text_part}{pos_part}{view_part}")

        budget = 2500
        output_lines = list(lines)
        omitted = 0
        for i, cline in enumerate(control_lines):
            test_output = "\n".join(output_lines + [cline])
            if len(test_output) > budget:
                omitted = len(control_lines) - i + max(0, snapshot.get("total", len(snapshot["elements"])) - len(snapshot["elements"]))
                break
            output_lines.append(cline)

        if omitted > 0:
            output_lines.append(f"(+{omitted} more, scroll)")
        result = "\n".join(output_lines)

        # Store for change detection
        current_url = snapshot['url']
        old_url = self._last_url
        if old_url != current_url:
            self._last_url = current_url
            self._last_dom_snapshot = result
            if self._dom_update_callback:
                try:
                    self._dom_update_callback(result, url_changed=True, old_url=old_url)
                except Exception:
                    pass
        elif self._last_dom_snapshot != result:
            self._last_dom_snapshot = result
            if self._dom_update_callback:
                try:
                    self._dom_update_callback(result, url_changed=False, old_url=current_url)
                except Exception:
                    pass

        return result

    def set_dom_update_callback(self, callback):
        """Set a callback that will be called when DOM changes."""
        self._dom_update_callback = callback

    def get_current_dom(self) -> dict:
        """Get current DOM as structured data (shares exact tagging and ordering with page_context)."""
        return self._get_dom_data()

    def scroll_by_pixels(self, pixels: int) -> str:
        """Scroll by specific pixel amount."""
        page = self._active_page()
        try:
            moved = page.evaluate("""pixels => {
                const before = window.scrollY;
                window.scrollBy({top: pixels, behavior: 'smooth'});
                return window.scrollY !== before;
            }""", int(pixels))
            direction = "down" if pixels > 0 else "up"
            return f"Scrolled {direction} by {abs(pixels)} pixels." if moved else "Already at edge."
        except Exception as exc:
            raise BrowserError(f"Could not scroll: {exc}") from None

    def press_key(self, key: str) -> str:
        page = self._active_page()
        try:
            page.keyboard.press(key)
            return f"Pressed browser key {key}."
        except Exception as exc:
            raise BrowserError(f"Could not press {key}: {exc}") from None

    def scroll_to_element(self, reference: str) -> str:
        """Scroll to a specific element by reference."""
        if not re.fullmatch(r"e\d{1,3}", str(reference)):
            raise BrowserError(f"Invalid element reference: {reference} (expected e.g. e1, e12)")
        page = self._active_page()
        try:
            page.evaluate("""ref => {
                const el = document.querySelector('[data-riftshell-ref="' + ref + '"]');
                if (el) el.scrollIntoView({behavior: 'smooth', block: 'center'});
            }""", str(reference))
            return f"Scrolled to element {reference}."
        except Exception as exc:
            raise BrowserError(f"Could not scroll to {reference}: {exc}") from None

    def click_at_coordinates(self, x: int, y: int) -> str:
        """Click at specific screen coordinates."""
        page = self._active_page()
        try:
            page.mouse.click(x, y)
            return f"Clicked at coordinates ({x}, {y})."
        except Exception as exc:
            raise BrowserError(f"Could not click at ({x}, {y}): {exc}") from None

    def get_element_info(self, reference: str) -> dict:
        """Get detailed information about a specific element."""
        if not re.fullmatch(r"e\d{1,3}", str(reference)):
            raise BrowserError(f"Invalid element reference: {reference} (expected e.g. e1, e12)")
        page = self._active_page()
        try:
            return page.evaluate("""reference => {
                const el = document.querySelector('[data-riftshell-ref="' + reference + '"]');
                if (!el) return null;
                const rect = el.getBoundingClientRect();
                return {
                    ref: reference,
                    tag: el.tagName.toLowerCase(),
                    text: el.innerText || el.value || '',
                    attributes: Object.fromEntries(
                        Array.from(el.attributes).map(attr => [attr.name, attr.value])
                    ),
                    position: { x: Math.round(rect.x + rect.width / 2), y: Math.round(rect.y + rect.height / 2), width: Math.round(rect.width), height: Math.round(rect.height) },
                    visible: rect.width > 0 && rect.height > 0,
                    styles: window.getComputedStyle(el).cssText
                };
            }""", str(reference))
        except Exception as exc:
            raise BrowserError(f"Could not get element info for {reference}: {exc}") from None

    def youtube_control(self, action: str) -> str:
        """Special YouTube controls."""
        page = self._active_page()
        
        if "youtube.com" not in page.url.lower():
            raise BrowserError("Not on YouTube. Navigate to YouTube first.")
        
        try:
            if action == "play":
                page.keyboard.press("k")
                return "Sent play/pause command to YouTube."
            elif action == "pause":
                page.keyboard.press("k")
                return "Sent play/pause command to YouTube."
            elif action == "fullscreen":
                page.keyboard.press("f")
                return "Toggled fullscreen on YouTube."
            elif action == "mute":
                page.keyboard.press("m")
                return "Toggled mute on YouTube."
            elif action == "forward":
                page.keyboard.press("ArrowRight")
                return "Skipped forward 5 seconds."
            elif action == "back":
                page.keyboard.press("ArrowLeft")
                return "Skipped back 5 seconds."
            elif action == "next":
                page.keyboard.press("Shift+n")
                return "Skipped to next video."
            elif action == "prev":
                page.keyboard.press("Shift+p")
                return "Went to previous video."
            elif action == "speed_up":
                page.keyboard.press("Shift+>")
                return "Increased playback speed."
            elif action == "speed_down":
                page.keyboard.press("Shift+<")
                return "Decreased playback speed."
            elif action in {"subscribe", "like"}:
                # Find and click subscribe/like button
                selector = "ytd-subscribe-button-renderer button" if action == "subscribe" else "like-button-view-model button"
                page.locator(selector).first.click()
                return f"Clicked {action} button."
            else:
                raise BrowserError(f"Unknown YouTube action: {action}")
        except Exception as exc:
            raise BrowserError(f"YouTube control failed: {exc}") from None

    def control_youtube(self, action: str) -> str:
        return self.youtube_control(action)

    def close(self) -> None:
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass
        finally:
            if self.driver:
                try:
                    self.driver.stop()
                except Exception:
                    pass
            self.driver = self.browser = self.context = self.page = None


class BrowserController:
    """Thread-safe background controller for browser operations."""

    def __init__(self, channel: str | None = None):
        self.channel = channel
        self._queue: Queue = Queue()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._closed = False

    def _worker(self) -> None:
        session = BrowserSession(channel=self.channel)
        try:
            while True:
                task = self._queue.get()
                if task is None:
                    break
                op, args, kwargs, future = task
                if future.set_running_or_notify_cancel():
                    try:
                        handler = getattr(session, op, None)
                        if handler is None:
                            raise BrowserError(f"Unknown browser operation: {op}")
                        result = handler(*args, **kwargs)
                        future.set_result(result)
                    except Exception as exc:
                        future.set_exception(exc)
        finally:
            session.close()

    def _call(self, op: str, *args, **kwargs):
        future: Future = Future()
        with self._lock:
            if self._closed:
                raise BrowserError("Browser controller is closed.")
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._worker, name="riftshell-browser", daemon=True)
                self._thread.start()
            self._queue.put((op, args, kwargs, future))
        return future.result()

    def open_url(self, url: str) -> str:
        return self._call("open_url", url)

    def search(self, query: str, engine: str = "Google") -> str:
        return self._call("search", query, engine=engine)

    def control(self, action: str) -> str:
        return self._call("control", action)

    def switch_tab(self, number: int) -> str:
        return self._call("switch_tab", number)

    def open_result(self, number: int) -> str:
        return self._call("open_result", number)

    def play_result(self, number: int) -> str:
        return self._call("play_result", number)

    def click_matching(self, target: str) -> str:
        return self._call("click_matching", target)

    def click_element(self, reference: str) -> str:
        return self._call("click_element", reference)

    def fill_element(self, reference: str, value: str) -> str:
        return self._call("fill_element", reference, value)

    def page_context(self) -> str:
        return self._call("page_context")

    def get_current_dom(self) -> dict:
        return self._call("get_current_dom")

    def scroll_by_pixels(self, pixels: int) -> str:
        return self._call("scroll_by_pixels", pixels)

    def press_key(self, key: str) -> str:
        return self._call("press_key", key)

    def scroll_to_element(self, reference: str) -> str:
        return self._call("scroll_to_element", reference)

    def click_at_coordinates(self, x: int, y: int) -> str:
        return self._call("click_at_coordinates", x, y)

    def get_element_info(self, reference: str) -> dict:
        return self._call("get_element_info", reference)

    def youtube_control(self, action: str) -> str:
        return self._call("youtube_control", action)

    def control_youtube(self, action: str) -> str:
        return self.youtube_control(action)

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._closed = True
                if self._thread and self._thread.is_alive():
                    self._queue.put(None)
            thread = self._thread
        if thread and thread.is_alive() and thread != threading.current_thread():
            thread.join(timeout=3.0)


_GLOBAL_CONTROLLER: BrowserController | None = None
_GLOBAL_LOCK = threading.Lock()


def get_browser_controller() -> BrowserController:
    global _GLOBAL_CONTROLLER
    with _GLOBAL_LOCK:
        if _GLOBAL_CONTROLLER is None or _GLOBAL_CONTROLLER._closed:
            _GLOBAL_CONTROLLER = BrowserController()
            atexit.register(cleanup_browser_controller)
        return _GLOBAL_CONTROLLER


def cleanup_browser_controller() -> None:
    global _GLOBAL_CONTROLLER
    with _GLOBAL_LOCK:
        if _GLOBAL_CONTROLLER is not None:
            try:
                _GLOBAL_CONTROLLER.close()
            except Exception:
                pass
            _GLOBAL_CONTROLLER = None
