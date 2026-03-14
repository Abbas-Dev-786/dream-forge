import {
  CreateStoryPayload,
  SelectChoicePayload,
  StoryNodeResponse,
  StorySessionCreateResponse,
  StorySessionSummaryResponse,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

async function readJson<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const response = await fetch(input, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function createStorySession(payload: CreateStoryPayload) {
  return readJson<StorySessionCreateResponse>(
    `${API_BASE}/api/v1/story-sessions`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function selectChoice(storyId: string, payload: SelectChoicePayload) {
  return readJson<StorySessionCreateResponse>(
    `${API_BASE}/api/v1/story-sessions/${storyId}/choices`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function getStoryByShareSlug(shareSlug: string) {
  return readJson<StorySessionSummaryResponse>(
    `${API_BASE}/api/v1/story-sessions/by-share-slug/${shareSlug}`,
  );
}

export function getNode(storyId: string, nodeId: string) {
  return readJson<StoryNodeResponse>(
    `${API_BASE}/api/v1/story-sessions/${storyId}/nodes/${nodeId}`,
  );
}
