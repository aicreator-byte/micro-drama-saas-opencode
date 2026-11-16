import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, Token, Project, Character, Location, Episode, Scene, Shot, Prompt, GoogleAccount, FlowBridgeTask, FlowBridgeAsset } from '@/types';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
  updateUser: (user: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      setAuth: (user, token) => set({ user, token, isAuthenticated: true }),
      clearAuth: () => set({ user: null, token: null, isAuthenticated: false }),
      updateUser: (userData) => set((state) => ({ user: state.user ? { ...state.user, ...userData } : null })),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user, token: state.token, isAuthenticated: state.isAuthenticated }),
    }
  )
);

interface ProjectState {
  currentProject: Project | null;
  projects: Project[];
  setCurrentProject: (project: Project | null) => void;
  setProjects: (projects: Project[]) => void;
  addProject: (project: Project) => void;
  updateProject: (id: string, data: Partial<Project>) => void;
  removeProject: (id: string) => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  currentProject: null,
  projects: [],
  setCurrentProject: (project) => set({ currentProject: project }),
  setProjects: (projects) => set({ projects }),
  addProject: (project) => set((state) => ({ projects: [project, ...state.projects] })),
  updateProject: (id, data) => set((state) => ({
    projects: state.projects.map((p) => (p.id === id ? { ...p, ...data } : p)),
    currentProject: state.currentProject?.id === id ? { ...state.currentProject, ...data } : state.currentProject,
  })),
  removeProject: (id) => set((state) => ({
    projects: state.projects.filter((p) => p.id !== id),
    currentProject: state.currentProject?.id === id ? null : state.currentProject,
  })),
}));

interface CharacterState {
  characters: Character[];
  setCharacters: (characters: Character[]) => void;
  addCharacter: (character: Character) => void;
  updateCharacter: (id: string, data: Partial<Character>) => void;
  removeCharacter: (id: string) => void;
  clearCharacters: () => void;
}

export const useCharacterStore = create<CharacterState>((set) => ({
  characters: [],
  setCharacters: (characters) => set({ characters }),
  addCharacter: (character) => set((state) => ({ characters: [...state.characters, character] })),
  updateCharacter: (id, data) => set((state) => ({
    characters: state.characters.map((c) => (c.id === id ? { ...c, ...data } : c)),
  })),
  removeCharacter: (id) => set((state) => ({
    characters: state.characters.filter((c) => c.id !== id),
  })),
  clearCharacters: () => set({ characters: [] }),
}));

interface LocationState {
  locations: Location[];
  setLocations: (locations: Location[]) => void;
  addLocation: (location: Location) => void;
  updateLocation: (id: string, data: Partial<Location>) => void;
  removeLocation: (id: string) => void;
  clearLocations: () => void;
}

export const useLocationStore = create<LocationState>((set) => ({
  locations: [],
  setLocations: (locations) => set({ locations }),
  addLocation: (location) => set((state) => ({ locations: [...state.locations, location] })),
  updateLocation: (id, data) => set((state) => ({
    locations: state.locations.map((l) => (l.id === id ? { ...l, ...data } : l)),
  })),
  removeLocation: (id) => set((state) => ({
    locations: state.locations.filter((l) => l.id !== id),
  })),
  clearLocations: () => set({ locations: [] }),
}));

interface EpisodeState {
  episodes: Episode[];
  currentEpisode: Episode | null;
  scenes: Scene[];
  shots: Shot[];
  setEpisodes: (episodes: Episode[]) => void;
  addEpisode: (episode: Episode) => void;
  updateEpisode: (id: string, data: Partial<Episode>) => void;
  removeEpisode: (id: string) => void;
  setCurrentEpisode: (episode: Episode | null) => void;
  setScenes: (scenes: Scene[]) => void;
  addScene: (scene: Scene) => void;
  updateScene: (id: string, data: Partial<Scene>) => void;
  removeScene: (id: string) => void;
  setShots: (shots: Shot[]) => void;
  addShot: (shot: Shot) => void;
  updateShot: (id: string, data: Partial<Shot>) => void;
  removeShot: (id: string) => void;
  clearEpisodes: () => void;
}

