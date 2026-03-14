export type Tone = 'gentle' | 'funny' | 'adventurous' | 'educational';

export type StoryChoicePayload = {
  choice_id: string;
  label: string;
};

export type AssetState = {
  status: 'pending' | 'processing' | 'ready' | 'failed';
  url: string | null;
};

export type StoryNodeResponse = {
  node_id: string;
  title: string;
  scene_summary: string;
  story_text: string;
  narration_text: string;
  image: AssetState;
  audio: AssetState;
  choices: StoryChoicePayload[];
  is_terminal: boolean;
};

export type StorySessionSummaryResponse = {
  story_id: string;
  share_slug: string;
  status: string;
  current_node_id: string;
  expires_at: string;
};

export type StorySessionCreateResponse = StorySessionSummaryResponse & {
  node: StoryNodeResponse;
};

export type CreateStoryPayload = {
  child_name: string;
  child_age: number;
  interests: string[];
  theme: string;
  tone: Tone;
  language: 'en';
};

export type SelectChoicePayload = {
  node_id: string;
  choice_id: string;
};
