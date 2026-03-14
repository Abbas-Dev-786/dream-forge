import Image from 'next/image';
import { StoryNodeResponse } from '@/lib/types';

type StoryReaderProps = {
  node: StoryNodeResponse | null;
  isSubmitting: boolean;
  onChoice: (choiceId: string) => void;
};

export function StoryReader({ node, isSubmitting, onChoice }: StoryReaderProps) {
  if (!node) {
    return (
      <section className="storybook-shell paper-grid rounded-[2rem] border border-white/50 bg-[var(--panel)] p-8">
        <div className="space-y-5">
          <div className="h-6 w-40 animate-pulse rounded-full bg-white/70" />
          <div className="h-[320px] animate-pulse rounded-[1.5rem] bg-white/60" />
          <div className="space-y-3">
            <div className="h-4 animate-pulse rounded-full bg-white/70" />
            <div className="h-4 animate-pulse rounded-full bg-white/60" />
            <div className="h-4 w-5/6 animate-pulse rounded-full bg-white/70" />
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="storybook-shell overflow-hidden rounded-[2rem] border border-white/50 bg-[var(--panel)]">
      <div className="grid gap-0 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="relative min-h-[320px] border-b border-[var(--line)] bg-[#fff4db] lg:min-h-[560px] lg:border-b-0 lg:border-r">
          {node.image.url ? (
            <Image
              src={node.image.url}
              alt={node.title}
              fill
              className="object-cover"
              sizes="(max-width: 1024px) 100vw, 50vw"
            />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-4 bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.92),_rgba(240,193,119,0.8))] p-8 text-center">
              <div className="h-24 w-24 animate-float rounded-full border border-white/80 bg-white/50" />
              <div>
                <p className="font-[var(--font-display)] text-4xl text-[var(--ink)]">Illustration loading</p>
                <p className="mt-2 text-sm uppercase tracking-[0.28em] text-[var(--muted)]">
                  {node.image.status}
                </p>
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-6 p-7 sm:p-9">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-[var(--muted)]">Current Page</p>
            <h2 className="mt-3 font-[var(--font-display)] text-5xl leading-none text-[var(--ink)]">
              {node.title}
            </h2>
            <p className="mt-4 text-sm leading-7 text-[var(--muted)]">{node.scene_summary}</p>
          </div>

          <div className="rounded-[1.4rem] border border-[var(--line)] bg-[var(--card)]/85 p-6 text-[15px] leading-8 text-[var(--ink)]">
            {node.story_text}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {node.audio.url ? (
              <audio controls className="w-full lg:w-[340px]">
                <source src={node.audio.url} />
              </audio>
            ) : (
              <button
                disabled
                className="rounded-full border border-[var(--line)] bg-white/70 px-5 py-3 text-sm text-[var(--muted)]"
              >
                Narration {node.audio.status}
              </button>
            )}
          </div>

          <div className="space-y-3">
            <p className="text-xs uppercase tracking-[0.3em] text-[var(--muted)]">Choose What Happens Next</p>
            {node.is_terminal ? (
              <div className="rounded-[1.2rem] border border-[var(--line)] bg-white/70 p-4 text-sm text-[var(--muted)]">
                This branch has reached its ending.
              </div>
            ) : (
              <div className="grid gap-3">
                {node.choices.map((choice) => (
                  <button
                    key={choice.choice_id}
                    type="button"
                    onClick={() => onChoice(choice.choice_id)}
                    disabled={isSubmitting}
                    className="rounded-[1.2rem] border border-[var(--line)] bg-white px-5 py-4 text-left text-sm font-medium text-[var(--ink)] transition hover:-translate-y-0.5 hover:border-[var(--brand)] hover:shadow-panel disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {choice.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
