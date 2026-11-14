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
        if not self.browser or not self.browser.is_connected() or not self.context:
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

    def click_matching(self, target: str) -> str:
        page = self._active_page()
        try:
            match = page.evaluate("""target => {
                const normalize = val => (val || '').replace(/\\s+/g, ' ').trim().toLowerCase();
                const wanted = normalize(target);
                const selector = 'a,button,[role="button"],[role="link"],[role="tab"],[role="menuitem"]';
                const visible = el => {
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style.visibility !== 'hidden' && style.display !== 'none'
                        && rect.width > 0 && rect.height > 0
                        && !el.disabled && el.getAttribute('aria-disabled') !== 'true';
                };
                const name = el => normalize(
                    el.innerText || el.getAttribute('aria-label') || el.title || el.value
                );
                const candidates = Array.from(document.querySelectorAll(selector))
                    .filter(visible)
                    .map((element, index) => ({element, index, name: name(element)}))
                    .filter(item => item.name === wanted || item.name.includes(wanted));
                if (candidates.length !== 1) {
                    return {count: candidates.length, names: candidates.slice(0, 5).map(item => item.name)};
                }
                const item = candidates[0];
                item.element.setAttribute('data-riftshell-ref', `direct-${item.index}`);
                return {count: 1, ref: `direct-${item.index}`, name: item.name};
            }""", target)

            if match["count"] == 0:
                raise BrowserError(f"No visible button or link found matching '{target}'.")
            if match["count"] > 1:
                names = ", ".join(repr(n) for n in match["names"] if n)
                raise BrowserError(f"Multiple elements match '{target}': {names}. Please be more specific.")

            locator = page.locator(f'[data-riftshell-ref="{match["ref"]}"]')
            locator.click()
            page.wait_for_load_state("domcontentloaded", timeout=8000)
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

    def page_context(self) -> str:
        page = self._active_page()
        try:
            snapshot = page.evaluate("""() => {
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
                const selector = 'a,button,input,select,textarea,[role="button"],[role="link"],[role="tab"]';
                const elements = Array.from(document.querySelectorAll(selector))
                    .filter(visible).slice(0, 150);
                return {
                    title: document.title.slice(0, 150),
                    url: location.href,
                    body: (document.body ? document.body.innerText : '')
                        .replace(/\\s+/g, ' ').trim().slice(0, 600),
                    elements: elements.map((element, index) => {
                        const ref = `e${index + 1}`;
                        element.setAttribute('data-riftshell-ref', ref);
                        return {
                            ref,
                            tag: element.tagName.toLowerCase(),
                            role: element.getAttribute('role') || '',
                            type: element.getAttribute('type') || '',
                            name: element.getAttribute('name') || '',
                            text: text(element),
                            disabled: Boolean(element.disabled || element.getAttribute('aria-disabled') === 'true')
                        };
                    })
                };
            }""")
        except Exception as exc:
            raise BrowserError(f"Could not read page context: {exc}") from None

        lines = [f"TITLE: {snapshot['title']}", f"URL: {snapshot['url']}"]
        if snapshot["body"]:
            lines.append(f"PAGE TEXT: {snapshot['body']}")
        lines.append("CONTROLS:")
        for el in snapshot["elements"]:
            details = [el["tag"]]
            if el["role"]:
                details.append(f"role={el['role']}")
            if el["type"]:
                details.append(f"type={el['type']}")
            if el["name"]:
                details.append(f"name={el['name']}")
            if el["text"]:
                details.append(f"text={el['text']!r}")
            if el["disabled"]:
                details.append("disabled")
            lines.append(f"[{el['ref']}] " + ", ".join(details))
        return "\n".join(lines)[:2500]

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

    def fill_element(self, reference: str, value: str) -> str:
        return self._call("fill_element", reference, value)

    def page_context(self) -> str:
        return self._call("page_context")

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
