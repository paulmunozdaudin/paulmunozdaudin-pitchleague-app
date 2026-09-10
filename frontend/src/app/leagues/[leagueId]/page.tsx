import { redirect } from "next/navigation";

export default async function LeagueIndexPage({ params }: { params: Promise<{ leagueId: string }> }) {
  const { leagueId } = await params;
  redirect(`/leagues/${leagueId}/gameweek`);
}
