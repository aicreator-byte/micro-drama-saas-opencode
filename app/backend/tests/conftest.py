import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Config now reads the leg-root .env from any CWD; that .env ships a
# postgresql+asyncpg DATABASE_URL, but asyncpg is not installed here.
# Pin sqlite before the app is imported so test collection never touches
# the real DATABASE_URL (the test engine is in-memory regardless).
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User
from app.models.project import Project
from app.models.character import Character
from app.models.location import Location
from app.models.episode import Episode, Scene, Shot
from app.models.series_bible import SeriesBible
from app.models.prompt import Prompt
from app.models.google_account import GoogleAccount
from app.models.flow_bridge import FlowBridgeTask, FlowBridgeAsset
from app.models.audit_log import AuditLog


# Use in-memory SQLite for testing - create fresh engine per test
def create_test_engine():
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_test_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user2(db_session):
    user = User(
        email="test2@example.com",
        hashed_password=get_password_hash("testpassword123"),
        full_name="Test User 2",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(client, test_user):
    response = await client.post("/api/v1/auth/login", data={
        "username": "test@example.com",
        "password": "testpassword123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def auth_headers2(client, test_user2):
    response = await client.post("/api/v1/auth/login", data={
        "username": "test2@example.com",
        "password": "testpassword123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def test_project(db_session, test_user):
    project = Project(
        owner_id=test_user.id,
        title="Test Project",
        description="A test project",
        genre="Drama",
        themes="['family', 'betrayal']",
        status="draft",
        total_episodes=20,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_project2(db_session, test_user2):
    project = Project(
        owner_id=test_user2.id,
        title="Test Project 2",
        description="Another test project",
        genre="Comedy",
        themes="['friendship', 'humor']",
        status="in_progress",
        total_episodes=10,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_series_bible(db_session, test_project):
    sb = SeriesBible(
        project_id=test_project.id,
        premise="A family drama about betrayal and redemption",
        main_plot="The siblings fight for control of the family company while uncovering their father's secrets",
        subplots='["Romantic subplot", "Business rivalry"]',
        character_relationships='{"John": "rival with Jane", "Michael": "ally to John"}',
        world_settings="Modern day New York, corporate world",
        tone_and_visual_style="Cinematic, muted colors, intimate closeups",
        ending_direction="Bittersweet resolution with family unity",
        episode_structure='["Ep 1: Funeral", "Ep 2: Will reading", "Ep 3-20: Business battles"]',
    )
    db_session.add(sb)
    await db_session.commit()
    await db_session.refresh(sb)
    return sb


@pytest_asyncio.fixture
async def test_character(db_session, test_project):
    char = Character(
        project_id=test_project.id,
        name="John Doe",
        role="protagonist",
        age="40",
        gender="Male",
        ethnicity="Caucasian",
        height="6'0\"",
        build="Athletic",
        hair_color="Dark brown",
        hair_style="Short, professional",
        eye_color="Brown",
        skin_tone="Fair",
        distinguishing_features="Small scar above left eyebrow",
        personality_traits='["Responsible", "Protective", "Secretly vulnerable"]',
        background="Left home at 18, returned after father's death",
        motivations="Save the family business, prove himself to siblings",
        fears="Failure, losing his siblings' respect",
        quirks='["Taps fingers when thinking", "Always straightens tie"]',
        costume_style="Business formal, dark suits",
        signature_items='["Father\'s watch", "Cufflinks"]',
        color_palette='["Navy", "Charcoal", "White"]',
        consistency_instructions="Always wear the watch on left wrist",
    )
    db_session.add(char)
    await db_session.commit()
    await db_session.refresh(char)
    return char


@pytest_asyncio.fixture
async def test_location(db_session, test_project):
    loc = Location(
        project_id=test_project.id,
        name="Family Mansion",
        type="exterior",
        description="Grand but aging family estate in the Hamptons",
        environment_details='{"architecture": "Victorian", "gardens": "overgrown", "interior": "dusty chandeliers"}',
        visual_style_notes="Melancholic grandeur, muted lighting",
        lighting='{"key_light": "soft natural", "mood": "somber"}',
        atmosphere="Melancholic grandeur",
        time_of_day="Afternoon",
        weather="Overcast",
        consistency_instructions="Always show the mansion from the same angle",
    )
    db_session.add(loc)
    await db_session.commit()
    await db_session.refresh(loc)
    return loc


@pytest_asyncio.fixture
async def test_episode(db_session, test_project):
    from app.models.episode import EpisodeStatus
    ep = Episode(
        project_id=test_project.id,
        episode_number=1,
        title="The Return",
        summary="Eldest son returns home for father's funeral",
        status=EpisodeStatus.OUTLINED,
    )
    db_session.add(ep)
    await db_session.commit()
    await db_session.refresh(ep)
    return ep


@pytest_asyncio.fixture
async def test_scene(db_session, test_episode, test_location):
    from app.models.episode import SceneStatus
    scene = Scene(
        episode_id=test_episode.id,
        scene_number=1,
        title="Funeral Scene",
        description="Family gathers at the funeral",
        location_id=test_location.id,
        time_of_day="Afternoon",
        duration_estimate=300,
        status=SceneStatus.PLANNED,
        characters_present='["John"]',
    )
    db_session.add(scene)
    await db_session.commit()
    await db_session.refresh(scene)
    return scene


@pytest_asyncio.fixture
async def test_prompt(db_session, test_project):
    from app.models.prompt import PromptType, PromptStatus
    prompt = Prompt(
        project_id=test_project.id,
        prompt_type=PromptType.CHARACTER_IMAGE,
        title="Character Introduction Prompt",
        prompt_text="Write an introduction for {character_name} that shows their {personality_trait}",
        negative_prompt="",
        parameters='{"model": "test", "steps": 20}',
        status=PromptStatus.DRAFT,
        created_by=None
    )
    db_session.add(prompt)
    await db_session.commit()
    await db_session.refresh(prompt)
    return prompt


@pytest_asyncio.fixture
async def test_settings_with_mock(db_session):
    """Create AppSettings with mock AI provider for testing."""
    from app.models.settings import AppSettings
    settings = AppSettings(
        ai_providers=[
            {
                "id": "mock-provider",
                "provider": "mock",
                "model": "mock-model",
                "key_env": "MOCK_API_KEY",
                "enabled": True,
                "priority": 1,
            }
        ]
    )
    db_session.add(settings)
    await db_session.commit()
    await db_session.refresh(settings)
    return settings