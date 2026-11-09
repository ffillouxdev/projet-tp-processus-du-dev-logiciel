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
        Authorization: `Bearer ${accessToken.value}`,
      },
    })
  }

  return {
    fetchVisibleTournaments,
  }
}
