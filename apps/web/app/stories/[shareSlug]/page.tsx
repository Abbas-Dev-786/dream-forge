import { StoryStudio } from '@/components/story-studio';

type StoryPageProps = {
  params: Promise<{ shareSlug: string }>;
};

export default async function StorySharePage({ params }: StoryPageProps) {
  const { shareSlug } = await params;
  return <StoryStudio initialShareSlug={shareSlug} />;
}