export const useEpisodeStore = create<EpisodeState>((set) => ({
  episodes: [],
  currentEpisode: null,
  scenes: [],
  shots: [],
  setEpisodes: (episodes) => set({ episodes }),
  addEpisode: (episode) => set((state) => ({ episodes: [...state.episodes, episode] })),
  updateEpisode: (id, data) => set((state) => ({
    episodes: state.episodes.map((e) => (e.id === id ? { ...e, ...data } : e)),
    currentEpisode: state.currentEpisode?.id === id ? { ...state.currentEpisode, ...data } : state.currentEpisode,
  })),
  removeEpisode: (id) => set((state) => ({
    episodes: state.episodes.filter((e) => e.id !== id),
    currentEpisode: state.currentEpisode?.id === id ? null : state.currentEpisode,
  })),
  setCurrentEpisode: (episode) => set({ currentEpisode: episode }),
  setScenes: (scenes) => set({ scenes }),
  addScene: (scene) => set((state) => ({ scenes: [...state.scenes, scene] })),
  updateScene: (id, data) => set((state) => ({
    scenes: state.scenes.map((s) => (s.id === id ? { ...s, ...data } : s)),
  })),
  removeScene: (id) => set((state) => ({
    scenes: state.scenes.filter((s) => s.id !== id),
  })),
  setShots: (shots) => set({ shots }),
  addShot: (shot) => set((state) => ({ shots: [...state.shots, shot] })),
  updateShot: (id, data) => set((state) => ({
    shots: state.shots.map((s) => (s.id === id ? { ...s, ...data } : s)),
  })),
  removeShot: (id) => set((state) => ({
    shots: state.shots.filter((s) => s.id !== id),
  })),
  clearEpisodes: () => set({ episodes: [], currentEpisode: null, scenes: [], shots: [] }),
}));

interface PromptState {
  prompts: Prompt[];
  setPrompts: (prompts: Prompt[]) => void;
  addPrompt: (prompt: Prompt) => void;
  updatePrompt: (id: string, data: Partial<Prompt>) => void;
  removePrompt: (id: string) => void;
  clearPrompts: () => void;
}

export const usePromptStore = create<PromptState>((set) => ({
  prompts: [],
  setPrompts: (prompts) => set({ prompts }),
  addPrompt: (prompt) => set((state) => ({ prompts: [...state.prompts, prompt] })),
  updatePrompt: (id, data) => set((state) => ({
    prompts: state.prompts.map((p) => (p.id === id ? { ...p, ...data } : p)),
  })),
  removePrompt: (id) => set((state) => ({
    prompts: state.prompts.filter((p) => p.id !== id),
  })),
  clearPrompts: () => set({ prompts: [] }),
}));

interface GoogleAccountState {
  accounts: GoogleAccount[];
  setAccounts: (accounts: GoogleAccount[]) => void;
  addAccount: (account: GoogleAccount) => void;
  updateAccount: (id: string, data: Partial<GoogleAccount>) => void;
  removeAccount: (id: string) => void;
}

export const useGoogleAccountStore = create<GoogleAccountState>((set) => ({
  accounts: [],
  setAccounts: (accounts) => set({ accounts }),
  addAccount: (account) => set((state) => ({ accounts: [...state.accounts, account] })),
  updateAccount: (id, data) => set((state) => ({
    accounts: state.accounts.map((a) => (a.id === id ? { ...a, ...data } : a)),
  })),
  removeAccount: (id) => set((state) => ({
    accounts: state.accounts.filter((a) => a.id !== id),
  })),
}));

interface FlowBridgeState {
  tasks: FlowBridgeTask[];
  assets: FlowBridgeAsset[];
  setTasks: (tasks: FlowBridgeTask[]) => void;
  addTask: (task: FlowBridgeTask) => void;
  updateTask: (id: string, data: Partial<FlowBridgeTask>) => void;
  removeTask: (id: string) => void;
  setAssets: (assets: FlowBridgeAsset[]) => void;
  addAsset: (asset: FlowBridgeAsset) => void;
  updateAsset: (id: string, data: Partial<FlowBridgeAsset>) => void;
  removeAsset: (id: string) => void;
}

export const useFlowBridgeStore = create<FlowBridgeState>((set) => ({
  tasks: [],
  assets: [],
  setTasks: (tasks) => set({ tasks }),
  addTask: (task) => set((state) => ({ tasks: [...state.tasks, task] })),
  updateTask: (id, data) => set((state) => ({
    tasks: state.tasks.map((t) => (t.id === id ? { ...t, ...data } : t)),
  })),
  removeTask: (id) => set((state) => ({
    tasks: state.tasks.filter((t) => t.id !== id),
  })),
  setAssets: (assets) => set({ assets }),
  addAsset: (asset) => set((state) => ({ assets: [...state.assets, asset] })),
  updateAsset: (id, data) => set((state) => ({
    assets: state.assets.map((a) => (a.id === id ? { ...a, ...data } : a)),
  })),
  removeAsset: (id) => set((state) => ({
    assets: state.assets.filter((a) => a.id !== id),
  })),
}));

interface UIState {
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  activeTab: 'overview',
  setActiveTab: (tab) => set({ activeTab: tab }),
}));