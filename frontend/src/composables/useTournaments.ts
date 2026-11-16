import { useAuth } from './useAuth'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export type TournamentStatus = 'draft' | 'open' | 'ongoing' | 'finished'

export interface Tournament {
  id: number
  name: string
  description: string | null
  status: TournamentStatus
  max_participants: number | null
  start_date: string | null
  end_date: string | null
  association_id: number
  winner_id?: number | null
  created_at: string
  updated_at: string
}

export interface TournamentParticipant {
  tournament_id: number
  user_id: number
  registered_at: string
  user: {
    id: number
    username: string
    full_name: string | null
  }
}

export interface TournamentBracketPlayer {
  id: number | null
  name: string
  score: number | null
  status: 'winner' | 'loser' | 'pending'
}

export interface TournamentBracketMatch {
  id: number
  round: string
  round_number: number
  match_order: number
  players: [TournamentBracketPlayer, TournamentBracketPlayer]
  winner_id: number | null
  status: 'winner' | 'loser' | 'pending'
  next_match_id: number | null
}

export interface TournamentStartResponse {
  message: string
  tournament_id: number
  status: TournamentStatus
  total_participants: number
  total_matches: number
  bracket: TournamentBracketMatch[]
}

export interface TournamentWebSocketMessage {
  type: 'initial_bracket' | 'bracket_updated' | string
  tournament_id: number
  status: TournamentStatus
  winner_id: number | null
  bracket: TournamentBracketMatch[]
}

export interface TournamentDetail extends Tournament {
  association: {
    id: number
    name: string
    description: string | null
  }
  participants: TournamentParticipant[]
  bracket?: TournamentBracketMatch[]
  total_participants?: number
  total_matches?: number
  message?: string
}

export interface AssociationSummary {
  id: number
  name: string
  description: string | null
}

export interface TournamentCreateInput {
  name: string
  description?: string | null
  status?: TournamentStatus
  max_participants?: number | null
  start_date?: string | null
  end_date?: string | null
  association_id: number
}

export function getTournamentWebSocketUrl(id: number): string {
  const wsBaseUrl = API_BASE_URL.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:')
  return `${wsBaseUrl}/tournaments/${id}/ws`
}

export function connectTournamentWebSocket(
  id: number,
  onMessage: (data: TournamentWebSocketMessage) => void,
): WebSocket {
  const url = getTournamentWebSocketUrl(id)
  const socket = new WebSocket(url)

  socket.onmessage = (event: MessageEvent<string>) => {
    try {
      const data = JSON.parse(event.data) as TournamentWebSocketMessage
      onMessage(data)
    } catch {
      // Ignore unparseable frames
    }
  }

  return socket
}

export function useTournaments() {
  const { fetchWithAuth } = useAuth()

  async function fetchVisibleTournaments(): Promise<Tournament[]> {
    return fetchWithAuth<Tournament[]>('/tournaments')
  }

  async function fetchTournament(id: number): Promise<TournamentDetail> {
    return fetchWithAuth<TournamentDetail>(`/tournaments/${id}`)
  }

  async function fetchTournamentBracket(id: number): Promise<TournamentBracketMatch[]> {
    return fetchWithAuth<TournamentBracketMatch[]>(`/tournaments/${id}/bracket`)
  }

  async function joinTournament(id: number): Promise<TournamentParticipant> {
    return fetchWithAuth<TournamentParticipant>(`/tournaments/${id}/participants`, {
      method: 'POST',
    })
  }

  async function leaveTournament(id: number): Promise<void> {
    await fetchWithAuth(`/tournaments/${id}/participants/me`, {
      method: 'DELETE',
    })
  }

  async function startTournament(id: number): Promise<TournamentStartResponse> {
    return fetchWithAuth<TournamentStartResponse>(`/tournaments/${id}/start`, {
      method: 'POST',
    })
  }

  async function reportScore(
    tournamentId: number,
    matchId: number,
    scorePlayer1: number,
    scorePlayer2: number,
  ): Promise<{ message: string }> {
    return fetchWithAuth<{ message: string }>(
      `/tournaments/${tournamentId}/matches/${matchId}/score`,
      {
        method: 'PATCH',
        body: {
          score_player1: scorePlayer1,
          score_player2: scorePlayer2,
        },
      },
    )
  }

  async function declareForfeit(
    tournamentId: number,
    matchId: number,
    forfeitingUserId?: number,
  ): Promise<{ message: string }> {
    return fetchWithAuth<{ message: string }>(
      `/tournaments/${tournamentId}/matches/${matchId}/forfeit`,
      {
        method: 'POST',
        body: forfeitingUserId ? { forfeiting_user_id: forfeitingUserId } : {},
      },
    )
  }

  async function fetchAssociations(): Promise<AssociationSummary[]> {
    return fetchWithAuth<AssociationSummary[]>('/associations')
  }

  async function createTournament(input: TournamentCreateInput): Promise<Tournament> {
    return fetchWithAuth<Tournament>('/tournaments', {
      method: 'POST',
      body: input,
    })
  }

  return {
    fetchVisibleTournaments,
    fetchTournament,
    fetchTournamentBracket,
    fetchAssociations,
    createTournament,
    joinTournament,
    leaveTournament,
    startTournament,
    reportScore,
    declareForfeit,
    connectTournamentWebSocket,
  }
}
