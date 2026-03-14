'use client';

import { startTransition, useEffect, useState } from 'react';
import { createStorySession, getNode, getStoryByShareSlug, selectChoice } from '@/lib/api';
import { StorySessionCreateResponse, StorySessionSummaryResponse } from '@/lib/types';
import { StoryReader } from './story-reader';

type StoryStudioProps = {
  initialShareSlug?: string;
};

type FormState = {
  child_name: string;
  child_age: number;
  interests: string;
  theme: string;
  tone: 'gentle' | 'funny' | 'adventurous' | 'educational';
};

const defaultForm: FormState = {
  child_name: 'Maya',
  child_age: 8,
  interests: 'space, pandas',
  theme: 'space adventure',
  tone: 'gentle',
};

export function StoryStudio({ initialShareSlug }: StoryStudioProps) {
  const [form, setForm] = useState<FormState>(defaultForm);
  const [story, setStory] = useState<StorySessionCreateResponse | null>(null);
  const [summary, setSummary] = useState<StorySessionSummaryResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentNodeId = story?.node.node_id ?? summary?.current_node_id ?? null;
  const currentStoryId = story?.story_id ?? summary?.story_id ?? null;
  const currentShareSlug = story?.share_slug ?? summary?.share_slug ?? initialShareSlug ?? null;
  const hasPendingMedia = !!story?.node
    && (story.node.image.status !== 'ready' || story.node.audio.status !== 'ready');

  useEffect(() => {
    if (initialShareSlug) {
      void (async () => {
        setError(null);
        try {
          const nextSummary = await getStoryByShareSlug(initialShareSlug);
          const nextNode = await getNode(nextSummary.story_id, nextSummary.current_node_id);
          startTransition(() => {
            setSummary(nextSummary);
            setStory({ ...nextSummary, node: nextNode });
          });
        } catch (cause) {
          setError(cause instanceof Error ? cause.message : 'Unable to load story.');
        }
      })();
    }
  }, [initialShareSlug]);

  useEffect(() => {
    if (!hasPendingMedia || !currentStoryId || !currentNodeId) {
      return;
    }
    const timer = window.setInterval(() => {
      void (async () => {
        const nextNode = await getNode(currentStoryId, currentNodeId);
        startTransition(() => {
          setStory((previous) => {
            if (!previous) {
              return previous;
            }
            return { ...previous, node: nextNode };
          });
        });
      })();
    }, 2000);
    return () => window.clearInterval(timer);
  }, [currentNodeId, currentStoryId, hasPendingMedia]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await createStorySession({
        child_name: form.child_name,
        child_age: form.child_age,
        interests: form.interests.split(',').map((value) => value.trim()).filter(Boolean),
        theme: form.theme,
        tone: form.tone,
        language: 'en',
      });
      startTransition(() => {
        setStory(response);
        setSummary(response);
      });
      window.history.replaceState({}, '', `/stories/${response.share_slug}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'DreamForge could not create the story.');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleChoice(choiceId: string) {
    if (!story) {
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const response = await selectChoice(story.story_id, {
        node_id: story.node.node_id,
        choice_id: choiceId,
      });
      startTransition(() => {
        setStory(response);
        setSummary(response);
      });
      window.history.replaceState({}, '', `/stories/${response.share_slug}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'DreamForge could not continue the story.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen px-4 py-6 sm:px-6 lg:px-10">
      <div className="mx-auto grid max-w-[1480px] gap-8 xl:grid-cols-[420px_minmax(0,1fr)]">
        <section className="storybook-shell paper-grid rounded-[2rem] border border-white/55 bg-[var(--panel)] p-7 sm:p-8">
          <div className="space-y-8">
            <div>
              <p className="text-xs uppercase tracking-[0.34em] text-[var(--muted)]">DreamForge Demo</p>
              <h1 className="mt-4 font-[var(--font-display)] text-6xl leading-[0.9] text-[var(--ink)]">
                Build a child into the heart of the story.
              </h1>
              <p className="mt-5 max-w-md text-sm leading-7 text-[var(--muted)]">
                Generate a living storybook with branching choices, staged illustrations, and narration that appears as the media worker completes each asset.
              </p>
            </div>

            <form className="space-y-4" onSubmit={handleSubmit}>
              <Field label="Hero Name">
                <input
                  value={form.child_name}
                  onChange={(event) => setForm({ ...form, child_name: event.target.value })}
                  className="w-full rounded-2xl border border-[var(--line)] bg-white px-4 py-3 outline-none transition focus:border-[var(--brand)]"
                />
              </Field>

              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Age">
                  <input
                    type="number"
                    min={5}
                    max={14}
                    value={form.child_age}
                    onChange={(event) => setForm({ ...form, child_age: Number(event.target.value) })}
                    className="w-full rounded-2xl border border-[var(--line)] bg-white px-4 py-3 outline-none transition focus:border-[var(--brand)]"
                  />
                </Field>
                <Field label="Tone">
                  <select
                    value={form.tone}
                    onChange={(event) => setForm({ ...form, tone: event.target.value as FormState['tone'] })}
                    className="w-full rounded-2xl border border-[var(--line)] bg-white px-4 py-3 outline-none transition focus:border-[var(--brand)]"
                  >
                    <option value="gentle">Gentle</option>
                    <option value="funny">Funny</option>
                    <option value="adventurous">Adventurous</option>
                    <option value="educational">Educational</option>
                  </select>
                </Field>
              </div>

              <Field label="Interests">
                <input
                  value={form.interests}
                  onChange={(event) => setForm({ ...form, interests: event.target.value })}
                  placeholder="space, pandas"
                  className="w-full rounded-2xl border border-[var(--line)] bg-white px-4 py-3 outline-none transition focus:border-[var(--brand)]"
                />
              </Field>

              <Field label="Story Theme">
                <textarea
                  value={form.theme}
                  onChange={(event) => setForm({ ...form, theme: event.target.value })}
                  rows={4}
                  className="w-full rounded-[1.6rem] border border-[var(--line)] bg-white px-4 py-3 outline-none transition focus:border-[var(--brand)]"
                />
              </Field>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full rounded-full bg-[var(--brand)] px-6 py-4 text-sm font-semibold uppercase tracking-[0.22em] text-white transition hover:bg-[var(--brand-deep)] disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isSubmitting ? 'Forging story...' : 'Forge story'}
              </button>
            </form>

            {currentShareSlug ? (
              <div className="rounded-[1.4rem] border border-[var(--line)] bg-white/70 p-4 text-sm text-[var(--muted)]">
                <p className="text-xs uppercase tracking-[0.25em]">Share Link</p>
                <p className="mt-2 break-all font-medium text-[var(--ink)]">
                  {typeof window === 'undefined' ? `/stories/${currentShareSlug}` : `${window.location.origin}/stories/${currentShareSlug}`}
                </p>
              </div>
            ) : null}

            {error ? (
              <div className="rounded-[1.4rem] border border-[#d97b67] bg-[#fff0eb] p-4 text-sm text-[#8c2f1e]">
                {error}
              </div>
            ) : null}
          </div>
        </section>

        <div className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3 px-1">
            <div>
              <p className="text-xs uppercase tracking-[0.34em] text-[var(--muted)]">Storybook</p>
              <p className="mt-2 text-sm text-[var(--muted)]">
                Text appears first. Illustration and narration catch up as the worker finishes each asset.
              </p>
            </div>
            {summary ? (
              <div className="rounded-full border border-white/50 bg-white/55 px-4 py-2 text-xs uppercase tracking-[0.22em] text-[var(--muted)]">
                {summary.status}
              </div>
            ) : null}
          </div>

          <StoryReader node={story?.node ?? null} isSubmitting={isSubmitting} onChoice={handleChoice} />
        </div>
      </div>
    </main>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-2">
      <span className="text-xs uppercase tracking-[0.28em] text-[var(--muted)]">{label}</span>
      {children}
    </label>
  );
}
