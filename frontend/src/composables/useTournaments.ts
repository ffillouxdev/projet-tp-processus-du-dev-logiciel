import { $fetch } from 'ofetch'
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

const api = $fetch.create({
  baseURL: API_BASE_URL,
})

export function useTournaments() {
  const { accessToken } = useAuth()

  async function fetchVisibleTournaments(): Promise<Tournament[]> {
    if (!accessToken.value) {
      throw new Error('Vous devez être connecté pour consulter vos tournois.')
    }

    return api<Tournament[]>('/tournaments', {
      headers: {
        Authorization: 'Bearer ' + accessToken.value,
      },
    })
  }

  async function fetchTournament(id: number): Promise<TournamentDetail> {
    if (!accessToken.value) {
      throw new Error('Vous devez être connecté pour consulter ce tournoi.')
    }

    return api<TournamentDetail>(`/tournaments/${id}`, {
      headers: {
        Authorization: 'Bearer ' + accessToken.value,
      },
    })
  }

  async function fetchTournamentBracket(id: number): Promise<TournamentBracketMatch[]> {
    if (!accessToken.value) {
      throw new Error('Vous devez être connecté pour consulter le bracket de ce tournoi.')
    }

    return api<TournamentBracketMatch[]>(`/tournaments/${id}/bracket`, {
      headers: {
        Authorization: 'Bearer ' + accessToken.value,
      },
    })
  }

  async function joinTournament(id: number): Promise<TournamentParticipant> {
    if (!accessToken.value) {
      throw new Error('Vous devez être connecté pour rejoindre ce tournoi.')
    }

    return api<TournamentParticipant>(`/tournaments/${id}/participants`, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer ' + accessToken.value,
      },
    })
  }

  async function leaveTournament(id: number): Promise<void> {
    if (!accessToken.value) {
      throw new Error('Vous devez être connecté pour quitter ce tournoi.')
    }

    await api(`/tournaments/${id}/participants/me`, {
      method: 'DELETE',
      headers: {
        Authorization: 'Bearer ' + accessToken.value,
      },
    })
  }

  async function startTournament(id: number): Promise<TournamentStartResponse> {
    if (!accessToken.value) {
      throw new Error('Vous devez être connecté pour lancer ce tournoi.')
    }

    return api<TournamentStartResponse>(`/tournaments/${id}/start`, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer ' + accessToken.value,
      },
    })
  }

  return {
    fetchVisibleTournaments,
    fetchTournament,
    fetchTournamentBracket,
    joinTournament,
    leaveTournament,
    startTournament,
  }
}
