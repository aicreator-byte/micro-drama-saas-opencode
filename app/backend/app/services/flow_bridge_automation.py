"""
Flow Bridge Browser Automation Service
Uses Playwright for browser automation of Google accounts and AI image generation services.
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class AutomationTaskType(str, Enum):
    LOGIN_GOOGLE = "login_google"
    GENERATE_IMAGES = "generate_images"
    UPLOAD_ASSETS = "upload_assets"
    DOWNLOAD_ASSETS = "download_assets"
    CHECK_ACCOUNT_STATUS = "check_account_status"
    REFRESH_SESSION = "refresh_session"


class AutomationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class AutomationStep:
    step_id: str
    action: str  # click, type, wait, navigate, screenshot, evaluate
    selector: Optional[str] = None
    value: Optional[str] = None
    url: Optional[str] = None
    wait_time: Optional[int] = None
    description: str = ""
    result: Optional[Any] = None
    error: Optional[str] = None
    completed: bool = False


@dataclass
class AutomationTask:
    task_id: str
    task_type: AutomationTaskType
    google_account_id: str
    project_id: str
    flow_task_id: Optional[str] = None
    status: AutomationStatus = AutomationStatus.PENDING
    steps: List[AutomationStep] = field(default_factory=list)
    current_step: int = 0
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class BrowserAutomationService:
    """
    Service for managing browser automation tasks using Playwright.
    Handles Google account login, session management, and AI service interactions.
    """
    
    def __init__(self, mock_mode: bool = True):
        self.tasks: Dict[str, AutomationTask] = {}
        self.browser = None
        self.context = None
        self._running = False
        self.mock_mode = mock_mode
    
    async def initialize(self):
        """Initialize the browser."""
        if self.mock_mode:
            logger.info("Browser automation service initialized (MOCK MODE)")
            return
        
        try:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu',
                    '--window-size=1920,1080'
                ]
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            logger.info("Browser automation service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            if not self.mock_mode:
                raise
            logger.warning("Falling back to MOCK MODE")
            self.mock_mode = True
    
    async def close(self):
        """Close the browser."""
        if self.mock_mode:
            logger.info("Browser automation service closed (MOCK MODE)")
            return
        
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        logger.info("Browser automation service closed")
    
    def create_task(
        self,
        task_type: AutomationTaskType,
        google_account_id: str,
        project_id: str,
        flow_task_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> AutomationTask:
        """Create a new automation task."""
        task = AutomationTask(
            task_id=str(uuid.uuid4()),
            task_type=task_type,
            google_account_id=google_account_id,
            project_id=project_id,
            flow_task_id=flow_task_id
        )
        
        # Build steps based on task type
        if task_type == AutomationTaskType.LOGIN_GOOGLE:
            task.steps = self._build_google_login_steps(parameters)
        elif task_type == AutomationTaskType.GENERATE_IMAGES:
            task.steps = self._build_image_generation_steps(parameters)
        elif task_type == AutomationTaskType.CHECK_ACCOUNT_STATUS:
            task.steps = self._build_account_check_steps(parameters)
        elif task_type == AutomationTaskType.REFRESH_SESSION:
            task.steps = self._build_session_refresh_steps(parameters)
        
        self.tasks[task.task_id] = task
        return task
    
    def _build_google_login_steps(self, params: Optional[Dict[str, Any]]) -> List[AutomationStep]:
        """Build steps for Google login."""
        return [
            AutomationStep(
                step_id=str(uuid.uuid4()),
                action="navigate",
                url="https://accounts.google.com",
                description="Navigate to Google accounts page"
            ),
            AutomationStep(
                step_id=str(uuid.uuid4()),
                action="wait",
                selector="input[type='email']",
                wait_time=5000,
                description="Wait for email input field"
            ),
            AutomationStep(
                step_id=str(uuid.uuid4()),
                action="type",
                selector="input[type='email']",
                value=params.get("email", "") if params else "",
                description="Enter email address"
            ),
            AutomationStep(
                step_id=str(uuid.uuid4()),
                action="click",
                selector="button:has-text('Next')",
                description="Click Next button"
            ),
            AutomationStep(
                step_id=str(uuid.uuid4()),
                action="wait",
                selector="input[type='password']",
                wait_time=5000,
                description="Wait for password field"
            ),
            AutomationStep(
                step_id=str(uuid.uuid4()),
                action="type",
                selector="input[type='password']",
                value=params.get("password", "") if params else "",
                description="Enter password"
            ),
            AutomationStep(
                step_id=str(uuid.uuid4()),
                action="click",
                selector="button:has-text('Next')",
                description="Click Next button"
            ),
            AutomationStep(
                step_id=str(uuid.uuid4()),
                action="wait",
                wait_time=10000,
                description="Wait for login to complete"
            ),
            AutomationStep(
                step_id=str(uuid.uuid4()),
                action="evaluate",
                value="() => document.cookie",
                description="Extract session cookies"
            )
        ]
    
    def _build_image_generation_steps(self, params: Optional[Dict[str, Any]]) -> List[AutomationStep]:
        """Build steps for AI image generation (Midjourney, DALL-E, etc.)."""
        service = params.get("service", "midjourney") if params else "midjourney"
        
        if service == "midjourney":
            return [
                AutomationStep(
                    step_id=str(uuid.uuid4()),
                    action="navigate",
                    url="https://www.midjourney.com/app/",
                    description="Navigate to Midjourney"
                ),
                AutomationStep(
                    step_id=str(uuid.uuid4()),
                    action="wait",
                    selector="textarea, input[placeholder*='prompt']",
                    wait_time=10000,
                    description="Wait for prompt input"
                ),
                AutomationStep(
                    step_id=str(uuid.uuid4()),
                    action="type",
                    selector="textarea, input[placeholder*='prompt']",
                    value=params.get("prompt", "") if params else "",
                    description="Enter prompt"
                ),
                AutomationStep(
                    step_id=str(uuid.uuid4()),
                    action="click",
                    selector="button[type='submit'], button:has-text('Generate')",
                    description="Submit generation"
                ),
                AutomationStep(
                    step_id=str(uuid.uuid4()),
                    action="wait",
                    wait_time=120000,
                    description="Wait for generation to complete"
                ),
                AutomationStep(
                    step_id=str(uuid.uuid4()),
                    action="evaluate",
                    value="() => Array.from(document.querySelectorAll('img')).map(img => img.src)",
                    description="Extract generated image URLs"
                )
            ]
        elif service == "dalle":
            return [
                AutomationStep(
                    step_id=str(uuid.uuid4()),
                    action="navigate",
                    url="https://labs.openai.com/",
                    description="Navigate to DALL-E"
                ),
                AutomationStep(
                    step_id=str(uuid.uuid4()),
                    action="wait",
                    selector="textarea, input[placeholder*='prompt']",
                    wait_time=10000,
                    description="Wait for prompt input"
                ),
                AutomationStep(
                    step_id=str(uuid.uuid4()),
                    action="type",
                    selector="textarea, input[placeholder*='prompt']",
                    value=params.get("prompt", "") if params else "",
                    description="Enter prompt"
                ),
                AutomationStep(
                    step_id=str(uuid.uuid4()),
                    action="click",
                    selector="button[type='submit'], button:has-text('Generate')",
                    description="Submit generation"
                ),
                AutomationStep(
                    step_id=str(uuid.uuid4()),
                    action="wait",
                    wait_time=60000,
                    description="Wait for generation to complete"
                ),
                AutomationStep(
                    step_id=str(uuid.uuid4()),
                    action="evaluate",
                    value="() => Array.from(document.querySelectorAll('img')).map(img => img.src)",
                    description="Extract generated image URLs"
                )
            ]
        return []
    
    def _build_account_check_steps(self, params: Optional[Dict[str, Any]]) -> List[AutomationStep]:
        """Build steps for checking Google account status."""
        return [
            AutomationStep(
                step_id=str(uuid.uuid4()),
                action="navigate",
                url="https://myaccount.google.com/",
                description="Navigate to Google account page"
            ),
            AutomationStep(
                step_id=str(uuid.uuid4()),
                action="wait",
                wait_time=5000,
                description="Wait for page load"
            ),
            AutomationStep(
                step_id=str(uuid.uuid4()),
                action="evaluate",
                value="() => ({ loggedIn: !!document.querySelector('[data-email]'), url: window.location.href })",
                description="Check login status"
            )
        ]
    
    def _build_session_refresh_steps(self, params: Optional[Dict[str, Any]]) -> List[AutomationStep]:
        """Build steps for refreshing session."""
        return [
            AutomationStep(
                step_id=str(uuid.uuid4()),
                action="navigate",
                url="https://accounts.google.com",
                description="Navigate to Google accounts"
            ),
            AutomationStep(
                step_id=str(uuid.uuid4()),
                action="wait",
                wait_time=3000,
                description="Wait for page load"
            ),
            AutomationStep(
                step_id=str(uuid.uuid4()),
                action="evaluate",
                value="() => document.cookie",
                description="Get current cookies"
            )
        ]
    
    async def execute_task(self, task_id: str) -> AutomationTask:
        """Execute an automation task."""
        task = self.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if not self.mock_mode and (not self.browser or not self.context):
            await self.initialize()
        
        task.status = AutomationStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        
        if self.mock_mode:
            # Mock execution - simulate successful completion
            await asyncio.sleep(0.1)  # Simulate some work
            
            for i, step in enumerate(task.steps):
                task.current_step = i
                task.updated_at = datetime.utcnow()
                logger.info(f"Executing step {i+1}/{len(task.steps)} (MOCK): {step.description}")
                
                # Mock step results based on task type
                if task.task_type == AutomationTaskType.LOGIN_GOOGLE:
                    if step.action == "evaluate":
                        step.result = "mock_session_cookies=abc123; session_id=xyz789"
                elif task.task_type == AutomationTaskType.GENERATE_IMAGES:
                    if step.action == "evaluate":
                        step.result = [
                            "https://example.com/generated_image_1.png",
                            "https://example.com/generated_image_2.png"
                        ]
                elif task.task_type == AutomationTaskType.CHECK_ACCOUNT_STATUS:
                    if step.action == "evaluate":
                        step.result = {"loggedIn": True, "url": "https://myaccount.google.com/"}
                elif task.task_type == AutomationTaskType.REFRESH_SESSION:
                    if step.action == "evaluate":
                        step.result = "mock_session_cookies=refreshed_abc123; session_id=refreshed_xyz789"
                
                step.completed = True
                task.updated_at = datetime.utcnow()
            
            task.status = AutomationStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            
            # Collect results
            if task.task_type == AutomationTaskType.LOGIN_GOOGLE:
                cookie_step = next((s for s in task.steps if s.action == "evaluate"), None)
                if cookie_step and cookie_step.result:
                    task.result_data = {"cookies": cookie_step.result}
            elif task.task_type == AutomationTaskType.GENERATE_IMAGES:
                image_step = next((s for s in task.steps if s.action == "evaluate" and "image" in s.description.lower()), None)
                if image_step and image_step.result:
                    task.result_data = {"image_urls": image_step.result}
            elif task.task_type == AutomationTaskType.CHECK_ACCOUNT_STATUS:
                check_step = next((s for s in task.steps if s.action == "evaluate"), None)
                if check_step and check_step.result:
                    task.result_data = check_step.result
            elif task.task_type == AutomationTaskType.REFRESH_SESSION:
                session_step = next((s for s in task.steps if s.action == "evaluate"), None)
                if session_step and session_step.result:
                    task.result_data = {"cookies": session_step.result}
        
        else:
            page = await self.context.new_page()
            
            try:
                for i, step in enumerate(task.steps):
                    task.current_step = i
                    task.updated_at = datetime.utcnow()
                    
                    logger.info(f"Executing step {i+1}/{len(task.steps)}: {step.description}")
                    
                    result = await self._execute_step(page, step)
                    step.result = result
                    step.completed = True
                    task.updated_at = datetime.utcnow()
                
                task.status = AutomationStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                
                # Collect results
                if task.task_type == AutomationTaskType.LOGIN_GOOGLE:
                    cookie_step = next((s for s in task.steps if s.action == "evaluate"), None)
                    if cookie_step and cookie_step.result:
                        task.result_data = {"cookies": cookie_step.result}
                elif task.task_type == AutomationTaskType.GENERATE_IMAGES:
                    image_step = next((s for s in task.steps if s.action == "evaluate" and "image" in s.description.lower()), None)
                    if image_step and image_step.result:
                        task.result_data = {"image_urls": image_step.result}
                elif task.task_type == AutomationTaskType.CHECK_ACCOUNT_STATUS:
                    check_step = next((s for s in task.steps if s.action == "evaluate"), None)
                    if check_step and check_step.result:
                        task.result_data = check_step.result
            
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                task.status = AutomationStatus.FAILED
                task.error_message = str(e)
                task.completed_at = datetime.utcnow()
            finally:
                await page.close()
                task.updated_at = datetime.utcnow()
        
        return task
    
    async def _execute_step(self, page, step: AutomationStep) -> Any:
        """Execute a single automation step."""
        if step.action == "navigate":
            await page.goto(step.url, wait_until="networkidle", timeout=30000)
            return {"url": page.url}
        
        elif step.action == "click":
            await page.click(step.selector, timeout=10000)
            return {"clicked": step.selector}
        
        elif step.action == "type":
            await page.fill(step.selector, step.value or "", timeout=10000)
            return {"typed": step.selector}
        
        elif step.action == "wait":
            if step.selector:
                await page.wait_for_selector(step.selector, timeout=step.wait_time or 10000)
            else:
                await page.wait_for_timeout(step.wait_time or 1000)
            return {"waited": True}
        
        elif step.action == "evaluate":
            result = await page.evaluate(step.value)
            return result
        
        elif step.action == "screenshot":
            screenshot = await page.screenshot(full_page=True)
            return {"screenshot": screenshot}
        
        else:
            raise ValueError(f"Unknown action: {step.action}")
    
    def get_task(self, task_id: str) -> Optional[AutomationTask]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    def list_tasks(self, project_id: Optional[str] = None) -> List[AutomationTask]:
        """List all tasks, optionally filtered by project."""
        tasks = list(self.tasks.values())
        if project_id:
            tasks = [t for t in tasks if t.project_id == project_id]
        return tasks


# Global service instance
automation_service = BrowserAutomationService(mock_mode=True)


async def get_automation_service() -> BrowserAutomationService:
    """Dependency injection for the automation service."""
    return automation_service